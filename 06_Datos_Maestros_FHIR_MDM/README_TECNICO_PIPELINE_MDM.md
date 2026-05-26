# Pipeline Tecnico MDM Inspirado En FHIR

## 1. Objetivo Tecnico

Construir un Master Patient Index (MPI) y un modelo relacional curado a partir de fuentes hospitalarias heterogeneas:

```text
transacciones
clinica
prescripciones
```

El pipeline resuelve cuatro problemas:

```text
1. Normalizacion y trazabilidad de 27 archivos raw.
2. Resolucion de identidad de pacientes mediante record linkage.
3. Asociacion de eventos clinicos y solicitudes farmaceuticas con consultas.
4. Materializacion de tablas relacionales inspiradas en recursos FHIR.
```

## 2. Contrato De Entrada Raw

### 2.1 Archivos

```text
[sistema]_[pais]_[anio].csv
```

Parametros:

```text
sistemas: transacciones, clinica, prescripciones
paises: mexico, estados_unidos, espana
anios: 2023, 2024, 2025
total archivos: 27
```

### 2.2 Cardinalidad Generada

```text
transacciones: 15000
clinica: 15000
prescripciones: 8237
total raw: 38237
```

### 2.3 Reglas De Dependencia Raw

```text
Toda transaccion tiene un registro clinico correspondiente.
Clinica no almacena id_transaccion en raw.
Prescripciones solo contiene solicitudes efectivas de medicamentos.
Prescripciones no almacena id_transaccion en raw.
No todas las transacciones tienen prescripcion.
```

### 2.4 Identificadores De Origen

```text
transacciones.id_transaccion: identificador de consulta/cobro del sistema financiero
clinica.id_lab: identificador propio del evento clinico
prescripciones.id_farmacia: identificador propio de la solicitud farmaceutica
```

Decision:

```text
Los IDs de origen son independientes. id_consulta no existe en clinica ni
prescripciones raw; se deriva en la capa de integracion.
```

## 3. Correcciones Aplicadas Al Generador De Datos

### 3.1 Demografia Clinica

Se agregaron en archivos clinicos:

```text
sexo
fecha_nacimiento
```

Justificacion:

```text
La generacion de id_master y el entity resolution requieren DOB y sexo
observables en una fuente de alta confiabilidad.
```

### 3.2 Relacion Transaccion-Clinica

Regla corregida:

```text
clinica_probability_per_transaction = 1.00
```

Cada transaccion produce una observacion clinica con los campos obligatorios:

```text
sexo
fecha_nacimiento
edad
frecuencia_card
presion_arterial
peso_kg
altura_cm
tipo_sangre
fumador
oxigenacion
fecha_estudios
```

Panel de laboratorio:

```text
COMPLETE_LAB_PANEL_PROBABILITY = 0.60

glucosa
colesterol_LDL
colesterol_HDL
trigliceridos
hemoglobina
```

Resultado validado:

```text
clinica/transacciones = 15000/15000 = 1.00
campos obligatorios clinicos vacios = 0
panel laboratorio completo = 9016 registros = 60.11%
```

### 3.3 Logica De Prescripciones

Se eliminaron de raw:

```text
tratamiento
pedido
```

Justificacion:

```text
El registro existe unicamente cuando la solicitud de medicamentos ocurrio;
ambas banderas eran redundantes.
```

Regla de generacion:

```text
prescription_request_probability_per_transaction = 0.55
```

Resultado validado:

```text
prescripciones = 8237
prescripciones/transacciones = 54.91%
```

### 3.4 Fechas Operativas

Se elimino el ruido artificial de fechas para campos usados en linkage de eventos:

```text
transacciones.fecha: valida y en formato regional
clinica.fecha_estudios: valida y dentro de 0 a 14 dias posteriores a la consulta
prescripciones.fecha_prescripcion: igual a la fecha de la consulta asociada
```

Se conserva error controlado solo en:

```text
transacciones.fecha_primer_registro: 3% invalidas
```

Justificacion:

```text
No introducir errores sinteticos en llaves temporales necesarias para
reconstruir relaciones entre eventos.
```

### 3.5 Identidad En Eventos Relacionados

La prescripcion y la observacion clinica heredan el nombre registrado en la
consulta, permitiendo solo variaciones de formato:

```text
mayusculas
minusculas
```

Justificacion:

```text
Permitir enlace por nombre normalizado y fecha sin utilizar una llave
artificial compartida en raw.
```

### 3.6 Correos Sinteticos

