# Manual de FixMate

Cómo se usa el diagnóstico de fallas, pantalla por pantalla y botón por botón.

Está escrito para el técnico que lo va a usar en el patio, no para quien lo
programó. Lo de la oficina —armar el índice desde la computadora— está en la
[sección 8](#8-desde-la-oficina). El detalle técnico de cómo funciona por
dentro está en [FIXMATE.md](FIXMATE.md).

Esto es otra aplicación que la de actas fotográficas. Si busca cómo se levanta
un acta de despacho o recepción, eso es [MANUAL-APP.md](MANUAL-APP.md).

- [1. Qué hace y qué no](#1-qué-hace-y-qué-no)
- [2. Instalarlo en el teléfono](#2-instalarlo-en-el-teléfono)
- [3. La Biblioteca: cargar el historial y los manuales](#3-la-biblioteca-cargar-el-historial-y-los-manuales)
- [4. Preguntar](#4-preguntar)
- [5. Lo que contesta](#5-lo-que-contesta)
- [6. Antes de tocar la máquina](#6-antes-de-tocar-la-máquina)
- [7. Registrar lo que resultó](#7-registrar-lo-que-resultó)
- [8. Desde la oficina](#8-desde-la-oficina)
- [9. Qué se guarda y qué no](#9-qué-se-guarda-y-qué-no)
- [10. Cuando algo falla](#10-cuando-algo-falla)
- [11. Lo que no hace, dicho aquí](#11-lo-que-no-hace-dicho-aquí)

---

## 1. Qué hace y qué no

**Hace:** contesta «qué le pasa a esta máquina» buscando en el historial de
fallas de la flota y en los manuales del fabricante. Dice la causa raíz más
probable, los pasos del antecedente que la resolvió, los repuestos, los pares
de apriete citados y **de dónde salió cada cosa**. Después registra lo que
usted encontró al desarmar, para que el siguiente que pregunte lo mismo ya lo
tenga.

**No hace:** no manda nada a ningún servidor, no necesita señal, no pide cuenta
ni contraseña. Todo ocurre dentro del teléfono. No hay ninguna configuración en
la que esto llame a nadie.

**Las tres reglas que cumple**, y conviene saberlas porque explican sus
respuestas:

1. **Sin antecedente no hay diagnóstico.** Si nada en lo cargado respalda la
   consulta, contesta «no hay antecedentes» en vez de conjeturar. Eso no es un
   fallo: es la respuesta.
2. **Ningún par de apriete se estima.** Copia el que está escrito en la fuente,
   o no da ninguno.
3. **Todo se cita.** Cada respuesta dice qué orden de trabajo o qué sección de
   manual la sostiene.

---

## 2. Instalarlo en el teléfono

Ábralo desde la dirección publicada:

```
https://nilthonnn.github.io/nefer/fixmate/app/
```

- **Android (Chrome).** Menú **⋮** → *Instalar aplicación* o *Agregar a
  pantalla de inicio*. Queda con su icono y abre a pantalla completa.
- **iPhone (Safari).** **Compartir** (el cuadro con la flecha, abajo) →
  **Añadir a pantalla de inicio** → **Añadir**.

Instalado, **funciona sin señal**: la primera vez se guarda entero en el
aparato. En el socavón abre igual.

**Si no hay internet ni para la primera vez**, existe el archivo suelto:

```
https://nilthonnn.github.io/nefer/fixmate-app.html
```

Son 320 KB en un solo archivo. Se manda por WhatsApp o por cable, se abre con
doble clic o desde Archivos, y no necesita instalar nada. Trae un taller de
ejemplo adentro, rotulado como inventado.

---

## 3. La Biblioteca: cargar el historial y los manuales

**Esto es lo primero que hay que hacer.** Recién instalado, FixMate está vacío
y no puede contestar nada: no tiene con qué.

Abra **Biblioteca** y toque **Agregar historiales y manuales**. Acepta, tal
como están, sin preparar nada:

| Formato | Para qué sirve |
|---|---|
| `.xlsx` `.xlsm` | El historial de fallas tal como lo lleva el taller, con su membrete y sus columnas |
| `.csv` `.tsv` | Lo mismo, exportado |
| `.pdf` | Los manuales del fabricante |
| `.docx` | Manuales e instructivos en Word |
| `.md` `.txt` | Procedimientos escritos a mano |
| `.json` | Un historial, o un índice ya armado por la oficina |

Se leen **en el propio teléfono**. No se suben a ninguna parte.

**No hace falta que el Excel esté ordenado de una forma concreta.** Reconoce
las columnas como las escribe un taller: `N° OT`, `Nº de orden`, `Falla
reportada`, `Descripción de la falla`, `Causa raíz`, `Solución aplicada`,
`Horómetro`, `Equipo`. Si su encabezado está dos filas abajo del membrete,
igual lo encuentra.

**Y lee el historial que exporta el sistema, no solo la plantilla.** Esos
exports no traen una fila por orden: traen la cabecera repetida una vez por
cada orden, con veinte o noventa filas de material debajo, la fecha de
despacho delante de cada línea y el nombre del técnico detrás. Eso entra tal
cual. El nombre del técnico se guarda aparte, para que `ACEITE 15W40 RIMULA
R4X SHELL` no sean seis repuestos distintos, uno por quien lo pidió.

**Si su historial no trae columna de causa raíz, igual sirve.** Muchos no la
traen: lo que está escrito es lo que se cambió y lo que hizo el tercero. Con
eso FixMate le da el ritmo de uso, el próximo servicio y dónde se va el dinero
por sistema. Lo que **no** va a hacer es inventarle la causa: las órdenes sin
causa salen contadas como «sin codificar», y ese número es exactamente lo que
falta por escribir en el taller.

Tres cosas que conviene saber:

- **Lo que se agrega se suma.** El historial de otra faena no borra el
  anterior. Puede cargar de a poco, cuando vaya consiguiendo los papeles.
- **Un número de orden repetido no desaparece en silencio.** Si vuelve a
  cargar una orden que ya estaba, le dice cuál reemplazó, con su número.
- **Un PDF escaneado no se puede leer.** Si el PDF es una foto de la página en
  vez de texto, lo detecta y lo dice, en vez de cargarlo vacío y después
  contestar «no hay antecedente», que sería mentirle con más pasos. Ese manual
  necesita OCR antes.

Abajo, la Biblioteca muestra **de qué archivo salió cada cosa**, cuántos
equipos hay y **qué aprendió**: su acierto medido, al lado de la línea base.
Si todavía no opina, dice por qué (hacen falta doce casos confirmados).

**Cargar el taller de ejemplo** mete un historial inventado para ver cómo
funciona. Sale rotulado «inventado» en cada respuesta, para que nunca se
confunda con el suyo. **Vaciar la biblioteca** borra todo lo cargado en ese
teléfono.

---

## 4. Preguntar

Escriba la falla **como se la contaría a un compañero**:

> humo negro y pierde fuerza en la subida

No hace falta acertar con las palabras del manual. El buscador encuentra por
dos caminos a la vez: las palabras exactas —un código de falla, un número de
parte— y el parecido de significado, que es lo que salva cuando usted dice
«gotea aceite» y el manual dice «fuga en el sello del vástago».

Donde el teléfono lo permite, **Dictar** escribe lo que usted diga. Lo dictado
queda a la vista antes de buscar, para corregirlo si entendió otra cosa.

Los dos campos de abajo afinan, y **ninguno es obligatorio**:

| Campo | Qué hace |
|---|---|
| **Código de falla** (`P0300`) | **Filtra.** Si nada cita ese código, avisa y busca por la descripción |
| **Equipo** (`GE074-01`) | **No filtra, prefiere.** Sube lo de esa máquina sin esconder lo demás |

La diferencia importa: el código filtra porque un código es exacto; el equipo
sólo prefiere, porque la misma falla en la máquina de al lado le sirve igual.

---

## 5. Lo que contesta

- La **causa raíz más probable**, tomada de un antecedente real.
- Los **pasos** de ese antecedente, con sus **herramientas y repuestos**.
- Los **pares de apriete citados en la fuente**, copiados literales, con el
  aviso de contrastarlos con el manual del fabricante.
- **Lo que dice el historial completo**: a qué causa terminan pareciéndose las
  descripciones así, **con el acierto medido al lado**. Un 93% no dice nada
  hasta que se ve que contestar siempre la más común acertaría el 21%; por eso
  van los dos números juntos.
- La **Evidencia**: qué orden de trabajo o qué sección de manual lo respalda,
  con su porcentaje de parecido y el extracto.

**Los pasos salen del antecedente que explica esa causa**, no del primero que
aparezca. Si el que da la causa no trae procedimiento, no inventa uno de otra
avería: dice que no hay. Mejor sin pasos que con los del trabajo equivocado.

---

## 6. Antes de tocar la máquina

Si la respuesta trae pasos, **siempre** trae antes un bloque **Antes de tocar
la máquina**. No es decorativo y no se puede quitar.

Sale de los sistemas que el propio procedimiento nombra: si los pasos hablan
de un cilindro hay energía hidráulica almacenada; si hablan del arranque,
eléctrica; de un inyector, combustible a presión. Un procedimiento que no
nombra ninguno lleva igual la de bloqueo, porque «no está escrito» no es «no
aplica».

Cada precaución dice **de dónde viene**:

- **manual** — copiada literal de un manual cargado, y citada. Es evidencia.
- **regla de la herramienta** — una precaución fija, que no afirma nada sobre
  *esta* máquina: dice qué verificar antes de intervenir.

Nada de esto reemplaza al manual del fabricante ni al procedimiento de bloqueo
del taller, y el texto lo dice en voz alta.

---

## 7. Registrar lo que resultó

Debajo de la respuesta —y también **cuando no hubo respuesta, que es cuando
más importa**— aparece **Cuando lo resuelva**. Tres campos: la falla como se
vio, la causa que usted confirmó al desarmar, y qué hizo. Más los repuestos.

La falla viene escrita y la causa viene propuesta, pero **corrija la causa si
era otra cosa**. Lo que se registra es lo que usted encontró, no lo que la
máquina supuso. Si lo deja como vino sin mirar, está ensuciando el historial de
toda la flota.

Al tocar **Registrar**, ese informe:

1. Queda guardado en el teléfono con un código propio `OT-CAMPO-…`.
2. **Se puede consultar en el acto**, en ese mismo teléfono y sin señal: el
   compañero que pregunte algo parecido ya lo encuentra.
3. Se suma a la cuenta de **informes por enviar**.

Cuando haya señal, **Enviar a la oficina** los manda todos juntos en un
archivo, por WhatsApp, correo o descarga. Los informes **no se borran del
teléfono al enviarlos**: mandar el mismo archivo dos veces no duplica nada.

---

## 8. Desde la oficina

Nada de esto hace falta para usar FixMate en el teléfono. Sirve cuando el
historial es grande y conviene prepararlo en la computadora.

**Armar el índice** con todo lo que haya:

```
nefer fixmate indexar historial.xlsx manuales/ actas/ -o indice.json
```

Ese `indice.json` se pasa al teléfono una sola vez y se carga desde la
Biblioteca.

**Para que el técnico no haga nada:** publique ese archivo **con el nombre
`indice.json`, en la misma carpeta que la app**. Al abrirla, si el teléfono
todavía no tiene nada guardado, lo toma solo y queda listo. Si el teléfono ya
tiene su biblioteca, manda lo guardado: no le pisa al técnico lo que él
cargó.

**Meter al historial lo que el teléfono cerró en faena:**

```
nefer fixmate recibir informes-de-campo-2026-09-16.json
```

Otras órdenes:

| Orden | Para qué |
|---|---|
| `nefer fixmate estado` | Qué hay en el índice y qué tan bien aprende |
| `nefer fixmate consultar` | Preguntar desde la computadora |
| `nefer fixmate predecir` | Qué le va a pasar a un equipo, según lo que ya le pasó |
| `nefer fixmate cerrar` | Registrar una falla resuelta |
| `nefer fixmate servir` | Levantar la API HTTP |
| `nefer fixmate subir` / `sql` | Mudar el índice a PostgreSQL cuando ya no cabe en un archivo |

---

## 9. Qué se guarda y qué no

- **Lo cargado en la Biblioteca se queda** en ese teléfono. Al volver a abrir,
  sigue ahí. No hay que cargarlo de nuevo cada mañana.
- **Los informes registrados se quedan**, y **Vaciar la biblioteca no los
  toca**: borra los historiales y manuales cargados, no lo que usted registró.
  La app lo avisa antes de hacerlo.
- **Nada sale del teléfono** salvo cuando usted toca *Enviar a la oficina*, y
  ahí lo manda usted, por donde usted elija.

---

## 10. Cuando algo falla

| Lo que pasa | Qué hacer |
|---|---|
| Contesta «no hay antecedentes» | Es la respuesta correcta: no hay nada cargado que lo respalde. Regístrelo al resolverlo y la próxima vez lo habrá |
| No dice el acierto del historial | Hacen falta doce casos confirmados y dos causas distintas. Con menos, no opina, que es lo honesto |
| Un PDF se carga vacío | Es un escaneo (una foto de la página). Necesita OCR antes |
| El Excel no entra | Compruebe que tenga una columna de falla y una de causa. Si el encabezado está muy abajo del membrete, déjelo igual: lo busca |
| Desaparecieron órdenes al cargar | No desaparecieron: se reemplazaron por número de orden repetido, y la app dice cuáles |
| No aparece el botón **Dictar** | Ese navegador no lo ofrece. Escriba a mano |
| Abre en blanco tras instalarlo | Borre el acceso directo y vuelva a instalarlo desde la dirección publicada |

---

## 11. RCM: análisis de confiabilidad (en construcción)

Desde esta versión FixMate tiene el esqueleto de un análisis RCM: activo →
función → falla funcional → modo de falla → efecto → consecuencia, con las
siete preguntas de SAE JA1011 verificadas y una matriz de decisión que elige
entre las seis estrategias de mantenimiento y deja escrito por qué.

Todavía **no tiene pantalla ni comandos**: se usa como biblioteca. El diseño
completo, con lo que hace y lo que no, está en
[ARQUITECTURA-RCM-TPM.md](ARQUITECTURA-RCM-TPM.md); los casos de prueba
funcionales, en [CASOS-RCM-TPM-FIXMATE.md](CASOS-RCM-TPM-FIXMATE.md).

Tres cosas conviene saber antes de usarlo:

- **No marca «completo» por cortesía.** El criterio de JA1011 es binario:
  faltando una de las siete preguntas, el análisis no está completo, y si
  falta alguna de las cuatro que sostienen la cadena, el resumen dice que
  todavía no es un análisis RCM.
- **No trae escala de criticidad.** La matriz es de su empresa. Sin método
  configurado, la criticidad queda «no evaluada», que no es cero.
- **Con consecuencia de seguridad nunca sale «operar hasta la falla».** Si
  ninguna tarea proactiva sirve, la salida es rediseño, y es obligatorio.

## 12. Lo que no hace, dicho aquí

- **La foto todavía no diagnostica.** La consulta es texto o dictado. Reconocer
  la avería en una imagen pide un modelo que necesita red, que es justo lo que
  falta en faena.
- **No propone la prueba que confirma antes de desarmar.** Entrega la causa y
  los pasos; todavía no le dice cuál es la comprobación más barata que
  descartaría. Es lo siguiente.
- **No sabe lo que no se cargó.** Si el historial está viejo, las respuestas
  también.
- **No es mantenimiento predictivo.** No hay sensores. Lo que hay es analítica
  sobre fechas y horómetro anotados a mano: útil y honesto, pero no es lo
  mismo.
- **No tiene TPM.** Ni checklist de mantenimiento autónomo ni registro de
  anomalías. Está diseñado y pendiente de construir.
- **No genera el plan de tareas.** El análisis RCM dice qué estrategia
  corresponde; todavía no produce la tarea con su intervalo, herramienta y
  repuesto.
- **No calcula costo-efectividad.** No hay un solo dato económico en el
  sistema. Donde haría falta, dice «información económica insuficiente» y no
  declara ningún ahorro.
- **No garantiza que su RCM esté bien hecho.** Exige que las siete preguntas
  estén respondidas; no puede juzgar si están bien respondidas. Eso pide un
  facilitador y a los mantenedores en la sala, y eso no es software.
