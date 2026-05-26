"""Construye el esquema relacional curado a partir del MPI y enlaces de eventos."""

from __future__ import annotations

from collections import defaultdict

import mdm_config as cfg
from mdm_utils import mode, name_tokens, read_rows, write_rows


def main() -> None:
    transactions = read_rows(cfg.STANDARDIZED_DIR / "transacciones_standardized.csv")
    clinical = read_rows(cfg.STANDARDIZED_DIR / "clinica_standardized.csv")
    prescriptions = read_rows(cfg.STANDARDIZED_DIR / "prescripciones_standardized_workers.csv")
    patient_master = read_rows(cfg.MASTER_INDEX_DIR / "Clientes_Patient.csv")
    consultation_map = read_rows(cfg.MASTER_INDEX_DIR / "consultation_to_master_mapping.csv")
    clinical_map = read_rows(cfg.LINKAGE_DIR / "clinical_to_encounter_mapping.csv")
    prescription_map = read_rows(cfg.LINKAGE_DIR / "prescription_to_encounter_mapping.csv")

    master_by_tx_key = {row["consultation_record_key"]: row["id_master"] for row in consultation_map}
    consultation_id_by_tx_key = {row["consultation_record_key"]: row["id_consulta"] for row in consultation_map}
    tx_by_key = {row["source_record_key"]: row for row in transactions}
    clinical_by_key = {row["source_record_key"]: row for row in clinical}
    prescriptions_by_key = {row["source_record_key"]: row for row in prescriptions}

    clinical_for_tx = {row["transaction_record_key"]: row for row in clinical_map}
    prescription_for_tx = {row["transaction_record_key"]: row for row in prescription_map}

    patient_transactions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in transactions:
        id_master = master_by_tx_key.get(row["source_record_key"], "")
        if id_master:
            patient_transactions[id_master].append(row)

    administrative = []
    contact_points = []
    addresses = []
    for patient in patient_master:
        id_master = patient["id_master"]
        observed = patient_transactions.get(id_master, [])
        nombre, apellido1, apellido2 = name_tokens(patient["nombre_completo"])
        registration_dates = sorted(row["fecha_primer_registro_iso"] for row in observed if row["fecha_primer_registro_iso"])
        countries = sorted(set(row["source_country"] for row in observed))
        administrative.append(
            {
                "id_master": id_master,
                "nombres": nombre,
                "apellido1": apellido1,
                "apellido2": apellido2,
                "fecha_primer_registro": registration_dates[0] if registration_dates else "",
                "contacto": int(any(row["phone_std"] or row["email_std"] for row in observed)),
                "pais": " | ".join(countries),
                "fhir_equivalent": "Patient.contact/address",
            }
        )
        contacts_seen = set()
        addresses_seen = set()
        contact_index = address_index = 0
        for row in observed:
            for contact_type, value in [("phone", row["phone_std"]), ("email", row["email_std"])]:
                if value and (contact_type, value) not in contacts_seen:
                    contact_index += 1
                    contacts_seen.add((contact_type, value))
                    contact_points.append(
                        {
                            "id_contacto": f"CNT_{id_master}_{contact_index:02d}",
                            "id_master": id_master,
                            "tipo_contacto": contact_type,
                            "valor": value,
                        }
                    )
            raw_address = row.get("direccion", "")
            if raw_address and raw_address not in addresses_seen:
                address_index += 1
                addresses_seen.add(raw_address)
                components = [part.strip() for part in raw_address.split(",")]
                addresses.append(
                    {
                        "id_direccion": f"ADR_{id_master}_{address_index:02d}",
                        "id_master": id_master,
                        "pais": row["source_country"],
                        "direccion_completa": raw_address,
                        "componente_via": components[0] if components else "",
                        "componente_localidad": components[1] if len(components) > 1 else "",
                        "componente_region": components[2] if len(components) > 2 else "",
                    }
                )

    fact_transactions = []
    fact_clinical = []
    fact_prescriptions = []
    full_source_mapping = []
    for tx in transactions:
        tx_key = tx["source_record_key"]
        id_master = master_by_tx_key.get(tx_key, "")
        if not id_master:
            continue
        curated_consultation_id = consultation_id_by_tx_key[tx_key]
        rx_map = prescription_for_tx.get(tx_key)
        rx = prescriptions_by_key.get(str(rx_map["source_record_key"])) if rx_map else None
        solicitud = int(rx is not None)
        fact_transactions.append(
            {
                "id_master": id_master,
                "id_consulta": curated_consultation_id,
                "id_consulta_original": tx["id_transaccion"],
                "tipo_consulta": tx["tipo_consulta"],
                "fecha": tx["fecha_iso"],
                "metodo_pago": tx["metodo_pago"],
                "monto_cobro": tx["monto_cobro"],
                "solicitud_medicamentos": solicitud,
                "costo_meds": "",
                "costo_total": tx["monto_cobro"] if not solicitud else "",
                "pais": tx["source_country"],
                "id_trabajador": rx["id_trabajador"] if rx else "",
                "fhir_equivalent": "Encounter/ChargeItem",
            }
        )
        full_source_mapping.append(
            {
                "source_system": "transacciones",
                "source_record_id": tx["id_transaccion"],
                "source_record_key": tx_key,
                "id_consulta": curated_consultation_id,
                "id_consulta_original": tx["id_transaccion"],
                "id_master": id_master,
            }
        )
        cl_map = clinical_for_tx.get(tx_key)
        if cl_map:
            lab = clinical_by_key[str(cl_map["source_record_key"])]
            fact_clinical.append(
                {
                    "id_master": id_master,
                    "id_lab": lab["id_lab"],
                    "id_consulta": curated_consultation_id,
                    "id_consulta_original": tx["id_transaccion"],
                    "sexo": lab["sex"],
                    "fecha_nacimiento": lab["birth_date_iso"],
                    "edad": lab["edad"],
                    "glucosa": lab["glucosa"],
                    "colesterol_LDL": lab["colesterol_LDL"],
                    "colesterol_HDL": lab["colesterol_HDL"],
                    "trigliceridos": lab["trigliceridos"],
                    "hemoglobina": lab["hemoglobina"],
                    "frecuencia_card": lab["frecuencia_card"],
                    "presion_arterial": lab["presion_arterial"],
                    "peso_kg": lab["peso_kg"],
                    "altura_cm": lab["altura_cm"],
                    "tipo_sangre": lab["tipo_sangre"],
                    "fumador": lab["fumador"],
                    "oxigenacion": lab["oxigenacion"],
                    "fecha_estudios": lab["fecha_estudios_iso"],
                    "fhir_equivalent": "Observation",
                }
            )
            full_source_mapping.append(
                {
                    "source_system": "clinica",
                    "source_record_id": lab["id_lab"],
                    "source_record_key": lab["source_record_key"],
                    "id_consulta": curated_consultation_id,
                    "id_consulta_original": tx["id_transaccion"],
                    "id_master": id_master,
                }
            )
        if rx:
            fact_prescriptions.append(
                {
                    "id_master": id_master,
                    "id_farmacia": rx["id_farmacia"],
                    "id_consulta": curated_consultation_id,
                    "id_consulta_original": tx["id_transaccion"],
                    "medicamentos_unidades": rx["medicamentos_unidades"],
                    "fecha_prescripcion": rx["fecha_prescripcion_iso"],
                    "id_trabajador": rx["id_trabajador"],
                    "sucursal": rx["sucursal"],
                    "costo_meds": "",
                    "fhir_equivalent": "MedicationRequest",
                }
            )
            full_source_mapping.append(
                {
                    "source_system": "prescripciones",
                    "source_record_id": rx["id_farmacia"],
                    "source_record_key": rx["source_record_key"],
                    "id_consulta": curated_consultation_id,
                    "id_consulta_original": tx["id_transaccion"],
                    "id_master": id_master,
                }
            )

    write_rows(cfg.RELATIONAL_DIR / "Clientes_Patient.csv", patient_master)
    write_rows(cfg.RELATIONAL_DIR / "Administrativo.csv", administrative)
    write_rows(cfg.RELATIONAL_DIR / "ContactPoints.csv", contact_points)
    write_rows(cfg.RELATIONAL_DIR / "Addresses.csv", addresses)
    write_rows(cfg.RELATIONAL_DIR / "Transacciones_Encounter.csv", fact_transactions)
    write_rows(cfg.RELATIONAL_DIR / "Clinico_Observation.csv", fact_clinical)
    write_rows(cfg.RELATIONAL_DIR / "Prescripciones_MedicationRequest.csv", fact_prescriptions)
    write_rows(cfg.MASTER_INDEX_DIR / "source_to_master_mapping.csv", full_source_mapping)
    write_rows(
        cfg.RELATIONAL_DIR / "Medicamentos_Cost.csv",
        [],
        ["id_medicamento", "nombre_medicamento", "costo_unitario", "moneda", "vigencia_desde"],
    )
    write_rows(
        cfg.RELATIONAL_DIR / "Solicitudes_Bimestrales.csv",
        [],
        ["id_medicamento", "pais", "anio", "bimestre", "unidades_solicitadas"],
    )
    (cfg.RELATIONAL_DIR / "README.md").write_text(
        "# 06_relational_model\n\n"
        "Modelo curado inspirado en recursos FHIR:\n\n"
        "- `Clientes_Patient.csv`: entidad maestra del paciente (`Patient`).\n"
        "- `Transacciones_Encounter.csv`: consultas/cobros (`Encounter` / `ChargeItem`).\n"
        "- `Clinico_Observation.csv`: signos y laboratorio (`Observation`).\n"
        "- `Prescripciones_MedicationRequest.csv`: solicitudes de medicamentos (`MedicationRequest`).\n"
        "- `Workers_Practitioner.csv`: personal medico (`Practitioner`).\n"
        "- `Administrativo.csv`, `ContactPoints.csv`, `Addresses.csv`: datos administrativos y contacto.\n\n"
        "`id_consulta` es el identificador curado del evento; `id_consulta_original` "
        "conserva el identificador recibido de transacciones. Las colisiones raw reciben "
        "sufijos solo en la capa curada.\n\n"
        "`Medicamentos_Cost.csv` y `Solicitudes_Bimestrales.csv` se dejan con esquema vacio "
        "hasta parsear medicamentos y definir costos.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