Se modifico la generacion del correo base para hacerlo unico por paciente:

```text
nombre.apellido.consecutivo@dominio
```

Luego se aplican errores de calidad sobre el valor exportado.

Justificacion:

```text
Un correo valido exacto debe funcionar como evidencia fuerte de identidad;
correos no unicos generaban falsos matches masivos.
```

## 4. Arquitectura De Capas

```text
02_Datos_Crudos/
    fuente original regenerable

06_Datos_Maestros_FHIR_MDM/
    00_raw_copy/
        copia inmutable usada por el pipeline
    01_staging_ingestion/
        consolidacion por sistema y control table
    02_standardized/
        formatos normalizados y atributos de linkage
    03_profiling/
        completitud, cardinalidad y duplicados
    04_linkage_candidates/
        vinculo de eventos y pares candidatos de pacientes
    05_master_index/
        entidad maestra Patient y mapping de origen
    06_relational_model/
        tablas curadas y base SQLite
    manual_review/
        conflictos no resueltos automaticamente
    sql/
        documentacion de exportacion SQL
```

Decision:

```text
02_Datos_Crudos no se usa como capa mutable de procesamiento. Cada corrida inicia
copiando raw a 00_raw_copy.
```

## 5. Scripts Y Secuencia De Ejecucion

Ubicacion:

```text
05_Scripts_MDM/
```

Secuencia:

```text
01_ingest.py
02_standardize.py
03_profile_standardized.py
04_build_workers.py
05_link_events.py
06_entity_resolution.py
07_build_relational_model.py
08_export_sqlite.py
```

Orquestador:

```text
run_pipeline.py
```

## 6. Ingesta Y Trazabilidad

### 6.1 Tabla De Control

Archivo:

```text
01_staging_ingestion/control_table_files.csv
```

Columnas:

```text
file_id
source_file
source_system
source_country
source_year
source_path
```

### 6.2 Columnas De Linaje Agregadas A Cada Registro

```text
source_file
source_system
source_country
source_year
source_row_index
source_record_key
```

Formato de clave de trazabilidad:

```text
[source_system]|[source_file]|[row_number]
```

## 7. Estandarizacion

### 7.1 Nombre

Reglas:

```text
lowercase
eliminar acentos
eliminar signos de puntuacion
eliminar espacios al inicio y final
compactar espacios multiples
```

Columnas derivadas:

```text
full_name_std
nombre_std
apellido1_std
apellido2_std
nombre_soundex
apellido1_soundex
```

### 7.2 Fechas

Todas las fechas parseables se convierten a ISO:

```text
YYYY-MM-DD
```

Columnas derivadas:

```text
transacciones.fecha_iso
transacciones.fecha_primer_registro_iso
clinica.fecha_estudios_iso
clinica.birth_date_iso
prescripciones.fecha_prescripcion_iso
```

### 7.3 Contacto

```text
phone_std: solo digitos
email_std: lowercase y patron valido usuario@dominio.extension
contacto_disponible: 0/1
```

### 7.4 Sexo

```text
clinica.sexo -> sex en {F, M}
```

## 8. Perfilado E Identificacion De Errores

Outputs:

```text
03_profiling/column_completeness_cardinality.csv
03_profiling/duplicate_summary.csv
manual_review/ids_duplicados_nombres_distintos.csv
```

Medidas:

```text
completitud por columna
cardinalidad por columna
filas duplicadas exactas
IDs de origen repetidos
IDs repetidos con nombres estandarizados distintos
```

Todo conflicto conserva:

```text
source_id
source_record_key
source_file
```

## 9. Construccion De Workers

Origen:

```text
prescripciones.medico_cargo
```

Tabla final:

```text
Workers_Practitioner.csv
```

Reglas:

```text
todos los trabajadores actuales tienen rol = medico
id_trabajador = MED_[consecutivo]
area_hospitalaria = no_especificada
```

Decision:

```text
El esquema permite en el futuro roles administrativo, funcionario y
apoyo_medico sin alterar el modelo principal.
```

Resultado:

```text
Workers_Practitioner = 15 registros
```

## 10. Linkage De Eventos Y Derivacion De id_consulta

### 10.0 Control De Colisiones Del Identificador De Consulta

El identificador recibido desde transacciones se preserva como:

```text
id_consulta_original
```

En la capa curada se materializa:

```text
id_consulta
```

Regla:

```text
ID raw sin colision -> id_consulta = id_consulta_original
ID raw asignado a mas de un evento -> id_consulta = id_consulta_original_01, _02, ...
```

