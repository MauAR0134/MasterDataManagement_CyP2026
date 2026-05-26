# 06_relational_model

Modelo curado inspirado en recursos FHIR:

- `Clientes_Patient.csv`: entidad maestra del paciente (`Patient`).
- `Transacciones_Encounter.csv`: consultas/cobros (`Encounter` / `ChargeItem`).
- `Clinico_Observation.csv`: signos y laboratorio (`Observation`).
- `Prescripciones_MedicationRequest.csv`: solicitudes de medicamentos (`MedicationRequest`).
- `Workers_Practitioner.csv`: personal medico (`Practitioner`).
- `Administrativo.csv`, `ContactPoints.csv`, `Addresses.csv`: datos administrativos y contacto.

`id_consulta` es el identificador curado del evento; `id_consulta_original` conserva el identificador recibido de transacciones. Las colisiones raw reciben sufijos solo en la capa curada.

`Medicamentos_Cost.csv` y `Solicitudes_Bimestrales.csv` se dejan con esquema vacio hasta parsear medicamentos y definir costos.
