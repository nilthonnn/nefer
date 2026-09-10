# Esquema del manifiesto JSON

El manifiesto es la única entrada del sistema. De él salen el Excel, el PDF, la
hoja de consumibles y las guías. Todo lo que no esté en el manifiesto no
aparece en el acta.

Valide siempre antes de construir:

```bash
python -m nefer validar acta.json
```

## Estructura

```json
{
  "encabezado": {
    "empresa": "Maquinarias del Sur S.A.C.",
    "tipo_documento": "DESPACHO",
    "n_acta": "001-000123",
    "n_guia": "T001-00004567",
    "cliente": "CONSTRUCTORA ANDINA S.A.C.",
    "obra": "PROYECTO DE AMPLIACIÓN — UNIDAD MINERA NORTE",
    "fecha": "2026-08-26",
    "horometro": 1548.7,
    "codigo_equipo": "GE074-01",
    "modelo_equipo": "GRUPO ELECTRÓGENO INSONORIZADO DE 74 KW (POT. CONTINUA)",
    "categoria": "grupo_electrogeno"
  },
  "inspeccion_componentes": [
    {
      "item": "Módulo de control DeepSea",
      "estado": "OK",
      "observacion": "Sin códigos de falla en pantalla."
    }
  ],
  "registro_fotografico": [
    {
      "foto_id": 1,
      "descripcion": "VISTA FRONTAL",
      "archivo": "fotos/frontal.jpg"
    }
  ],
  "consumibles": [
    {
      "descripcion": "EXTINTOR DE 6 KG",
      "cantidad": 1,
      "estado_recepcion": "NO_RETORNA",
      "foto_despacho": "fotos/extintor-despacho.jpg",
      "foto_recepcion": null
    }
  ],
  "control_consumibles": [
    {
      "consumible": "Combustible diésel",
      "unidad": "%",
      "despacho": 100,
      "recepcion": 35,
      "estado": "OBS",
      "observacion": "Rellenar antes del próximo despacho."
    }
  ],
  "resumen_ejecutivo": "Equipo operativo; retorna sin barra de tierra, se genera recuperación."
}
```

## `encabezado`

| Campo | Obligatorio | Reglas |
|---|---|---|
| `empresa` | no | Razón social. Si se omite, el acta sale sin ella |
| `tipo_documento` | **sí** | `DESPACHO` o `RECEPCION`. Decide en qué casilla va la **X** |
| `n_acta` | no | Número correlativo del acta |
| `n_guia` | no | Guía de remisión. Sin guía el equipo no sale de patio |
| `cliente` | **sí** | Razón social completa |
| `obra` | no | Sitio de entrega o recepción |
| `fecha` | **sí** | `YYYY-MM-DD`. Se imprime como `DD/MM/YYYY` |
| `horometro` | **sí** | Número de horas, o la cadena `REVISIÓN MANUAL REQUERIDA` si la lectura es ilegible |
| `codigo_equipo` | **sí** | Código interno del equipo (`GE074-01`, `PLT010-02`) |
| `modelo_equipo` | **sí** | Descripción del equipo tal como va en el acta |
| `categoria` | no | Define los rótulos sugeridos y la tabla de consumibles |
| `logo` | no | Ruta al logo de la organización; si se omite, el acta sale sin logo. Si se declara, el archivo debe existir |
| `codigo_formato` | no | Bloque de control documental. Por defecto `FO-DR-001` |
| `version_formato` | no | Por defecto `00` |
| `fecha_formato` | no | Fecha de emisión del formato. Vacía por defecto |

Categorías: `grupo_electrogeno`, `torre_iluminacion`, `compresor`, `plataforma_elevacion`,
`maquinaria_amarilla`, `generico`.

### Horómetro ilegible

Cuando la foto no permite leer el valor con certeza, el manifiesto lleva
`"horometro": "REVISIÓN MANUAL REQUERIDA"`. El acta imprime esa leyenda sobre
fondo amarillo en lugar de un número, para que nadie la firme como si fuera una
lectura. Nunca se estima un valor aproximado.

## `inspeccion_componentes`

Lista libre. Cada elemento:

- `item` (**obligatorio**): componente inspeccionado.
- `estado` (**obligatorio**): `OK` funcional, `OBS` observado, `D` dañado.
- `observacion`: **obligatoria** cuando el estado es `OBS` o `D`.

Se imprime en la hoja `INSPECCIÓN`.

## `registro_fotografico`

El orden de la lista es el orden de la rejilla del formato: la foto 1 va arriba
a la izquierda, la 2 arriba a la derecha, y así sucesivamente. Cada par de fotos
ocupa un bloque de 15 filas.

