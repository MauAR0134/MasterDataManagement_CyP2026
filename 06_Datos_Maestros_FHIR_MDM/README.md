# 06 Datos Maestros FHIR MDM

Salidas del pipeline de integracion y resolucion de entidades, organizadas por
capa de procesamiento.

## Capas

| Carpeta | Contenido |
|---|---|
| `00_raw_copy/` | Copia de ingestion de los archivos raw |
| `01_staging_ingestion/` | Consolidacion por sistema y tabla de control de archivos |
| `02_standardized/` | Variables estandarizadas y metadatos de trazabilidad |
| `03_profiling/` | Resultados de calidad sobre tablas consolidadas |
| `04_linkage_candidates/` | Asociacion de eventos y pares candidatos puntuados |
| `05_master_index/` | Entidad Patient y mapeos hacia `id_master` |
| `06_relational_model/` | Tablas curadas y base SQLite |
| `manual_review/` | Casos pendientes o resueltos con evidencia de decision |
| `sql/` | Documentacion de la base relacional |

## Documentacion

| Archivo | Contenido |
|---|---|
| `README_TECNICO_PIPELINE_MDM.md` | Arquitectura, reglas, decisiones y cardinalidades |
| `manual_review/README.md` | Inventario de archivos de revision |
| `06_relational_model/README.md` | Esquema curado y equivalencias FHIR |
