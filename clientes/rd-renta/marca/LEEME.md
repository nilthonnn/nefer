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

## El logo en la aplicación de campo

La aplicación (`docs/app/`) arma el Excel y el PDF dentro del teléfono, sin
pasar por el motor, y lleva **su propia copia del logo incrustada** en el
código: `var LOGO` en la sección de entregables, en JPEG sobre blanco y a 2×
del hueco. Va dentro del archivo y no al lado porque la app funciona sin señal
y se reparte como un `.html` suelto, que no tiene vecinos de donde cargarlo.

Si el logo cambia, hay que cambiarlo **en los dos sitios**: `marca/logo.png`
para el motor y esa constante para la app. Para rehacer la constante:

```bash
python3 - <<'FIN'
import base64, io
from PIL import Image
src = Image.open("marca/logo.png")
im = src.resize((src.width * 2, src.height * 2), Image.LANCZOS)
fondo = Image.new("RGB", im.size, "white")
fondo.paste(im, mask=im.split()[-1])
buf = io.BytesIO(); fondo.save(buf, "JPEG", quality=94, optimize=True)
print(fondo.size, base64.b64encode(buf.getvalue()).decode())
FIN
```

Después, `python3 herramientas/empaquetar-demo.py docs/rdrenta-app.html` para
que el archivo único lo lleve también.
