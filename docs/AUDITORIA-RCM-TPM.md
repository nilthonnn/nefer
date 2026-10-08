# Auditoría de conformidad · RCM + TPM en FixMate

**Fecha:** 2026-10-08 · **Revisión:** 2 · **Alcance auditado:** `commit ee0229c`

> **Revisión 2** — cerrada OBS-02 con la taxonomía implementada. La revisión 1
> la dejaba abierta y documentada.

Esta auditoría no pregunta si FixMate funciona —de eso responden 970 pruebas—
sino algo distinto: **si lo que declara cumplir, lo cumple**, y si lo que
produce sirve como registro dentro de dos años, cuando el que lo escribió ya
no esté y quien lo mire sea un auditor externo o un cliente que reclama.

Se audita el proyecto contra el criterio que **él mismo invoca**. Ésa es la
regla: una herramienta no es no conforme por no hacer algo que nunca
prometió; lo es por prometerlo y no hacerlo.

---

## 1. Alcance

| | |
|---|---|
| **Incluido** | El paquete `nefer/fixmate/` (RCM, TPM, criticidad, catálogo, decisión, FMECA), las dos pantallas generadas, los ejemplos repartidos como modelo y la documentación que los acompaña |
| **Excluido** | El motor de diagnóstico y el aprendizaje —auditados por su propia suite—, y los otros tres productos del repositorio (actas, camal, EEFF) |
| **Método** | Revisión documental contra el criterio, inspección de código con evidencia en `archivo:línea`, y ejecución de las pruebas como evidencia objetiva |

### Criterio: referencias normativas

Esto faltaba, y es la primera no conformidad: se citaban normas **sin
edición**. Una auditoría se hace contra un texto concreto.

| Referencia | Edición tomada | Qué se toma de ella | Estado |
|---|---|---|---|
| SAE JA1011 · *Evaluation Criteria for RCM Processes* | 1999-08, rev. 2009-08 | Las siete preguntas, el orden del árbol de decisión, las acciones por defecto | Existe una revisión **2024-11** listada por distribuidores que **no se ha verificado** contra el texto de SAE. Mientras no se verifique, el criterio aplicado es la de 2009 |
| SAE JA1012 · guía de la anterior | — | Vocabulario | No consultada: no se tiene el texto |
| ISO 14224 | 2016 (3.ª ed., confirmada 2022) | **Sólo la estructura**: modo / mecanismo / causa, la recomendación de no tener «Otro» y la de conservar el texto libre | Los **códigos no se toman**: ver NC-01 |
| Manual AIAG-VDA FMEA | 1.ª ed., 2019 | La tabla de prioridad de acción que reemplaza al RPN | Aplicado |
| ISO 8601 | — | El formato de fecha de los registros | Aplicado desde esta auditoría |

**Lo que el proyecto NO declara cumplir, y por tanto no se audita:** ISO
55001 (gestión de activos), ISO 9001, IEC 60812. Si alguna vez se declaran,
se auditan.

### Clasificación de hallazgos

- **No conformidad mayor:** se declara una conformidad que no se sustenta, o
  falta un control sin el cual el registro no vale.
- **No conformidad menor:** un incumplimiento puntual que no invalida el
  sistema.
- **Observación:** no incumple nada hoy; va camino de hacerlo.

---

## 2. Resultado

| # | Hallazgo | Clase | Estado |
|---|---|---|---|
| NC-01 | Se declaran códigos «ISO 14224» que son propios | **Mayor** | Subsanada |
| NC-02 | Normas citadas sin edición | Menor | Subsanada |
| NC-03 | Fechas de registro sin formato controlado | Menor | Subsanada |
| NC-04 | El análisis no se identifica: ni versión, ni aprobación, ni vigencia | Menor | Subsanada |
| NC-05 | Ambigüedad de códigos detectada en uso, no en revisión | Menor | Subsanada |
| OBS-01 | Seis clases de consecuencia frente a cuatro de la norma, sin mapeo declarado | Observación | Subsanada |
| OBS-02 | Jerarquía de activos de tres niveles frente a la taxonomía de la norma | Observación | Subsanada en rev. 2 |

---

## 3. Hallazgos

### NC-01 · Mayor — Se atribuía a ISO 14224 un juego de códigos propio

**Criterio.** La regla del propio proyecto: *«no declares que FixMate cumple
hasta que las funciones estén implementadas y probadas»*, y la regla de
evidencia: *si no existe, no inventar*. Atribuir a una norma un contenido que
no sale de ella es exactamente eso.

**Evidencia.**

- `nefer/fixmate/anomalia.py:15` — «`catalogo.clasificar()`, que devuelve un
  código **ISO 14224**».
- `nefer/fixmate/rcm.py:204`, `tpm.py:102`, las dos pantallas y tres manuales
  — «el catálogo ISO 14224».
- `docs/ARQUITECTURA-RCM-TPM.md`, tabla de capacidades — fila «Taxonomía de
  fallas ISO 14224 | **Sí**».
