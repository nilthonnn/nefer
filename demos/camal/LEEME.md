# La app del camal

Dos cosas viven en esta carpeta, y conviene no confundirlas.

## El prototipo del PDF

`demo_camal.html` es el demo que llegó en el PDF, sin una línea cambiada, y
`ANALISIS.md` es lo que pasó al ejecutarlo: las tres funciones responden y los
totales cuadran, pero la jornada no sobrevive a una recarga, el peso con coma
pierde el decimal y el conteo rápido acepta texto y números negativos.

Se conserva como estaba porque es la referencia contra la que se mide lo que
sigue. Sus pruebas son `probar_demo.py` y `probar_bordes.py`.

## La app por lotes

`app-camal.cuerpo.html` es el original de la app de verdad: la jornada se
organiza en lotes, el pesaje lleva correlativo automático y el precio recién se
pide cuando el lote está cerrado y la suma cuadrada contra la balanza.

De ese único original salen las dos formas de abrirla:

```bash
python3 demos/camal/construir.py
```

| Archivo | Para qué |
|---|---|
| `app-camal.html` | El que se guarda en el teléfono y se abre sin señal |
| `artefacto-celular.html` | El que se publica como enlace; sin envoltura, la pone el visor |

Los dos se generan: editarlos a mano es perder el cambio en la siguiente
construcción. Lo que se toca es el cuerpo.

La app se prueba de punta a punta, como una jornada:

```bash
python3 demos/camal/probar_lotes.py salidas/
```

Abre un lote de 40 alpacas, pesa tres —una con coma decimal, a propósito—,
rechaza lo que no es un peso, amplía el lote, corrige y borra una pesada,
cierra, pone el precio, abre un lote de menudencias por unidad, recarga el
teléfono y exporta las dos hojas. Veinte comprobaciones; cualquiera que falle
devuelve código 1.

### Lo que arregla del prototipo

| Defecto de `ANALISIS.md` | Cómo queda |
|---|---|
| La jornada se pierde al recargar | Se guarda en `localStorage` en cada cambio |
| «38,5» entraba como 38 | Coma y punto son lo mismo; lo que no es número se rechaza |
| El conteo aceptaba texto y negativos | Peso mayor que cero y menor que 400 kg, con aviso a la vista |
| No se podía corregir ni borrar | Se toca una pesada y se corrige o se elimina |
| Un solo precio para todo | Precio por lote, con referencia por categoría |
| No había contador por especie | Cada lote es de una categoría y lleva su propio avance |
| La hora en dos formatos, sin fecha | Fecha y hora de 24 horas en las dos hojas |

### El Excel

Dos hojas, porque son dos niveles de dato y mezclarlos es lo que vuelve
inservible un archivo:

- **Detalle por animal** — `Fecha, Lote, Categoria, N, Peso (kg), Precio x Kg, Subtotal`.
  Una fila por cabeza, con su correlativo dentro del lote. Es la hoja para
  auditar contra la balanza.
- **Resumen por lote** — `Fecha, Lote, Tipo, Categoria, Cantidad, Unidad,
  Peso total, Precio, Total, Estado, Inicio, Fin`. Una fila por lote, pesaje y
  menudencias juntos. Es la hoja para cuadrar el dinero del día.

Los precios que trae el catálogo son referenciales y están para confirmarse:
no son los del camal.

### El cierre del lote, en tres pasos

La pantalla del lote culminado va numerada porque es una secuencia, no una
lista de campos: **1** el peso total, que sale de sumar las pesadas; **2** el
precio por kg, que recién ahí se pide; **3** el precio total, que es el
producto de los dos. Cobrar antes de cuadrar el peso contra la balanza es
exactamente lo que ese orden impide. Los lotes de menudencias llevan la misma
secuencia con cantidad por unidad en el primer paso.
