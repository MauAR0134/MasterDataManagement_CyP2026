"""Copia los raw y consolida una entrada por sistema con metadata de origen."""

from __future__ import annotations

import mdm_config as cfg
from mdm_utils import copy_raw, discover_files, ensure_dirs, read_rows, write_rows


def main() -> None:
    ensure_dirs()
    metadata = discover_files()
    if len(metadata) != 27:
        raise ValueError(f"Se esperaban 27 archivos raw y se encontraron {len(metadata)}.")
    copy_raw(metadata)
    write_rows(cfg.STAGING_DIR / "control_table_files.csv", metadata)

    totals = []
    for system in cfg.SYSTEMS:
        consolidated = []
        for file_meta in [record for record in metadata if record["source_system"] == system]:
            source_rows = read_rows(cfg.RAW_COPY_DIR / str(file_meta["source_file"]))
            for row_number, row in enumerate(source_rows, start=1):
                row.update(
                    {
                        "source_file": file_meta["source_file"],
                        "source_system": system,
                        "source_country": file_meta["source_country"],
                        "source_year": file_meta["source_year"],
                        "source_row_index": row_number,
                        "source_record_key": f"{system}|{file_meta['source_file']}|{row_number}",
                    }
                )
                consolidated.append(row)
        write_rows(cfg.STAGING_DIR / f"{system}_all_staging.csv", consolidated)
        totals.append({"source_system": system, "rows": len(consolidated), "files": 9})

    write_rows(cfg.STAGING_DIR / "ingestion_summary.csv", totals)
    (cfg.STAGING_DIR / "README.md").write_text(
        "# 01_staging_ingestion\n\n"
        "Capa de ingesta inspirada en trazabilidad FHIR. Contiene la tabla de control y "
        "una entrada consolidada por sistema. Cada registro conserva `source_file`, "
        "`source_system`, `source_country`, `source_year`, `source_row_index` y "
        "`source_record_key`.\n\n"
        "Los datos se leen desde `00_raw_copy`; la carpeta original `02_Datos_Crudos` no se modifica.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
