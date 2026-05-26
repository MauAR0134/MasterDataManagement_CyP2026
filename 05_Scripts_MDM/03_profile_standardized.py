"""Perfila las tablas estandarizadas y exporta conflictos para revision."""

from __future__ import annotations

from collections import Counter, defaultdict

import mdm_config as cfg
from mdm_utils import read_rows, write_rows


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
        "cardinalidad y resumen de duplicados. Los IDs repetidos asociados a diferentes nombres "
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
        "| `prescription_event_ambiguous_links.csv` | Alternativas de enlace farmaceutico |\n\n"
        "`transactions_without_prescription.csv` identifica consultas sin solicitud de medicamentos; "
        "no representa un error de integridad.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
