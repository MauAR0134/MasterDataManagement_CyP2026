# Documentacion del codigo de generacion

Esta carpeta contiene los scripts para generar los datos sinteticos raw del proyecto. Los archivos finales se escribiran en:

```text
../02_Datos_Crudos
```

El generador crea 27 archivos CSV:

```text
3 sistemas x 3 sedes x 3 anios = 27 archivos
```

## Archivos

### generation_config.py

Contiene los parametros modificables de la generacion. Su objetivo es funcionar como archivo tipo requirements/configuracion para no tener que cambiar la logica principal cuando se quiera regenerar el dataset.

Define:

```text
sedes
anios
semilla aleatoria
carpeta de salida
volumen de transacciones por sede y anio
proporcion de pacientes unicos por sede
probabilidades de aparicion en clinica y prescripciones
formatos regionales de fecha
probabilidades de errores por campo
rangos monetarios por sede y tipo de consulta
rangos y reglas clinicas
catalogos de nombres, doctores, sucursales y medicamentos
probabilidad de unidades inusuales en medicamentos_unidades
```

Valores clave actuales:

```text
transacciones por sede, 2023-2025: 5000
pacientes unicos por sede: 45% del volumen de transacciones, aproximadamente 2250
clinica: 100% de las transacciones
prescripciones: aproximadamente 55% de las transacciones, solo cuando hay solicitud de medicamentos
fechas operativas validas (consulta, estudios y prescripcion): 100%
fecha_primer_registro valida: 97%
fecha_primer_registro invalida: 3%
fechas faltantes: 0%
medicamentos_unidades validos: 98%
medicamentos_unidades con unidades inusuales: 2%
```

El archivo deja abierto un escenario de mayor escala:

```text
TRANSACTION_VOLUME_MODE = "per_site_total"
```

Ese es el modo actual. Reparte `transaction_total = 5000` entre los tres anios de cada sede.

Si en el futuro se quiere generar aproximadamente 5000 transacciones por sede y por anio, se puede cambiar a:

```text
TRANSACTION_VOLUME_MODE = "per_site_year"
```

Con ese cambio, cada sede tendria 5000 transacciones en 2023, 5000 en 2024 y 5000 en 2025. El resto de sistemas escalaria desde esas transacciones usando las probabilidades de cobertura configuradas.

### generar_datos.py

Es el generador principal. Usa solo biblioteca estandar de Python y toma todos sus parametros desde `generation_config.py`.

Flujo tecnico:

```text
1. Fija la semilla aleatoria.
2. Crea una poblacion base por sede.
3. Genera transacciones como sistema obligatorio.
4. Genera registros clinicos solamente desde transacciones existentes.
5. Genera prescripciones solamente desde transacciones existentes.
6. Escribe los 27 CSV en Datos Raw.
```

La poblacion base no se exporta a los CSV finales. Se usa internamente para controlar coincidencias entre sistemas y permitir despues deduplicacion, record linkage y fusion de datos maestros.

## Relacion entre sistemas

El sistema de transacciones es obligatorio:

```text
si no existe transaccion, no puede existir clinica ni prescripcion
```

Por eso `generar_datos.py` primero crea los registros de transacciones y guarda un contexto interno por registro. Clinica y prescripciones se generan seleccionando subconjuntos de esos contextos.

Esto garantiza:

```text
no hay laboratorio sin cobro
no hay receta sin cobro
las coincidencias entre sistemas no quedan demasiado desconectadas
```

Los registros clinicos y de prescripciones no incluyen `id_consulta` en raw. La relacion con la consulta original se construira despues en la integracion maestra mediante resolucion de entidades y cercania de fechas entre paciente, sede y evento.

El sistema clinico incluye `sexo` y `fecha_nacimiento` como atributos demograficos necesarios para la resolucion de entidades y la construccion posterior del `id_master`. Cada transaccion genera una consulta clinica con datos obligatorios; aproximadamente 60% incluye panel de laboratorio completo.

Cada transaccion incluye `medico_cargo` como atributo obligatorio de la consulta. El valor se selecciona de forma deterministica dentro del catalogo de medicos del pais para no alterar aleatoriamente los restantes atributos del evento al regenerar.

Prescripciones solo contiene solicitudes efectivas de medicamentos. Por eso no se incluyen las columnas redundantes `tratamiento`, `pedido` ni `medico_cargo`: la fecha de prescripcion coincide con la fecha de la transaccion y el medico se deriva del Encounter enlazado en el modelo curado.

Los correos base se crean como valores unicos por paciente antes de insertar valores faltantes o formatos invalidos, para que los correos validos coincidentes puedan usarse como evidencia fuerte en la resolucion de entidades.

## Identificadores

Los identificadores se crean de acuerdo con la especificacion:

```text
id_transaccion:
iniciales del paciente + sexo + sede + dia/mes + consecutivo corto

id_lab:
componentes del nombre + sexo + dia/mes de primer registro

id_farmacia:
FARM_[sede]_[anio]_[consecutivo]
```

Estos IDs no son llaves maestras universales. Estan disenados para ser utiles, pero imperfectos, y asi justificar la fase de gestion de datos maestros.

## Fechas

Cada sede usa un formato regional:

```text
mexico: DD/MM/YYYY
estados_unidos: MM/DD/YYYY
espana: YYYY-MM-DD
```

La funcion `maybe_invalid_date` aplica:

```text
97% fecha valida
3% fecha invalida
0% fecha faltante
```

## Datos clinicos

Cada paciente recibe un riesgo clinico:

```text
bajo
medio
alto
```

Despues se asignan condiciones probables como diabetes, hipertension, dislipidemia, anemia, obesidad y tabaquismo. Los valores clinicos se generan de forma dependiente de esas condiciones para que los datos no sean puramente aleatorios.

Ejemplos:

```text
diabetes aumenta glucosa
hipertension aumenta presion arterial
dislipidemia aumenta LDL y trigliceridos
anemia reduce hemoglobina
obesidad afecta peso e IMC
```

## Prescripciones

El campo `medicamentos_unidades` simula captura automatica por software categorico.

Formato valido:

```text
medicamentoUnidad,medicamentoUnidad
```

Ejemplos:

```text
paracetamol1,diclofenaco2
losartan2,atorvastatina1
metformina2,insulina1
```

Errores permitidos:

```text
unidades negativas
unidades cero
unidades excesivas
```

No se generan errores de separador, medicamentos mal escritos ni texto libre en ese campo.

## Ejecucion futura

Cuando se decida generar los datos, el comando sera:

```text
python generar_datos.py
```

Debe ejecutarse desde la carpeta `Generacion de Datos` o usando la ruta completa del archivo.

Por ahora los scripts quedaron creados, pero el generador no fue ejecutado.
