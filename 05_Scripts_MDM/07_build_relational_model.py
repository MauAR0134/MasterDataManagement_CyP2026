"""Construye el esquema relacional curado a partir del MPI y enlaces de eventos."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

import mdm_config as cfg
from mdm_utils import name_tokens, read_rows, write_rows


def latest_non_empty(rows: list[dict[str, str]], column: str) -> tuple[str, str]:
    ordered = sorted(rows, key=lambda row: (row["fecha_iso"], row["source_record_key"]), reverse=True)
    for row in ordered:
        if row.get(column, "").strip():
            return row[column], row["fecha_iso"]
    return "", ""


def medication_id(name: str) -> str:
    return f"MED_{name.upper()}"


def parse_medication_items(
    prescription: dict[str, str], country: str
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], float]:
    details = []
    removed = []
    outliers = []
    total = 0.0
    for item_number, chunk in enumerate(prescription["medicamentos_unidades"].split(","), start=1):
        text = chunk.strip().lower()
        match = re.fullmatch(r"([a-z]+)(-?\d+)", text)
        if not match:
            removed.append(
                {
                    "id_farmacia": prescription["id_farmacia"],
                    "texto_original": text,
                    "quality_flag": "FORMATO_NO_PARSEABLE",
                }
            )
            continue
        name, units_text = match.groups()
        units = int(units_text)
        if units <= 0:
            removed.append(
                {
                    "id_farmacia": prescription["id_farmacia"],
                    "nombre_medicamento": name,
                    "unidades": units,
                    "texto_original": text,
                    "quality_flag": "UNIDADES_NO_POSITIVAS_ELIMINADAS",
                }
            )
            continue
        unit_cost = cfg.MEDICATION_COSTS_EUR[name]
        line_cost = round(units * unit_cost, 2)
        quality_flag = (
            "OUTLIER_POSITIVE_UNITS"
            if units > cfg.MEDICATION_UNIT_OUTLIER_THRESHOLD
            else "VALID"
        )
        detail = {
            "id_detalle_medicamento": f"{prescription['id_farmacia']}_{item_number:02d}",
            "id_farmacia": prescription["id_farmacia"],
            "id_medicamento": medication_id(name),
            "nombre_medicamento": name,
            "unidades": units,
            "costo_unitario_eur": f"{unit_cost:.2f}",
            "costo_linea_eur": f"{line_cost:.2f}",
            "moneda": "EUR",
            "fecha_prescripcion": prescription["fecha_prescripcion_iso"],
            "pais": country,
            "quality_flag": quality_flag,
        }
        details.append(detail)
        total += line_cost
        if quality_flag != "VALID":
            outliers.append(detail)
    return details, removed, outliers, round(total, 2)


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
        id_admin = f"ADM_{id_master}"
        observed = patient_transactions.get(id_master, [])
        nombre, apellido1, apellido2 = name_tokens(patient["nombre_completo"])
        registration_dates = sorted(row["fecha_primer_registro_iso"] for row in observed if row["fecha_primer_registro_iso"])
        countries = sorted(set(row["source_country"] for row in observed))
        phone, phone_date = latest_non_empty(observed, "phone_std")
        email, email_date = latest_non_empty(observed, "email_std")
        address, address_date = latest_non_empty(observed, "direccion")
        contact_dates = [value for value in [phone_date, email_date] if value]
        contact_date = max(contact_dates) if contact_dates else ""
        address_country = ""
        if address:
            address_country = next(
                row["source_country"]
                for row in observed
                if row["direccion"] == address and row["fecha_iso"] == address_date
            )
        administrative.append(
            {
                "id_admin": id_admin,
                "id_master": id_master,
                "nombres": nombre,
                "apellido1": apellido1,
                "apellido2": apellido2,
                "fecha_primer_registro": registration_dates[0] if registration_dates else "",
                "contacto": int(bool(phone or email)),
                "pais": " | ".join(countries),
                "fhir_equivalent": "Patient.administrative",
            }
        )
        contact_points.append(
            {
                "id_contacto": f"CNT_{id_master}",
                "id_admin": id_admin,
                "id_master": id_master,
                "contacto": int(bool(phone or email)),
                "telefono": phone,
                "correo_electronico": email,
                "fecha_actualizacion": contact_date,
            }
        )
        components = [part.strip() for part in address.split(",")] if address else []
        addresses.append(
            {
                "id_direccion": f"ADR_{id_master}",
                "id_admin": id_admin,
                "id_master": id_master,
                "pais": address_country,
                "direccion_completa": address,
                "componente_via": components[0] if components else "",
                "componente_localidad": components[1] if len(components) > 1 else "",
                "componente_region": components[2] if len(components) > 2 else "",
                "fecha_actualizacion": address_date,
            }
        )

    fact_transactions = []
    fact_clinical = []
    fact_prescriptions = []
    medication_details = []
    medication_removed = []
    medication_outliers = []
    full_source_mapping = []
    for tx in transactions:
        tx_key = tx["source_record_key"]
        id_master = master_by_tx_key.get(tx_key, "")
        if not id_master:
            continue
        id_consulta = consultation_id_by_tx_key[tx_key]
        rx_map = prescription_for_tx.get(tx_key)
        rx = prescriptions_by_key.get(str(rx_map["source_record_key"])) if rx_map else None
        rx_cost = 0.0
        if rx:
            details, removed, outliers, rx_cost = parse_medication_items(
                rx, tx["source_country"]
            )
            medication_details.extend(details)
            medication_removed.extend(removed)
            medication_outliers.extend(outliers)
        raw_amount_text = tx["monto_cobro"].strip()
        raw_amount = float(raw_amount_text) if raw_amount_text else None
        exchange_rate = cfg.EXCHANGE_RATE_TO_EUR[tx["source_country"]]
        consultation_cost_eur = round(raw_amount * exchange_rate, 2) if raw_amount is not None else None
        total_cost_eur = round(consultation_cost_eur + rx_cost, 2) if consultation_cost_eur is not None else None
        fact_transactions.append(
            {
                "id_master": id_master,
                "id_consulta": id_consulta,
                "id_consulta_original": tx["id_transaccion"],
                "tipo_consulta": tx["tipo_consulta"],
                "fecha": tx["fecha_iso"],
                "metodo_pago": tx["metodo_pago"],
                "monto_cobro_original": raw_amount_text,
                "moneda_original": cfg.CURRENCY_BY_SITE[tx["source_country"]],
                "tipo_cambio_a_eur": f"{exchange_rate:.3f}",
                "monto_cobro": f"{consultation_cost_eur:.2f}" if consultation_cost_eur is not None else "",
                "moneda": "EUR",
                "monto_cobro_quality_flag": "VALID" if consultation_cost_eur is not None else "MISSING_SOURCE_VALUE",
                "solicitud_medicamentos": int(rx is not None),
                "costo_meds": f"{rx_cost:.2f}",
                "costo_total": f"{total_cost_eur:.2f}" if total_cost_eur is not None else "",
                "costo_total_status": "COMPLETE" if total_cost_eur is not None else "INCOMPLETE_MISSING_CONSULTATION_COST",
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
                "id_consulta": id_consulta,
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
                    "id_consulta": id_consulta,
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
                    "id_consulta": id_consulta,
                    "id_consulta_original": tx["id_transaccion"],
                    "id_master": id_master,
                }
            )
        if rx:
            fact_prescriptions.append(
                {
                    "id_master": id_master,
                    "id_farmacia": rx["id_farmacia"],
                    "id_consulta": id_consulta,
                    "id_consulta_original": tx["id_transaccion"],
                    "medicamentos_unidades_original": rx["medicamentos_unidades"],
                    "fecha_prescripcion": rx["fecha_prescripcion_iso"],
                    "id_trabajador": rx["id_trabajador"],
                    "sucursal": rx["sucursal"],
                    "costo_meds": f"{rx_cost:.2f}",
                    "moneda": "EUR",
                    "fhir_equivalent": "MedicationRequest",
                }
            )
            full_source_mapping.append(
                {
                    "source_system": "prescripciones",
                    "source_record_id": rx["id_farmacia"],
                    "source_record_key": rx["source_record_key"],
                    "id_consulta": id_consulta,
                    "id_consulta_original": tx["id_transaccion"],
                    "id_master": id_master,
                }
            )

    medication_catalog = [
        {
            "id_medicamento": medication_id(name),
            "nombre_medicamento": name,
            "costo_unitario_eur": f"{cost:.2f}",
            "moneda": "EUR",
            "cost_type": "SYNTHETIC_CONFIGURABLE",
        }
        for name, cost in sorted(cfg.MEDICATION_COSTS_EUR.items())
    ]
    bimonthly: dict[tuple[str, str, str, int, int], int] = defaultdict(int)
    for detail in medication_details:
        date = datetime.strptime(str(detail["fecha_prescripcion"]), "%Y-%m-%d")
        bimester = ((date.month - 1) // 2) + 1
        key = (
            str(detail["id_medicamento"]),
            str(detail["nombre_medicamento"]),
            str(detail["pais"]),
            date.year,
            bimester,
        )
        bimonthly[key] += int(detail["unidades"])
    bimonthly_rows = [
        {
            "id_medicamento": key[0],
            "nombre_medicamento": key[1],
            "pais": key[2],
            "anio": key[3],
            "bimestre": key[4],
            "unidades_solicitadas": units,
            "moneda": "EUR",
        }
        for key, units in sorted(bimonthly.items())
    ]

    write_rows(cfg.RELATIONAL_DIR / "Clientes_Patient.csv", patient_master)
    write_rows(cfg.RELATIONAL_DIR / "Administrativo.csv", administrative)
    write_rows(cfg.RELATIONAL_DIR / "ContactPoints.csv", contact_points)
    write_rows(cfg.RELATIONAL_DIR / "Addresses.csv", addresses)
    write_rows(cfg.RELATIONAL_DIR / "Transacciones_Encounter.csv", fact_transactions)
    write_rows(cfg.RELATIONAL_DIR / "Clinico_Observation.csv", fact_clinical)
    write_rows(cfg.RELATIONAL_DIR / "Prescripciones_MedicationRequest.csv", fact_prescriptions)
    write_rows(cfg.RELATIONAL_DIR / "Prescripcion_Detalle_Medicamento.csv", medication_details)
    write_rows(cfg.RELATIONAL_DIR / "Medicamentos_Cost.csv", medication_catalog)
    write_rows(cfg.RELATIONAL_DIR / "Solicitudes_Bimestrales.csv", bimonthly_rows)
    write_rows(cfg.MANUAL_REVIEW_DIR / "medicamentos_unidades_eliminadas.csv", medication_removed)
    write_rows(cfg.MANUAL_REVIEW_DIR / "medicamentos_unidades_outliers.csv", medication_outliers)
    write_rows(cfg.MASTER_INDEX_DIR / "source_to_master_mapping.csv", full_source_mapping)
    (cfg.RELATIONAL_DIR / "README.md").write_text(
        "# 06_relational_model\n\n"
        "Modelo curado inspirado en recursos FHIR. `Clientes_Patient`, `Administrativo`, "
        "`ContactPoints` y `Addresses` son dimensiones con un registro por `id_master`; "
        "contacto y direccion conservan el valor no vacio mas reciente.\n\n"
        "`Transacciones_Encounter` conserva el monto original y expresa `monto_cobro`, "
        "`costo_meds` y `costo_total` en EUR. El tipo de cambio y los costos unitarios "
        "son parametros sinteticos configurables de `05_Scripts_MDM/mdm_config.py`.\n\n"
        "`Prescripcion_Detalle_Medicamento.csv` se relaciona con la solicitud mediante "
        "`id_farmacia`. Se eliminan unidades cero o negativas; las positivas altas se "
        "mantienen con bandera de outlier. `Solicitudes_Bimestrales.csv` agrega unidades "
        "validas y positivas por medicamento.\n\n"
        "Pendiente: preprocesamiento analitico de variables biologicas de "
        "`Clinico_Observation`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
