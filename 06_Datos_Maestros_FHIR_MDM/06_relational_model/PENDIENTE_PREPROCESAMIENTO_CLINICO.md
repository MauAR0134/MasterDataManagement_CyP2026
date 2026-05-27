# Preprocesamiento Clinico

Implementado en `05_Scripts_MDM/10_preprocess_clinico.py`.

## Variables procesadas

```text
edad
glucosa
colesterol_LDL
colesterol_HDL
trigliceridos
hemoglobina
frecuencia_card
presion_arterial  ->  presion_sistolica / presion_diastolica
peso_kg
altura_cm
fumador
oxigenacion
```

## Procesos implementados

```text
conversion y validacion numerica          -- to_float() con flag no_numericos
separacion sistolica/diastolica           -- parse_presion() sobre "NNN/NNN"
calculo de IMC                            -- peso_kg / (altura_cm/100)^2
clasificacion descriptiva de rangos       -- classify_range() con RANGOS biologicos
perfilado de outliers biologicos IQR      -- percentile() Q1-1.5*IQR / Q3+1.5*IQR
bandera de panel de laboratorio completo  -- panel_laboratorio_completo = "1"/"0"
deteccion de duplicados exactos y por ID  -- detect_duplicates()
```

## Salidas generadas

| Archivo | Descripcion |
|---|---|
| `06_relational_model/Clinico_Observation_preprocessed.csv` | Tabla original + columnas derivadas |
| `03_profiling/clinico_resumen_calidad.csv` | Estadisticos IQR y completitud por variable |
| `manual_review/clinico_duplicados.csv` | Registros duplicados para revision |
| `manual_review/clinico_outliers_biologicos.csv` | Filas outlier por variable |

## Nota sobre valores faltantes del panel

Los valores faltantes del panel de laboratorio no se imputan.
Representan consultas sin estudios completos y se reflejan en
`panel_laboratorio_completo = "0"`.
