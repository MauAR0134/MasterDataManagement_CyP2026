"""
Parametros centrales para generar datos sinteticos del proyecto.

Este archivo concentra los valores que conviene modificar si se desea
regenerar los CSV con otro volumen, otra semilla o distintas tasas de error.
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = BASE_DIR / "02_Datos_Crudos"

RANDOM_SEED = 20260525

SITES = {
    "mexico": {
        "code": "MEX",
        "date_format": "%d/%m/%Y",
        "currency": "MXN",
        "phone_prefix": "+52",
        "transaction_total": 5000,
        "unique_patient_ratio": 0.45,
        "branches": [
            "Hospital Central Mexico",
            "Clinica Norte Mexico",
            "Unidad Medica Sur Mexico",
        ],
        "street_terms": ["Calle", "Avenida", "Privada", "Boulevard"],
        "cities": ["Ciudad de Mexico", "Guadalajara", "Monterrey", "Puebla", "Queretaro"],
        "states": ["CDMX", "Jalisco", "Nuevo Leon", "Puebla", "Queretaro"],
        "first_names_f": [
            "Maria", "Ana", "Sofia", "Fernanda", "Valeria", "Laura", "Daniela", "Carmen",
            "Patricia", "Gabriela", "Lucia", "Elena",
        ],
        "first_names_m": [
            "Juan", "Jose", "Carlos", "Luis", "Miguel", "Jorge", "Fernando", "Ricardo",
            "Alejandro", "Eduardo", "Daniel", "Manuel",
        ],
        "last_names": [
            "Hernandez", "Garcia", "Lopez", "Martinez", "Gonzalez", "Perez", "Rodriguez",
            "Sanchez", "Ramirez", "Cruz", "Flores", "Torres", "Vargas", "Castillo",
        ],
        "doctors": [
            "Dra. Ana Martinez", "Dr. Carlos Hernandez", "Dra. Laura Garcia",
            "Dr. Miguel Lopez", "Dra. Sofia Ramirez",
        ],
    },
    "estados_unidos": {
        "code": "USA",
        "date_format": "%m/%d/%Y",
        "currency": "USD",
        "phone_prefix": "+1",
        "transaction_total": 5000,
        "unique_patient_ratio": 0.45,
        "branches": [
            "International Hospital USA",
            "North Care Clinic USA",
            "West Medical Center USA",
        ],
        "street_terms": ["Street", "Avenue", "Road", "Drive"],
        "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
        "states": ["NY", "CA", "IL", "TX", "AZ"],
        "first_names_f": [
            "Mary", "Emily", "Sarah", "Jessica", "Jennifer", "Elizabeth", "Linda",
            "Patricia", "Susan", "Karen", "Nancy", "Laura",
        ],
        "first_names_m": [
            "John", "Michael", "David", "James", "Robert", "William", "Daniel",
            "Joseph", "Charles", "Thomas", "George", "Anthony",
        ],
        "last_names": [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor", "Moore",
        ],
        "doctors": [
            "Dr. John Smith", "Dra. Emily Johnson", "Dr. Michael Brown",
            "Dra. Sarah Davis", "Dr. Robert Wilson",
        ],
    },
    "espana": {
        "code": "ESP",
        "date_format": "%Y-%m-%d",
        "currency": "EUR",
        "phone_prefix": "+34",
        "transaction_total": 5000,
        "unique_patient_ratio": 0.45,
        "branches": [
            "Hospital Central Espana",
            "Clinica Madrid Norte",
            "Centro Medico Barcelona",
        ],
        "street_terms": ["Calle", "Avenida", "Paseo", "Ronda"],
        "cities": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza"],
        "states": ["Madrid", "Cataluna", "Valencia", "Andalucia", "Aragon"],
        "first_names_f": [
            "Lucia", "Maria", "Carmen", "Marta", "Elena", "Paula", "Sara",
            "Laura", "Isabel", "Claudia", "Irene", "Nuria",
        ],
        "first_names_m": [
            "Alejandro", "Pablo", "Javier", "Carlos", "David", "Daniel", "Miguel",
            "Sergio", "Antonio", "Manuel", "Rafael", "Alvaro",
        ],
        "last_names": [
            "Garcia", "Fernandez", "Rodriguez", "Lopez", "Sanchez", "Martinez",
            "Perez", "Gomez", "Martin", "Jimenez", "Ruiz", "Hernandez", "Diaz",
        ],
        "doctors": [
            "Dra. Lucia Garcia", "Dr. Javier Fernandez", "Dra. Marta Sanchez",
            "Dr. Pablo Lopez", "Dra. Carmen Martin",
        ],
    },
}

YEARS = [2023, 2024, 2025]

# Modo actual:
# - "per_site_total": los valores de transaction_total se reparten entre los anios.
#
# Modo alternativo futuro:
# - "per_site_year": cada sede tendria transaction_total registros en cada anio.
#   Para activar ese escenario, cambiar TRANSACTION_VOLUME_MODE a "per_site_year"
#   y regenerar TRANSACTIONS_PER_SITE_YEAR con build_transactions_per_site_year().
TRANSACTION_VOLUME_MODE = "per_site_total"


def build_transactions_per_site_year() -> dict[str, dict[int, int]]:
    """Construye el volumen de transacciones por sede y anio.

    En el modo actual reparte 5000 transacciones por sede entre 2023-2025.
    En el modo alternativo deja 5000 transacciones por sede en cada anio.
    """
    volumes: dict[str, dict[int, int]] = {}

    for site, site_cfg in SITES.items():
        site_total = site_cfg["transaction_total"]

        if TRANSACTION_VOLUME_MODE == "per_site_year":
            volumes[site] = {year: site_total for year in YEARS}
            continue

        if TRANSACTION_VOLUME_MODE != "per_site_total":
            raise ValueError(f"Modo de volumen no reconocido: {TRANSACTION_VOLUME_MODE}")

        base = site_total // len(YEARS)
        remainder = site_total % len(YEARS)
        volumes[site] = {
            year: base + (1 if index < remainder else 0)
            for index, year in enumerate(YEARS)
        }

    return volumes


TRANSACTIONS_PER_SITE_YEAR = build_transactions_per_site_year()

SYSTEM_COVERAGE = {
    "clinica_probability_per_transaction": 1.00,
    "prescription_request_probability_per_transaction": 0.55,
}

# Todos los eventos clinicos incluyen signos y datos de consulta regular.
# Solo este porcentaje incluye el panel de laboratorio completo.
COMPLETE_LAB_PANEL_PROBABILITY = 0.60

DATE_QUALITY = {
    "valid_probability": 0.97,
    "invalid_probability": 0.03,
    "missing_probability": 0.00,
}

NAME_VARIATION_PROBABILITIES = {
    "exact": 0.60,
    "compact": 0.15,
    "initials": 0.10,
    "uppercase": 0.05,
    "omit_last_name": 0.07,
    "typo": 0.03,
}

CONSULTATION_PROBABILITIES = {
    "general": 0.30,
    "cardiologia": 0.15,
    "odontologia": 0.12,
    "neurologia": 0.10,
    "endocrinologia": 0.12,
    "pediatria": 0.08,
    "urgencias": 0.13,
}

PAYMENT_METHOD_PROBABILITIES = {
    "tarjeta": 0.45,
    "transferencia": 0.30,
    "efectivo": 0.25,
}

REGISTRO_PREVIO_PROBABILITY = 0.55

AMOUNT_RANGES = {
    "mexico": {
        "general": (500, 1200),
        "cardiologia": (1200, 3000),
        "odontologia": (800, 2500),
        "neurologia": (1800, 4000),
        "endocrinologia": (1000, 2800),
        "pediatria": (500, 1500),
        "urgencias": (1500, 6000),
    },
    "estados_unidos": {
        "general": (80, 250),
        "cardiologia": (250, 900),
        "odontologia": (120, 600),
        "neurologia": (300, 1200),
        "endocrinologia": (200, 850),
        "pediatria": (90, 300),
        "urgencias": (700, 3500),
    },
    "espana": {
        "general": (50, 150),
        "cardiologia": (120, 400),
        "odontologia": (80, 350),
        "neurologia": (150, 500),
        "endocrinologia": (100, 350),
        "pediatria": (60, 180),
        "urgencias": (200, 900),
    },
}

AMOUNT_QUALITY = {
    "normal": 0.94,
    "outlier_high": 0.03,
    "zero": 0.01,
    "negative": 0.01,
    "missing": 0.01,
}

EMAIL_QUALITY = {
    "valid": 0.82,
    "missing": 0.08,
    "missing_at": 0.04,
    "incomplete_domain": 0.03,
    "spaces_or_uppercase": 0.03,
}

PHONE_QUALITY = {
    "valid_local": 0.65,
    "valid_international": 0.20,
    "extra_separators": 0.07,
    "wrong_length": 0.05,
    "missing": 0.03,
}

CLINICAL_RISK_PROBABILITIES = {
    "bajo": 0.50,
    "medio": 0.35,
    "alto": 0.15,
}

CONDITION_PROBABILITIES_BY_RISK = {
    "bajo": {
        "diabetes": 0.06,
        "hipertension": 0.08,
        "dislipidemia": 0.10,
        "anemia": 0.04,
        "obesidad": 0.08,
        "tabaquismo": 0.14,
    },
    "medio": {
        "diabetes": 0.16,
        "hipertension": 0.22,
        "dislipidemia": 0.25,
        "anemia": 0.08,
        "obesidad": 0.22,
        "tabaquismo": 0.24,
    },
    "alto": {
        "diabetes": 0.34,
        "hipertension": 0.42,
        "dislipidemia": 0.38,
        "anemia": 0.14,
        "obesidad": 0.36,
        "tabaquismo": 0.34,
    },
}

BMI_CATEGORY_PROBABILITIES = {
    "normal": 0.45,
    "sobrepeso": 0.35,
    "obesidad": 0.15,
    "bajo_peso": 0.05,
}

BLOOD_TYPE_PROBABILITIES = {
    "O+": 0.38,
    "A+": 0.28,
    "B+": 0.12,
    "AB+": 0.04,
    "O-": 0.07,
    "A-": 0.06,
    "B-": 0.03,
    "AB-": 0.02,
}

CLINICAL_VALUE_QUALITY = {
    "valid": 0.96,
    "outlier": 0.03,
    "missing": 0.01,
}

PRESSURE_QUALITY = {
    "valid": 0.96,
    "format_error": 0.02,
    "outlier": 0.02,
}

UNUSUAL_MEDICATION_UNIT_PROBABILITY = 0.02

MEDICATIONS_BY_CONDITION = {
    "diabetes": ["metformina", "insulina", "glibenclamida"],
    "hipertension": ["losartan", "enalapril", "amlodipino"],
    "dislipidemia": ["atorvastatina", "rosuvastatina"],
    "anemia": ["sulfatoferroso", "acidofolico"],
    "obesidad": ["orlistat", "metformina"],
    "tabaquismo": ["bupropion", "vareniclina"],
    "general": ["paracetamol", "ibuprofeno", "omeprazol"],
    "cardiologia": ["losartan", "amlodipino", "atorvastatina"],
    "odontologia": ["ibuprofeno", "diclofenaco", "amoxicilina"],
    "neurologia": ["pregabalina", "gabapentina", "naproxeno"],
    "endocrinologia": ["metformina", "insulina", "levotiroxina"],
    "pediatria": ["paracetamol", "ibuprofeno", "loratadina"],
    "urgencias": ["paracetamol", "ketorolaco", "omeprazol"],
}
