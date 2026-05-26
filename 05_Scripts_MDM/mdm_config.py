"""Configuracion central del pipeline MDM inspirado en FHIR."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "02_Datos_Crudos"
MDM_DIR = BASE_DIR / "06_Datos_Maestros_FHIR_MDM"

RAW_COPY_DIR = MDM_DIR / "00_raw_copy"
STAGING_DIR = MDM_DIR / "01_staging_ingestion"
STANDARDIZED_DIR = MDM_DIR / "02_standardized"
PROFILING_DIR = MDM_DIR / "03_profiling"
LINKAGE_DIR = MDM_DIR / "04_linkage_candidates"
MASTER_INDEX_DIR = MDM_DIR / "05_master_index"
RELATIONAL_DIR = MDM_DIR / "06_relational_model"
MANUAL_REVIEW_DIR = MDM_DIR / "manual_review"
SQL_DIR = MDM_DIR / "sql"
SCRIPTS_DIR = BASE_DIR / "05_Scripts_MDM"

SYSTEMS = ["transacciones", "clinica", "prescripciones"]
SITES = ["mexico", "estados_unidos", "espana"]
YEARS = [2023, 2024, 2025]

DATE_FORMATS_BY_SITE = {
    "mexico": "%d/%m/%Y",
    "estados_unidos": "%m/%d/%Y",
    "espana": "%Y-%m-%d",
}

CURRENCY_BY_SITE = {
    "mexico": "MXN",
    "estados_unidos": "USD",
    "espana": "EUR",
}

# Parametros sinteticos: la capa analitica utiliza EUR como moneda comun.
# Los montos originales se preservan para trazabilidad.
EXCHANGE_RATE_TO_EUR = {
    "mexico": 0.050,
    "estados_unidos": 0.920,
    "espana": 1.000,
}

# Catalogo sintetico configurable de costo por unidad en EUR.
MEDICATION_COSTS_EUR = {
    "acidofolico": 0.18,
    "amlodipino": 0.32,
    "amoxicilina": 0.48,
    "atorvastatina": 0.58,
    "bupropion": 1.10,
    "diclofenaco": 0.30,
    "enalapril": 0.22,
    "gabapentina": 0.44,
    "glibenclamida": 0.24,
    "ibuprofeno": 0.16,
    "insulina": 6.80,
    "ketorolaco": 0.75,
    "levotiroxina": 0.14,
    "loratadina": 0.20,
    "losartan": 0.34,
    "metformina": 0.20,
    "naproxeno": 0.26,
    "omeprazol": 0.28,
    "orlistat": 1.35,
    "paracetamol": 0.12,
    "pregabalina": 0.92,
    "rosuvastatina": 0.72,
    "sulfatoferroso": 0.16,
    "vareniclina": 1.85,
}

MEDICATION_UNIT_OUTLIER_THRESHOLD = 4

SYSTEM_ID_COLUMNS = {
    "transacciones": "id_transaccion",
    "clinica": "id_lab",
    "prescripciones": "id_farmacia",
}

SYSTEM_NAME_COLUMNS = {
    "transacciones": "nombre_paciente",
    "clinica": "nombre_completo",
    "prescripciones": "nombre_completo",
}

ID_MASTER_FORMAT = "NoApAp_ddbbaaaS_mmaaa"

LINKAGE_THRESHOLDS = {
    "auto_match": 0.88,
    "manual_review_min": 0.74,
}

# Reglas de clasificacion suplementarias aprobadas para reducir la bandeja manual.
# Mantienen el score como evidencia, pero permiten resolver variaciones de captura
# cuando la identidad esta soportada por DOB/contacto/apellidos.
SUPPORTED_MATCH_RULES = {
    "same_dob_last_names_min_name": 0.70,
    "dob_conflict_min_name": 0.95,
    "dob_conflict_min_last_names": 0.95,
}

MATCH_WEIGHTS = {
    "full_name": 0.40,
    "birth_date": 0.30,
    "sex": 0.10,
    "last_names": 0.10,
    "contact": 0.10,
}

# La variable se denomina country en outputs porque los raw identifican pais,
# no una institucion hospitalaria especifica.
BLOCKING_PASSES = [
    {"name": "birthdate_country", "columns": ["birth_date_iso", "source_country"]},
    {"name": "birthdate_lastname_soundex_country", "columns": ["birth_date_iso", "apellido1_soundex", "source_country"]},
    {"name": "birthdate_name_lastname_soundex_country", "columns": ["birth_date_iso", "nombre_soundex", "apellido1_soundex", "source_country"]},
    {"name": "phone_country", "columns": ["phone_std", "source_country"], "require_non_null": ["phone_std"]},
    {"name": "email_exact", "columns": ["email_std"], "require_non_null": ["email_std"]},
]

# Disponible para diagnostico exploratorio, excluido del matching productivo
# porque genera demasiados homonimos con DOB diferente.
SORTED_NEIGHBORHOOD = {"enabled": False, "sort_key": "full_name_std", "window": 5, "partition": "source_country"}

EVENT_LINKAGE = {
    "clinical_days_after_transaction": 14,
    "prescription_days_after_transaction": 0,
}

WORKER_ROLE_PREFIX = {
    "medico": "MED",
    "administrativo": "ADM",
    "funcionario": "FUN",
    "apoyo_medico": "APM",
}
DEFAULT_WORKER_ROLE = "medico"
