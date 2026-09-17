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
| `docs/camal/index.html` | La forma instalable en Android; Pages sirve `docs/` |

Los dos se generan: editarlos a mano es perder el cambio en la siguiente
construcción. Lo que se toca es el cuerpo.

La app se prueba de punta a punta, como una jornada:

```bash
python3 demos/camal/probar_lotes.py salidas/
```

Abre un lote de 40 alpacas degolladas, pesa tres —una con coma decimal, a
propósito—, rechaza lo que no es un peso, amplía el lote, corrige una pesada
sin motivo (y comprueba que no se aplica) y con motivo, anula otra, cierra,
pone el precio, abre un lote de menudencias por unidad, recarga el teléfono,
revisa la bitácora y descarga los dos archivos.

Después sale del navegador y **audita lo exportado con librerías ajenas a la
app**: abre el `.xlsx` con openpyxl —comprueba las cuatro hojas, que no haya
dos identificadores repetidos, que la anulada viaje marcada, que el resumen
sean fórmulas contra el detalle y que el total en frío cuadre con la pantalla—
y el PDF con pypdf. Sesenta y tres comprobaciones; cualquiera que falle
devuelve código 1.

### La app instalable en Android

`docs/camal/` es la app como aplicación: `index.html` generado, más el
manifiesto, el trabajador de servicio, los tres iconos —dibujados por
`iconos.py`, una balanza de dos platillos— y el QR que lleva a la dirección
publicada. GitHub Pages sirve `docs/` desde `main`, así que queda en
**https://nilthonnn.github.io/nefer/camal/** en cuanto la rama se integre.

En Android, Chrome ofrece «Instalar aplicación» y queda con su icono, abre sin
barra de navegador y funciona sin señal. En iPhone es *Compartir › Añadir a
pantalla de inicio*.

Se comprueba como app, no como página:

```bash
python3 demos/camal/probar_android.py salidas/
```

Levanta un servidor sobre `docs/camal/` —igual que hará Pages—, conduce un
Chromium emulando un Pixel con pantalla táctil, y verifica lo que Android
exige para instalarla: manifiesto con nombre, `display: standalone`, iconos de
192 y 512 con uno recortable, y un trabajador de servicio activo con la app ya
guardada. Después **corta la red**: recarga, comprueba que la jornada sigue
entera, pesa otra cabeza y descarga el Excel y el PDF sin conexión. Termina
midiendo que ninguna pantalla se salga de ancho en 393 px.

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

### Trazabilidad

Un registro que se puede cambiar sin dejar rastro no vale para auditar, así que
la app está construida sobre tres reglas:

- **Todo tiene identificador.** La jornada es `J-AAAAMMDD-XXXX` —con sufijo al
  azar, para que dos teléfonos no generen el mismo código el mismo día—, cada
  lote es `…-L001` y cada pesada, `…-L001-007`. Ese código es el que aparece en
  el Excel, en el PDF y en la pantalla: es la misma carcasa en los tres sitios.
- **Nada se borra.** Una pesada equivocada se **anula con motivo**: deja de
  sumar, pero sigue en el detalle marcada como `ANULADO`, con su motivo al lado.
  Corregir un peso pide motivo también, y el valor anterior queda guardado.
  El correlativo de una anulada no se reutiliza.
- **Todo queda anotado.** La bitácora recoge cada apertura, pesada, corrección,
  anulación, precio, cierre y exportación, con marca de tiempo, valor anterior,
  valor nuevo, motivo y responsable. Responde a «quién cambió qué, cuándo y por
  qué», que es lo que pregunta un auditor.

El responsable del registro se declara en la pantalla de jornada y viaja en el
control documental de cada archivo. Sin declararlo, los archivos salen con
«(sin declarar)» a la vista: es mejor un hueco visible que un nombre supuesto.

El control documental (código de formato `REG-CAM-001`, versión, aplicación de
origen, identificador de jornada, fecha, responsable y hora de emisión) va en
la portada del Excel y en la cabecera del PDF.

### Los archivos

Los dos se arman dentro de la app, sin librerías: en el camal no hay señal para
descargarlas. El `.xlsx` es un zip de XML escrito a mano y el PDF se ensambla
objeto por objeto, con Helvetica en WinAnsi, que cubre el castellano entero.

**Excel, cinco hojas.** `CONTROL` (portada y cifras del día), `PESOS POR LOTE`
(la hoja que se lee), `DETALLE` (la tabla que se filtra), `RESUMEN` (una fila
por lote) y `BITACORA` (el rastro).

`PESOS POR LOTE` está segmentada: un bloque por lote, separado por una fila en
blanco, con su banda de encabezado —código, categoría, cantidad, estado y
horas—, debajo los pesos uno a uno con su identificador y su estado, y al pie
tres filas alineadas bajo su columna: **peso total del lote**, **precio por
kg** y **precio total del lote**. Al final, el total de la jornada. Es la hoja
que se imprime: va con ajuste a una página de ancho.

Lo importante no es que haya cuatro hojas sino que estén **vinculadas**: el
resumen no lleva números pegados sino fórmulas —`SUMIFS` y `COUNTIFS` contra el
detalle, filtrando por `ESTADO="VIGENTE"`—, y la portada cuenta vigentes y
anulados con `COUNTIF`. Si en la oficina corrigen un peso en `DETALLE`, el
resumen y la portada se recalculan solos. El subtotal de cada fila también es
fórmula: `=IF($L2="VIGENTE",ROUND($H2*$I2,2),0)`.

**PDF, el acta firmable.** Control documental, cifras del día, resumen por
lote, detalle por cabeza con sus anulaciones y motivos, bitácora completa y dos
firmas: responsable del registro y conformidad del cliente. Pie de página con
código de formato, jornada, hora de emisión y numeración.

### El Excel

Un lote todavía sin precio deja las celdas de dinero **vacías**, no en cero:
cero se lee como «cobrado a cero», y no es lo mismo que «aún sin tasar».

Columnas, por hoja:

- **DETALLE** — `ID_REGISTRO, JORNADA, FECHA, COD_LOTE, LOTE, CATEGORIA,
  CORRELATIVO, PESO_KG, PRECIO_KG, SUBTOTAL_SOLES, REGISTRADO, ESTADO, MOTIVO,
  RESPONSABLE`.
- **RESUMEN** — `COD_LOTE, LOTE, TIPO, CATEGORIA, CANTIDAD, UNIDAD,
  PESO_TOTAL_KG, PRECIO, TOTAL_SOLES, ESTADO, INICIO, FIN`, más una fila de
  totales.
- **BITACORA** — `MARCA_TIEMPO, ACCION, REFERENCIA, ANTES, DESPUES, MOTIVO,
  RESPONSABLE`.

Las tres van con fila de cabecera congelada y autofiltro puesto. Desde la
pantalla de exportación, cualquiera de las tres se puede ver y copiar suelta en
CSV, para pegarla en Google Sheets.

Los precios que trae el catálogo son referenciales y están para confirmarse:
no son los del camal.

### El cierre del lote, en tres pasos

La pantalla del lote culminado va numerada porque es una secuencia, no una
lista de campos: **1** el peso total, que sale de sumar las pesadas; **2** el
precio por kg, que recién ahí se pide; **3** el precio total, que es el
producto de los dos. Cobrar antes de cuadrar el peso contra la balanza es
exactamente lo que ese orden impide. Los lotes de menudencias llevan la misma
secuencia con cantidad por unidad en el primer paso.
