# Master Data Management Para Una Red Hospitalaria Internacional

Proyecto final de Calidad y Preprocesamiento de Datos. Implementa un pipeline
de datos sinteticos, perfilado, estandarizacion, resolucion de entidades y
materializacion de un Master Patient Index (MPI) mediante un modelo relacional
inspirado en FHIR.

## Alcance

Fuentes simuladas:

| Sistema | Funcion | Registros |
|---|---|---:|
| Transacciones | Consultas y cobros | 15,000 |
| Clinica | Signos vitales y estudios asociados a consultas | 15,000 |
| Prescripciones | Solicitudes efectivas de medicamentos | 8,237 |

Cobertura geografica y temporal:

```text
paises: mexico, estados_unidos, espana
anios: 2023, 2024, 2025
archivos raw: 27 CSV
```

Resultado curado:

| Entidad | Registros |
|---|---:|
| Patient / Clientes | 6,811 |
| Encounter / Transacciones | 15,000 |
| Observation / Clinico | 15,000 |
| MedicationRequest / Prescripciones | 8,237 |
| Practitioner / Workers | 15 |

Poblacion sintetica base esperada: `6,750` pacientes. Permanecen `338` pares
de candidatos disponibles para resolucion manual.

## Estructura Del Repositorio

| Carpeta | Contenido |
|---|---|
| [`01_Generacion_de_Datos`](01_Generacion_de_Datos/) | Configuracion, script generador y especificacion de datos sinteticos |
| [`02_Datos_Crudos`](02_Datos_Crudos/) | 27 archivos CSV generados por sistema, pais y anio |
| [`03_Perfilado`](03_Perfilado/) | Scripts, notebooks y reportes exploratorios de calidad |
| [`04_Limpieza_y_Preprocesamiento`](04_Limpieza_y_Preprocesamiento/) | Notebook de transformaciones iniciales |
| [`05_Scripts_MDM`](05_Scripts_MDM/) | Pipeline modular para integracion, linkage, MPI y exportacion |
| [`06_Datos_Maestros_FHIR_MDM`](06_Datos_Maestros_FHIR_MDM/) | Capas de salida, revision manual, tablas finales y SQLite |

## Pipeline

```text
Generacion sintetica
  -> Datos crudos inmutables
  -> Ingesta y trazabilidad
  -> Estandarizacion
  -> Perfilado consolidado
  -> Enlace de eventos
  -> Resolucion de entidades
  -> Master Patient Index
  -> Modelo relacional curado
  -> SQLite para consultas y BI
```

## Modelo Curado

```text
Clientes_Patient
  -> Administrativo
  -> Transacciones_Encounter
       -> Clinico_Observation
       -> Prescripciones_MedicationRequest
  -> Workers_Practitioner (atencion/prescripcion)
```

La documentacion completa de decisiones tecnicas, reglas de linkage,
survivorship, colisiones de identificadores y salidas se encuentra en
[`README_TECNICO_PIPELINE_MDM.md`](06_Datos_Maestros_FHIR_MDM/README_TECNICO_PIPELINE_MDM.md).

## Ejecucion

Generacion de raw:

```bash
python 01_Generacion_de_Datos/generar_datos.py
```

Pipeline MDM:

```bash
python 05_Scripts_MDM/run_pipeline.py
```

La base relacional final se materializa en:

```text
06_Datos_Maestros_FHIR_MDM/06_relational_model/hospital_mdm_fhir.sqlite
```
