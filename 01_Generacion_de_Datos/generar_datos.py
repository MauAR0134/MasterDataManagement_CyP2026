"""
Generador de datos sinteticos para los sistemas:
- transacciones
- clinica
- prescripciones

Al ejecutarse, crea 27 archivos CSV en la carpeta "02_Datos_Crudos".
No requiere dependencias externas; usa solo la biblioteca estandar de Python.
"""

from __future__ import annotations

import csv
import random
import string
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import generation_config as cfg


@dataclass
class Patient:
    patient_id: str
    site: str
    sex: str
    first_name: str
    paternal_last_name: str
    maternal_last_name: str
    birth_date: date
    phone: str
    email: str
    address: str
    blood_type: str
    clinical_risk: str
    conditions: list[str]
    first_registration_date: date

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.paternal_last_name} {self.maternal_last_name}"


@dataclass
class TransactionContext:
    patient: Patient
    site: str
    year: int
    transaction_id: str
    transaction_name: str
    transaction_date_real: date
    transaction_date_text: str
    first_registration_text: str
    consultation_type: str
    branch: str


def weighted_choice(options: dict[str, float]) -> str:
    labels = list(options.keys())
    weights = list(options.values())
    return random.choices(labels, weights=weights, k=1)[0]


def random_date(year: int) -> date:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def format_regional_date(value: date, site: str) -> str:
    return value.strftime(cfg.SITES[site]["date_format"])


def maybe_invalid_date(value: date, site: str) -> str:
    if random.random() < cfg.DATE_QUALITY["invalid_probability"]:
        if site == "mexico":
            return random.choice(["31/02/2025", "99/99/2024", "13/40/2023"])
        if site == "estados_unidos":
            return random.choice(["02/31/2025", "40/13/2024", "99/99/2023"])
        return random.choice(["2025-15-99", "2024-02-31", "2023-99-99"])
    return format_regional_date(value, site)


def clean_token(value: str, length: int) -> str:
    token = "".join(ch for ch in value.upper() if ch in string.ascii_uppercase)
    return (token + "XXX")[:length]


def initials(value: str) -> str:
    pieces = value.split()
    return "".join(piece[0].upper() for piece in pieces if piece)


def make_transaction_id(patient: Patient, site: str, tx_date: date, local_index: int) -> str:
    name_part = (
        clean_token(patient.first_name, 1)
        + clean_token(patient.paternal_last_name, 1)
        + clean_token(patient.maternal_last_name, 1)
    )
    return f"{name_part}_{patient.sex}_{cfg.SITES[site]['code']}_{tx_date:%d%m}_{local_index % 100:02d}"


def make_lab_id(patient: Patient) -> str:
    name_part = (
        clean_token(patient.first_name, 2)
        + clean_token(patient.paternal_last_name, 2)
        + clean_token(patient.maternal_last_name, 2)
    )
    return f"{name_part}_{patient.sex}_{patient.first_registration_date:%d%m}"


def make_pharmacy_id(site: str, year: int, local_index: int) -> str:
    return f"FARM_{cfg.SITES[site]['code']}_{year}_{local_index:06d}"


def vary_name(patient: Patient) -> str:
    mode = weighted_choice(cfg.NAME_VARIATION_PROBABILITIES)
    full = patient.full_name

    if mode == "exact":
        return full
    if mode == "compact":
        return " ".join(full.split())
    if mode == "initials":
        return f"{patient.first_name[0]}. {patient.paternal_last_name} {patient.maternal_last_name}"
    if mode == "uppercase":
        return full.upper()
    if mode == "omit_last_name":
        return f"{patient.first_name} {patient.paternal_last_name}"
    if mode == "typo":
        target = patient.paternal_last_name
        if len(target) > 3:
            pos = random.randint(1, len(target) - 2)
            target = target[:pos] + target[pos + 1 :]
        return f"{patient.first_name} {target} {patient.maternal_last_name}"
    return full


def vary_name_format_only(patient: Patient) -> str:
    """Aplica solo cambios de formato, conservando la identidad textual."""
    full = patient.full_name
    return random.choice([full, full.upper(), full.lower()])


