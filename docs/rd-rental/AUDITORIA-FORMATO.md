# Auditoría del entregable

Comparación medida entre el acta que produce la aplicación y las actas reales
que se usan hoy en patio, y lista de no conformidades levantadas.

La comparación se hizo sobre cuatro actas reales de equipos distintos
—una torre de iluminación, un compresor, una plataforma y una excavadora— y
sobre el acta de recepción que generó la aplicación. Las actas se identifican
aquí como **A1** a **A4**; **A1** es la de la torre de iluminación. Todo lo
que sigue está medido en el XML del libro y en el PDF exportado, no estimado
a ojo.

- [1. Cómo se midió](#1-cómo-se-midió)
- [2. No conformidades del entregable de la aplicación](#2-no-conformidades-del-entregable-de-la-aplicación)
- [3. No conformidades del proceso manual](#3-no-conformidades-del-proceso-manual)
- [4. Diferencias deliberadas](#4-diferencias-deliberadas)
- [5. Cómo quedó](#5-cómo-quedó)

---

## 1. Cómo se midió

| Magnitud | Cómo se obtiene |
|---|---|
| Ancho de columna en píxeles | `round(ancho_en_caracteres × 7) + 5` (Calibri 11) |
| Alto de fila en puntos | el valor de `ht` en `sheet1.xml`, 15,0 pt por defecto |
| Alto útil de la página | A4 (841,89 pt) menos los márgenes superior e inferior |
| Escala de impresión | ancho útil ÷ ancho de la rejilla, cuando el libro va ajustado a lo ancho |

Con eso, una franja fotográfica (14 filas de imagen a 15 pt más el rótulo a
16,5 pt) mide **226,5 pt** y la cabecera (nueve filas a 15 pt más el separador
a 10,5 pt) mide **145,5 pt**. Las mismas cifras salen del acta **A1**:
cabecera 145,5 pt y franja 226,5 pt. La rejilla y el formato miden lo mismo.

---

## 2. No conformidades del entregable de la aplicación

### NC-1 · Cabían cuatro franjas por página; solo entran tres

**Constatado.** El acta **A1** corta su primera página en la fila 54,
que suman **807 pt**: cabecera más tres franjas. La aplicación cortaba cada
cuatro franjas, es decir 145,5 + 4 × 226,5 = **1 051,5 pt**, un 30 % más de lo
que entra en la caja de impresión. El resultado era que Excel metía su propio
salto en medio de una franja y separaba una fotografía de su rótulo.

**Levantada.** `BLOQUES_FOTO_POR_PAGINA` pasa de 4 a 3 en el generador y en la
aplicación; el PDF pasa de 8 a 6 fotografías por página y la casilla baja de
196 a 188 pt para que las tres franjas entren bajo la cabecera.

### NC-2 · Las columnas H e I medían el doble de lo que miden en el formato

**Constatado.** En las cuatro actas reales `H` e `I` miden 4,00 caracteres.
La geometría de la aplicación las dejaba en 8,43 —el ancho por omisión de
Excel— porque la extracción no leyó el rango `<col min="7" max="9">` del libro
original, que declara G, H e I de una sola vez.

Consecuencia medible: el panel izquierdo (A:L) quedaba en 472 px contra 435 px
del derecho (M:Z). En el formato real la relación es la contraria —410 px contra
433 px— así que la casilla de despacho salía **62 px (15 %) más ancha de lo que
debe**, y encima más ancha que la de recepción, en un formato cuya razón de ser
es comparar una con otra.

**Levantada.** `H` e `I` vuelven a 4,00. Los paneles quedan en 410 px y 435 px:
2 px del formato real.

### NC-3 · La fila de tipo de documento no estaba en las columnas del formato

**Constatado.** En las cuatro actas reales la fila 6 se reparte así:

| Rango | Contenido |
|---|---|
| `A6:F6` | `FECHA:` |
| `G6:M6` | la fecha |
| `N6:R6` | `DESPACHO` |
| `S6:T6` | casilla de despacho |
| `U6:Y6` | `RECEPCIÓN` |
| `Z6` | casilla de recepción |

La aplicación escribía `DESPACHO` en `S6:T6` —es decir, encima de la casilla— y
`RECEPCIÓN` en `V6:Y6`. Lo mismo en la fila 9: `HORÓMETRO:` iba en `S9:U9`
cuando el formato lo pone en `M9:R9`.

**Levantada.** La cabecera de la aplicación se reescribió celda por celda
igual que la del generador, que sí seguía el formato.

### NC-4 · El nombre del cliente se recortaba en el PDF

**Constatado.** En el formato el cliente ocupa de `G` a `Z`. En el PDF de la
aplicación ocupaba el 46 % del ancho y el resto quedaba en blanco: un cliente
identificado con RUC y razón social —`20100000001 - CONSTRUCTORA DEMO S.A.C.`
es de las cortas, y las hay de 58 caracteres— quedaba al filo del recorte, y cualquiera
más largo se cortaba.

**Levantada.** Las filas de cliente, equipo y guía se extienden hasta el borde
derecho, igual que en el formato: de 60 a unos 110 caracteres visibles.

### NC-5 · La descripción de un accesorio se cortaba

**Constatado.** La fila donde va lo que salió y lo que retornó medía 16,5 pt en
el Excel —una línea— y una línea en el PDF. Una descripción corriente,
`01 BASE DE EXTINTOR DE 6 KG CON SU SOPORTE DE PARED DESPACHADO`, mide 61
caracteres: en el Excel quedaba cortada por abajo y en el PDF salía
`… CON SU SOPORTE DE PARED DESPAC…`. Lo que se pierde es justo lo que
identifica la pieza que se reclama.

**Levantada.** La fila pasa a 28,5 pt —dos líneas de Calibri 10— y el PDF
reparte el texto en dos renglones. Los 10 pt que necesita el PDF salen de la
casilla de la foto, de modo que el bloque sigue midiendo 195 pt y siguen
entrando tres por página.

### NC-6 · El Excel y el PDF paginaban distinto

**Constatado.** El Excel abre página en el título `OBSERVACIONES`, como el
formato real —el acta **A1** corta en la fila 84 y abre su página 3 con
`OBSERVACIONES`—. El PDF, en cambio, encajaba el título a continuación de las
fotografías. Dos entregables del mismo acta con distinto reparto de hojas no se
pueden cotejar hoja contra hoja.

**Levantada.** Toda sección con título abre página también en el PDF. Sobre el
acta de prueba —diez vistas y cuatro accesorios— los dos entregables salen
ahora con las mismas cuatro páginas y el mismo contenido en cada una.

### NC-7 · El libro salía sin área de impresión ni saltos declarados

**Constatado.** El acta que generó la aplicación no traía `print_area`, ni
altura declarada en las filas 1 a 9, ni las líneas de cuadrícula apagadas. Quien
lo abriera e imprimiera obtenía un reparto de páginas distinto del que se ve en
pantalla.

**Levantada.** El libro declara `_xlnm.Print_Area`, fija la altura de todas las
filas, apaga la cuadrícula y ajusta los márgenes.

### NC-8 · Un acta incompleta salía con apariencia de acta firmable

**Constatado.** Sin número de acta, sin cliente, sin código de equipo y sin
horómetro, el entregable salía idéntico a uno completo. Un acta así no sirve
como respaldo de un cobro por faltantes.

**Levantada.** El entregable comprueba los campos que identifican el acta y,
si falta alguno, imprime una banda de advertencia —«BORRADOR — SIN VALOR PARA
FIRMA. Falta: …»— en la cabecera de cada página del PDF y al pie del Excel.

### NC-9 · Una casilla sin fotografía no se distinguía de una fotografía en blanco

**Constatado.** Las vistas sin foto salían como recuadros vacíos, que es lo
mismo que se ve cuando una imagen no se llegó a incrustar.

**Levantada.** La casilla vacía imprime `(sin fotografía)`.

---

## 3. No conformidades del proceso manual

Salieron al comparar; no son de la aplicación, son de cómo se llena el formato
hoy. Se levantan aquí porque la aplicación ya las evita.

### NC-10 · Un acta imprimió 3 de sus 9 recuperaciones

**Constatado.** El libro de **A1** tiene ocho números de recuperación en
nueve franjas, hasta la fila 222. Su área de impresión termina en la fila 136.
El PDF que se archivó tiene cuatro páginas y **acaba en «RECUPERACIÓN 3»**.
Las franjas de las filas 137 a 222 —cinco recuperaciones más, entre ellas un
gancho, un grillete y tres seguros de sujeción— **no se imprimieron**. El
respaldo documental del cobro de esos faltantes no existe.

**Cómo lo evita la aplicación.** El área de impresión se calcula a partir de la
última fila escrita, no se arrastra de un libro anterior.

### NC-11 · La numeración de recuperaciones se repite

**Constatado.** En el mismo libro, «RECUPERACIÓN 6» aparece dos veces (filas 171
y 188) y después salta a 7 y 8. La serie real es 1, 2, 3, 4, 5, 6, 6, 7, 8:
nueve franjas, ocho números.

**Cómo lo evita la aplicación.** La numeración se genera por posición dentro de
su propia serie; no se teclea.

### NC-12 · Un retorno conforme quedó registrado como recuperación

**Constatado.** La última franja dice «EL EQUIPO RETORNÓ **CON** 01 BASE DE
EXTINTOR DE 6 KG» y sin embargo va rotulada «RECUPERACIÓN 8». Lo que retornó
completo no es una recuperación; contarlo como tal infla el pendiente del
cliente.

**Cómo lo evita la aplicación.** El rótulo se deriva del estado del ítem:
`RECUPERACIÓN N° n` cuando falta, `CONFORME N° n` cuando retornó completo, cada
uno con su propia numeración.

### NC-13 · Un retorno parcial no tenía dónde declararse

**Constatado.** En **A1**, un bloque declara «02 GANCHO MAS 02 GRILLETES EN
DESPACHO» y cierra con **dos** franjas seguidas —«RECUPERACIÓN 4 : 01 GRILLETE»
y «RECUPERACIÓN 5 : 01 GANCHO»— porque de cada par volvió uno. El formato no
tiene casilla para eso: el operador lo resolvió juntando dos accesorios en un
bloque y añadiendo una fila a mano. Un retorno parcial declarado como «no
retornó» cobra de más, y declarado como «retornó» cobra de menos.

**Levantada.** El accesorio declara cuántas unidades volvieron
(`cantidad_retorna`). Con un retorno parcial el bloque cierra con dos franjas
—la recuperación de lo que falta y el conforme de lo que volvió— y la celda de
recepción dice «EL EQUIPO RETORNÓ CON 01 DE 02 …». La rejilla crece una fila y
el reparto en hojas pasó a hacerse por el alto real de cada bloque, no por
cuenta de bloques, para que ninguno quede partido.

### NC-14 · Las páginas sueltas no se pueden trazar

**Constatado.** En el PDF del acta real la cabecera —número de acta, cliente,
equipo, código, horómetro— aparece **solo en la página 1**. Las páginas 2, 3 y 4
no llevan ningún dato que las ate al acta. Tampoco hay numeración de páginas.

**Cómo lo evita la aplicación.** La primera hoja del PDF lleva la cabecera
entera; las siguientes, una franja de 26 pt con número de acta, cliente,
equipo, código, horómetro, tipo de documento y «Pág. n de N». Repetir la
cabecera completa costaría 120 pt por hoja y obligaría a sacrificar un bloque;
la franja corta cuesta 26 y deja la hoja igual de identificada. En el Excel la
cabecera sigue saliendo sólo en la primera hoja, como en el formato: el
entregable que se firma e imprime es el PDF.

### NC-15 · Una franja del formato perdió una fila

**Constatado.** En **A1** las franjas van de 15 filas salvo la tercera
(filas 41 a 54), que tiene 14: alguien borró una fila de la plantilla y la
fotografía de esa franja es un 7 % más baja que las demás.

**Cómo lo evita la aplicación.** La rejilla se calcula, no se edita.

### NC-16 · Ortografía del rótulo

**Constatado.** El formato real rotula `BATERIA`, sin tilde. La aplicación
escribe `BATERÍA`.

---

## 4. Diferencias deliberadas

Puntos en los que la aplicación no copia el formato, a propósito:

| Punto | Formato real | Aplicación | Motivo |
|---|---|---|---|
| Numeración de recuperaciones | `RECUPERACIÓN 1 :` | `RECUPERACIÓN N° 1 :` | pedido expreso |
| Cabecera en páginas siguientes | solo en la primera | en todas, en el PDF | trazabilidad de hojas sueltas |
| Numeración de páginas | no tiene | `Pág. n de N`, en el PDF | detectar hojas faltantes |
| Columna `M` | oculta | visible, 1,43 | una columna oculta dentro del área impresa es una trampa de mantenimiento; ensancha el panel derecho 15 px sobre 843 |
| Obra | no tiene casilla | queda en el registro, no se imprime | el formato no tiene dónde ponerla |
| Código de formato | el del formato de origen | `FO-DR-001` | el proyecto es independiente de la empresa de origen |

---

## 5. Cómo quedó

Medido sobre un acta de recepción de prueba —torre de iluminación, diez vistas
y cuatro accesorios, uno de ellos retornado conforme—:

| | Antes | Ahora | Formato real |
|---|---|---|---|
| Ancho de la rejilla | 907 px | 845 px | 843 px |
| Panel de despacho (A:L) | 472 px | 410 px | 410 px |
| Panel de recepción (M:Z) | 435 px | 435 px | 433 px |
| Franjas fotográficas por hoja | 4 | 3 | 3 |
| `DESPACHO` / `RECEPCIÓN` | `S6:T6` / `V6:Y6` | `N6:R6` / `U6:Y6` | `N6:R6` / `U6:Y6` |
| `HORÓMETRO:` | `S9:U9` | `M9:R9` | `M9:R9` |
| Renglones para la descripción | 1 | 2 | 1 a 3, a mano |
| Hojas del PDF y del Excel | 3 y 4 | 4 y 4 | — |
| Identificación en las hojas 2+ | ninguna | franja de 26 pt en el PDF | ninguna |
| Retorno parcial | no se podía declarar | dos franjas de cierre | a mano, juntando bloques |
| Reparto en hojas | por cuenta de bloques | por alto real del bloque | a ojo |

El acta de prueba sale con las mismas cuatro páginas en los dos entregables y
el mismo contenido en cada una: tres franjas, dos franjas, `OBSERVACIONES` con
tres accesorios y el cuarto accesorio en la última.
