# Auditoría de calidad de la aplicación

Revisión interna de la aplicación de campo guiada por el modelo de calidad de
producto de **ISO/IEC 25010**, con las medidas de **ISO/IEC 25023**, la
usabilidad de **ISO 9241-11** y la accesibilidad de **WCAG 2.2 AA** (la norma
que **EN 301 549** exige en compra pública).

No es una certificación —eso lo emite un organismo acreditado, no un informe
interno—. Es la misma revisión que haría un auditor, con el instrumental que se
puede aplicar aquí: todo lo que sigue está medido, y cada cifra se puede volver
a tomar con los guiones que quedan en el repositorio.

- [1. Resumen](#1-resumen)
- [2. Hallazgo mayor: 13 segundos de pantalla en blanco](#2-hallazgo-mayor-13-segundos-de-pantalla-en-blanco)
- [3. Las ocho características de ISO/IEC 25010](#3-las-ocho-características-de-isoiec-25010)
- [4. Código que no se usaba](#4-código-que-no-se-usaba)
- [5. Espacio: lo que se puede ganar y lo que no](#5-espacio-lo-que-se-puede-ganar-y-lo-que-no)
- [6. Funciones que el operador no usará](#6-funciones-que-el-operador-no-usará)
- [7. Lo que queda abierto](#7-lo-que-queda-abierto)

---

## 1. Resumen

| Medida | Antes | Después |
|---|---:|---:|
| Arranque sin señal (hasta poder tocar) | 12 991 ms | **572 ms** |
| Primer pintado sin señal | 12 888 ms | **272 ms** |
| Llamadas a terceros | 1 | **0** |
| Nombres en la API interna | 31 | **22** |
| Funciones y estilos muertos | 7 | **0** |
| Peso que viaja por la red | 77,7 KB | 77,6 KB |
| La suite de pruebas (sin salida a internet) | 721 s | **205 s** |

Lo que valía la pena arreglar no era el peso: era **el tiempo y la privacidad**.

---

## 2. Hallazgo mayor: 13 segundos de pantalla en blanco

**Severidad: crítica.** Afectaba a fiabilidad, desempeño y seguridad a la vez.

La página cargaba una hoja de estilos de tipografía desde `fonts.googleapis.com`
en el `<head>`, de forma bloqueante. Un `<link rel="stylesheet">` detiene el
primer pintado hasta que responde o el navegador se rinde.

La aplicación existe para levantar actas **donde no hay señal**. Ahí, esa
petición no responde: se agota. Medido tres veces sobre la misma página:

| Condición | Hasta poder tocar | Primer pintado |
|---|---:|---:|
| Con la tipografía externa, red inalcanzable | 12 991 ms | 12 888 ms |
| Con la tipografía externa, respuesta instantánea | 307 ms | 144 ms |
| **Sin tipografía externa** | **231 ms** | **184 ms** |

**73 veces más lenta** en la única condición que importa. Y en silencio: el
operador ve una pantalla en blanco, sin nada que le diga que espere.

Había un segundo problema en el mismo renglón. Era **la única conexión a un
tercero** que hacía la aplicación: cada apertura de un acta le comunicaba a
Google la dirección IP del operador y la hora. En una herramienta que promete
que «las fotos y los datos del cliente no salen de este teléfono», eso es una
contradicción con el propio texto de la portada.

**Corregido en dos pasos.** Primero se retiró la petición externa. Después se
alojó la tipografía en el propio repositorio, en `docs/app/tipografia/`: cinco
cortes de Barlow y Barlow Condensed, subconjunto latin, 110 KB en total, con su
licencia OFL. Van declarados con `font-display:swap`, que es lo que impide que
esto vuelva a ser una espera: el texto se pinta de inmediato con la tipografía
del sistema y cambia a Barlow cuando el archivo está.

Medido con la tipografía ya alojada:

| | |
|---|---:|
| Arranque hasta poder tocar | 572 ms |
| Primer pintado | 272 ms |
| Peticiones a terceros | **ninguna** |
| Caras activas tras recargar **sin red** | las mismas |

Sigue siendo **23 veces** más rápida que con la tipografía prestada, y ahora
además conserva el aspecto de la marca. Los archivos van en la lista del
trabajador de servicio, así que están desde la segunda visita aunque no haya
señal.

**Efecto secundario medido:** la suite de pruebas pasó de **721 s a 205 s** en
un entorno sin salida a internet. Las 58 pruebas de navegador pagaban esa misma
espera en cada carga.

**Y aquí está lo importante del hallazgo.** En el runner de GitHub el trabajo
tardó lo mismo antes y después (227 s → 247 s), porque allí
`fonts.googleapis.com` **sí responde**: nunca se pagaba la espera. Es decir,
este defecto era **invisible para cualquier infraestructura bien conectada**.
Una comprobación automática en la nube no lo habría encontrado nunca. Sólo
aparece en la condición para la que se hizo la aplicación: sin señal.

---

## 3. Las ocho características de ISO/IEC 25010

### 3.1 Adecuación funcional — **conforme**

El formato se cotejó celda por celda contra cuatro actas reales; el detalle
está en [AUDITORIA-FORMATO.md](AUDITORIA-FORMATO.md). 132 pruebas
automatizadas, de las cuales 58 conducen un navegador de verdad.

Completitud: cubre despacho y recepción, las diez vistas por familia de equipo,
observaciones con retorno parcial, comparativo y daños. Corrección: el Excel y
el PDF de una misma acta se cortan por las mismas filas, comprobado por prueba.

### 3.2 Eficiencia de desempeño — **conforme tras la corrección**

| Medida | Valor | Referencia |
|---|---:|---|
| Arranque hasta interactivo | 572 ms | < 5 s en 3G |
| Generar el PDF con 10 fotos | 161 ms | — |
| Generar el Excel con 10 fotos | 93 ms | — |
| Memoria JS en uso | 3,9 MB | — |
| Nodos en el DOM | 500 | < 1 500 |
| Peso comprimido (página) | 77,6 KB | < 170 KB |
| Tipografía, una sola vez | 110 KB | — |

Sin dependencias de terceros: ni React, ni jQuery, ni biblioteca de PDF. El
PDF, el Excel y el ZIP se escriben a mano, byte a byte.

### 3.3 Compatibilidad — **conforme**

El manifiesto es el único formato de intercambio y está documentado
([ESQUEMA-JSON.md](ESQUEMA-JSON.md)). El acta que produce el teléfono y la que
produce el generador de escritorio caen en las mismas filas: hay pruebas que
fallan si dejan de coincidir.

### 3.4 Interacción (usabilidad) — **conforme**

| Criterio | Medido |
|---|---|
| WCAG 2.2 §2.5.8, objetivos táctiles ≥ 24×24 | ninguno por debajo |
| Objetivos ≥ 44×44 (umbral con guantes) | 8 de 8 |
| Contraste de texto ≥ 4,5:1 | verificado en la auditoría de accesibilidad |
| La app se adapta al aparato | sí, ver §6 |

### 3.5 Fiabilidad — **conforme tras la corrección**

Recargada **sin red** tras la primera visita: la página vuelve completa y el
demo sigue disponible. Antes de esta corrección, la primera carga se quedaba
13 s colgada de una petición externa aunque el trabajador de servicio ya
tuviera todo lo demás guardado.

Tolerancia a fallos: un acta incompleta sale marcada como borrador sin valor
para firma; una casilla sin fotografía se imprime como tal; una foto que el
navegador no puede decodificar se rechaza por nombre y con el motivo.

### 3.6 Seguridad — **conforme tras la corrección**

| Punto | Estado |
|---|---|
| Peticiones a terceros | **0** (era 1) |
| Datos que salen del aparato | ninguno: todo se procesa en el navegador |
| Guiones de terceros | ninguno |
| Datos de cliente en el repositorio | ninguno; las fotos están excluidas |

La aplicación no tiene servidor, no tiene sesión y no guarda nada fuera del
teléfono. La superficie de ataque es la del propio navegador.

### 3.7 Mantenibilidad — **observaciones levantadas**

Modularidad: seis módulos con una puerta de entrada declarada. La superficie
pública pasó de 31 a 22 nombres al quitar los que nadie consumía; cuanto más
estrecha, menos sitios donde algo puede desincronizarse.

**Riesgo estructural que sigue abierto:** la geometría del formato está escrita
dos veces, en `nefer/layout.py` y en el JavaScript de la aplicación. Está
mitigado —hay pruebas que comparan las dos copias cifra por cifra y fallan si
se separan— pero mitigado no es resuelto. Ver §7.

### 3.8 Flexibilidad y portabilidad — **conforme**

Un solo archivo, sin instalación ni compilación. Funciona servido y funciona
descargado, con una diferencia medida y avisada en pantalla: desde un archivo
suelto el navegador deniega el permiso de cámara y no hay forma de concederlo.

---

## 4. Código que no se usaba

Detectado con análisis de referencias sobre el árbol completo, iterando hasta
punto fijo. Todo lo listado se retiró.

| Qué | Dónde | Por qué sobraba |
|---|---|---|
| `filaPar()` | app, bloque 2 | resto del diseño anterior de recepción |
| `textoRecuperacion()` | app, entregables | lo sustituyó `textoCierre()` |
| `CAB_ALTO` | app, entregables | de antes de reescribir la cabecera del PDF |
| `FOTOS_POR_PAGINA` | app, entregables | lo sustituyó el reparto por alto |
| `ALTO_BLOQUE_CONSUMIBLE` | app, Excel | el bloque dejó de medir siempre lo mismo |
| `RUTAS.pegar`, `RUTAS.arrastre` | app, núcleo | indicadores que nadie consultaba |
| `.aviso-pin`, `.ok-msg` | CSS | declarados y nunca aplicados |
| `ultima_fila()` | `nefer/layout.py` | sin ninguna llamada |
| Comentario huérfano | app, recepción | describía una función ya borrada |

Un comentario que describe algo que ya no existe es peor que no tener
comentario: manda a quien lo lea en la dirección equivocada.

**Falsos positivos que NO se tocaron**, por si alguien repite el análisis:
`publicarCatalogo` es una función anónima con nombre —se ejecuta sola—, y los
`cmd_*` de `nefer/cli.py` los despacha argparse, no una llamada directa.

---

## 5. Espacio: lo que se puede ganar y lo que no

Aquí el resultado honesto es que **casi no había nada que ganar**:

| Parte | En disco | Comprimido |
|---|---:|---:|
| JavaScript | 191 KB | — |
| CSS | 31 KB | — |
| HTML | 27 KB | — |
| **Total** | **250 KB** | **77,6 KB** |

Lo que viaja por la red son 77,6 KB, menos de la mitad del presupuesto
habitual de 170 KB. No hay dependencias que recortar porque no hay ninguna.

Los comentarios ocupan 43,7 KB, el 23 % del JavaScript. Quitarlos ahorraría
unos 6 KB comprimidos —el 8 %— a cambio de perder la explicación de por qué
cada cifra del formato vale lo que vale. **No se recomienda.** Un
minificador daría algo más, pero convertiría un archivo que cualquiera puede
abrir y leer en uno que sólo una herramienta puede tocar, y este proyecto vive
de que el formato se pueda auditar a mano.

El espacio no era el problema. El tiempo sí.

---

## 6. Funciones que el operador no usará

La pregunta era buscar lo que sobra de cara al usuario. El resultado es que la
aplicación **ya se adapta al aparato** y no ofrece lo que no sirve. Medido
sobre la misma pantalla de despacho:

| Vía para meter fotos | En el teléfono | En el PC |
|---|:--:|:--:|
| Cámara dentro de la app | ✅ | según tenga webcam |
| Cámara del sistema | ✅ | — |
| Galería | ✅ | ✅ (como «elegir») |
| Carpeta completa | — | ✅ |
| Arrastrar | — | ✅ |
| Pegar | ✅ silencioso | ✅ silencioso |

Ninguna vía estorba donde no aplica: el selector de carpeta no aparece en
pantalla táctil y el recuadro de arrastre se sustituye por «Toque Tomar foto».
No hay nada que quitar aquí; lo que había que quitar eran los dos indicadores
internos que decían medir esto y que nadie leía (§4).

---

## 7. Lo que queda abierto

### 7.1 La geometría escrita dos veces — riesgo medio

`nefer/layout.py` y el JavaScript de la aplicación describen la misma rejilla.
Hoy lo sujetan tres pruebas que comparan constantes, anchos y paneles, más dos
que exigen que las dos implementaciones caigan en las mismas filas y corten por
los mismos sitios. Se han verificado rompiendo la copia de Python a propósito:
las pruebas fallan.

Aun así, es duplicación. La salida limpia sería generar el bloque de
constantes del JavaScript desde `layout.py` en la comprobación automática y
fallar si el archivo publicado no coincide. **No lo he hecho**: cambia cómo se
construye el proyecto y merece decidirse aparte, no colarlo en una auditoría.

### 7.2 La tipografía de la marca — **cerrado**

Barlow está alojada en `docs/app/tipografia/` con su licencia. Detalle en
[tipografia/LEEME.md](app/tipografia/LEEME.md).

Queda un matiz que conviene saber: el **demo descargado como archivo suelto**
no lleva los `woff2` —es un solo `.html`— y ahí el texto sale con la tipografía
del sistema. Se lee igual de bien; sólo cambia el aspecto. La versión servida,
que es la que se usa en patio, sí lleva Barlow.

### 7.3 Sin medición en aparato real

Todo lo de aquí está medido en Chromium sobre un contenedor Linux. Los números
de un teléfono de gama baja con Android serán peores en términos absolutos,
aunque la proporción entre antes y después se mantiene: 13 segundos de espera
por una petición de red no dependen del procesador del teléfono.
