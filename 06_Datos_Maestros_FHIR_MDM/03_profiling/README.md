# 03_profiling

Perfilado posterior a la estandarizacion, sin alterar registros. Incluye completitud, cardinalidad, duplicados y control de `monto_cobro` por moneda original mediante IQR. Los IDs repetidos asociados a diferentes nombres se envian a `manual_review/ids_duplicados_nombres_distintos.csv`, conservando indices de origen para facilitar la decision manual.
