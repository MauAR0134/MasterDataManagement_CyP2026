# Scripts MDM inspirados en FHIR

Este pipeline realiza ingesta, estandarizacion, perfilado, vinculacion de eventos, resolucion de entidades y construccion del modelo relacional. Siempre parte de una copia de los archivos raw.

## Scripts

| Archivo | Proceso | Output principal |
|---|---|---|
| `mdm_config.py` | Parametros modificables, umbrales, pesos, blocking y ventanas | Configuracion central |
| `mdm_utils.py` | Funciones de normalizacion, Soundex, Jaro-Winkler, fechas y clustering | Utilidades compartidas |
| `01_ingest.py` | Copia raw y consolida archivos por sistema | `00_raw_copy`, `01_staging_ingestion` |
| `02_standardize.py` | Estandariza nombres, tokens, fechas ISO y contacto | `02_standardized` |
| `03_profile_standardized.py` | Completitud, cardinalidad, duplicados y conflictos de ID | `03_profiling`, `manual_review` |
| `04_build_workers.py` | Crea tabla Workers/Practitioner desde `medico_cargo` | `Workers_Practitioner.csv` |
| `05_link_events.py` | Enlaza clinica y prescripciones con transacciones | `04_linkage_candidates`, `manual_review` |
| `06_entity_resolution.py` | Blocking, scoring, clusters e `id_master` | `05_master_index` |
| `09_prepare_manual_review.py` | Genera plantilla de decision humana sin puntajes que sesguen la revision | `manual_review/plantilla_decision_pares_pendientes.csv` |
| `07_build_relational_model.py` | Tablas curadas relacionadas | `06_relational_model` |
| `08_export_sqlite.py` | Exporta las tablas curadas a SQLite e indices SQL | `hospital_mdm_fhir.sqlite` |
| `run_pipeline.py` | Ejecuta todas las etapas secuencialmente | Todos los outputs |

## Matching y survivorship

Los umbrales son modificables en `mdm_config.py`:

```text
auto_match >= 0.88
revision_manual >= 0.74 y < 0.88
no_match < 0.74
```

Pesos:

```text
nombre completo: 40%
fecha de nacimiento: 30%
sexo: 10%
apellidos: 10%
telefono/correo: 10%
```

Reglas:

- DOB igual con sexo/apellidos consistentes o contacto exacto puede resolverse como `auto_match` soportado aunque exista abreviacion en el nombre.
- DOB diferente con contacto exacto, sexo igual y nombre/apellidos casi exactos se une como `auto_match_dob_conflict`, preservando una bandera de conflicto.
- DOB diferente con contacto exacto pero identidad incompatible se clasifica como `no_match`; los casos ambiguos permanecen en revision.
- Sexo diferente puede pasar como error corregible cuando los demas elementos fuertes coinciden.
- El nombre canonico es el nombre estandarizado mas largo del cluster.
- DOB y sexo sobreviven por valor mas frecuente; una DOB empatada en conflicto queda vacia y marcada en `Patient`.

El blocking productivo utiliza combinaciones estrictas con DOB y pais: `DOB + pais`, `DOB + soundex(apellido1) + pais`, `DOB + soundex(nombre) + soundex(apellido1) + pais`, ademas de telefono o correo valido exactos. Se asume que un paciente recibe atencion en un solo pais en esta version. `sorted_neighborhood` queda desactivado del matching productivo por generar demasiados homonimos.

## Modelo relacional

Las tablas usan nombres alineados conceptualmente con FHIR:

```text
Clientes_Patient
Transacciones_Encounter
Clinico_Observation
Prescripciones_MedicationRequest
Workers_Practitioner
```

`Medicamentos_Cost` y `Solicitudes_Bimestrales` se crean vacias para completarlas cuando se realice el parsing de medicamentos y se definan costos.

`id_consulta_original` conserva el ID recibido desde transacciones. Cuando dos
eventos comparten ese ID raw, `id_consulta` recibe un sufijo secuencial en la
capa curada y la reasignacion queda registrada para auditoria.
