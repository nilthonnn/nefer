# Logo de la empresa

El repositorio **no trae ningún logo ni nombre de empresa**. Cada instalación
pone el suyo, y no se sube aquí.

## En el teléfono

**Ajustes › Identidad del formato**: nombre de la empresa, logo (una foto o
imagen del teléfono) y bloque de control documental (código, versión y fecha).
Se guarda sólo en ese teléfono y sale en el PDF y el Excel.

## En la computadora

Copie el logo a `marca/logo.png` y declare la ruta en `catalogo.json`:

```json
"logo": "marca/logo.png"
```

`marca/logo.*` está en `.gitignore`: el archivo se queda en esa computadora.

| | |
|---|---|
| Formato | PNG o JPEG (no SVG: Excel no lo incrusta) |
| Hueco en el acta | `A1:F3`, **177 × 60 px** — proporción ≈ 3:1, horizontal |
| Fondo | Transparente o blanco |

Se recomienda entregarlo a 2× o 3× (por ejemplo 531 × 180 px).
