"""Ejecuta secuencialmente las etapas del pipeline MDM."""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPTS = [
    "01_ingest.py",
    "02_standardize.py",
    "03_profile_standardized.py",
    "04_build_workers.py",
    "05_link_events.py",
    "06_entity_resolution.py",
    "09_prepare_manual_review.py",
    "07_build_relational_model.py",
    "08_export_sqlite.py",
    "10_preprocess_clinico.py",
]


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    for script in SCRIPTS:
        print(f"Ejecutando {script}...")
        runpy.run_path(str(script_dir / script), run_name="__main__")
    print("Pipeline MDM completado.")


if __name__ == "__main__":
    main()