- Los códigos reales: `ADM.RESTRICCION.FILTRO`, `TER.SOBRECALENTAMIENTO.RADIADOR`.
  ISO 14224 publica sus propias listas, del estilo `FTS`, `ELP`, `VIB`, `OHE`.

**Análisis.** Lo que sí viene de la norma es real y vale: la separación en
modo / mecanismo / causa, la ausencia de «Otro» y la conservación del texto
libre. Lo que no viene son los códigos, que son de FixMate y están hechos
para maquinaria pesada, no para equipo de proceso de petróleo y gas. La
diferencia importa el día que un cliente pida *«datos en formato ISO 14224»*:
con lo que había, alguien habría contestado que sí.

**Subsanación.**
1. Corregido el texto en los nueve sitios: «el catálogo de fallas», y donde
   corresponde, «con la **estructura** de ISO 14224 y códigos propios».
2. `catalogo.Entrada` gana `codigo_iso`, opcional y **vacío de fábrica**,
   para que una planta que tenga la norma mapee sus entradas. No se rellena a
   ojo: un mapeo inventado viaja como si fuera bueno.
3. La tabla de capacidades dice ahora «con la **estructura** de ISO 14224» y
   remite a esta no conformidad.

### NC-02 · Menor — Normas citadas sin edición

**Evidencia.** «SAE JA1011» e «ISO 14224» aparecen sin año en código y
documentación; sólo AIAG-VDA llevaba fecha (2019).

**Análisis.** Sin edición no hay criterio: JA1011 tiene al menos tres
revisiones y lo que se declara cumplir cambia con ellas.

**Subsanación.** La tabla de referencias normativas de §1, con la edición
tomada, qué se toma de cada una y qué no se ha verificado.

### NC-03 · Menor — Fechas de registro sin formato controlado

**Evidencia.** `rcm.Analisis.fecha`, `tpm.Ejecucion.fecha` y
`anomalia.Anomalia.fecha` eran cadenas sin validar. Peor:
`Anomalia.dias_abierta()` capturaba el `ValueError` y devolvía `None`.

**Análisis.** «03/04/2026» es el 3 de abril en Lima y el 4 de marzo en
Houston. Y el modo de fallar era el peor posible: **silencioso**. Una
anomalía mal fechada entraba al sistema, no daba error en ninguna parte y
desaparecía de la cuenta de días abiertos. Justo la mal registrada dejaba de
pedir atención.

**Subsanación.** `nefer/fixmate/registro.py`: la fecha de un registro es ISO
8601 (`AAAA-MM-DD`) o está vacía. Vacía se admite —es «no declarada», que es
honesto y los informes cuentan—; ambigua, no. Aplicado a los tres registros,
con el error nombrando el archivo.

### NC-04 · Menor — El análisis no se identificaba como documento

**Criterio.** JA1011 exige que el análisis sea **revisable**, y revisable
quiere decir poder saber qué versión se mira, quién la aprobó y cuándo toca
volver a mirarla.

**Evidencia.** `Analisis` tenía facilitador, participantes y fecha. No tenía
versión, ni aprobación, ni próxima revisión. El `estado`
propuesto/validado/descartado es **por modo de falla**, no del documento.

**Análisis.** Un análisis sin versión ni aprobación es un borrador que
alguien va a usar como si fuera definitivo. Y sin fecha de próxima revisión,
una consecuencia evaluada en un contexto operacional que ya cambió sigue
pareciendo vigente.

**Subsanación.** `revision`, `aprobado_por` y `proxima_revision`, **opcionales**
—exigirlas rompería los análisis que ya existen, y un campo obligatorio que
la gente rellena con «-» no registra nada—. Lo que hace el sistema es
decirlo: `rcm.calidad()` audita el análisis **como registro**, el comando
`rcm analizar` lo imprime y la pantalla lo muestra en su propio panel. El
análisis de ejemplo —el que todo el mundo copia— quedó identificado.

> **Completitud y registro son dos medidas distintas.** Las siete preguntas
> dicen si el análisis está terminado; el registro, si dentro de dos años se
> puede saber quién responde por él. Un análisis puede tener las siete
> contestadas y no ser un registro válido, y ésa es la diferencia que nadie
> ve hasta que llega la auditoría.

### NC-05 · Menor — Ambigüedad de códigos detectada en uso, no en revisión

**Evidencia.** `anomalia.enlazar()` se niega —correctamente— a elegir cuando
dos modos del mismo análisis declaran el mismo código de catálogo. Pero
`rcm.completitud()` no lo reportaba: el análisis se daba por completo con la
ambigüedad dentro.

**Análisis.** El control existía en el peor sitio: en el momento de usar el
dato, meses después, en la oficina, cuando llega una anomalía de campo que no
engancha y nadie sabe por qué. La ambigüedad se resuelve en el análisis.

**Subsanación.** `rcm.calidad()` la denuncia al revisar, nombrando los dos
modos y el código. Se ve en el comando y en la pantalla.

