# Especificacion de generacion de datos sinteticos

Proyecto: Gestion de Datos Maestros para una Red Hospitalaria Internacional mediante un Modelo Relacional inspirado en FHIR.

Esta especificacion define las reglas para generar archivos sinteticos de tres sistemas hospitalarios: transacciones, sistema clinico y prescripciones. La generacion se realizara con una poblacion base controlada, de modo que los registros puedan vincularse entre sistemas durante la etapa de deduplicacion, fusion y obtencion de datos maestros.

## 1. Convencion de archivos

Todos los archivos generados deben seguir la convencion:

```text
[sistema]_[sede]_[anio].csv
```

Sistemas:

```text
transacciones
clinica
prescripciones
```

Sedes:

```text
mexico
estados_unidos
espana
```

Anios:

```text
2023
2024
2025
```

Total esperado de archivos:

```text
3 sistemas x 3 sedes x 3 anios = 27 archivos CSV
```

Ejemplos:

```text
transacciones_mexico_2025.csv
clinica_estados_unidos_2024.csv
prescripciones_espana_2023.csv
```

## 2. Arquitectura general de generacion

La tecnica seleccionada es generacion sintetica basada en reglas con una poblacion base.

Primero se creara una poblacion base interna de pacientes sinteticos. Esta poblacion no representa un archivo final de entrega, sino una verdad controlada desde la cual se derivaran los registros de los tres sistemas.

```text
Poblacion base de pacientes
        |
        |-- Sistema de transacciones
        |-- Sistema clinico
        |-- Sistema de prescripciones
```

La poblacion base permitira generar coincidencias realistas entre sistemas, introducir variaciones controladas en nombres y datos de contacto, y conservar una referencia interna para evaluar la calidad de la fusion posterior.

## 3. Definicion de indices e identificadores

Los identificadores visibles en los sistemas no seran llaves maestras universales. Cada sistema tendra su propio identificador, siguiendo reglas distintas y con posibilidad de colisiones o ambiguedad. Esto justifica la necesidad de record linkage y gestion de datos maestros.

### 3.1 Identificador interno de poblacion base

Campo interno no exportado en los CSV finales:

```text
id_paciente_base
```

Formato sugerido:

```text
PB_[sede]_[consecutivo]
```

Ejemplo:

```text
PB_MEX_000001
PB_USA_000235
PB_ESP_000087
```

Este identificador solo se usara durante la generacion para controlar coincidencias. No debe aparecer en las fuentes raw finales.

### 3.2 id_transaccion

El campo `id_transaccion` se generara a partir de componentes del nombre, sexo, sede y fecha de transaccion.

Regla base:

```text
[inicial nombre][inicial apellido paterno][inicial apellido materno]_[sexo]_[sede]_[dia][mes]_[consecutivo corto]
```

Ejemplo:

```text
JGL_M_MEX_1804_03
MFH_F_ESP_1209_01
```

Consideraciones:

- Puede haber colisiones parciales entre pacientes con iniciales similares.
- El consecutivo corto reduce colisiones, pero no convierte el identificador en llave maestra.
- El ID depende del registro de transaccion, no de la identidad consolidada del paciente.

### 3.3 id_lab

El campo `id_lab` se generara usando componentes del nombre completo, sexo y fecha del primer registro historico.

Regla base:

```text
[primeras 2 letras nombre][primeras 2 letras apellido paterno][primeras 2 letras apellido materno]_[sexo]_[dia][mes]
```

Ejemplo:

```text
MAHELO_F_1203
JOGALO_M_2508
```

Consideraciones:

- Si el sistema clinico recibe una variante del nombre, el `id_lab` puede diferir respecto a otros sistemas.
- Puede haber pacientes diferentes con identificadores parecidos.
- Este campo no debe asumirse como identificador maestro.

### 3.4 id_farmacia

El campo `id_farmacia` sera un identificador administrativo por registro de prescripcion.

Regla base:

```text
FARM_[sede]_[anio]_[consecutivo]
```

Ejemplo:

```text
FARM_MEX_2025_000123
FARM_USA_2024_000045
```