Resultado:

```text
id_consulta_original distintos en transacciones: 14997
id_consulta curados distintos en transacciones: 15000
IDs raw colisionados: 3
filas reasignadas: 6
```

Las reasignaciones se documentan en:

```text
manual_review/id_consulta_collisions_classified.csv
```

### 10.1 Clinica -> Transacciones

Reglas de candidato:

```text
mismo full_name_std
mismo source_country
fecha_estudios_iso entre 0 y 14 dias despues de fecha_iso
```

Seleccion:

```text
matching bipartito maximo dentro de identidad/pais
preferencia por menor diferencia de dias
```

Decision corregida:

```text
Se reemplazo la seleccion greedy por matching bipartito para no perder
observaciones cuando existen multiples consultas proximas de un paciente.
```

Resultado:

```text
transacciones = 15000
clinica enlazada = 15000
clinical_without_consultation = 0
transactions_without_clinical = 0
```

### 10.2 Prescripciones -> Transacciones

Reglas:

```text
mismo full_name_std
mismo source_country
fecha_prescripcion_iso = fecha_iso
```

Resultado:

```text
prescripciones enlazadas = 8237
prescription_without_consultation = 0
transactions_without_prescription = 6763
```

Interpretacion:

```text
Las 6763 transacciones sin prescripcion no son errores: corresponden a
consultas sin solicitud de medicamentos.
```

## 11. Entity Resolution Y Master Patient Index

### 11.1 Unidad De Resolucion

La unidad de clustering es la consulta enriquecida con identidad clinica:

```text
id_consulta
full_name_std
birth_date_iso
sex
phone_std
email_std
source_country
```

### 11.2 Supuesto Geografico

```text
Un paciente solo recibe atencion en un pais en esta version del modelo.
```

Por esta razon, `source_country` participa en todas las claves relevantes de
blocking.

### 11.3 Blocking Productivo Aprobado

```text
Pass 1: DOB + pais
Pass 2: DOB + soundex(apellido1) + pais
Pass 3: DOB + soundex(nombre) + soundex(apellido1) + pais
Pass 4: telefono valido exacto + pais
Pass 5: correo valido exacto
```

Decision corregida:

```text
Se desactivaron apellido1 + apellido2 + sexo + pais y sorted neighborhood
del matching productivo porque producian demasiados homonimos y conflictos
irrelevantes de DOB.
```

### 11.4 Scoring

Pesos configurables en `mdm_config.py`:

```text
nombre completo: 0.40
fecha de nacimiento: 0.30
sexo: 0.10
apellidos: 0.10
telefono/correo: 0.10
```

Metricas:

```text
nombre completo: Jaro-Winkler
fecha de nacimiento: exact match
sexo: exact match
apellidos: promedio Jaro-Winkler
contacto: exact match de telefono o correo valido
```

### 11.5 Umbrales Configurables

```text
auto_match: score >= 0.88
manual_review: 0.74 <= score < 0.88
no_match: score < 0.74
```

### 11.6 Conflictos DOB Y Sexo

Reglas DOB aplicadas:

```text
DOB igual + sexo igual + apellidos exactos + nombre >= 0.70 -> auto_match soportado
DOB igual + sexo igual + telefono o correo valido identico -> auto_match soportado
DOB diferente + contacto identico + sexo igual + nombre >= 0.95
  + apellidos >= 0.95 -> auto_match con bandera DOB_CONFLICT
DOB diferente + contacto identico + identidad claramente incompatible
  -> no_match por conflicto de nombre
DOB diferente + contacto identico sin evidencia concluyente -> manual_review
DOB diferente sin contacto identico -> no_match
```

Regla sexo aprobada:

```text
sexo diferente puede resolverse como error si los demas atributos fuertes
del par pasan el matching; en otro caso se envia a revision.
```

### 11.7 Resultado De Candidatos

```text
auto_match total: 13079
auto_match_dob_conflict: 49
manual_review_score: 323
manual_review_dob_conflict: 15
no_match: 1234
no_match_dob_conflict_name_incompatible: 1
total revision manual: 338
```

### 11.8 Survivorship

```text
nombre canonico: nombre estandarizado mas largo del cluster
DOB canonica: valor mas frecuente si existe mayoria
DOB en empate conflictivo: valor vacio + dob_conflict = 1
birth_dates_observed: conserva todas las DOB observadas del cluster
sexo canonico: valor mas frecuente; fuente clinica es origen disponible
fecha_primer_registro: fecha ISO valida mas antigua observada
```

