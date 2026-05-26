"""Asocia Observation/MedicationRequest con Encounter (transaccion) por paciente y fecha."""

from __future__ import annotations

from collections import defaultdict

import mdm_config as cfg
from mdm_utils import days_between, read_rows, write_rows


def assign_curated_consultation_ids(transactions: list[dict[str, str]]) -> list[dict[str, object]]:
    """Conserva el ID raw y desambigua solamente las colisiones observadas."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in transactions:
        grouped[row["id_transaccion"]].append(row)

    collision_rows = []
    for original_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: (row["fecha_iso"], row["source_record_key"]))
        for sequence, row in enumerate(ordered, start=1):
            row["id_consulta_curado"] = (
                original_id if len(ordered) == 1 else f"{original_id}_{sequence:02d}"
            )
            if len(ordered) > 1:
                collision_rows.append(
                    {
                        "id_consulta_original": original_id,
                        "id_consulta_curado": row["id_consulta_curado"],
                        "source_record_key": row["source_record_key"],
                        "source_country": row["source_country"],
                        "fecha_iso": row["fecha_iso"],
                        "full_name_std": row["full_name_std"],
                        "classification": "COLLISION_DISTINCT_ENCOUNTERS_REASSIGNED",
                        "reason": "mismo_id_raw_asignado_a_pacientes_o_eventos_distintos",
                    }
                )
    return collision_rows


def group_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["source_country"], row["full_name_std"])].append(row)
    return groups


def link_events(
    source_rows: list[dict[str, str]],
    transactions: list[dict[str, str]],
    source_date_column: str,
    max_days_after: int,
    event_system: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    tx_groups = group_rows(transactions)
    event_groups = group_rows(source_rows)
    mappings = []
    ambiguous = []
    unmatched = []

    for identity_key, events in event_groups.items():
        possible_tx = tx_groups.get(identity_key, [])
        eligible: dict[int, list[tuple[int, int]]] = {}
        for event_index, event in enumerate(events):
            candidates = []
            for tx_index, tx in enumerate(possible_tx):
                difference = days_between(event[source_date_column], tx["fecha_iso"])
                if difference is not None and 0 <= difference <= max_days_after:
                    candidates.append((difference, tx_index))
            eligible[event_index] = sorted(candidates, key=lambda item: (item[0], possible_tx[item[1]]["source_record_key"]))

        # Maximum bipartite matching avoids losing a clinical event when a
        # locally closest transaction is needed by another event in the group.
        tx_assignment: dict[int, int] = {}

        def assign(event_index: int, visited: set[int]) -> bool:
            for _, tx_index in eligible[event_index]:
                if tx_index in visited:
                    continue
                visited.add(tx_index)
                if tx_index not in tx_assignment or assign(tx_assignment[tx_index], visited):
                    tx_assignment[tx_index] = event_index
                    return True
            return False

        for event_index in sorted(eligible, key=lambda index: (len(eligible[index]), events[index][source_date_column])):
            assign(event_index, set())
        event_assignment = {event_index: tx_index for tx_index, event_index in tx_assignment.items()}

        for event_index, event in enumerate(events):
            if event_index not in event_assignment:
                unmatched.append(
                    {
                        "source_system": event_system,
                        "source_record_id": event["source_record_id"],
                        "source_record_key": event["source_record_key"],
                        "source_country": event["source_country"],
                        "full_name_std": event["full_name_std"],
                        "event_date_iso": event[source_date_column],
                        "reason": "sin_transaccion_en_ventana",
                    }
                )
                continue
            selected_index = event_assignment[event_index]
            selected = possible_tx[selected_index]
            best_difference = next(difference for difference, tx_index in eligible[event_index] if tx_index == selected_index)
            tied = [possible_tx[tx_index] for difference, tx_index in eligible[event_index] if difference == best_difference]
            status = "linked" if len(tied) == 1 else "ambiguous_selected_for_processing"
            if len(tied) > 1:
                ambiguous.append(
                    {
                        "source_system": event_system,
                        "source_record_id": event["source_record_id"],
                        "source_record_key": event["source_record_key"],
                        "id_consulta_selected": selected["id_consulta_curado"],
                        "candidate_consultation_ids": " | ".join(tx["id_consulta_curado"] for tx in tied),
                        "candidate_transaction_keys": " | ".join(tx["source_record_key"] for tx in tied),
                        "days_difference": best_difference,
                        "reason": "multiples_transacciones_equivalentes_en_ventana",
                    }
                )
            mappings.append(
                {
                    "source_system": event_system,
                    "source_record_id": event["source_record_id"],
                    "source_record_key": event["source_record_key"],
                    "id_consulta": selected["id_consulta_curado"],
                    "id_consulta_original": selected["id_transaccion"],
                    "transaction_record_key": selected["source_record_key"],
                    "source_country": event["source_country"],
                    "full_name_std": event["full_name_std"],
                    "event_date_iso": event[source_date_column],
                    "transaction_date_iso": selected["fecha_iso"],
                    "days_difference": best_difference,
                    "link_status": status,
                }
            )
    return mappings, ambiguous, unmatched


def transactions_without_link(
    transactions: list[dict[str, str]], mappings: list[dict[str, object]], link_name: str
) -> list[dict[str, object]]:
    linked = {str(mapping["transaction_record_key"]) for mapping in mappings}
    return [
        {
            "id_transaccion": row["id_transaccion"],
            "id_consulta_curado": row["id_consulta_curado"],
            "source_record_key": row["source_record_key"],
            "source_country": row["source_country"],
            "fecha_iso": row["fecha_iso"],
            "full_name_std": row["full_name_std"],
            "missing_link_type": link_name,
        }
        for row in transactions
        if row["source_record_key"] not in linked
    ]


def main() -> None:
    transaction_file = cfg.STANDARDIZED_DIR / "transacciones_standardized_workers.csv"
    transactions = read_rows(transaction_file if transaction_file.exists() else cfg.STANDARDIZED_DIR / "transacciones_standardized.csv")
    clinical = read_rows(cfg.STANDARDIZED_DIR / "clinica_standardized.csv")
    prescriptions = read_rows(cfg.STANDARDIZED_DIR / "prescripciones_standardized.csv")
    consultation_collisions = assign_curated_consultation_ids(transactions)
    write_rows(cfg.MANUAL_REVIEW_DIR / "id_consulta_collisions_classified.csv", consultation_collisions)

    clinical_map, clinical_ambiguous, clinical_unmatched = link_events(
        clinical,
        transactions,
        "fecha_estudios_iso",
        cfg.EVENT_LINKAGE["clinical_days_after_transaction"],
        "clinica",
    )
    prescription_map, prescription_ambiguous, prescription_unmatched = link_events(
        prescriptions,
        transactions,
        "fecha_prescripcion_iso",
        cfg.EVENT_LINKAGE["prescription_days_after_transaction"],
        "prescripciones",
    )
    write_rows(cfg.LINKAGE_DIR / "clinical_to_encounter_mapping.csv", clinical_map)
    write_rows(cfg.LINKAGE_DIR / "prescription_to_encounter_mapping.csv", prescription_map)
    write_rows(cfg.MANUAL_REVIEW_DIR / "clinical_event_ambiguous_links.csv", clinical_ambiguous)
    write_rows(cfg.MANUAL_REVIEW_DIR / "prescription_event_ambiguous_links.csv", prescription_ambiguous)
    write_rows(cfg.MANUAL_REVIEW_DIR / "clinical_without_consultation.csv", clinical_unmatched)
    write_rows(cfg.MANUAL_REVIEW_DIR / "prescription_without_consultation.csv", prescription_unmatched)
    write_rows(cfg.MANUAL_REVIEW_DIR / "transactions_without_clinical.csv", transactions_without_link(transactions, clinical_map, "clinical"))
    write_rows(cfg.MANUAL_REVIEW_DIR / "transactions_without_prescription.csv", transactions_without_link(transactions, prescription_map, "prescription"))

    clinical_by_tx = {mapping["transaction_record_key"]: mapping for mapping in clinical_map}
    clinical_by_key = {row["source_record_key"]: row for row in clinical}
    identity_rows = []
    for transaction in transactions:
        event_map = clinical_by_tx.get(transaction["source_record_key"])
        linked_clinical = clinical_by_key.get(str(event_map["source_record_key"])) if event_map else None
        identity_rows.append(
            {
                "consultation_record_key": transaction["source_record_key"],
                "id_consulta": transaction["id_consulta_curado"],
                "id_consulta_original": transaction["id_transaccion"],
                "source_country": transaction["source_country"],
                "source_year": transaction["source_year"],
                "full_name_std": transaction["full_name_std"],
                "nombre_std": transaction["nombre_std"],
                "apellido1_std": transaction["apellido1_std"],
                "apellido2_std": transaction["apellido2_std"],
                "nombre_soundex": transaction["nombre_soundex"],
                "apellido1_soundex": transaction["apellido1_soundex"],
                "birth_date_iso": linked_clinical["birth_date_iso"] if linked_clinical else "",
                "sex": linked_clinical["sex"] if linked_clinical else "",
                "phone_std": transaction["phone_std"],
                "email_std": transaction["email_std"],
                "fecha_primer_registro_iso": transaction["fecha_primer_registro_iso"],
                "clinical_record_key": linked_clinical["source_record_key"] if linked_clinical else "",
                "clinical_source_id": linked_clinical["id_lab"] if linked_clinical else "",
                "clinical_link_status": event_map["link_status"] if event_map else "unmatched",
            }
        )
    write_rows(cfg.LINKAGE_DIR / "consultation_identity_records.csv", identity_rows)
    (cfg.LINKAGE_DIR / "README_events.md").write_text(
        "# Event linkage\n\n"
        "Genera `id_consulta` solo en la capa integrada. Clinica se enlaza a transacciones "
        "por pais, nombre estandarizado y una ventana de 0 a 14 dias; prescripciones por "
        "pais, nombre estandarizado y la misma fecha. Los empates y ausencias se conservan "
        "en `manual_review` con indices de origen. Las colisiones del ID raw se conservan "
        "en `id_consulta_original` y reciben un `id_consulta` curado con sufijo secuencial.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
