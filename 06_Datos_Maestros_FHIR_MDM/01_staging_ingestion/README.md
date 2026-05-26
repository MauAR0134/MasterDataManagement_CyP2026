# 01_staging_ingestion

Capa de ingesta inspirada en trazabilidad FHIR. Contiene la tabla de control y una entrada consolidada por sistema. Cada registro conserva `source_file`, `source_system`, `source_country`, `source_year`, `source_row_index` y `source_record_key`.

Los datos se leen desde `00_raw_copy`; la carpeta original `02_Datos_Crudos` no se modifica.