### OBS-01 · Seis clases de consecuencia frente a cuatro de la norma

JA1011 agrupa las consecuencias en cuatro categorías —oculta, seguridad o
medio ambiente, operacional y no operacional—; FixMate usa seis. No es una
discrepancia: la norma agrupa y aquí se separa lo que el taller distingue al
decidir. Lo que faltaba era el **mapeo declarado**, sin el cual nadie puede
auditar un análisis de FixMate contra la norma.

**Subsanación.** `rcm.CONSECUENCIAS_JA1011` declara la equivalencia de las
seis, y `rcm.OCULTA_JA1011` deja constancia de que la cuarta categoría de la
norma no es una clase aquí sino el booleano `evidente` del modo de falla —la
primera bifurcación del análisis—. El mapeo viaja también a la pantalla.

### OBS-02 · La jerarquía de activos frente a la taxonomía de la norma

**Evidencia.** ISO 14224 define una taxonomía de **nueve niveles**: los cinco
primeros dicen dónde está el equipo y a qué operación pertenece; los cuatro
últimos lo desarman. FixMate tenía el activo más sistema / subsistema /
componente, sin decir en ningún sitio a qué nivel correspondía cada uno.

**Análisis.** Lo que estaba abierto no era «faltan niveles». Era que **nadie
podía responder si la jerarquía mapea a la norma sin abrir el código**, y que
el día que un cliente pidiera intercambio conforme, alguien tendría que
inventar el mapeo contra reloj. Ampliar la jerarquía «por si acaso» habría
sido peor: un nivel que nadie necesita se rellena con cualquier cosa, que es
el problema de «Otro» por otro camino.

**Subsanación.** `nefer/fixmate/taxonomia.py` declara los nueve niveles y, en
cada uno, **de qué campo sale o por qué no se modela**:

| | Nivel | De dónde sale |
|---|---|---|
| 1 | industria | constante de la instalación, la pone quien exporta |
| 2 | categoría de negocio | ídem |
| 3 | instalación | `Activo.instalacion` — **nuevo**: es el único de los cinco de localización que cambia por activo en una flota que se mueve |
| 4 | planta o unidad | **no se modela**: una flota móvil no tiene planta estable |
| 5 | sección o sistema | **no se modela**: el frente cambia de turno a turno |
| 6 | **unidad de equipo** | `Activo.codigo` — es el *nivel común de reporte* de la norma, y es donde FixMate cuenta el MTBF |
| 7 | subunidad | `Ubicacion.sistema`, con `subsistema` como refinamiento propio |
| 8 | **componente / ítem mantenible** | `Ubicacion.componente` — es *donde cae el mantenimiento* según la norma, y donde RCM decide la estrategia |
| 9 | parte | **no se modela**: RCM decide en el ítem mantenible |

Que los dos niveles con nombre propio en la norma —el 6 y el 8— coincidan
con cómo ya trabajaba FixMate no es casualidad: es la razón de que el mapeo
salga limpio sin tocar el modelo.

`fixmate rcm taxonomia` lo imprime nivel por nivel, y con `--csv` saca una
fila por modo de falla con su taxonomía entera, que es la forma que tiene un
archivo de intercambio. Los niveles que no se modelan salen **vacíos y
dichos**, no omitidos.

**Lo que sigue sin estar, y es una decisión, no un olvido:** los niveles 4, 5
y 9. Si el cliente es una planta fija en vez de una flota, el 4 y el 5 pasan
a tener sentido y hay que agregarlos; está escrito en el encabezado del
módulo para que quien llegue a esa necesidad lo encuentre.

---

## 4. Lo que esta auditoría no cubre

- **No se verificó contra el texto de las normas.** No se tienen: ISO 14224 y
  SAE JA1011 son documentos con licencia. Se auditó contra lo que el proyecto
  declara y contra fuentes secundarias verificables. Una auditoría de
  certificación necesita los textos.
- **No se audita la calidad técnica de los análisis**, sólo su forma. Que un
  modo de falla sea el correcto para esa máquina no lo puede decir un
  programa: eso es el equipo en la sala, y es lo que JA1011 pide.
- **No cubre el motor de diagnóstico**, que tiene su propia suite y su propia
  regla de evidencia.

## 5. Conclusión

Los siete hallazgos quedaron subsanados, con pruebas que los fijan: seis en
la revisión 1 y OBS-02 en la revisión 2, con la taxonomía de los nueve
niveles implementada y el mapeo probado.

El hallazgo que importa es NC-01, y conviene decir por qué: **el sistema era
honesto en su comportamiento y no en su etiqueta**. El catálogo nunca
inventó un código, nunca enganchó al «más parecido» y siempre contó lo que no
sabía codificar. Lo que fallaba era el rótulo, que prometía una conformidad
con una norma que nadie había comprobado. Es la clase de defecto que no se
nota hasta que alguien de fuera lo mira — que es, exactamente, lo que es una
auditoría.
