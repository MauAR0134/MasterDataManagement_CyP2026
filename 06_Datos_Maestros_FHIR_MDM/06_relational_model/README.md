# 06_relational_model

Modelo curado inspirado en recursos FHIR. `Clientes_Patient`, `Administrativo`, `ContactPoints` y `Addresses` son dimensiones con un registro por `id_master`; contacto y direccion conservan el valor no vacio mas reciente.

`Transacciones_Encounter` conserva el monto original y expresa `monto_cobro`, `costo_meds` y `costo_total` en EUR. El tipo de cambio y los costos unitarios son parametros sinteticos configurables de `05_Scripts_MDM/mdm_config.py`. `id_trabajador` proviene del medico asignado a la consulta en transacciones raw y se propaga a prescripciones enlazadas por `id_consulta`.

`Prescripcion_Detalle_Medicamento.csv` se relaciona con la solicitud mediante `id_farmacia`. Se eliminan unidades cero o negativas; las positivas altas se mantienen con bandera de outlier. `Solicitudes_Bimestrales.csv` agrega unidades validas y positivas por medicamento.

Pendiente: preprocesamiento analitico de variables biologicas de `Clinico_Observation`.
