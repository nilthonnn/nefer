# Marca de RD RENTAL

`logo.png` es el logo de RD RENTAL, extraído del informe `C375-40` que entregó
el cliente: allí va incrustado en `A1:F3`, el mismo hueco que este proyecto
reserva.

## El archivo

| | |
|---|---|
| Ruta | `marca/logo.png` — 275 × 77 px, PNG con transparencia |
| Formato | PNG (también sirve JPEG; no SVG, Excel no lo incrusta) |
| Hueco en el acta | `A1:F3`, **177 × 60 px** — proporción ≈ 3:1, horizontal |
| Fondo | Transparente o blanco; la celda de abajo es blanca |

Se recomienda entregarlo a 2× o 3× (por ejemplo 531 × 180 px): la imagen se
reduce al hueco, y un original grande imprime nítido. Un logo cuadrado o
vertical entra igual, pero deja aire a los lados.

## Cómo se usa

La ruta ya está declarada en `catalogo.json`:

```json
"logo": "marca/logo.png"
```

Se resuelve **desde la carpeta del manifiesto** —el JSON del acta—, no desde
este archivo. Dos formas de que siempre encuentre el logo:

- Generar las actas desde la raíz del proyecto, que es donde `rdrenta acta`
  las deja por omisión. La ruta relativa funciona tal cual.
- O escribir en `catalogo.json` una ruta absoluta
  (`/home/usuario/rd-renta/marca/logo.png`), si las actas viven en otra parte.

Si el archivo se borra o se mueve, el acta sale igual pero sin logo y el
generador avisa:

```
logo: no existe .../marca/logo.png; el acta sale sin logo.
```

## Lo que no lleva logo

La aplicación de campo (`docs/app/`) arma su Excel en el teléfono y hoy no
incrusta logo: emite a nombre de **RD RENTAL** —el campo «Empresa» viene
prellenado— con el bloque de control `RD-FO-DE-022 / 00 / 25-11-2024`, y el
logo se añade al pasar el acta por `rdrenta construir`.
