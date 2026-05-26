# Master Patient Index

Contiene la entidad `Clientes_Patient` y el mapeo de consultas hacia `id_master`. El identificador sigue `NoApAp_ddmmyyyyS_mmyyyy`. Las reglas de matching y sus umbrales estan centralizadas en `05_Scripts_MDM/mdm_config.py`.

Survivorship aplicado: nombre estandarizado mas largo; DOB y sexo por valor mas frecuente. Cuando DOB tiene empate conflictivo, queda vacia en Patient, se marca `DOB_CONFLICT` y se conservan sus valores observados. Conflictos no concluyentes y scores intermedios permanecen en `manual_review`.