Consideraciones:

- Identifica la prescripcion, no al paciente.
- La vinculacion con transacciones y clinica dependera de nombre, fecha, sucursal y otros atributos.

## 4. Poblacion base

La poblacion base contendra atributos demograficos, administrativos y clinicos latentes. Estos atributos se usaran para derivar los valores visibles en cada sistema.

Campos internos sugeridos:

```text
id_paciente_base
nombre
apellido_paterno
apellido_materno
sexo
fecha_nacimiento
sede_base
telefono_base
correo_base
direccion_base
tipo_sangre
riesgo_clinico
condiciones_probables
fecha_primer_registro_real
```

Sedes:

```text
mexico
estados_unidos
espana
```

Anios activos:

```text
2023
2024
2025
```

Volumen total objetivo para todos los archivos generados:

```text
35000 a 40000 registros en total
```

Este total incluye transacciones, clinica y prescripciones de todos los anios y sedes.

Distribucion recomendada del total:

```text
transacciones: 14500 a 15500 registros
clinica: 14500 a 15500 registros
prescripciones: 7800 a 8700 registros
```

La distribucion exacta se controlara desde un archivo de configuracion para poder regenerar los datos con otros volumenes.

La escala base sera de aproximadamente 5000 registros de transacciones por sede considerando los tres anios. Como existen tres sedes, el sistema de transacciones tendra alrededor de 15000 registros globales.

La proporcion de pacientes unicos por sede sera de aproximadamente 45% respecto al numero de transacciones de esa sede. Esto significa que, si una sede tiene cerca de 5000 transacciones en total, debera tener alrededor de 2250 pacientes unicos. El 55% restante de registros corresponde a pacientes repetidos por nuevas consultas, visitas en distintos anios o multiples servicios.

Distribucion aproximada por sede:

```text
transacciones por sede, 2023-2025: ~5000 registros
pacientes unicos por sede: ~2250 pacientes
transacciones por paciente unico: promedio cercano a 2.2
```

Distribucion aproximada por sede y anio:

```text
transacciones: 1550 a 1750 registros
clinica: 1550 a 1750 registros
prescripciones: 850 a 1000 registros
```

Resumen aproximado por sistema y sede:

| Sistema | Registros por sede/anio | Registros por sede total 2023-2025 |
|---|---:|---:|
| transacciones | 1550 a 1750 | ~5000 |
| clinica | 1550 a 1750 | ~5000 |
| prescripciones | 850 a 1000 | ~2750 |

Resumen aproximado por sede:

| Sede | Transacciones | Clinica | Prescripciones | Total aproximado |
|---|---:|---:|---:|---:|
| mexico | ~5000 | ~5000 | ~2750 | ~12750 |
| estados_unidos | ~5000 | ~5000 | ~2750 | ~12750 |
| espana | ~5000 | ~5000 | ~2750 | ~12750 |

Resumen global estimado:

```text
transacciones: ~15000 registros
clinica: ~15000 registros
prescripciones: ~8250 registros
global: ~38250 registros
```

## 5. Regla de dependencia entre sistemas

La existencia de registros debe respetar la logica operativa del negocio:

```text
Si un paciente no aparece en transacciones, no puede aparecer en clinica ni en prescripciones.
```

Por lo tanto, el sistema de transacciones sera la fuente obligatoria de aparicion. Clinica y prescripciones solo podran generarse para pacientes que ya tengan una transaccion asociada en la misma sede y anio.

Reglas de cobertura propuestas entre pacientes con transaccion:

```text
Transacciones: 100% de los pacientes activos generados para el sistema.
Clinica: 100% de las consultas/transacciones.
Prescripciones: aproximadamente 55% de las consultas/transacciones, solo cuando se solicita medicamento.
Aparecen en los 3 sistemas: aproximadamente 55% de las consultas.
Aparecen en transacciones y clinica: aproximadamente 45% de las consultas.
Aparecen solo en transacciones: 0%.
```

Restricciones:

- No debe existir registro clinico sin registro de transaccion.
- No debe existir registro de prescripcion sin registro de transaccion.
- Toda transaccion debe tener un registro clinico correspondiente con variables obligatorias de consulta regular.
- Toda prescripcion representa una solicitud real de medicamentos; por lo tanto, no incluye banderas redundantes de tratamiento o pedido.
- Las coincidencias no deben ser demasiado desconectadas; la mayoria de pacientes deben poder vincularse mediante combinaciones de nombre, fecha, telefono, sucursal o sede.
- La mayoria de pacientes con actividad clinica relevante deben aparecer en dos o tres sistemas, para que la gestion de datos maestros tenga suficiente evidencia de integracion.
- Los registros de clinica y prescripciones se seleccionaran desde el universo de transacciones existentes de la misma sede y anio.

## 6. Reglas regionales

Cada region tendra nombres, telefonos, direcciones, moneda y formato de fecha predominante distintos.

### 6.1 Mexico

Formato de fecha regional:

```text
DD/MM/YYYY
```

Ejemplo:

```text
18/04/2025
```

Telefonos:

```text
+52 55 1234 5678
55-1234-5678
5512345678
```

Moneda implicita:

```text
MXN
```

Direcciones:

```text
Calle, Avenida, Colonia, Alcaldia o Municipio, Estado
```

### 6.2 Estados Unidos

Formato de fecha regional:

```text
MM/DD/YYYY
```

Ejemplo:

```text
04/18/2025
```

Telefonos:

```text
+1 202-555-0145
(202) 555-0145
2025550145
```

Moneda implicita:

```text
USD
```

Direcciones:

```text
Street, Avenue, City, State, ZIP
```

### 6.3 Espana

Formato de fecha regional:

```text
YYYY-MM-DD
```

Ejemplo:

```text
2025-04-18
```

Telefonos:

```text
+34 612 345 678
612-345-678
612345678
```

Moneda implicita:

```text
EUR
```

Direcciones:

```text
Calle, Avenida, Piso, Provincia, Codigo postal
```

## 7. Reglas generales para fechas

Las fechas operativas utilizadas para relacionar hechos deben conservar validez completa:

```text
fecha
fecha_estudios
fecha_prescripcion
```

Distribucion de calidad para fechas operativas:

```text
Fecha valida: 100%
Fecha invalida: 0%
Fecha faltante: 0%
```

Estas fechas deben seguir el formato regional correspondiente a la sede. Esta regla permite asociar posteriormente transacciones con observaciones clinicas dentro de 14 dias y prescripciones con transacciones de la misma fecha.

La variable historica `fecha_primer_registro` conserva errores controlados para el ejercicio de calidad:

```text
Fecha valida: 97%
Fecha invalida: 3%
Fecha faltante: 0%
```

Fechas invalidas posibles:

```text
31/02/2025
13/40/2024
2025-15-99
99/99/2023
```

Restricciones temporales:

- Las fechas operativas del archivo deben ser validas y permitir la integracion temporal de eventos.
- `fecha_primer_registro` debe ser anterior o igual a la fecha de transaccion en la mayoria de los casos.
- Las fechas invalidas se usaran para evaluar validez y limpieza, no como valores faltantes.

## 8. Variaciones de identidad entre sistemas

A partir del nombre base del paciente se generaran variantes por sistema.

Ejemplo base:

```text
Maria Fernanda Hernandez Lopez
```

Variantes posibles:

```text
Maria Fernanda Hernandez Lopez
Maria F. Hernandez Lopez
M. Fernanda Hernandez
MARIA HERNANDEZ LOPEZ
Maria Hernandez
Maria Fernanda Hdez Lopez
```

Distribucion propuesta:

```text
Nombre exacto o casi exacto: 60%
Sin acentos: 15%
Iniciales o abreviaturas: 10%
Mayusculas completas: 5%
Un apellido omitido: 7%
Error tipografico leve: 3%
```

Estas variaciones deben aplicarse de manera controlada para permitir el linkage, no para volver imposible la integracion.

## 9. Sistema de transacciones

Archivo:

```text
transacciones_[sede]_[anio].csv
```

Variables:

```text
id_transaccion
fecha
nombre_paciente
tipo_consulta
telefono_contacto
correo_electronico
direccion
monto_cobro
metodo_pago
registro_previo
fecha_primer_registro
```

### 9.1 Asignacion de tipo_consulta

Catalogo sugerido:

```text
general
cardiologia
odontologia
neurologia
endocrinologia
pediatria
urgencias
```

Distribucion sugerida:

```text
general: 30%
cardiologia: 15%
odontologia: 12%
neurologia: 10%
endocrinologia: 12%
pediatria: 8%
urgencias: 13%
```

### 9.2 Montos por sede y consulta

Mexico, moneda implicita MXN:

```text
general: 500 a 1200
cardiologia: 1200 a 3000
odontologia: 800 a 2500
neurologia: 1800 a 4000
endocrinologia: 1000 a 2800
pediatria: 500 a 1500
urgencias: 1500 a 6000
```

Estados Unidos, moneda implicita USD:

```text
general: 80 a 250
cardiologia: 250 a 900
odontologia: 120 a 600
neurologia: 300 a 1200
endocrinologia: 200 a 850
pediatria: 90 a 300
urgencias: 700 a 3500
```

Espana, moneda implicita EUR:

```text
general: 50 a 150
cardiologia: 120 a 400
odontologia: 80 a 350
neurologia: 150 a 500
endocrinologia: 100 a 350
pediatria: 60 a 180
urgencias: 200 a 900
```

Calidad de monto:

```text
Monto normal: 94%
Outlier alto: 3%
Monto cero: 1%
Monto negativo: 1%
Monto faltante: 1%
```

### 9.3 Metodo de pago

Distribucion sugerida:

```text
tarjeta: 45%
transferencia: 30%
efectivo: 25%
```

### 9.4 Registro previo

Distribucion sugerida:

```text
registro_previo = 1: 55%
registro_previo = 0: 45%
```

Si `registro_previo = 1`, `fecha_primer_registro` debe estar antes de la fecha de transaccion salvo errores controlados de fecha.

### 9.5 Correo electronico

El correo base sintetico sera unico por paciente mediante un consecutivo interno incorporado antes del dominio. Esto permite utilizar coincidencias exactas de correo valido como evidencia fuerte de identidad, mientras que los errores de calidad se aplican posteriormente sobre el valor exportado.

Distribucion de calidad:

```text
Correo valido: 82%
Correo faltante: 8%
Correo sin arroba: 4%
Dominio incompleto: 3%
Espacios o mayusculas: 3%
```

Ejemplos:

```text
maria.hernandez@gmail.com
maria.hernandezgmail.com
maria.hernandez@
MARIA.HERNANDEZ@GMAIL.COM
```

### 9.6 Telefono contacto

Distribucion de calidad:

```text
Formato valido local: 65%
Formato valido internacional: 20%
Separadores variados o caracteres extra: 7%
Longitud incorrecta: 5%
Telefono faltante: 3%
```

## 10. Sistema clinico

Archivo:

```text
clinica_[sede]_[anio].csv
```

Variables:

```text
id_lab
nombre_completo
sexo
fecha_nacimiento
edad
glucosa
colesterol_LDL
colesterol_HDL
trigliceridos
hemoglobina
frecuencia_card
presion_arterial
peso_kg
altura_cm
tipo_sangre
fumador
oxigenacion
fecha_estudios
```

Los registros clinicos se generaran para todas las transacciones en la misma sede y anio, pero el archivo raw clinico no incluye el identificador de transaccion. La asociacion posterior con una consulta se resolvera durante la integracion maestra usando paciente, pais y cercania de fechas.

Los campos `sexo` y `fecha_nacimiento` se incluyen en el sistema clinico porque son atributos demograficos de alta utilidad para la resolucion de entidades, generacion del `id_master` y validacion de consistencia del paciente.

Todos los registros clinicos incluyen obligatoriamente:

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

El 60% de los registros incluye ademas estudios de laboratorio completos:

```text
glucosa
colesterol_LDL
colesterol_HDL
trigliceridos
hemoglobina
```

El 40% restante representa consultas regulares sin panel de laboratorio solicitado, por lo que esos campos pueden estar vacios sin considerarse error de completitud.

