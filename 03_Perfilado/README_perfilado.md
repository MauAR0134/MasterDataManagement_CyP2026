# Perfilado de calidad de datos

Esta carpeta contiene la fase de perfilado del proyecto. El objetivo es analizar los archivos raw sin modificarlos.

## Archivos principales

```text
perfilado.py
perfilado_notebook.ipynb
```

### perfilado.py

Script reutilizable que lee los 27 CSV de `02_Datos_Crudos` y genera reportes en `03_Perfilado/reportes`.

Evalua:

```text
inventario de archivos
estructura de columnas
valores faltantes
duplicados exactos
duplicados por identificador
formatos invalidos
catalogos fuera de dominio
inconsistencias entre campos
outliers financieros y clinicos
candidatos preliminares a duplicados de paciente
score de calidad por archivo
```

### perfilado_notebook.ipynb

Notebook para ejecutar el perfilado de forma guiada. Cada seccion tiene:

```text
subtitulo
descripcion de lo que se revisa
codigo ejecutable
salida con hallazgos relevantes
```

## Reportes generados

Al ejecutar `perfilado.py` o la ultima celda del notebook, se crean:

```text
reportes/reporte_archivos.csv
reportes/reporte_columnas.csv
reportes/reporte_duplicados.csv
reportes/reporte_formatos_invalidos.csv
reportes/reporte_inconsistencias.csv
reportes/reporte_outliers.csv
reportes/reporte_candidatos_duplicados_paciente.csv
reportes/resumen_calidad_por_archivo.csv
```

## Ejecucion

Desde la carpeta `Perfilado`:

```text
python perfilado.py
```

Esta ejecucion no modifica los datos raw. Solo crea reportes descriptivos.
