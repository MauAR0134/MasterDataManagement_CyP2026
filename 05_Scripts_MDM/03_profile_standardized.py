"""Perfila las tablas estandarizadas y exporta conflictos para revision."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median

import mdm_config as cfg
from mdm_utils import read_rows, write_rows


def percentile(values: list[float], proportion: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def profile_monto_cobro() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows = read_rows(cfg.STANDARDIZED_DIR / "transacciones_standardized.csv")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["source_country"]].append(row)
    summary = []
    outliers = []
    for country, country_rows in sorted(grouped.items()):
        valid = []
        nulls = non_numeric = 0
        for row in country_rows:
            value = row.get("monto_cobro", "").strip()
            if not value:
                nulls += 1
                continue
            try:
                valid.append((row, float(value)))
            except ValueError:
                non_numeric += 1
        amounts = [amount for _, amount in valid]
        q1 = percentile(amounts, 0.25)
        q3 = percentile(amounts, 0.75)
        iqr = q3 - q1
        lower_limit = q1 - (1.5 * iqr)
        upper_limit = q3 + (1.5 * iqr)
        country_outliers = [(row, amount) for row, amount in valid if amount < lower_limit or amount > upper_limit]
        summary.append(
            {
                "source_country": country,
                "currency_original": cfg.CURRENCY_BY_SITE[country],
                "records": len(country_rows),
                "null_or_blank": nulls,
                "non_numeric": non_numeric,
                "valid_numeric": len(amounts),
                "minimum": round(min(amounts), 2) if amounts else "",
                "q1": round(q1, 2) if amounts else "",
                "median": round(median(amounts), 2) if amounts else "",
                "q3": round(q3, 2) if amounts else "",
                "maximum": round(max(amounts), 2) if amounts else "",
                "iqr_lower_limit": round(lower_limit, 2) if amounts else "",
                "iqr_upper_limit": round(upper_limit, 2) if amounts else "",
                "outliers_iqr": len(country_outliers),
            }
        )
        for row, amount in country_outliers:
            outliers.append(
                {
                    "source_country": country,
                    "currency_original": cfg.CURRENCY_BY_SITE[country],
                    "source_record_key": row["source_record_key"],
                    "id_transaccion": row["id_transaccion"],
                    "monto_cobro": amount,
                    "iqr_lower_limit": round(lower_limit, 2),
                    "iqr_upper_limit": round(upper_limit, 2),
                    "quality_flag": "OUTLIER_IQR",
                }
            )
    return summary, outliers


def profile_system(system: str) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rows = read_rows(cfg.STANDARDIZED_DIR / f"{system}_standardized.csv")
    columns = list(rows[0]) if rows else []
    column_profile = []
    for column in columns:
        values = [str(row.get(column, "")).strip() for row in rows]
        blanks = sum(not value for value in values)
        column_profile.append(
            {
                "source_system": system,
                "column": column,
                "records": len(rows),
                "null_or_blank": blanks,
                "completeness_pct": round((1 - blanks / len(rows)) * 100, 3) if rows else 0,
                "cardinality": len(set(value for value in values if value)),
            }
        )

    exact_counter = Counter(tuple(row.get(column, "") for column in columns) for row in rows)
    id_column = cfg.SYSTEM_ID_COLUMNS[system]
    by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_id[row[id_column]].append(row)
    duplicate_summary = [
        {
            "source_system": system,
            "records": len(rows),
            "exact_duplicate_additional_rows": sum(count - 1 for count in exact_counter.values() if count > 1),
            "distinct_ids_repeated": sum(1 for group in by_id.values() if len(group) > 1),
            "additional_rows_with_repeated_id": sum(len(group) - 1 for group in by_id.values() if len(group) > 1),
        }
    ]
    conflicts = []
    for source_id, group in by_id.items():
        names = sorted(set(row["full_name_std"] for row in group))
        if len(names) > 1:
            conflicts.append(
                {
                    "source_system": system,
                    "source_id": source_id,
                    "record_count": len(group),
                    "different_names_count": len(names),
                    "standardized_names": " | ".join(names),
                    "source_record_keys": " | ".join(row["source_record_key"] for row in group),
                    "source_files": " | ".join(sorted(set(row["source_file"] for row in group))),
                }
            )
    return column_profile, duplicate_summary, conflicts


def main() -> None:
    all_columns = []
    all_duplicates = []
    all_conflicts = []
    for system in cfg.SYSTEMS:
        columns, duplicates, conflicts = profile_system(system)
        all_columns.extend(columns)
        all_duplicates.extend(duplicates)
        all_conflicts.extend(conflicts)
    write_rows(cfg.PROFILING_DIR / "column_completeness_cardinality.csv", all_columns)
    write_rows(cfg.PROFILING_DIR / "duplicate_summary.csv", all_duplicates)
    monetary_summary, monetary_outliers = profile_monto_cobro()
    write_rows(cfg.PROFILING_DIR / "monto_cobro_quality_summary.csv", monetary_summary)
    write_rows(
        cfg.PROFILING_DIR / "monto_cobro_outliers.csv",
        monetary_outliers,
        [
            "source_country",
            "currency_original",
            "source_record_key",
            "id_transaccion",
            "monto_cobro",
            "iqr_lower_limit",
            "iqr_upper_limit",
            "quality_flag",
        ],
    )
    write_rows(
        cfg.MANUAL_REVIEW_DIR / "ids_duplicados_nombres_distintos.csv",
        all_conflicts,
        [
            "source_system",
            "source_id",
            "record_count",
            "different_names_count",
            "standardized_names",
            "source_record_keys",
            "source_files",
        ],
    )
    (cfg.PROFILING_DIR / "README.md").write_text(
        "# 03_profiling\n\n"
        "Perfilado posterior a la estandarizacion, sin alterar registros. Incluye completitud, "
        "cardinalidad, duplicados y control de `monto_cobro` por moneda original mediante IQR. "
        "Los IDs repetidos asociados a diferentes nombres "
        "se envian a `manual_review/ids_duplicados_nombres_distintos.csv`, conservando indices "
        "de origen para facilitar la decision manual.\n",
        encoding="utf-8",
    )
    (cfg.MANUAL_REVIEW_DIR / "README.md").write_text(
        "# manual_review\n\n"
        "Archivos que requieren revision humana o evidencian errores de calidad. Cada salida "
        "conserva IDs e indices de origen (`source_record_key`) para regresar al registro original.\n\n"
        "## Salidas\n\n"
        "| Archivo | Uso |\n"
        "|---|---|\n"
        "| `posibles_matches_revision_manual.csv` | Pares de identidad no concluyentes |\n"
        "| `plantilla_decision_pares_pendientes.csv` | Formato para registrar `MATCH` o `NO_MATCH` |\n"
        "| `conflictos_dob.csv` | Pares con DOB diferente aun ambiguos |\n"
        "| `dob_conflictos_auto_resueltos.csv` | Pares unidos por evidencia fuerte con conflicto documentado |\n"
        "| `dob_conflictos_descartados_por_nombre.csv` | Pares descartados por identidad incompatible |\n"
        "| `id_consulta_collisions_classified.csv` | Eventos reasignados por colision del ID raw |\n"
        "| `ids_duplicados_nombres_distintos.csv` | Conflictos de IDs de sistema fuente |\n"
        "| `clinical_event_ambiguous_links.csv` | Alternativas de enlace clinico |\n"
        "| `prescription_event_ambiguous_links.csv` | Alternativas de enlace farmaceutico |\n"
        "| `medicamentos_unidades_eliminadas.csv` | Partidas con unidades cero o negativas excluidas del modelo curado |\n"
        "| `medicamentos_unidades_outliers.csv` | Partidas positivas altas conservadas para analisis |\n\n"
        "`transactions_without_prescription.csv` identifica consultas sin solicitud de medicamentos; "
        "no representa un error de integridad.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
