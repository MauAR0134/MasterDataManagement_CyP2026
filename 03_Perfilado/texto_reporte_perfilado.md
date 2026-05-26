# 7. Perfilado de Datos

El perfilado de datos se realizo sobre los 27 archivos CSV generados para los tres sistemas de la red hospitalaria internacional: transacciones, sistema clinico y prescripciones. El objetivo de esta fase fue evaluar la estructura general de las fuentes, identificar valores nulos, revisar duplicados exactos y detectar posibles conflictos de identificadores antes de aplicar cualquier proceso de limpieza o fusion. Para conservar la trazabilidad, cada archivo fue analizado considerando su sistema de origen, sede y anio.

## 7.1 Perfilado de Transacciones

El sistema de transacciones agrupa los registros administrativos y financieros asociados a los servicios medicos. Esta fuente es la base operativa del proyecto, ya que los registros clinicos y de prescripciones dependen de la existencia de una transaccion previa. Tambien contiene `medico_cargo`, atributo obligatorio del profesional responsable de cada consulta. Durante el perfilado se consolidaron los archivos de Mexico, Estados Unidos y Espana para los anios 2023, 2024 y 2025.

### 7.1.1 Valores nulos

La revision de valores nulos en transacciones se enfoco en campos criticos para contacto, identificacion y trazabilidad financiera, como `telefono_contacto`, `correo_electronico`, `direccion`, `monto_cobro`, `fecha` y `fecha_primer_registro`. El conteo de nulos permite dimensionar problemas de completitud que pueden afectar procesos como contacto con pacientes, validacion de identidad, conciliacion de pagos y seguimiento historico. En particular, los campos de contacto son relevantes porque posteriormente pueden servir como evidencia para vincular registros entre sistemas.

### 7.1.2 Duplicados

El analisis de duplicados considero dos niveles: filas duplicadas exactas e identificadores de transaccion repetidos. Las filas duplicadas exactas indicarian registros cargados mas de una vez sin ninguna diferencia entre columnas. Los IDs repetidos, por otro lado, podrian senalar colisiones o errores de generacion/captura. Adicionalmente, se reviso si un mismo `id_transaccion` estaba asociado con nombres de paciente diferentes, ya que esto representaria una inconsistencia grave de identidad y trazabilidad financiera.

## 7.2 Perfilado de Sistema Clinico

El sistema clinico contiene variables de laboratorio y signos medicos, tales como glucosa, colesterol, trigliceridos, hemoglobina, presion arterial, peso, altura, tipo de sangre, fumador y oxigenacion. Esta fuente es fundamental para evaluar condiciones de salud y construir analisis descriptivos o predictivos posteriores.

### 7.2.1 Valores nulos

La revision de nulos en el sistema clinico se concentro en las mediciones necesarias para interpretar el estado de salud del paciente. La ausencia de valores en variables como glucosa, colesterol, hemoglobina, presion arterial u oxigenacion puede limitar la deteccion de riesgos clinicos, generar sesgos en analisis posteriores o impedir comparaciones entre sedes. Por esta razon, el perfilado identifica tanto el total de faltantes por variable como el porcentaje de nulos por archivo.

### 7.2.2 Duplicados

En el sistema clinico se revisaron filas duplicadas exactas y repeticiones del identificador `id_lab`. Debido a que este identificador se construye a partir de componentes del nombre, sexo y fecha de primer registro, puede presentar colisiones en pacientes con nombres similares o fechas coincidentes. Por ello, tambien se revisaron los nombres asociados a cada `id_lab` repetido, con el fin de identificar posibles conflictos de identidad que deberan resolverse en la fase de datos maestros.

## 7.3 Perfilado de Prescripciones

El sistema de prescripciones registra solicitudes efectivas de medicamentos y la sucursal que las dispensa. Esta fuente es importante para analizar demanda de medicamentos dentro de la red hospitalaria; el medico responsable se obtiene posteriormente desde la consulta enlazada.

### 7.3.1 Valores nulos

El perfilado de nulos en prescripciones se centro en `nombre_completo`, `medicamentos_unidades`, `fecha_prescripcion` y `sucursal`. La completitud en estos atributos es necesaria para conocer que medicamentos fueron solicitados y donde se dispensaron. El responsable medico se valida mediante el enlace posterior con `transacciones.medico_cargo`.

### 7.3.2 Duplicados

Para prescripciones se analizaron duplicados exactos e identificadores `id_farmacia` repetidos. Como `id_farmacia` identifica registros de prescripcion y no necesariamente pacientes, su repeticion puede indicar errores administrativos o duplicidad en solicitudes. Tambien se reviso si un mismo identificador aparece con nombres de paciente distintos, lo que representaria un conflicto de trazabilidad entre receta, paciente y sucursal.