### 11.9 id_master

Formato:

```text
NoApAp_ddmmyyyyS_mmyyyy
```

Componentes:

```text
No: primeras dos letras del nombre canonico
Ap: primeras dos letras del apellido1
Ap: primeras dos letras del apellido2
ddmmyyyy: fecha de nacimiento canonica
S: sexo canonico
mmyyyy: mes y anio del primer registro valido
```

Si existiera colision de `id_master`, se agrega sufijo secuencial y se
registra en:

```text
manual_review/id_master_collisions.csv
```

Resultado actual:

```text
Clientes_Patient = 6811 entidades
Patient con dob_conflict = 19
id_master_collisions = 0
```

## 12. Modelo Relacional Curado

Equivalencias conceptuales FHIR:

| Tabla | Equivalente FHIR / Proposito |
|---|---|
| `Clientes_Patient.csv` | `Patient`: entidad maestra del paciente |
| `Administrativo.csv` | Datos administrativos asociados a Patient |
| `ContactPoints.csv` | `Patient.telecom` |
| `Addresses.csv` | `Patient.address` |
| `Transacciones_Encounter.csv` | `Encounter` y atributos de cobro tipo `ChargeItem` |
| `Clinico_Observation.csv` | `Observation`: consulta, signos y laboratorio |
| `Prescripciones_MedicationRequest.csv` | `MedicationRequest` |
| `Workers_Practitioner.csv` | `Practitioner` |
| `Medicamentos_Cost.csv` | Catalogo futuro de costo por medicamento |
| `Solicitudes_Bimestrales.csv` | Agregacion futura de solicitudes tras parsing |

Cardinalidades actuales:

```text
Clientes_Patient: 6811
Administrativo: 6811
ContactPoints: 15692
Addresses: 6834
Transacciones_Encounter: 15000
Clinico_Observation: 15000
Prescripciones_MedicationRequest: 8237
Workers_Practitioner: 15
Medicamentos_Cost: 0 (esquema reservado)
Solicitudes_Bimestrales: 0 (esquema reservado)
```

## 13. Revision Manual

Directorio:

```text
manual_review/
```

Archivos principales:

```text
posibles_matches_revision_manual.csv: 338 pares
conflictos_dob.csv: 15 pares pendientes
dob_conflictos_auto_resueltos.csv: 49 pares unidos con bandera de calidad
dob_conflictos_descartados_por_nombre.csv: 1 par descartado
id_consulta_collisions_classified.csv: 6 filas de 3 IDs raw colisionados
ids_duplicados_nombres_distintos.csv: conflictos de IDs de fuente
clinical_event_ambiguous_links.csv: empates documentados de evento clinico
prescription_event_ambiguous_links.csv: empates documentados de prescripcion
clinical_without_consultation.csv: 0
prescription_without_consultation.csv: 0
transactions_without_clinical.csv: 0
transactions_without_prescription.csv: 6763 casos esperados
```

Todos los reportes de decision preservan indices y claves de origen.

## 14. Base SQLite Para Explotacion Analitica

Archivo:

```text
06_relational_model/hospital_mdm_fhir.sqlite
```

El archivo es una base de datos SQLite materializada desde las tablas curadas.
Contiene:

```text
clientes
administrativo
contact_points
addresses
transacciones
clinico
prescripciones
workers
medicamentos_cost
solicitudes_bimestrales
```

Indices SQL:

```text
idx_transacciones_master ON transacciones(id_master)
idx_transacciones_consulta UNIQUE ON transacciones(id_consulta)
idx_clinico_master ON clinico(id_master)
idx_prescripciones_master ON prescripciones(id_master)
idx_clinico_consulta ON clinico(id_consulta)
idx_prescripciones_consulta ON prescripciones(id_consulta)
```

Uso previsto:

```text
1. Ejecutar consultas SQL con joins por id_master o id_consulta.
2. Conectar Power BI mediante conector SQLite/ODBC.
3. Exportar tablas o resultados de consultas a Excel.
4. Mantener relaciones y consultas reproducibles sin depender de joins
   manuales sobre multiples CSV.
```

## 15. Ejecucion Reproducible

Comando:

```text
python "05_Scripts_MDM\run_pipeline.py"
```

Dependencias tecnicas del pipeline:

```text
Python standard library
```

El pipeline no modifica `02_Datos_Crudos`; recrea salidas desde la copia en
`00_raw_copy`.
