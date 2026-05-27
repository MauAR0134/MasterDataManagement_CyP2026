"""Preprocesamiento clinico de Clinico_Observation.

Procesos implementados:
  - Deteccion de duplicados exactos y por id_lab con contenido distinto
  - Deteccion de valores nulos por columna del panel
  - Validacion y conversion numerica de todas las variables clinicas
  - Separacion de presion_arterial en presion_sistolica / presion_diastolica
  - Calculo de IMC (peso_kg / (altura_cm/100)^2)
  - Clasificacion descriptiva de rangos biologicos por variable
  - Perfilado de outliers IQR por variable numerica
  - Bandera panel_laboratorio_completo (sin imputacion)

Salidas:
  06_relational_model/Clinico_Observation_preprocessed.csv  -- tabla enriquecida
  03_profiling/clinico_resumen_calidad.csv                  -- estadisticos + outliers por variable
  manual_review/clinico_duplicados.csv                      -- registros duplicados
  manual_review/clinico_outliers_biologicos.csv             -- filas outlier por variable
"""

from __future__ import annotations

from collections import Counter
from statistics import median

import mdm_config as cfg
from mdm_utils import read_rows, write_rows


# Variables del panel de laboratorio: ausencia indica consulta sin estudios completos,
# no debe imputarse.
PANEL_COLS = ["glucosa", "colesterol_LDL", "colesterol_HDL", "trigliceridos", "hemoglobina"]

# Variables numericas directas (excluye presion_arterial que requiere separacion)
NUMERIC_COLS = [
    "edad",
    "glucosa",
    "colesterol_LDL",
    "colesterol_HDL",
    "trigliceridos",
    "hemoglobina",
    "frecuencia_card",
    "peso_kg",
    "altura_cm",
    "oxigenacion",
]