def vary_recorded_name_format_only(name: str) -> str:
    """Cambia mayusculas/minusculas sin alterar el nombre de consulta."""
    return random.choice([name, name.upper(), name.lower()])


def make_email(first_name: str, last_name: str, patient_index: int) -> str:
    domain = random.choice(["gmail.com", "outlook.com", "hospitalmail.com", "mail.com"])
    return f"{first_name.lower()}.{last_name.lower()}.{patient_index:06d}@{domain}"


def apply_email_quality(email: str) -> str:
    mode = weighted_choice(cfg.EMAIL_QUALITY)
    if mode == "valid":
        return email
    if mode == "missing":
        return ""
    if mode == "missing_at":
        return email.replace("@", "")
    if mode == "incomplete_domain":
        return email.split("@")[0] + "@"
    if mode == "spaces_or_uppercase":
        return f" {email.upper()} "
    return email


def make_phone(site: str) -> str:
    if site == "mexico":
        digits = "55" + "".join(random.choices(string.digits, k=8))
    elif site == "estados_unidos":
        digits = "202" + "".join(random.choices(string.digits, k=7))
    else:
        digits = "6" + "".join(random.choices(string.digits, k=8))
    return digits


def apply_phone_quality(phone: str, site: str) -> str:
    mode = weighted_choice(cfg.PHONE_QUALITY)
    if mode == "missing":
        return ""
    if mode == "wrong_length":
        return phone[:-random.randint(1, 3)]
    if mode == "extra_separators":
        return f"{phone[:3]}--{phone[3:6]}..{phone[6:]}"
    if mode == "valid_international":
        return f"{cfg.SITES[site]['phone_prefix']} {phone}"
    if site == "estados_unidos" and len(phone) == 10:
        return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
    if site == "espana" and len(phone) == 9:
        return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    if site == "mexico" and len(phone) == 10:
        return f"{phone[:2]}-{phone[2:6]}-{phone[6:]}"
    return phone


def make_address(site: str) -> str:
    site_cfg = cfg.SITES[site]
    street = random.choice(site_cfg["street_terms"])
    name = random.choice(["Central", "Norte", "Sur", "Reforma", "Independencia", "Salud"])
    number = random.randint(10, 9999)
    city = random.choice(site_cfg["cities"])
    state = random.choice(site_cfg["states"])
    return f"{street} {name} {number}, {city}, {state}"


def pick_birth_date() -> date:
    age = random.choices(
        [random.randint(0, 17), random.randint(18, 39), random.randint(40, 64), random.randint(65, 90)],
        weights=[0.10, 0.35, 0.38, 0.17],
        k=1,
    )[0]
    today_anchor = date(2025, 7, 1)
    return today_anchor - timedelta(days=age * 365 + random.randint(0, 364))


def make_patient(site: str, index: int) -> Patient:
    site_cfg = cfg.SITES[site]
    sex = random.choice(["F", "M"])
    first_names = site_cfg["first_names_f"] if sex == "F" else site_cfg["first_names_m"]
    first_name = random.choice(first_names)
    paternal = random.choice(site_cfg["last_names"])
    maternal = random.choice(site_cfg["last_names"])
    base_phone = make_phone(site)
    email = make_email(first_name, paternal, index)
    risk = weighted_choice(cfg.CLINICAL_RISK_PROBABILITIES)
    conditions = [
        condition
        for condition, probability in cfg.CONDITION_PROBABILITIES_BY_RISK[risk].items()
        if random.random() < probability
    ]
    first_year = random.choice([2020, 2021, 2022, 2023])
    return Patient(
        patient_id=f"PB_{site_cfg['code']}_{index:06d}",
        site=site,
        sex=sex,
        first_name=first_name,
        paternal_last_name=paternal,
        maternal_last_name=maternal,
        birth_date=pick_birth_date(),
        phone=base_phone,
        email=email,
        address=make_address(site),
        blood_type=weighted_choice(cfg.BLOOD_TYPE_PROBABILITIES),
        clinical_risk=risk,
        conditions=conditions,
        first_registration_date=random_date(first_year),
    )


