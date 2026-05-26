"""Construye la tabla FHIR-inspired Practitioner/Workers desde medico_cargo."""

from __future__ import annotations

import mdm_config as cfg
from mdm_utils import normalize_name, read_rows, write_rows


def main() -> None:
    prescriptions = read_rows(cfg.STANDARDIZED_DIR / "prescripciones_standardized.csv")
    names = sorted(set(normalize_name(row["medico_cargo"]) for row in prescriptions if row["medico_cargo"]))
    workers = []
    mapping = {}
    for index, name in enumerate(names, start=1):
        worker_id = f"{cfg.WORKER_ROLE_PREFIX[cfg.DEFAULT_WORKER_ROLE]}_{index:05d}"
        mapping[name] = worker_id
        workers.append(
            {
                "id_trabajador": worker_id,
                "nombre_trabajador": name,
                "rol": cfg.DEFAULT_WORKER_ROLE,
                "area_hospitalaria": "Division Medica",
                "fhir_equivalent": "Practitioner",
            }
        )
    for row in prescriptions:
        row["id_trabajador"] = mapping.get(normalize_name(row["medico_cargo"]), "")
    write_rows(cfg.RELATIONAL_DIR / "Workers_Practitioner.csv", workers)
    write_rows(cfg.STANDARDIZED_DIR / "prescripciones_standardized_workers.csv", prescriptions)
    (cfg.RELATIONAL_DIR / "README_workers.md").write_text(
        "# Workers / Practitioner\n\n"
        "Tabla derivada de `medico_cargo`. En esta version todos los trabajadores son "
        "medicos asignados a `Division Medica`; el diseno admite roles y areas "
        "adicionales en futuras cargas.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
