# 02 Datos Crudos

Capa raw generada para la integracion. Los archivos siguen la convencion:

```text
[sistema]_[pais]_[anio].csv
```

## Inventario

| Sistema | Archivos | Registros |
|---|---:|---:|
| `transacciones` | 9 | 15,000 |
| `clinica` | 9 | 15,000 |
| `prescripciones` | 9 | 8,237 |

Paises: `mexico`, `estados_unidos`, `espana`.

Anios: `2023`, `2024`, `2025`.

Esta capa es entrada del pipeline MDM y no contiene transformaciones de
estandarizacion, matching o resolucion de identidad.
