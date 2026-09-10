# Manual de la aplicación de campo

Todo lo que hace la aplicación, pantalla por pantalla y botón por botón.

Está escrito para quien la va a usar en el patio, no para quien la programó.
Si busca cómo se levanta un acta desde la computadora, con la línea de
comandos, eso está en [MANUAL-OPERACION.md](MANUAL-OPERACION.md).

- [1. Qué hace y qué no](#1-qué-hace-y-qué-no)
- [2. Instalarla en el teléfono](#2-instalarla-en-el-teléfono)
- [3. Las cuatro pestañas](#3-las-cuatro-pestañas)
- [4. Despacho](#4-despacho)
- [5. Recepción](#5-recepción)
- [6. La cámara](#6-la-cámara)
- [7. Cómo entran las fotos](#7-cómo-entran-las-fotos)
- [8. Observaciones](#8-observaciones)
- [9. Componentes](#9-componentes)
- [10. Los entregables](#10-los-entregables)
- [11. Guía y comprobación del dispositivo](#11-guía-y-comprobación-del-dispositivo)
- [12. Qué se guarda y qué no](#12-qué-se-guarda-y-qué-no)
- [13. Cuando algo falla](#13-cuando-algo-falla)
- [14. Límites conocidos](#14-límites-conocidos)

---

## 1. Qué hace y qué no

**Hace:** levanta el acta fotográfica de salida y la de retorno de un equipo,
con el equipo delante, y produce el **PDF** y el **Excel** con el formato de la
empresa, en el propio teléfono.

**No hace:** no manda nada a ningún servidor, no necesita señal, no pide
cuenta ni contraseña y no guarda las fotos en la nube. Todo el procesamiento
ocurre dentro del navegador del teléfono.

Una cosa que conviene entender desde el principio, porque la mitad sorprende
para bien y la otra mitad para mal: si cierra la pestaña, **los datos escritos
se conservan pero las fotografías no**. Al volver a abrir siguen ahí la
familia, el cliente, el N° de acta y los demás campos; la rejilla vuelve
vacía. Descargue el paquete antes de cerrar.

---

## 2. Instalarla en el teléfono

Ábrala desde la dirección publicada y, en el menú del navegador (⋮ en Android,
el cuadrado con la flecha en iPhone), elija **Instalar aplicación** o **Añadir
a pantalla principal**. Queda como cualquier otra app: a pantalla completa, sin
barra de navegador, y abre sin señal.

Instalarla no es un capricho estético. Hay una diferencia que importa:

| | Abierta desde la dirección | Abierta como archivo descargado |
|---|:--:|:--:|
| Cámara **dentro** de la app | ✅ | ❌ el navegador la deniega |
| Cámara del sistema | ✅ | ✅ |
| Galería y carpeta | ✅ | ✅ |
| PDF, Excel y ZIP | ✅ | ✅ |
| Funciona sin señal | ✅ tras la primera visita | ✅ |

La cámara integrada —la que va tomando las diez vistas seguidas sin salir de la
app— **sólo funciona servida**. El navegador deniega ese permiso a los archivos
locales y no hay forma de concederlo; no es un fallo de la aplicación. Cuando
detecta esa situación lo avisa en pantalla y ofrece la cámara del sistema.

---

## 3. Las cuatro pestañas

Abajo, siempre visibles:

| Pestaña | Para qué |
|---|---|
| **Inicio** | Punto de partida y acta de ejemplo |
| **Despacho** | El acta de salida del equipo |
| **Recepción** | El acta de retorno |
| **Guía** | Procedimiento y comprobación del aparato |

Arriba a la derecha, el botón **Oscuro / Claro** cambia el tema. Con sol de
mediodía el claro se lee mejor; en interiores, el oscuro cansa menos.

En **Inicio** está el botón **Ver un acta de ejemplo**: carga diez fotos de
muestra y arma un acta completa sin que usted ponga nada. Es la forma de
entender la herramienta en un minuto, y de enseñársela a alguien.

---

## 4. Despacho

### 4.1 Elegir la familia

**Familia** decide qué vistas pide el formato. Hay seis:

| Familia | Vistas |
|---|---:|
| Grupo electrógeno | 10 |
| Torre de iluminación | 10 |
| Compresor transportable | 9 |
| Plataforma de elevación | 11 |
| Maquinaria amarilla | 10 |
| Genérico | 6 |

Cambiar de familia cambia la rejilla. Hágalo antes de empezar a fotografiar.

### 4.2 Meter las fotos

Tres botones, y sólo aparecen los que el aparato admite:

- **Cámara** — abre la cámara dentro de la app y va recorriendo las casillas
  vacías: dispara y pasa sola a la siguiente. Es la vía rápida.
- **Cámara del sistema** — abre la cámara del teléfono como respaldo.
- **Galería…** — elige fotos ya tomadas. En computadora dice **elegir**, y
  además aparece **carpeta** y se puede arrastrar.

Debajo hay una casilla, **Reducir a 1600 px al cargar**, marcada de fábrica.
1600 píxeles es de sobra para el formato impreso y hace que el acta pese
mucho menos. Desmárquela sólo si necesita el original.

### 4.3 La rejilla del formato

El corazón de la pantalla. Cada casilla es una vista del formato, con su
rótulo y su número. **Tóquela y se abre la cámara para esa vista**: la foto
entra donde toca, sin pasar por la bandeja.

El contador **0 / 10** dice cuántas van.

Arriba está **Sin asignar**: las fotos que entraron pero que todavía no tienen
casilla. Se tocan y se colocan.

Tres botones gobiernan la bandeja:

| Botón | Qué hace |
|---|---|
| **Reasignar** | Vuelve a repartir **todas** las fotos por orden y por nombre. Deshace lo colocado a mano. |
| **ver ejemplo** | Carga el acta de muestra |
| **vaciar** | Descarta todas las fotos cargadas |

La aplicación intenta adivinar la casilla por el nombre del archivo —una foto
llamada `horometro.jpg` va al horómetro— y, si no puede, por el orden.

### 4.4 Datos del acta

El desplegable **Datos del acta** lleva la cuenta de lo que falta: «faltan 4».
Los campos son cliente, obra, código de equipo, modelo, empresa (opcional),
N° de acta, N° de guía, fecha y horómetro de salida.

Un acta a la que le falten los datos que la identifican **sale marcada como
borrador sin valor para firma**, con una banda que dice exactamente qué falta.
Es deliberado: un acta incompleta que parece completa es peor que ninguna.

### 4.5 Observaciones

Es la sección **OBSERVACIONES** del acta, con su misma forma en pantalla: es
donde se deja constancia de lo que sale con el equipo y no es una vista de la
rejilla —extintor, conos, barra puesta a tierra, chapas, estrobos, ganchos,
grilletes— y de cualquier cosa que haya que fotografiar y comentar aparte.

**+ Añadir observación**, al pie de la pestaña, abre un bloque nuevo. No hay
límite: se añaden tantos como haga falta, y cada uno es una fotografía más con
su comentario.

Cada bloque lleva:

| Campo | Qué es |
|---|---|
| **nombre** | Catálogo de 17 nombres de los que aparecen en las actas, y acepta cualquier otro texto |
| **cantidad** | Cuántas unidades salen |
| **foto de DESPACHO** | Se toca la celda y se fotografía |
| **descripción** | El comentario que se imprime bajo la foto |

La descripción se **redacta sola** —`02 CONOS DE SEGURIDAD DE 28" DESPACHADO`—
mientras nadie la toque, y desde el momento en que se escribe encima manda lo
escrito. La columna **RECEPCIÓN** aparece apagada, con la palabra `al retorno`:
en un acta de salida el equipo todavía no ha vuelto y esa mitad no puede
afirmar nada. Se rellena en la pestaña de recepción, y se imprime en blanco.

---

## 5. Recepción

La recepción se puede empezar de tres maneras. La pantalla las llama **A**,
**B1** y **B2**.

### A · Sin acta de despacho

Elija la familia y toque **Empezar recepción**. Sirve cuando el acta de salida
se levantó en papel o no está a mano. Se pierde la comparación foto a foto,
pero el acta de retorno sale igual.

### B1 · Con el acta de despacho

**Cargar acta.json…** lee el paquete que produjo el despacho. Con eso la
recepción sabe qué equipo es, qué vistas tiene y qué accesorios salieron: todo
viene relleno.

Si el despacho se levantó en esta misma sesión, el botón **usar el acta de la
pestaña Despacho** lo trae sin pasar por archivos.

### B2 · Las fotos del despacho

**Cargar fotos…** trae las fotografías de salida para que aparezcan al lado de
las de retorno. Es lo que permite comparar y lo que sustenta un reclamo.

### 5.1 Vistas del equipo

Igual que en despacho, pero cada casilla muestra **dos**: la de salida a la
izquierda y la de retorno a la derecha. Tocar el recuadro vacío de la derecha
abre la cámara para esa vista.

**Observaciones por vista** deja escribir lo que se ve en cada fotografía.

### 5.2 Observaciones · el retorno parcial

Cada bloque de observación es el mismo del despacho con la mitad derecha ya
viva: su foto de retorno, su comentario y su franja de cierre. **+ Añadir
observación** sigue disponible al pie, para lo que aparezca al volver y no
estuviera en la salida.

Cada uno lleva **cuántos salieron** y **cuántos vuelven**, y un estado:

| Estado | Significa |
|---|---|
| **Conforme** | Volvió completo y bien |
| **Observado** | Volvió con algo que anotar |
| **Dañado** | Volvió roto |
| **No retornó** | No volvió |

La casilla **vuelven** es la que resuelve el caso incómodo. Si salieron dos
ganchos y vuelve uno, escriba 1: el bloque cierra con **dos** franjas en vez de
una.

```
02 GANCHOS DE IZAJE DESPACHADO  │  EL EQUIPO RETORNÓ CON 01 DE 02 GANCHOS
──────────────────────────────────────────────────────────────────────────
RECUPERACIÓN N° 1 : 01 GANCHOS DE IZAJE          ← amarillo, se cobra
CONFORME N° 1 : 01 GANCHOS DE IZAJE — SIN RECUPERACIÓN
```

Son dos hechos distintos: uno se cobra y el otro se da por conforme. Marcarlo
todo como «no retornó» cobra de más; marcarlo como «retornó» cobra de menos.

Las dos series se numeran por separado: el primero que falte es la
**RECUPERACIÓN N° 1** aunque no sea la primera observación de la lista.

Los tres textos —los dos rótulos y la franja— se redactan solos y **se pueden
reescribir**. La redacción automática es un punto de partida, no la última
palabra del que firma.

---

## 6. La cámara

Cuando se abre desde una casilla, la cámara sabe a qué vista pertenece la foto:
arriba se lee el rótulo —`VISTA FRONTAL`— y la cuenta de cuántas faltan.

| Botón | Qué hace |
|---|---|
| **obturador** (el círculo) | Dispara y pasa a la casilla siguiente |
| **Saltar** | Deja esa vista sin foto y pasa a la siguiente |
| **Galería** | Sale a las fotos ya tomadas, **sin perder la casilla** a la que apuntaba |
| **Cerrar** | Sale de la cámara |

Así se pueden tomar las diez vistas seguidas sin salir de la aplicación.

Las dos rutas de la foto —**disparar** y **elegir de la galería**— están en el
mismo mando, y es el mismo en toda la aplicación: en las vistas del equipo y
en las observaciones, en despacho y en recepción. Tocar una casilla vacía abre
la cámara; **Galería** lleva a las fotos ya tomadas y la deja en esa misma
casilla.

Si el aparato no concede la cámara —el caso del archivo descargado—, en lugar
de fallar en silencio muestra el motivo y un botón para usar la galería.

---

## 7. Cómo entran las fotos

Seis vías, y la aplicación **sólo enseña las que el aparato admite**:

| Vía | Teléfono | Computadora |
|---|:--:|:--:|
| Cámara dentro de la app | ✅ | si tiene webcam |
| Cámara del sistema | ✅ | — |
| Galería / elegir archivo | ✅ | ✅ |
| Carpeta completa | — | ✅ |
| Arrastrar y soltar | — | ✅ |
| Pegar desde el portapapeles | ✅ | ✅ |

**Qué acepta:** cualquier imagen que el navegador sepa abrir. La comprobación
es que se decodifique, no el nombre ni el tipo declarado, porque los selectores
de los teléfonos entregan a menudo ambos vacíos y filtrar por ellos hacía
desaparecer fotos sin aviso.

**Qué rechaza:** lo que no se pueda decodificar, **y lo dice por nombre y con
el motivo**. Nunca descarta una foto en silencio.

Sobre el HEIC de iPhone: si sus fotos no entran, en **Ajustes → Cámara →
Formatos** elija **«Más compatible»**. El teléfono pasará a guardar en JPG.

---

## 8. Observaciones

En el acta impresa, cada observación ocupa un bloque con la forma exacta del
formato: cabecera `DESPACHO | RECEPCIÓN`, las dos fotografías, los dos textos
y la franja de cierre. Las dos celdas de foto se tocan y se fotografían.

La pantalla dibuja ese mismo bloque, celda por celda, para que lo que se ve al
levantarlo sea lo que sale impreso:

```
┌───────────────┬───────────────┐
│   DESPACHO    │   RECEPCIÓN   │
├───────────────┼───────────────┤
│     foto      │     foto      │
├───────────────┼───────────────┤
│ 01 X DESPACH. │ EL EQUIPO ... │
├───────────────┴───────────────┤
│ RECUPERACIÓN N° 1 : 01 X      │
└───────────────────────────────┘
```

En un acta de **despacho** la columna derecha va apagada y se imprime vacía.

La franja va **amarilla cuando hay algo que recuperar** y en blanco cuando no.

---

## 9. Componentes

**+ Añadir componente** registra el estado de las partes del equipo —módulo de
control, nivel de combustible, mangueras, lo que corresponda— con tres estados:
**Funcional**, **Observado** o **Dañado**.

Lo observado y lo dañado, y sólo eso, forma la sección **DAÑOS** del acta: es
lo que sustenta un cobro.

---

## 10. Los entregables

Cuatro botones al final de las dos pestañas:

| Botón | Qué sale | Para qué |
|---|---|---|
| **Descargar PDF** | El acta impresa, A4, seis fotos por página | Firmarla en sitio con el cliente |
| **Descargar Excel** | El mismo acta en el formato de la empresa | Archivarla y editarla |
| **Paquete .zip** | `acta.json` más las fotos | Pasarlo a la computadora |
| **copiar JSON** | El acta como texto | Pegarla donde haga falta |

El PDF y el Excel **se cortan por las mismas filas**: la hoja 3 de uno es la
hoja 3 del otro. Eso permite cotejarlos hoja contra hoja, que es para lo que se
firman.

El PDF repite en cada hoja una franja con número de acta, cliente, equipo,
código, horómetro y «Pág. n de N». Una hoja suelta se puede identificar.

---

## 11. Guía y comprobación del dispositivo

La pestaña **Guía** lleva el procedimiento —antes de salir al patio, cómo entran
las fotos, al fotografiar, al armar el acta— y, al final, algo práctico:
**Comprobación del dispositivo**.

- **Probar carga de una foto** — confirma que el selector de este teléfono
  entrega archivos que la app puede leer.
- **Probar cámara** — pide el permiso y dice si se concedió o por qué no.
- **copiar informe** — copia el resultado para mandárselo a quien dé soporte.

Úselo **antes** de ir al patio con un teléfono nuevo, no cuando ya esté allí
con el equipo delante.

---

## 12. Qué se guarda y qué no

| | |
|---|---|
| Se manda a un servidor | **nada** |
| Llamadas a terceros | **ninguna** |
| Fotos que salen del teléfono | **ninguna**, salvo las que usted descargue |
| Se necesita cuenta o contraseña | no |
| Se conservan los datos escritos al cerrar | sí, en el propio teléfono |
| Se conservan las fotografías al cerrar | **no** |

Lo que la aplicación recuerda entre sesiones es sólo lo que usted teclea
—familia, cliente, obra, código, modelo, empresa, N° de acta, N° de guía,
fecha, horómetro y los nombres de los accesorios— y lo guarda **en el propio
teléfono**, en el almacenamiento del navegador. No viaja a ninguna parte.

Las fotografías no se conservan: son demasiado grandes para ese almacén y
llenarlo dejaría la aplicación inservible. Comprobado: tras recargar, los
campos siguen escritos y la rejilla vuelve vacía.

De ahí la regla: **lo que se guarda de verdad es lo que usted descarga**.

---

## 13. Cuando algo falla

| Lo que ve | Qué pasa | Qué hacer |
|---|---|---|
| «La cámara dentro de la app está desactivada aquí» | La abrió como archivo descargado | Ábrala desde la dirección publicada, o use la cámara del sistema |
| El navegador pide permiso y usted dice «no» | El permiso queda denegado | En el candado de la barra de direcciones, permita la cámara y recargue |
| Una foto no entra y aparece su nombre | El navegador no la sabe decodificar | Si es un iPhone, cambie el formato a «Más compatible» |
| Sale una banda «BORRADOR — SIN VALOR PARA FIRMA» | Faltan datos que identifican el acta | La banda dice cuáles; llénelos |
| Una casilla dice «(sin fotografía)» | Esa vista no se fotografió | Tóquela y fotografíela, o déjela así si es a propósito |
| Los botones de descarga no responden | No hay ninguna foto asignada | Asigne al menos una |
| La app no abre sin señal | Aún no la había abierto con señal | Ábrala una vez con conexión; después funciona sola |
| Al reabrir están los datos pero no las fotos | Es lo esperado: sólo se recuerda lo tecleado | Vuelva a cargar las fotografías |

---

## 14. Límites conocidos

- **El borrador guardado no incluye las fotos.** Si cierra la pestaña a media
  acta, los datos escritos vuelven solos pero hay que fotografiar otra vez.
  Descargue el paquete antes de cerrar.
- **La cámara integrada no funciona desde un archivo descargado.** Es una
  restricción del navegador, no de la aplicación.
- **No sincroniza entre teléfonos.** Cada acta vive donde se levantó hasta que
  usted la descarga y la pasa.
- **El demo de un solo archivo** no lleva los archivos de tipografía y el texto
  sale con la del sistema. Se lee igual; sólo cambia el aspecto.
