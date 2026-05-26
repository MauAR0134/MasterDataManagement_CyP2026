"""Carga tablas curadas a SQLite para consultas y uso posterior en BI."""

from __future__ import annotations

import csv
import sqlite3

import mdm_config as cfg


TABLE_FILES = {
    "clientes": "Clientes_Patient.csv",
    "administrativo": "Administrativo.csv",
    "contact_points": "ContactPoints.csv",
    "addresses": "Addresses.csv",
    "transacciones": "Transacciones_Encounter.csv",
    "clinico": "Clinico_Observation.csv",
    "prescripciones": "Prescripciones_MedicationRequest.csv",
    "workers": "Workers_Practitioner.csv",
    "medicamentos_cost": "Medicamentos_Cost.csv",
    "solicitudes_bimestrales": "Solicitudes_Bimestrales.csv",
}


def load_csv_to_table(connection: sqlite3.Connection, table: str, filename: str) -> None:
    with (cfg.RELATIONAL_DIR / filename).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        connection.execute(f"DROP TABLE IF EXISTS {table}")
        definitions = ", ".join(f'"{column}" TEXT' for column in columns)
        connection.execute(f"CREATE TABLE {table} ({definitions})")
        rows = list(reader)
        if rows:
            placeholders = ", ".join("?" for _ in columns)
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            connection.executemany(
                f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders})",
                [[row[column] for column in columns] for row in rows],
            )


def main() -> None:
    database_path = cfg.RELATIONAL_DIR / "hospital_mdm_fhir.sqlite"
    with sqlite3.connect(database_path) as connection:
        for table, filename in TABLE_FILES.items():
            load_csv_to_table(connection, table, filename)
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_transacciones_master ON transacciones(id_master);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_transacciones_consulta ON transacciones(id_consulta);
            CREATE INDEX IF NOT EXISTS idx_clinico_master ON clinico(id_master);
            CREATE INDEX IF NOT EXISTS idx_prescripciones_master ON prescripciones(id_master);
            CREATE INDEX IF NOT EXISTS idx_clinico_consulta ON clinico(id_consulta);
            CREATE INDEX IF NOT EXISTS idx_prescripciones_consulta ON prescripciones(id_consulta);
            """
        )
    (cfg.SQL_DIR / "README.md").write_text(
        "# SQL output\n\n"
        "La base `hospital_mdm_fhir.sqlite` se genera en `06_relational_model` para facilitar "
        "consultas SQL, carga en Power BI o exportacion posterior. Los indices aceleran uniones "
        "por `id_master` e `id_consulta`. La columna `id_consulta_original` conserva "
        "la trazabilidad raw; `id_consulta` es unica en Encounter tras resolver colisiones.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
