"""
Perfilado de calidad de datos para los archivos raw del proyecto.

Este modulo no modifica los datos. Lee los CSV de "02_Datos_Crudos", calcula
hallazgos de calidad y escribe reportes en la carpeta "03_Perfilado/reportes".
Tambien expone funciones pequenas para usarse desde el notebook.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "02_Datos_Crudos"
PROFILE_DIR = BASE_DIR / "03_Perfilado"
REPORT_DIR = PROFILE_DIR / "reportes"

SYSTEMS = ("transacciones", "clinica", "prescripciones")
SITES = ("mexico", "estados_unidos", "espana")
YEARS = (2023, 2024, 2025)

EXPECTED_COLUMNS = {
    "transacciones": [
        "id_transaccion",
        "fecha",
        "nombre_paciente",
        "tipo_consulta",
        "medico_cargo",
        "telefono_contacto",
        "correo_electronico",
        "direccion",
        "monto_cobro",
        "metodo_pago",
        "registro_previo",
        "fecha_primer_registro",
    ],
    "clinica": [
        "id_lab",
        "nombre_completo",
        "sexo",
        "fecha_nacimiento",
        "edad",
        "glucosa",
        "colesterol_LDL",
        "colesterol_HDL",
        "trigliceridos",
        "hemoglobina",
        "frecuencia_card",
        "presion_arterial",
        "peso_kg",
        "altura_cm",
        "tipo_sangre",
        "fumador",
        "oxigenacion",
        "fecha_estudios",
    ],
    "prescripciones": [
        "id_farmacia",
        "nombre_completo",
        "medicamentos_unidades",
        "fecha_prescripcion",
        "sucursal",
    ],
}

DATE_FORMATS = {
    "mexico": "%d/%m/%Y",
    "estados_unidos": "%m/%d/%Y",
    "espana": "%Y-%m-%d",
}

CATALOGS = {
    "tipo_consulta": {
        "general",
        "cardiologia",
        "odontologia",
        "neurologia",
        "endocrinologia",
        "pediatria",
        "urgencias",
    },
    "metodo_pago": {"efectivo", "tarjeta", "transferencia"},
    "binary": {"0", "1"},
    "tipo_sangre": {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"},
}

AMOUNT_RANGES = {
    "mexico": {
        "general": (500, 1200),
        "cardiologia": (1200, 3000),
        "odontologia": (800, 2500),
        "neurologia": (1800, 4000),
        "endocrinologia": (1000, 2800),
        "pediatria": (500, 1500),
        "urgencias": (1500, 6000),
    },
    "estados_unidos": {
        "general": (80, 250),
        "cardiologia": (250, 900),
        "odontologia": (120, 600),
        "neurologia": (300, 1200),
        "endocrinologia": (200, 850),
        "pediatria": (90, 300),
        "urgencias": (700, 3500),
    },
    "espana": {
        "general": (50, 150),
        "cardiologia": (120, 400),
        "odontologia": (80, 350),
        "neurologia": (150, 500),
        "endocrinologia": (100, 350),
        "pediatria": (60, 180),
        "urgencias": (200, 900),
    },
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PRESSURE_RE = re.compile(r"^(\d{2,3})/(\d{2,3})$")
MEDICATION_RE = re.compile(r"([a-zA-Z]+)(-?\d+)")
FILENAME_RE = re.compile(r"^(transacciones|clinica|prescripciones)_(mexico|estados_unidos|espana)_(2023|2024|2025)\.csv$")


@dataclass(frozen=True)
class FileMeta:
    path: Path
    filename: str
    system: str
    site: str
    year: int


def is_missing(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip() == ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def discover_files() -> list[FileMeta]:
    files = []
    for path in sorted(RAW_DIR.glob("*.csv")):
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        system, site, year = match.groups()
        files.append(FileMeta(path=path, filename=path.name, system=system, site=site, year=int(year)))
    return files


def parse_date(value: str, site: str) -> datetime | None:
    if is_missing(value):
        return None
    try:
        parsed = datetime.strptime(value.strip(), DATE_FORMATS[site])
    except ValueError:
        return None
    if parsed.strftime(DATE_FORMATS[site]) != value.strip():
        return None
    return parsed


def to_float(value: str) -> float | None:
    if is_missing(value):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def normalize_name(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def row_signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple((row.get(key, "") or "").strip() for key in sorted(row))


def infer_simple_type(values: Iterable[str]) -> str:
    non_missing = [v for v in values if not is_missing(v)]
    if not non_missing:
        return "empty"
    numeric = sum(1 for v in non_missing if to_float(v) is not None)
    if numeric == len(non_missing):
        return "numeric"
    return "text"


def profile_files(files: list[FileMeta]) -> list[dict[str, object]]:
    report = []
    for meta in files:
        rows = read_csv(meta.path)
        columns = list(rows[0].keys()) if rows else []
        expected = EXPECTED_COLUMNS[meta.system]
        missing_columns = [col for col in expected if col not in columns]
        extra_columns = [col for col in columns if col not in expected]
        report.append(
            {
                "archivo": meta.filename,
                "sistema": meta.system,
                "sede": meta.site,
                "anio": meta.year,
                "registros": len(rows),
                "columnas": len(columns),
                "columnas_esperadas": len(expected),
                "columnas_faltantes": "|".join(missing_columns),
                "columnas_extra": "|".join(extra_columns),
                "estructura_valida": int(not missing_columns and not extra_columns),
            }
        )
    return report


def profile_columns(files: list[FileMeta]) -> list[dict[str, object]]:
    report = []
    for meta in files:
        rows = read_csv(meta.path)
        columns = list(rows[0].keys()) if rows else EXPECTED_COLUMNS[meta.system]
        for column in columns:
            values = [row.get(column, "") for row in rows]
            missing = sum(1 for value in values if is_missing(value))
            unique = len(set(value for value in values if not is_missing(value)))
            report.append(
                {
                    "archivo": meta.filename,
                    "sistema": meta.system,
                    "sede": meta.site,
                    "anio": meta.year,
                    "columna": column,
                    "registros": len(rows),
                    "faltantes": missing,
                    "porcentaje_faltantes": round(missing / len(rows) * 100, 3) if rows else 0,
                    "unicos_no_faltantes": unique,
                    "tipo_inferido": infer_simple_type(values),
                }
            )
    return report


def profile_duplicates(files: list[FileMeta]) -> list[dict[str, object]]:
    id_column = {
        "transacciones": "id_transaccion",
        "clinica": "id_lab",
        "prescripciones": "id_farmacia",
    }
    report = []
    for meta in files:
        rows = read_csv(meta.path)
        signatures = Counter(row_signature(row) for row in rows)
        exact_duplicate_rows = sum(count - 1 for count in signatures.values() if count > 1)
        ids = [row.get(id_column[meta.system], "") for row in rows]
        id_counts = Counter(ids)
        duplicated_ids = sum(1 for _, count in id_counts.items() if count > 1)
        duplicated_id_rows = sum(count - 1 for _, count in id_counts.items() if count > 1)
        report.append(
            {
                "archivo": meta.filename,
                "sistema": meta.system,
                "sede": meta.site,
                "anio": meta.year,
                "registros": len(rows),
                "duplicados_exactos": exact_duplicate_rows,
                "ids_duplicados_distintos": duplicated_ids,
                "filas_con_id_repetido_adicionales": duplicated_id_rows,
            }
        )
    return report


def valid_phone_for_site(value: str, site: str) -> bool:
    if is_missing(value):
        return False
    digits = normalize_phone(value)
    if site == "mexico":
        return len(digits) in {10, 12}
    if site == "estados_unidos":
        return len(digits) in {10, 11}
    if site == "espana":
        return len(digits) in {9, 11}
    return False


def medication_units(value: str) -> list[int] | None:
    if is_missing(value):
        return []
    if value == "sin_medicamento":
        return []
    parts = value.split(",")
    units = []
    for part in parts:
        match = MEDICATION_RE.fullmatch(part.strip())
        if not match:
            return None
        units.append(int(match.group(2)))
    return units


def profile_invalid_formats(files: list[FileMeta]) -> list[dict[str, object]]:
    findings = []
    for meta in files:
        rows = read_csv(meta.path)
        counters = Counter()

        for row in rows:
            if meta.system == "transacciones":
                if parse_date(row["fecha"], meta.site) is None:
                    counters["fecha_invalida"] += 1
                if parse_date(row["fecha_primer_registro"], meta.site) is None:
                    counters["fecha_primer_registro_invalida"] += 1
                if not EMAIL_RE.match((row["correo_electronico"] or "").strip()):
                    counters["correo_invalido_o_faltante"] += 1
                if not valid_phone_for_site(row["telefono_contacto"], meta.site):
                    counters["telefono_invalido_o_faltante"] += 1
                if row["tipo_consulta"] not in CATALOGS["tipo_consulta"]:
                    counters["tipo_consulta_fuera_catalogo"] += 1
                if row["metodo_pago"] not in CATALOGS["metodo_pago"]:
                    counters["metodo_pago_fuera_catalogo"] += 1
                if str(row["registro_previo"]) not in CATALOGS["binary"]:
                    counters["registro_previo_no_binario"] += 1
                if to_float(row["monto_cobro"]) is None:
                    counters["monto_no_numerico_o_faltante"] += 1

            if meta.system == "clinica":
                if parse_date(row["fecha_estudios"], meta.site) is None:
                    counters["fecha_estudios_invalida"] += 1
                if str(row["sexo"]) not in {"F", "M"}:
                    counters["sexo_fuera_catalogo"] += 1
                if parse_date(row["fecha_nacimiento"], meta.site) is None:
                    counters["fecha_nacimiento_invalida"] += 1
                if str(row["fumador"]) not in CATALOGS["binary"]:
                    counters["fumador_no_binario"] += 1
                if row["tipo_sangre"] not in CATALOGS["tipo_sangre"]:
                    counters["tipo_sangre_fuera_catalogo"] += 1
                if PRESSURE_RE.match(row["presion_arterial"] or "") is None:
                    counters["presion_formato_invalido"] += 1
                for column in [
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
                ]:
                    if to_float(row[column]) is None:
                        counters[f"{column}_no_numerico_o_faltante"] += 1

            if meta.system == "prescripciones":
                if parse_date(row["fecha_prescripcion"], meta.site) is None:
                    counters["fecha_prescripcion_invalida"] += 1
                if medication_units(row["medicamentos_unidades"]) is None:
                    counters["medicamentos_unidades_formato_invalido"] += 1

        for rule, count in counters.items():
            findings.append(
                {
                    "archivo": meta.filename,
                    "sistema": meta.system,
                    "sede": meta.site,
                    "anio": meta.year,
                    "regla": rule,
                    "hallazgos": count,
                    "porcentaje": round(count / len(rows) * 100, 3) if rows else 0,
                }
            )
    return findings


def profile_inconsistencies(files: list[FileMeta]) -> list[dict[str, object]]:
    findings = []
    for meta in files:
        rows = read_csv(meta.path)
        counters = Counter()

        for row in rows:
            if meta.system == "transacciones":
                tx_date = parse_date(row["fecha"], meta.site)
                first_date = parse_date(row["fecha_primer_registro"], meta.site)
                if tx_date and first_date and first_date > tx_date:
                    counters["fecha_primer_registro_posterior_a_fecha"] += 1
                monto = to_float(row["monto_cobro"])
                if monto is not None and monto <= 0:
                    counters["monto_cero_o_negativo"] += 1

            if meta.system == "clinica":
                edad = to_float(row["edad"])
                if edad is not None and not (0 <= edad <= 110):
                    counters["edad_fuera_rango_humano"] += 1
                oxygen = to_float(row["oxigenacion"])
                if oxygen is not None and not (0 <= oxygen <= 100):
                    counters["oxigenacion_fuera_0_100"] += 1
                pressure = PRESSURE_RE.match(row["presion_arterial"] or "")
                if pressure:
                    systolic, diastolic = map(int, pressure.groups())
                    if systolic <= diastolic:
                        counters["presion_sistolica_menor_o_igual_diastolica"] += 1

            if meta.system == "prescripciones":
                units = medication_units(row["medicamentos_unidades"])
                if units is not None and any(unit <= 0 or unit > 30 for unit in units):
                    counters["unidades_medicamento_inusuales"] += 1

        for rule, count in counters.items():
            findings.append(
                {
                    "archivo": meta.filename,
                    "sistema": meta.system,
                    "sede": meta.site,
                    "anio": meta.year,
                    "regla": rule,
                    "hallazgos": count,
                    "porcentaje": round(count / len(rows) * 100, 3) if rows else 0,
                }
            )
    return findings


def profile_outliers(files: list[FileMeta]) -> list[dict[str, object]]:
    findings = []
    for meta in files:
        rows = read_csv(meta.path)
        counters = Counter()

        for row in rows:
            if meta.system == "transacciones":
                monto = to_float(row["monto_cobro"])
                consultation = row["tipo_consulta"]
                if monto is not None and consultation in AMOUNT_RANGES[meta.site]:
                    low, high = AMOUNT_RANGES[meta.site][consultation]
                    if monto > high * 3:
                        counters["monto_outlier_alto"] += 1

            if meta.system == "clinica":
                clinical_ranges = {
                    "glucosa": (50, 400),
                    "colesterol_LDL": (0, 350),
                    "colesterol_HDL": (10, 130),
                    "trigliceridos": (20, 1000),
                    "hemoglobina": (5, 22),
                    "frecuencia_card": (35, 180),
                    "peso_kg": (25, 250),
                    "altura_cm": (80, 230),
                }
                for column, (low, high) in clinical_ranges.items():
                    value = to_float(row[column])
                    if value is not None and not (low <= value <= high):
                        counters[f"{column}_outlier"] += 1

        for rule, count in counters.items():
            findings.append(
                {
                    "archivo": meta.filename,
                    "sistema": meta.system,
                    "sede": meta.site,
                    "anio": meta.year,
                    "regla": rule,
                    "hallazgos": count,
                    "porcentaje": round(count / len(rows) * 100, 3) if rows else 0,
                }
            )
    return findings


def profile_probable_patient_duplicates(files: list[FileMeta]) -> list[dict[str, object]]:
    by_name_site = defaultdict(list)
    by_phone_site = defaultdict(set)
    by_email_site = defaultdict(set)

    for meta in files:
        rows = read_csv(meta.path)
        for row in rows:
            name = row.get("nombre_paciente") or row.get("nombre_completo") or ""
            normalized = normalize_name(name)
            if normalized:
                by_name_site[(meta.site, normalized)].append(meta.filename)

            phone = normalize_phone(row.get("telefono_contacto", ""))
            if len(phone) >= 9:
                by_phone_site[(meta.site, phone)].add(normalized)

            email = (row.get("correo_electronico", "") or "").strip().lower()
            if EMAIL_RE.match(email):
                by_email_site[(meta.site, email)].add(normalized)

    findings = []
    for (site, normalized), files_seen in by_name_site.items():
        if len(files_seen) > 1:
            findings.append(
                {
                    "tipo": "nombre_normalizado_repetido",
                    "sede": site,
                    "valor": normalized,
                    "apariciones": len(files_seen),
                    "archivos_distintos": len(set(files_seen)),
                }
            )

    for (site, phone), names in by_phone_site.items():
        if len(names) > 1:
            findings.append(
                {
                    "tipo": "telefono_compartido_por_varios_nombres",
                    "sede": site,
                    "valor": phone,
                    "apariciones": len(names),
                    "archivos_distintos": "",
                }
            )

    for (site, email), names in by_email_site.items():
        if len(names) > 1:
            findings.append(
                {
                    "tipo": "correo_compartido_por_varios_nombres",
                    "sede": site,
                    "valor": email,
                    "apariciones": len(names),
                    "archivos_distintos": "",
                }
            )

    return sorted(findings, key=lambda item: int(item["apariciones"]), reverse=True)


def write_report(filename: str, rows: list[dict[str, object]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / filename
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_quality_summary(
    file_report: list[dict[str, object]],
    column_report: list[dict[str, object]],
    duplicate_report: list[dict[str, object]],
    invalid_report: list[dict[str, object]],
    inconsistency_report: list[dict[str, object]],
    outlier_report: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_file = {row["archivo"]: dict(row) for row in file_report}
    missing_by_file = defaultdict(int)
    invalid_by_file = defaultdict(int)
    inconsistency_by_file = defaultdict(int)
    outlier_by_file = defaultdict(int)

    for row in column_report:
        missing_by_file[row["archivo"]] += int(row["faltantes"])
    for row in invalid_report:
        invalid_by_file[row["archivo"]] += int(row["hallazgos"])
    for row in inconsistency_report:
        inconsistency_by_file[row["archivo"]] += int(row["hallazgos"])
    for row in outlier_report:
        outlier_by_file[row["archivo"]] += int(row["hallazgos"])

    duplicates_by_file = {
        row["archivo"]: int(row["duplicados_exactos"]) + int(row["filas_con_id_repetido_adicionales"])
        for row in duplicate_report
    }

    summary = []
    for filename, base in by_file.items():
        records = int(base["registros"])
        expected_columns = max(int(base["columnas_esperadas"]), 1)
        total_cells = max(records * expected_columns, 1)
        missing_rate = missing_by_file[filename] / total_cells
        invalid_rate = invalid_by_file[filename] / total_cells
        inconsistency_rate = inconsistency_by_file[filename] / max(records, 1)
        outlier_rate = outlier_by_file[filename] / max(records, 1)
        duplicate_rate = duplicates_by_file.get(filename, 0) / max(records, 1)
        penalty = (
            missing_rate * 25
            + invalid_rate * 25
            + inconsistency_rate * 20
            + outlier_rate * 15
            + duplicate_rate * 15
        )
        score = max(0, 100 - penalty)
        summary.append(
            {
                "archivo": filename,
                "sistema": base["sistema"],
                "sede": base["sede"],
                "anio": base["anio"],
                "registros": records,
                "faltantes": missing_by_file[filename],
                "formatos_invalidos": invalid_by_file[filename],
                "inconsistencias": inconsistency_by_file[filename],
                "outliers": outlier_by_file[filename],
                "duplicados": duplicates_by_file.get(filename, 0),
                "score_calidad": round(score, 2),
            }
        )
    return sorted(summary, key=lambda row: (row["sistema"], row["sede"], int(row["anio"])))


def generate_all_reports() -> dict[str, list[dict[str, object]]]:
    files = discover_files()
    file_report = profile_files(files)
    column_report = profile_columns(files)
    duplicate_report = profile_duplicates(files)
    invalid_report = profile_invalid_formats(files)
    inconsistency_report = profile_inconsistencies(files)
    outlier_report = profile_outliers(files)
    probable_duplicates = profile_probable_patient_duplicates(files)
    quality_summary = build_quality_summary(
        file_report,
        column_report,
        duplicate_report,
        invalid_report,
        inconsistency_report,
        outlier_report,
    )

    reports = {
        "reporte_archivos.csv": file_report,
        "reporte_columnas.csv": column_report,
        "reporte_duplicados.csv": duplicate_report,
        "reporte_formatos_invalidos.csv": invalid_report,
        "reporte_inconsistencias.csv": inconsistency_report,
        "reporte_outliers.csv": outlier_report,
        "reporte_candidatos_duplicados_paciente.csv": probable_duplicates,
        "resumen_calidad_por_archivo.csv": quality_summary,
    }
    for filename, rows in reports.items():
        write_report(filename, rows)
    return reports


def print_top_findings(rows: list[dict[str, object]], title: str, top: int = 10) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    if not rows:
        print("Sin hallazgos.")
        return
    sorted_rows = sorted(rows, key=lambda row: int(row.get("hallazgos", row.get("apariciones", 0))), reverse=True)
    for row in sorted_rows[:top]:
        print(row)


def print_basic_summary() -> None:
    files = discover_files()
    file_report = profile_files(files)
    totals_by_system = defaultdict(int)
    totals_by_site = defaultdict(int)
    for row in file_report:
        totals_by_system[row["sistema"]] += int(row["registros"])
        totals_by_site[row["sede"]] += int(row["registros"])
    print("Archivos encontrados:", len(files))
    print("Totales por sistema:")
    for system, total in sorted(totals_by_system.items()):
        print(f"- {system}: {total}")
    print("Totales por sede:")
    for site, total in sorted(totals_by_site.items()):
        print(f"- {site}: {total}")


def main() -> None:
    reports = generate_all_reports()
    print_basic_summary()
    print("\nReportes generados en:", REPORT_DIR)
    for filename, rows in reports.items():
        print(f"- {filename}: {len(rows)} filas")

    summary = reports["resumen_calidad_por_archivo.csv"]
    scores = [float(row["score_calidad"]) for row in summary]
    print("\nScore de calidad promedio:", round(mean(scores), 2) if scores else "N/A")
    print_top_findings(reports["reporte_formatos_invalidos.csv"], "Principales formatos invalidos", top=8)
    print_top_findings(reports["reporte_inconsistencias.csv"], "Principales inconsistencias", top=8)
    print_top_findings(reports["reporte_outliers.csv"], "Principales outliers", top=8)


if __name__ == "__main__":
    main()
