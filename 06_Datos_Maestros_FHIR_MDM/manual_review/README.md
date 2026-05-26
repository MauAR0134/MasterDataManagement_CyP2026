# manual_review

Archivos que requieren revision humana o evidencian errores de calidad. Cada salida conserva IDs e indices de origen (`source_record_key`) para regresar al registro original.

## Salidas

| Archivo | Uso |
|---|---|
| `posibles_matches_revision_manual.csv` | Pares de identidad no concluyentes |
| `plantilla_decision_pares_pendientes.csv` | Formato para registrar `MATCH` o `NO_MATCH` |
| `conflictos_dob.csv` | Pares con DOB diferente aun ambiguos |
| `dob_conflictos_auto_resueltos.csv` | Pares unidos por evidencia fuerte con conflicto documentado |
| `dob_conflictos_descartados_por_nombre.csv` | Pares descartados por identidad incompatible |
| `id_consulta_collisions_classified.csv` | Eventos reasignados por colision del ID raw |
| `ids_duplicados_nombres_distintos.csv` | Conflictos de IDs de sistema fuente |
| `clinical_event_ambiguous_links.csv` | Alternativas de enlace clinico |
| `prescription_event_ambiguous_links.csv` | Alternativas de enlace farmaceutico |

`transactions_without_prescription.csv` identifica consultas sin solicitud de medicamentos; no representa un error de integridad.
