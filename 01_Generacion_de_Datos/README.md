# 01 Generacion De Datos

Scripts y parametros para la construccion reproducible de las fuentes
sinteticas hospitalarias.

## Contenido

| Archivo | Funcion |
|---|---|
| `generation_config.py` | Semilla, volumen, sedes, tasas de error, coberturas y catalogos |
| `generar_datos.py` | Generacion de los 27 archivos CSV raw |
| `especificacion_generacion_datos.md` | Reglas de asignacion, identificadores y calidad simulada |
| `README_generacion_codigo.md` | Descripcion tecnica del generador |

## Salida

```text
../02_Datos_Crudos/[sistema]_[pais]_[anio].csv
```

Cardinalidad generada:

```text
transacciones: 15000
clinica: 15000
prescripciones: 8258
total: 38258
```