def create_patient_population() -> dict[str, list[Patient]]:
    population = {}
    for site, site_cfg in cfg.SITES.items():
        total_transactions = site_cfg["transaction_total"]
        unique_patients = round(total_transactions * site_cfg["unique_patient_ratio"])
        population[site] = [make_patient(site, idx + 1) for idx in range(unique_patients)]
    return population


def amount_for(site: str, consultation_type: str) -> str:
    mode = weighted_choice(cfg.AMOUNT_QUALITY)
    low, high = cfg.AMOUNT_RANGES[site][consultation_type]
    if mode == "missing":
        return ""
    if mode == "zero":
        return "0"
    if mode == "negative":
        return str(-random.randint(low, high))
    if mode == "outlier_high":
        return str(random.randint(high * 4, high * 12))
    return str(random.randint(low, high))


def make_transaction_rows(population: dict[str, list[Patient]]) -> tuple[dict[tuple[str, int], list[dict]], list[TransactionContext]]:
    rows_by_file: dict[tuple[str, int], list[dict]] = {}
    contexts: list[TransactionContext] = []

    for site in cfg.SITES:
        patients = population[site]
        total_site_transactions = sum(cfg.TRANSACTIONS_PER_SITE_YEAR[site].values())
        extra_transactions = total_site_transactions - len(patients)
        repeated_pool = patients + random.choices(patients, k=extra_transactions)
        random.shuffle(repeated_pool)
        cursor = 0

        for year in cfg.YEARS:
            rows = []
            target = cfg.TRANSACTIONS_PER_SITE_YEAR[site][year]
            site_cfg = cfg.SITES[site]
            for local_index in range(1, target + 1):
                patient = repeated_pool[cursor]
                cursor += 1
                tx_date = random_date(year)
                consultation_type = weighted_choice(cfg.CONSULTATION_PROBABILITIES)
                branch = random.choice(site_cfg["branches"])
                registro_previo = 1 if random.random() < cfg.REGISTRO_PREVIO_PROBABILITY else 0
                first_date = patient.first_registration_date if registro_previo else tx_date

                # La fecha del evento es necesaria para enlazar consulta,
                # laboratorio y prescripcion en la integracion posterior.
                tx_text = format_regional_date(tx_date, site)
                first_text = maybe_invalid_date(first_date, site)
                transaction_id = make_transaction_id(patient, site, tx_date, local_index)
                transaction_name = vary_name(patient)
                context = TransactionContext(
                    patient=patient,
                    site=site,
                    year=year,
                    transaction_id=transaction_id,
                    transaction_name=transaction_name,
                    transaction_date_real=tx_date,
                    transaction_date_text=tx_text,
                    first_registration_text=first_text,
                    consultation_type=consultation_type,
                    branch=branch,
                )
                contexts.append(context)

                rows.append(
                    {
                        "id_transaccion": transaction_id,
                        "fecha": tx_text,
                        "nombre_paciente": transaction_name,
                        "tipo_consulta": consultation_type,
                        "telefono_contacto": apply_phone_quality(patient.phone, site),
                        "correo_electronico": apply_email_quality(patient.email),
                        "direccion": patient.address,
                        "monto_cobro": amount_for(site, consultation_type),
                        "metodo_pago": weighted_choice(cfg.PAYMENT_METHOD_PROBABILITIES),
                        "registro_previo": registro_previo,
                        "fecha_primer_registro": first_text,
                    }
                )

            rows_by_file[(site, year)] = rows

    return rows_by_file, contexts


def clinical_value(value: float | int, outliers: list[float | int], decimals: int = 0, allow_missing: bool = True) -> str:
    mode = weighted_choice(cfg.CLINICAL_VALUE_QUALITY)
    if mode == "missing" and allow_missing:
        return ""
    if mode == "outlier":
        return str(random.choice(outliers))
    if decimals:
        return f"{value:.{decimals}f}"
    return str(round(value))


def generate_glucose(patient: Patient) -> str:
    if "diabetes" in patient.conditions:
        value = random.uniform(126, 250)
    elif patient.clinical_risk == "medio":
        value = random.uniform(90, 140)
    else:
        value = random.uniform(70, 110)
    return clinical_value(value, [20, 500, 999], allow_missing=False)


