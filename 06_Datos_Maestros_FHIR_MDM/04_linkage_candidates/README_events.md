# Event linkage

Genera `id_consulta` solo en la capa integrada. Clinica se enlaza a transacciones por pais, nombre estandarizado y una ventana de 0 a 14 dias; prescripciones por pais, nombre estandarizado y la misma fecha. Los empates y ausencias se conservan en `manual_review` con indices de origen. Las colisiones del ID raw se conservan en `id_consulta_original` y reciben un `id_consulta` curado con sufijo secuencial.
