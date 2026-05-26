# SQL output

La base `hospital_mdm_fhir.sqlite` se genera en `06_relational_model` para facilitar consultas SQL, carga en Power BI o exportacion posterior. Los indices aceleran uniones por `id_master` e `id_consulta`. La columna `id_consulta_original` conserva la trazabilidad raw; `id_consulta` es unica en Encounter tras resolver colisiones.