def generate_ldl(patient: Patient) -> str:
    if "dislipidemia" in patient.conditions or patient.clinical_risk == "alto":
        value = random.uniform(130, 260)
    else:
        value = random.uniform(70, 150)
    return clinical_value(value, [-20, 450], allow_missing=False)


def generate_hdl(patient: Patient) -> str:
    if "dislipidemia" in patient.conditions:
        value = random.uniform(25, 50)
    else:
        value = random.uniform(40, 85)
    return clinical_value(value, [-10, 180], allow_missing=False)


def generate_triglycerides(patient: Patient) -> str:
    if "dislipidemia" in patient.conditions or "obesidad" in patient.conditions:
        value = random.uniform(180, 600)
    else:
        value = random.uniform(50, 220)
    return clinical_value(value, [-50, 1400], allow_missing=False)


def generate_hemoglobin(patient: Patient) -> str:
    if "anemia" in patient.conditions:
        value = random.uniform(8.0, 11.9)
    elif patient.sex == "F":
        value = random.uniform(12.0, 15.5)
    else:
        value = random.uniform(13.5, 17.5)
    return clinical_value(value, [3.0, 25.5], decimals=1, allow_missing=False)


def generate_heart_rate(patient: Patient) -> str:
    if patient.clinical_risk == "alto":
        value = random.uniform(82, 135)
    else:
        value = random.uniform(58, 105)
    return clinical_value(value, [0, 250], allow_missing=False)


def generate_pressure(patient: Patient) -> str:
    mode = weighted_choice(cfg.PRESSURE_QUALITY)
    if mode == "format_error":
        return random.choice(["120-80", "120/abc"])
    if mode == "outlier":
        return random.choice(["999/80", "220/150"])
    if "hipertension" in patient.conditions:
        systolic = random.randint(130, 180)
        diastolic = random.randint(85, 110)
    else:
        systolic = random.randint(105, 135)
        diastolic = random.randint(65, 88)
    return f"{systolic}/{diastolic}"


def generate_body_metrics(patient: Patient) -> tuple[str, str]:
    if patient.sex == "F":
        height_cm = random.uniform(150, 175)
    else:
        height_cm = random.uniform(160, 190)

    bmi_category = "obesidad" if "obesidad" in patient.conditions else weighted_choice(cfg.BMI_CATEGORY_PROBABILITIES)
    bmi_ranges = {
        "bajo_peso": (17.0, 18.4),
        "normal": (18.5, 24.9),
        "sobrepeso": (25.0, 29.9),
        "obesidad": (30.0, 40.0),
    }
    bmi = random.uniform(*bmi_ranges[bmi_category])
    weight = bmi * ((height_cm / 100) ** 2)
    return (
        clinical_value(weight, [5, 350], decimals=1, allow_missing=False),
        clinical_value(height_cm, [30, 260], allow_missing=False),
    )


def generate_oxygenation(patient: Patient) -> str:
    if patient.clinical_risk == "alto" or "tabaquismo" in patient.conditions:
        value = random.uniform(88, 98)
    else:
        value = random.uniform(95, 100)
    return clinical_value(value, [45, 130], allow_missing=False)


def age_at(patient: Patient, moment: date) -> int:
    return moment.year - patient.birth_date.year - ((moment.month, moment.day) < (patient.birth_date.month, patient.birth_date.day))


