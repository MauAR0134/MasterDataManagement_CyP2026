"""Estandariza identidad, fechas y contacto en las tres entradas de staging."""

from __future__ import annotations

import mdm_config as cfg
from mdm_utils import (
    ensure_dirs,
    name_tokens,
    normalize_email,
    normalize_name,
    normalize_phone,
    parse_date,
    read_rows,
    soundex,
    write_rows,
)


def identity_columns(row: dict[str, str], system: str) -> None:
    raw_name = row[cfg.SYSTEM_NAME_COLUMNS[system]]
    standardized = normalize_name(raw_name)
    nombre, apellido1, apellido2 = name_tokens(standardized)
    row.update(
        {
            "source_record_id": row[cfg.SYSTEM_ID_COLUMNS[system]],
            "source_name_raw": raw_name,
            "full_name_std": standardized,
            "nombre_std": nombre,
            "apellido1_std": apellido1,
            "apellido2_std": apellido2,
            "nombre_soundex": soundex(nombre),
            "apellido1_soundex": soundex(apellido1),
        }
    )


def standardize_transacciones() -> list[dict[str, object]]:
    rows = read_rows(cfg.STAGING_DIR / "transacciones_all_staging.csv")
    for row in rows:
        identity_columns(row, "transacciones")
        country = row["source_country"]
        row["fecha_iso"] = parse_date(row["fecha"], country)
        row["fecha_primer_registro_iso"] = parse_date(row["fecha_primer_registro"], country)
        row["phone_std"] = normalize_phone(row["telefono_contacto"])
        row["email_std"] = normalize_email(row["correo_electronico"])
        row["contacto_disponible"] = int(bool(row["phone_std"] or row["email_std"]))
        row["birth_date_iso"] = ""
        row["sex"] = ""
    return rows


def standardize_clinica() -> list[dict[str, object]]:
    rows = read_rows(cfg.STAGING_DIR / "clinica_all_staging.csv")
    for row in rows:
        identity_columns(row, "clinica")
        country = row["source_country"]
        row["fecha_estudios_iso"] = parse_date(row["fecha_estudios"], country)
        row["birth_date_iso"] = parse_date(row["fecha_nacimiento"], country)
        row["sex"] = str(row["sexo"]).strip().upper() if str(row["sexo"]).strip().upper() in {"F", "M"} else ""
        row["phone_std"] = ""
        row["email_std"] = ""
        row["contacto_disponible"] = 0
    return rows


def standardize_prescripciones() -> list[dict[str, object]]:
    rows = read_rows(cfg.STAGING_DIR / "prescripciones_all_staging.csv")
    for row in rows:
        identity_columns(row, "prescripciones")
        country = row["source_country"]
        row["fecha_prescripcion_iso"] = parse_date(row["fecha_prescripcion"], country)
        row["birth_date_iso"] = ""
        row["sex"] = ""
        row["phone_std"] = ""
        row["email_std"] = ""
        row["contacto_disponible"] = 0
    return rows


def main() -> None:
    ensure_dirs()
    standardized = {
        "transacciones": standardize_transacciones(),
        "clinica": standardize_clinica(),
        "prescripciones": standardize_prescripciones(),
    }
    for system, rows in standardized.items():
        write_rows(cfg.STANDARDIZED_DIR / f"{system}_standardized.csv", rows)

    (cfg.STANDARDIZED_DIR / "README.md").write_text(
        "# 02_standardized\n\n"
        "Capa estandarizada para integracion. Las columnas originales se conservan y se agregan:\n\n"
        "- `full_name_std`, `nombre_std`, `apellido1_std`, `apellido2_std`;\n"
        "- `nombre_soundex`, `apellido1_soundex`;\n"
        "- fechas ISO por sistema;\n"
        "- `phone_std` y `email_std` donde existen;\n"
        "- `birth_date_iso` y `sex` desde el sistema clinico.\n\n"
        "Los nombres quedan en minusculas, sin acentos, sin puntuacion y sin espacios sobrantes.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
