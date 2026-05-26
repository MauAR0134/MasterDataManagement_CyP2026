# 02_standardized

Capa estandarizada para integracion. Las columnas originales se conservan y se agregan:

- `full_name_std`, `nombre_std`, `apellido1_std`, `apellido2_std`;
- `nombre_soundex`, `apellido1_soundex`;
- fechas ISO por sistema;
- `phone_std` y `email_std` donde existen;
- `birth_date_iso` y `sex` desde el sistema clinico.

Los nombres quedan en minusculas, sin acentos, sin puntuacion y sin espacios sobrantes.