def make_clinical_rows(contexts: list[TransactionContext]) -> dict[tuple[str, int], list[dict]]:
    rows_by_file: dict[tuple[str, int], list[dict]] = {(site, year): [] for site in cfg.SITES for year in cfg.YEARS}

    for context in contexts:
        patient = context.patient
        exam_date = context.transaction_date_real + timedelta(days=random.randint(0, 10))
        weight, height = generate_body_metrics(patient)
        age = age_at(patient, exam_date)
        if random.random() < 0.04:
            age = random.choice([-1, 150, age + random.randint(5, 20)])
        complete_labs = random.random() < cfg.COMPLETE_LAB_PANEL_PROBABILITY

        row = {
            "id_lab": make_lab_id(patient),
            "nombre_completo": vary_recorded_name_format_only(context.transaction_name),
            "sexo": patient.sex,
            "fecha_nacimiento": format_regional_date(patient.birth_date, context.site),
            "edad": age,
            "glucosa": generate_glucose(patient) if complete_labs else "",
            "colesterol_LDL": generate_ldl(patient) if complete_labs else "",
            "colesterol_HDL": generate_hdl(patient) if complete_labs else "",
            "trigliceridos": generate_triglycerides(patient) if complete_labs else "",
            "hemoglobina": generate_hemoglobin(patient) if complete_labs else "",
            "frecuencia_card": generate_heart_rate(patient),
            "presion_arterial": generate_pressure(patient),
            "peso_kg": weight,
            "altura_cm": height,
            "tipo_sangre": patient.blood_type,
            "fumador": 1 if "tabaquismo" in patient.conditions or random.random() < 0.12 else 0,
            "oxigenacion": generate_oxygenation(patient),
            "fecha_estudios": format_regional_date(exam_date, context.site),
        }
        rows_by_file[(context.site, context.year)].append(row)

    return rows_by_file


def choose_medications(context: TransactionContext) -> list[str]:
    patient = context.patient
    source_keys = list(patient.conditions) or [context.consultation_type, "general"]
    candidates: list[str] = []
    for key in source_keys:
        candidates.extend(cfg.MEDICATIONS_BY_CONDITION.get(key, []))
    if not candidates:
        candidates = cfg.MEDICATIONS_BY_CONDITION["general"]
    return random.sample(list(set(candidates)), k=min(random.randint(1, 3), len(set(candidates))))


def format_medications(medications: list[str]) -> str:
    chunks = []
    for medication in medications:
        if random.random() < cfg.UNUSUAL_MEDICATION_UNIT_PROBABILITY:
            units = random.choice([-2, -1, 0, 99, 120])
        else:
            units = random.randint(1, 4)
        chunks.append(f"{medication}{units}")
    return ",".join(chunks)


def make_prescription_rows(contexts: list[TransactionContext]) -> dict[tuple[str, int], list[dict]]:
    rows_by_file: dict[tuple[str, int], list[dict]] = {(site, year): [] for site in cfg.SITES for year in cfg.YEARS}
    counters = {(site, year): 0 for site in cfg.SITES for year in cfg.YEARS}

    for context in contexts:
        if random.random() > cfg.SYSTEM_COVERAGE["prescription_request_probability_per_transaction"]:
            continue

        patient = context.patient
        counters[(context.site, context.year)] += 1
        medications = format_medications(choose_medications(context))

        row = {
            "id_farmacia": make_pharmacy_id(context.site, context.year, counters[(context.site, context.year)]),
            "nombre_completo": vary_recorded_name_format_only(context.transaction_name),
            "medicamentos_unidades": medications,
            "fecha_prescripcion": context.transaction_date_text,
            "medico_cargo": random.choice(cfg.SITES[context.site]["doctors"]),
            "sucursal": context.branch,
        }
        rows_by_file[(context.site, context.year)].append(row)

    return rows_by_file


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No hay registros para escribir en {path}")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_all_outputs(
    transaction_rows: dict[tuple[str, int], list[dict]],
    clinical_rows: dict[tuple[str, int], list[dict]],
    prescription_rows: dict[tuple[str, int], list[dict]],
) -> None:
    for site in cfg.SITES:
        for year in cfg.YEARS:
            write_csv(cfg.RAW_DATA_DIR / f"transacciones_{site}_{year}.csv", transaction_rows[(site, year)])
            write_csv(cfg.RAW_DATA_DIR / f"clinica_{site}_{year}.csv", clinical_rows[(site, year)])
            write_csv(cfg.RAW_DATA_DIR / f"prescripciones_{site}_{year}.csv", prescription_rows[(site, year)])


def main() -> None:
    random.seed(cfg.RANDOM_SEED)
    population = create_patient_population()
    transaction_rows, contexts = make_transaction_rows(population)
    clinical_rows = make_clinical_rows(contexts)
    prescription_rows = make_prescription_rows(contexts)
    write_all_outputs(transaction_rows, clinical_rows, prescription_rows)


if __name__ == "__main__":
    main()