### 10.1 Riesgo clinico

Cada paciente tendra un riesgo clinico base:

```text
bajo: 50%
medio: 35%
alto: 15%
```

Condiciones probables:

```text
diabetes
hipertension
dislipidemia
anemia
obesidad
tabaquismo
```

Las mediciones clinicas se generaran de acuerdo con edad, sexo, riesgo clinico y condiciones probables.

### 10.2 Edad

La edad se calculara a partir de la fecha de nacimiento y la fecha de estudios.

Calidad:

```text
Edad valida: 96%
Edad inconsistente por error: 4%
Edad faltante: 0%
```

### 10.3 Glucosa

Rangos:

```text
normal: 70 a 99
prediabetes: 100 a 125
diabetes: 126 a 250
outlier/error: 20, 500, 999
```

Asignacion:

- Pacientes con diabetes tendran mayor probabilidad de valores entre 126 y 250.
- Pacientes de bajo riesgo tendran mayor probabilidad de valores entre 70 y 99.

### 10.4 Colesterol LDL

Rangos:

```text
normal: 70 a 129
alto: 130 a 190
muy alto: 191 a 260
outlier/error: valores negativos o mayores a 400
```

### 10.5 Colesterol HDL

Rangos:

```text
bajo: 25 a 39
normal: 40 a 70
alto: 71 a 95
outlier/error: valores negativos o mayores a 150
```

### 10.6 Trigliceridos

Rangos:

```text
normal: 50 a 149
alto: 150 a 300
muy alto: 301 a 600
outlier/error: valores negativos o mayores a 1200
```

### 10.7 Hemoglobina

Rangos:

```text
mujeres normal: 12.0 a 15.5
hombres normal: 13.5 a 17.5
anemia: 8.0 a 11.9
outlier/error: menor a 5.0 o mayor a 25.0
```

### 10.8 Frecuencia cardiaca

Rangos:

```text
normal: 60 a 100
bradicardia: 40 a 59
taquicardia: 101 a 140
outlier/error: 0 o mayor a 220
```

### 10.9 Presion arterial

Formato valido:

```text
sistolica/diastolica
```

Ejemplos validos:

```text
120/80
135/88
150/95
```

Errores posibles:

```text
120-80
120/abc
999/80
```

### 10.10 Peso y altura

La altura se generara segun sexo y sede.

Rangos base:

```text
mujeres: 150 a 175 cm
hombres: 160 a 190 cm
```

El peso se generara de forma relacionada con la altura mediante categoria IMC.

Categorias IMC:

```text
normal: 45%
sobrepeso: 35%
obesidad: 15%
bajo peso: 5%
```

### 10.11 Tipo de sangre

Catalogo:

```text
A+
A-
B+
B-
AB+
AB-
O+
O-
```

Distribucion aproximada configurable por sede.

### 10.12 Fumador

Valores:

```text
0
1
```

Probabilidad base:

```text
fumador = 1: 22%
fumador = 0: 78%
```

La probabilidad puede aumentar en pacientes de riesgo medio o alto.

### 10.13 Oxigenacion

Rangos:

```text
normal: 95 a 100
baja: 88 a 94
critica: 80 a 87
outlier/error: menor a 50 o mayor a 100
```

Calidad general de mediciones clinicas:

```text
Valor clinico valido: 94% a 97%
Valor fuera de rango o outlier: 1% a 3%
Formato invalido donde aplique: 1% a 2%
Valor faltante: 0% a 3% segun variable, excepto fechas y edad que no tendran faltantes
```

## 11. Sistema de prescripciones

Archivo:

```text
prescripciones_[sede]_[anio].csv
```

Variables:

```text
id_farmacia
nombre_completo
medicamentos_unidades
fecha_prescripcion
medico_cargo
sucursal
```

Los registros de prescripcion solo se generaran cuando un paciente solicite medicamentos derivados de una consulta. El archivo raw de prescripciones no incluye el identificador de transaccion. La asociacion posterior con una consulta se resolvera durante la integracion maestra usando paciente, pais y coincidencia de fecha.

