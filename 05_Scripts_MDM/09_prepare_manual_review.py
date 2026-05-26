"""Construye una plantilla legible para clasificacion manual de pares pendientes."""

from __future__ import annotations

import mdm_config as cfg
from mdm_utils import read_rows, write_rows


def main() -> None:
    identity_rows = read_rows(cfg.LINKAGE_DIR / "consultation_identity_records.csv")
    pending_pairs = read_rows(cfg.MANUAL_REVIEW_DIR / "posibles_matches_revision_manual.csv")

    output_rows = []
    for pair_number, pair in enumerate(pending_pairs, start=1):
        left_index = int(pair["left_index"])
        right_index = int(pair["right_index"])
        left = identity_rows[left_index]
        right = identity_rows[right_index]
        output_rows.append(
            {
                "pair_id": f"PAIR_{pair_number:04d}",
                "left_index": left_index,
                "right_index": right_index,
                "nombre_a": left["full_name_std"],
                "nombre_b": right["full_name_std"],
                "fecha_nacimiento_a": left["birth_date_iso"],
                "fecha_nacimiento_b": right["birth_date_iso"],
                "sexo_a": left["sex"],
                "sexo_b": right["sex"],
                "telefono_a": left["phone_std"],
                "telefono_b": right["phone_std"],
                "correo_a": left["email_std"],
                "correo_b": right["email_std"],
                "pais_a": left["source_country"],
                "pais_b": right["source_country"],
                "id_consulta_a": left["id_consulta"],
                "id_consulta_b": right["id_consulta"],
                "decision_manual": "",
            }
        )

    output_path = cfg.MANUAL_REVIEW_DIR / "plantilla_decision_pares_pendientes.csv"
    write_rows(output_path, output_rows)


if __name__ == "__main__":
    main()