- `foto_id` (**obligatorio**): entero positivo y único.
- `descripcion` (**obligatoria**): es el rótulo gris que se imprime bajo la foto.
- `archivo`: ruta relativa al JSON. PNG, JPG, GIF o BMP.
- `celda_excel_destino`: informativo. Lo calcula el sistema; si usted lo escribe,
  se ignora.

La celda de destino se puede consultar sin construir el libro:

```python
from nefer import schema
schema.celdas_destino(manifiesto)   # {1: "A11", 2: "M11", 3: "A26", ...}
```

## `consumibles`

Son los accesorios que salen con el equipo y que se cobran si no vuelven
(extintor, conos, barra de puesta a tierra, bandejas, tacos). Cada uno genera un
bloque en la sección **OBSERVACIONES**: foto de despacho a la izquierda, foto de
recepción a la derecha y una franja amarilla de recuperación.

- `descripcion` (**obligatoria**), `cantidad` (entero, por defecto 1).
- `cantidad_retorna`: cuántas unidades volvieron. Opcional; véase más abajo.
- `estado_recepcion`: `OK`, `OBS`, `D` o `NO_RETORNA`.
- `foto_despacho`, `foto_recepcion`: rutas relativas.
- `texto_despacho`, `texto_recepcion`: sobreescriben la redacción automática
  cuando se acordó otro texto con el cliente.
- `recuperacion` / `recuperaciones`: sobreescriben las franjas de cierre. Con
  una sola franja escrita a mano basta `recuperacion` (texto); con varias se
  usa `recuperaciones` (lista, una entrada por franja).

La franja amarilla dice `RECUPERACIÓN N° n` cuando el estado es `NO_RETORNA`,
`D` u `OBS`; en cualquier otro caso dice `CONFORME N° n — SIN RECUPERACIÓN`.
Las dos series se numeran por separado: el primer accesorio que falte es la
`RECUPERACIÓN N° 1` aunque no sea el primer bloque.

### Retorno parcial

Salieron dos ganchos y volvió uno. Eso no es «retornó» ni «no retornó»: son dos
hechos distintos, y el bloque los declara en dos franjas —una se cobra y la otra
se da por conforme—, que es como acaban las actas llenadas a mano cuando el
retorno es incompleto.

```json
{"descripcion": "GANCHOS DE IZAJE", "cantidad": 2,
 "estado_recepcion": "NO_RETORNA", "cantidad_retorna": 1}
```

```
┌──────────────────────────────┬──────────────────────────────┐
│ 02 GANCHOS DE IZAJE          │ EL EQUIPO RETORNÓ CON 01 DE  │
│ DESPACHADO                   │ 02 GANCHOS DE IZAJE          │
├──────────────────────────────┴──────────────────────────────┤
│ RECUPERACIÓN N° 1 : 01 GANCHOS DE IZAJE                     │  amarillo
├─────────────────────────────────────────────────────────────┤
│ CONFORME N° 1 : 01 GANCHOS DE IZAJE — SIN RECUPERACIÓN      │
└─────────────────────────────────────────────────────────────┘
```

`cantidad_retorna` es opcional y sólo hace falta declararla cuando el retorno es
parcial: sin ella, el acta lo deduce del estado —`NO_RETORNA` es cero, cualquier
otro estado es todo— y da exactamente el mismo resultado que antes de que el
campo existiera. Si el estado es `D` u `OBS`, lo que volvió tampoco se da por
conforme: cierra con su propia franja de recuperación.

### Un despacho no declara el retorno

En un acta de `DESPACHO` el equipo todavía no ha vuelto. Por eso:

- `estado_recepcion`, `texto_recepcion`, `foto_recepcion` y `cantidad_retorna`
  **son un error de validación**, no un descuido que se ignore: describen un hecho que aún no
  ocurrió en un documento que el cliente firma.
- La columna de recepción y la franja de recuperación salen en blanco, pero el
  bloque se imprime completo para poder cerrarlo a mano cuando el equipo
  regrese.

Esos mismos campos son válidos y esperados en un acta de `RECEPCION`.

## `control_consumibles`

Es el **formato de consumibles**, obligatorio en equipos móviles. Se imprime en
la hoja `CONSUMIBLES` con espacio para las dos firmas. Si se deja vacío, el
sistema emite la tabla en blanco que corresponde a la categoría del equipo para
que el operador la llene en campo.

- `consumible` (**obligatorio**), `unidad`.
- `despacho`, `recepcion`: número o texto (`OK`/`OBS`).
- `consumo`: si se omite y ambos valores son numéricos, se calcula solo.
- `estado`, `observacion`.

## `resumen_ejecutivo`

Obligatorio, **máximo 20 palabras**. Es la frase que el cliente lee antes de
firmar; el validador rechaza los textos más largos.