# Rangos biologicos de referencia para clasificacion descriptiva.
# Formato: lista de (limite_inferior_inclusive, limite_superior_exclusivo, etiqueta)
# Referencia: valores tipicos usados en datos sinteticos de clinica hospitalaria.
# colesterol_HDL y hemoglobina tienen cortes dependientes de sexo; aqui se usa
# una escala simplificada; ver columna sexo para analisis estratificado posterior.
RANGOS: dict[str, list[tuple[float, float, str]]] = {
    "glucosa": [
        (0, 70, "hipoglucemia"),
        (70, 100, "normal"),
        (100, 126, "prediabetes"),
        (126, float("inf"), "diabetes"),
    ],
    "colesterol_LDL": [
        (0, 100, "optimo"),
        (100, 130, "casi_optimo"),
        (130, 160, "borderline_alto"),
        (160, 190, "alto"),
        (190, float("inf"), "muy_alto"),
    ],
    "colesterol_HDL": [
        (0, 40, "bajo"),
        (40, 60, "normal"),
        (60, float("inf"), "protector"),
    ],
    "trigliceridos": [
        (0, 150, "normal"),
        (150, 200, "borderline"),
        (200, 500, "alto"),
        (500, float("inf"), "muy_alto"),
    ],
    "hemoglobina": [
        (0, 12, "anemia"),
        (12, 17.5, "normal"),
        (17.5, float("inf"), "policitemia"),
    ],
    "frecuencia_card": [
        (0, 60, "bradicardia"),
        (60, 101, "normal"),
        (101, float("inf"), "taquicardia"),
    ],
    "presion_sistolica": [
        (0, 120, "normal"),
        (120, 130, "elevada"),
        (130, 140, "hta_estadio_1"),
        (140, 180, "hta_estadio_2"),
        (180, float("inf"), "crisis_hipertensiva"),
    ],
    "presion_diastolica": [
        (0, 80, "normal"),
        (80, 90, "hta_estadio_1"),
        (90, 120, "hta_estadio_2"),
        (120, float("inf"), "crisis_hipertensiva"),
    ],
    "imc": [
        (0, 18.5, "bajo_peso"),
        (18.5, 25.0, "normal"),
        (25.0, 30.0, "sobrepeso"),
        (30.0, 35.0, "obesidad_1"),
        (35.0, 40.0, "obesidad_2"),
        (40.0, float("inf"), "obesidad_3"),
    ],
    "oxigenacion": [
        (0, 90, "hipoxia"),
        (90, 95, "borderline"),
        (95, float("inf"), "normal"),
    ],
}


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def to_float(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except (ValueError, AttributeError):
        return None


def classify_range(value: float, breakpoints: list[tuple[float, float, str]]) -> str:
    for low, high, label in breakpoints:
        if low <= value < high:
            return label
    return "fuera_de_rango"


def parse_presion(value: object) -> tuple[float | None, float | None]:
    """Divide '120/80' en (sistolica, diastolica). Devuelve (None, None) si formato invalido."""
    parts = str(value or "").strip().split("/")
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None, None


# ---------------------------------------------------------------------------
# Deteccion de duplicados
# ---------------------------------------------------------------------------

def detect_duplicates(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    report: list[dict[str, object]] = []

    # Duplicados exactos (todas las columnas identicas)
    exact_groups: dict[tuple[str, ...], list[int]] = {}
    for idx, row in enumerate(rows):
        key = tuple(row.values())
        exact_groups.setdefault(key, []).append(idx)
    for indices in exact_groups.values():
        if len(indices) > 1:
            for idx in indices[1:]:
                report.append({
                    "tipo": "duplicado_exacto",
                    "id_lab": rows[idx].get("id_lab", ""),
                    "id_master": rows[idx].get("id_master", ""),
                    "id_consulta": rows[idx].get("id_consulta", ""),
                    "cantidad_en_grupo": len(indices),
                    "detalle": "fila identica a otro registro del dataset",
                })

    # id_lab repetido con contenido distinto
    id_groups: dict[str, list[int]] = {}
    for idx, row in enumerate(rows):
        id_groups.setdefault(row.get("id_lab", ""), []).append(idx)
    for id_lab, indices in id_groups.items():
        if len(indices) < 2 or not id_lab:
            continue
        unique_content = {tuple(rows[i].values()) for i in indices}
        if len(unique_content) > 1:
            report.append({
                "tipo": "id_lab_repetido_contenido_distinto",
                "id_lab": id_lab,
                "id_master": " | ".join(rows[i].get("id_master", "") for i in indices),
                "id_consulta": " | ".join(rows[i].get("id_consulta", "") for i in indices),
                "cantidad_en_grupo": len(indices),
                "detalle": "mismo id_lab asociado a datos diferentes",
            })

    return report


# ---------------------------------------------------------------------------
# Perfilado IQR por variable numerica
# ---------------------------------------------------------------------------

def profile_numeric_col(
    rows: list[dict[str, str]], col: str
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Calcula estadisticos descriptivos y detecta outliers IQR para una columna."""
    valid: list[tuple[dict[str, str], float]] = []
    nulls = non_numeric = 0
    for row in rows:
        raw = str(row.get(col, "")).strip()
        if not raw:
            nulls += 1
            continue
        val = to_float(raw)
        if val is None:
            non_numeric += 1
        else:
            valid.append((row, val))

    amounts = [v for _, v in valid]
    q1 = percentile(amounts, 0.25) if amounts else 0.0
    q3 = percentile(amounts, 0.75) if amounts else 0.0
    iqr = q3 - q1
    lower_limit = q1 - 1.5 * iqr
    upper_limit = q3 + 1.5 * iqr

    outliers = [
        {
            "variable": col,
            "id_lab": row.get("id_lab", ""),
            "id_master": row.get("id_master", ""),
            "id_consulta": row.get("id_consulta", ""),
            "valor": val,
            "q1": round(q1, 3),
            "q3": round(q3, 3),
            "iqr_lower": round(lower_limit, 3),
            "iqr_upper": round(upper_limit, 3),
            "flag": "OUTLIER_IQR",
        }
        for row, val in valid
        if val < lower_limit or val > upper_limit
    ]

    summary = {
        "variable": col,
        "total_registros": len(rows),
        "nulos_o_vacios": nulls,
        "no_numericos": non_numeric,
        "completitud_pct": round(len(amounts) / len(rows) * 100, 2) if rows else 0,
        "minimo": round(min(amounts), 3) if amounts else "",
        "q1": round(q1, 3) if amounts else "",
        "mediana": round(median(amounts), 3) if amounts else "",
        "q3": round(q3, 3) if amounts else "",
        "maximo": round(max(amounts), 3) if amounts else "",
        "iqr_lower": round(lower_limit, 3) if amounts else "",
        "iqr_upper": round(upper_limit, 3) if amounts else "",
        "outliers_iqr": len(outliers),
    }
    return summary, outliers


def profile_fumador(rows: list[dict[str, str]]) -> dict[str, object]:
    """Perfila la variable categorica fumador (0/1) sin outliers IQR."""
    counter: Counter[str] = Counter()
    nulls = 0
    for row in rows:
        val = str(row.get("fumador", "")).strip()
        if not val:
            nulls += 1
        else:
            counter[val] += 1
    return {
        "variable": "fumador",
        "total_registros": len(rows),
        "nulos_o_vacios": nulls,
        "no_numericos": 0,
        "completitud_pct": round((len(rows) - nulls) / len(rows) * 100, 2) if rows else 0,
        "minimo": "",
        "q1": "",
        "mediana": "",
        "q3": "",
        "maximo": "",
        "iqr_lower": "",
        "iqr_upper": "",
        "outliers_iqr": f"categorica: {dict(counter)}",
    }


# ---------------------------------------------------------------------------
# Enriquecimiento de filas
# ---------------------------------------------------------------------------

def enrich_row(row: dict[str, str]) -> dict[str, object]:
    out: dict[str, object] = dict(row)

    # Separacion y clasificacion presion arterial
    sis, dia = parse_presion(row.get("presion_arterial", ""))
    out["presion_sistolica"] = round(sis, 1) if sis is not None else ""
    out["presion_diastolica"] = round(dia, 1) if dia is not None else ""
    out["presion_arterial_formato_valido"] = "1" if sis is not None else "0"
    out["presion_sistolica_rango"] = (
        classify_range(sis, RANGOS["presion_sistolica"]) if sis is not None else ""
    )
    out["presion_diastolica_rango"] = (
        classify_range(dia, RANGOS["presion_diastolica"]) if dia is not None else ""
    )

    # IMC
    peso = to_float(row.get("peso_kg", ""))
    altura = to_float(row.get("altura_cm", ""))
    if peso and altura and altura > 0:
        imc = peso / ((altura / 100) ** 2)
        out["imc"] = round(imc, 2)
        out["imc_categoria"] = classify_range(imc, RANGOS["imc"])
    else:
        out["imc"] = ""
        out["imc_categoria"] = ""

    # Clasificacion de rangos para variables del panel y signos vitales
    for col in ["glucosa", "colesterol_LDL", "colesterol_HDL", "trigliceridos",
                "hemoglobina", "frecuencia_card", "oxigenacion"]:
        val = to_float(row.get(col, ""))
        out[f"{col}_rango"] = classify_range(val, RANGOS[col]) if val is not None else ""

    # Bandera panel completo: 1 si todos los campos del panel tienen valor, 0 si alguno falta.
    # Los valores faltantes no se imputan; esta bandera solo informa completitud.
    out["panel_laboratorio_completo"] = (
        "1" if all(str(row.get(c, "")).strip() for c in PANEL_COLS) else "0"
    )

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    source = cfg.RELATIONAL_DIR / "Clinico_Observation.csv"
    rows = read_rows(source)
    print(f"  Clinico_Observation: {len(rows)} registros cargados.")

    # --- 1. DUPLICADOS ---
    dup_report = detect_duplicates(rows)
    write_rows(
        cfg.MANUAL_REVIEW_DIR / "clinico_duplicados.csv",
        dup_report,
        ["tipo", "id_lab", "id_master", "id_consulta", "cantidad_en_grupo", "detalle"],
    )
    print(f"  Duplicados detectados: {len(dup_report)} registros en reporte.")

    # --- 2. PERFILADO IQR ---
    # Agrega filas con presion separada para perfilar sistolica/diastolica
    rows_con_presion = []
    for row in rows:
        sis, dia = parse_presion(row.get("presion_arterial", ""))
        extended = dict(row)
        extended["presion_sistolica"] = str(sis) if sis is not None else ""
        extended["presion_diastolica"] = str(dia) if dia is not None else ""
        rows_con_presion.append(extended)

    profile_cols_numericas = NUMERIC_COLS + ["presion_sistolica", "presion_diastolica"]
    all_summaries: list[dict[str, object]] = []
    all_outliers: list[dict[str, object]] = []

    for col in profile_cols_numericas:
        source_rows = rows_con_presion if col in ("presion_sistolica", "presion_diastolica") else rows
        summary, outliers = profile_numeric_col(source_rows, col)
        all_summaries.append(summary)
        all_outliers.extend(outliers)

    all_summaries.append(profile_fumador(rows))

    write_rows(
        cfg.PROFILING_DIR / "clinico_resumen_calidad.csv",
        all_summaries,
        [
            "variable", "total_registros", "nulos_o_vacios", "no_numericos",
            "completitud_pct", "minimo", "q1", "mediana", "q3", "maximo",
            "iqr_lower", "iqr_upper", "outliers_iqr",
        ],
    )
    write_rows(
        cfg.MANUAL_REVIEW_DIR / "clinico_outliers_biologicos.csv",
        all_outliers,
        ["variable", "id_lab", "id_master", "id_consulta", "valor",
         "q1", "q3", "iqr_lower", "iqr_upper", "flag"],
    )
    print(
        f"  Outliers IQR: {len(all_outliers)} filas en "
        f"{len(profile_cols_numericas)} variables numericas."
    )

    # --- 3. NULOS POR COLUMNA DEL PANEL ---
    for col in PANEL_COLS:
        nulos = sum(1 for r in rows if not str(r.get(col, "")).strip())
        pct = round(nulos / len(rows) * 100, 1) if rows else 0
        print(f"    {col}: {nulos} nulos ({pct}%)  -- no se imputan")

    # --- 4. ENRIQUECIMIENTO ---
    enriched = [enrich_row(row) for row in rows]

    base_cols = list(rows[0].keys())
    new_cols = [
        "presion_sistolica",
        "presion_diastolica",
        "presion_arterial_formato_valido",
        "presion_sistolica_rango",
        "presion_diastolica_rango",
        "imc",
        "imc_categoria",
        "glucosa_rango",
        "colesterol_LDL_rango",
        "colesterol_HDL_rango",
        "trigliceridos_rango",
        "hemoglobina_rango",
        "frecuencia_card_rango",
        "oxigenacion_rango",
        "panel_laboratorio_completo",
    ]
    write_rows(
        cfg.RELATIONAL_DIR / "Clinico_Observation_preprocessed.csv",
        enriched,
        base_cols + new_cols,
    )

    completos = sum(1 for r in enriched if r.get("panel_laboratorio_completo") == "1")
    pct_panel = round(completos / len(enriched) * 100, 1) if enriched else 0
    print(
        f"  Clinico_Observation_preprocessed.csv: {len(enriched)} registros, "
        f"{len(base_cols + new_cols)} columnas."
    )
    print(f"  Panel laboratorio completo: {completos}/{len(enriched)} ({pct_panel}%)")


if __name__ == "__main__":
    main()