### 11.1 Medicamentos por condicion o consulta

La seleccion de medicamentos dependera de la condicion probable o tipo de consulta.

Diabetes:

```text
metformina
insulina
glibenclamida
```

Hipertension:

```text
losartan
enalapril
amlodipino
```

Dislipidemia:

```text
atorvastatina
rosuvastatina
```

Dolor o inflamacion:

```text
paracetamol
ibuprofeno
diclofenaco
```

Gastrointestinal:

```text
omeprazol
metoclopramida
```

### 11.2 medicamentos_unidades

Este campo simulara ser llenado por un software categorico automatico. Por esa razon, casi todos los registros tendran estructura valida y solo existiran errores de unidades inusuales.

Formato valido:

```text
medicamentoUnidad,medicamentoUnidad
```

Ejemplos validos:

```text
paracetamol1,diclofenaco2
losartan2,atorvastatina1
metformina2,insulina1
```

Distribucion de calidad:

```text
Formato y unidades validas: 98%
Unidades inusuales: 2%
```

Unidades inusuales:

```text
negativas: paracetamol-1
excesivas: losartan99
cero: metformina0
```

No se generaran errores de separador, nombres mal escritos, campos dobles vacios ni texto libre en este campo, porque se asume captura automatica/categorica.

### 11.3 Medico a cargo

Se generara desde catalogos sinteticos por sede.

Ejemplos:

```text
Dra. Ana Martinez
Dr. Carlos Hernandez
Dr. John Smith
Dra. Emily Johnson
Dra. Lucia Garcia
Dr. Javier Fernandez
```

### 11.4 Sucursal

La sucursal dependera de la sede.

Mexico:

```text
Hospital Central Mexico
Clinica Norte Mexico
Unidad Medica Sur Mexico
```

Estados Unidos:

```text
International Hospital USA
North Care Clinic USA
West Medical Center USA
```

Espana:

```text
Hospital Central Espana
Clinica Madrid Norte
Centro Medico Barcelona
```

## 12. Parametros configurables para el codigo

Cuando se construya el codigo de generacion, se debera crear un archivo de configuracion tipo requirements o parametros, por ejemplo:

```text
generation_requirements.yaml
```

o

```text
generation_config.py
```

Ese archivo debera contener, al menos:

```text
sedes
anios
rango_total_registros
volumen_por_sistema
formatos_fecha_por_sede
probabilidades_de_aparicion_por_sistema
probabilidades_de_variacion_de_nombre
probabilidades_de_error_por_campo
rangos_de_monto_por_sede_y_consulta
rangos_clinicos
catalogos_de_medicamentos
probabilidad_de_unidades_inusuales_en_prescripciones
semilla_aleatoria
```

Objetivo:

- Regenerar datos sin reescribir la logica principal.
- Cambiar volumen, porcentajes de error o rangos desde un solo lugar.
- Mantener trazabilidad metodologica para el reporte final.

## 13. Resumen de restricciones clave

```text
1. Se generaran 27 archivos CSV.
2. El total aproximado de registros en todos los sistemas sera de 35000 a 40000.
3. Transacciones es obligatorio: no puede haber clinica ni prescripcion sin transaccion.
4. Las fechas operativas de consulta, estudios y prescripcion seran validas para permitir vinculacion temporal; `fecha_primer_registro` conserva 3% de valores invalidos para perfilado.
5. Cada sede tendra formato regional de fecha distinto.
6. medicamentos_unidades tendra 98% valores validos y 2% errores solo por unidades inusuales.
7. La poblacion base controlara las coincidencias entre sistemas.
8. Los IDs de sistemas no seran llaves maestras universales.
9. El modelo canonico y la gestion de datos maestros seran el punto fuerte posterior del proyecto.
10. El sistema de transacciones tendra aproximadamente 5000 registros por sede considerando 2023, 2024 y 2025.
11. Cada sede tendra aproximadamente 45% de pacientes unicos respecto a su volumen de transacciones.
12. Clinica y prescripciones tendran menor volumen que transacciones, pero alta coincidencia con ella.
```
