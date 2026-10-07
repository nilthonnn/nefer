# Arquitectura RCM + TPM en FixMate

Documento de diseño. Dice **qué hay hoy**, **qué se agregó**, **qué evidencia
exige cada cosa** y, sobre todo, **qué NO hace**. Se actualiza en cada fase;
lo que todavía no está implementado aparece marcado como tal y no se describe
en presente.

Estado: **Fases 6–14 entregadas.** Modelo de datos, motor de decisión RCM,
TPM (pilar 1), plan de tareas, indexación e integración con el motor de
diagnóstico, cierre trazable, matriz FMECA, tablero, CLI y API de lectura.

Lo que sigue **sin existir** está en la sección 6, y no se describe en
presente en ninguna otra parte de este documento.

---

## 1. El punto de partida, sin adornos

FixMate no tenía RCM ni TPM. Tenía algo mejor de lo que suele suponerse, y
peor de lo que haría falta:

| Capacidad | Antes | Nota |
|---|---|---|
| Taxonomía de fallas ISO 14224 | **Sí** | `catalogo.py`: 41 entradas, 14 sistemas, 32 modos observables, 19 mecanismos. Sin categoría «Otro», por recomendación de la norma |
| Precauciones de seguridad con fuente | **Sí** | `seguridad.py`: distingue lo que dice el manual indexado de la regla fija de la herramienta |
| Cierre → historial → aprendizaje | **Sí** | `cierre.py` + `aprendizaje.py`, con precisión medida y publicada |
| MTBF, recurrencia, ritmo de uso | **Sí** | `prediccion.py`, rotulado explícitamente como *no* predictivo |
| Regla de evidencia | **Sí** | El motor se niega a responder sin antecedente y a estimar un par de apriete |
| Activo como entidad | **No** | `codigo_equipo` era un string en metadatos |
| Función / falla funcional / efecto / consecuencia | **No** | Cero ocurrencias en el paquete |
| Criticidad | **No** | — |
| Decisión de estrategia de mantenimiento | **No** | — |
| TPM (checklist, anomalía) | **No** | — |
| Datos económicos | **No** | Ni una tarifa en todo el repositorio |

## 2. La decisión que define todo lo demás

**RCM y TPM se guardan como fragmentos, no como tablas nuevas.**

Toda la persistencia de FixMate es un solo tipo:

```
Fragmento { id · texto · fuente · tipo · metadatos:dict · vector[256] }
```

que vive o en un archivo JSON que se copia al teléfono, o en una tabla
`fixmate_fragmentos` con `metadatos jsonb` y `embedding vector(256)`.

Meter tablas relacionales para RCM rompería la propiedad que sostiene el
producto: *un índice es un archivo que viaja al bolsillo del técnico y
funciona sin red*. Un análisis RCM en PostgreSQL deja de viajar.

En cambio, un análisis RCM indexado como fragmento:

- viaja en el mismo índice, sin red;
- cae en la misma tabla, con el mismo índice GIN;
- y **lo recupera el motor de diagnóstico sin escribir integración**:
  preguntar «motor se recalienta» devuelve los modos de falla RCM asociados
  porque ya son evidencia buscable.

## 3. El pegamento: el código del catálogo es la llave

```
            texto libre del técnico
                      │  catalogo.clasificar()
                      ▼
          TER.SOBRECALENTAMIENTO.RADIADOR      ← una sola llave estable
                      │
        ┌─────────────┼──────────────┬──────────────────┐
        ▼             ▼              ▼                  ▼
  RCM: ModoFalla   Historial:    TPM: anomalía     Plan: tarea
  .codigo_catalogo  informes      (pendiente)      (pendiente)
                    con esa causa
                    → MTBF, recurrencia
```

El catálogo ya codifica `sistema · modo observable · mecanismo · causa`. RCM
lo extiende **por los extremos** —arriba activo → función → falla funcional,
abajo efecto → consecuencia → criticidad → tarea— y no lo reemplaza. El
vocabulario de sistemas de `activos.py` se deriva del catálogo en tiempo de
import, justamente para que no puedan divergir.

## 4. Lo que se agregó

```
nefer/fixmate/activos.py      Activo · Ubicacion · Flota · desde_indice()
nefer/fixmate/criticidad.py   Metodo configurable · Factor · Nivel · evaluar()
nefer/fixmate/rcm.py          Funcion · FallaFuncional · ModoFalla · Efecto
                              · Consecuencia · Analisis · las 7 preguntas
nefer/fixmate/decision.py     Respuestas · Dictamen · decidir() · Decisiones
nefer/fixmate/tpm.py          Checklist · PuntoChecklist · Ejecucion
                              · estado() · cumplimiento()
nefer/fixmate/anomalia.py     Anomalia · desde_ejecucion() · clasificar()
                              · enlazar() · salud()
nefer/fixmate/plan.py         Tarea · Plan · generar() · punto_tpm()
nefer/fixmate/indexado.py     de_analisis() · de_checklist() · de_anomalia()
nefer/fixmate/fmeca.py        filas() · a_csv() · contrastar()
nefer/fixmate/tablero.py      rcm() · tpm() · confiabilidad() · completo()
nefer/fixmate/cargador.py     leer los JSON con errores que se entienden
```

Cambios **compatibles** en archivos existentes:

| Archivo | Cambio | Riesgo |
|---|---|---|
| `motor.py` | `Diagnostico.contexto_rcm`, con default `[]` | ninguno: campo nuevo al final |
| `ingesta.py` | 3 claves opcionales más en `CAMPOS_INFORME` | ninguno: sólo se copian si están |
| `cierre.py` | `desde_diagnostico()` copia el modo si hay uno solo | ninguno |
| `cli.py` | subcomandos `rcm`, `tpm`, `tablero` | ninguno: parsers nuevos |
| `api.py` | 4 endpoints GET; 3 campos opcionales en el informe | ninguno |

Ninguna función existente cambió de comportamiento. Las 671 pruebas previas
siguen pasando sin tocarse.

### 4.1 Cuatro cosas que el modelo se niega a aceptar

| Se rechaza | Por qué |
|---|---|
| Función sin estándar de desempeño | «El motor debe funcionar» no se puede fallar de forma verificable, y de ahí no sale ningún modo de falla útil |
| Falla funcional huérfana | Dice cómo falla algo que nadie declaró que la máquina deba hacer |
| Modo de falla `validado` sin evidencia | Un análisis validado de memoria es una opinión con sello |
| `Consecuencia("oculta")` | No es una categoría al lado de seguridad: es la primera bifurcación del análisis. Ver 4.2 |

### 4.2 Evidente u oculta va primero, y no es una consecuencia

Una falla oculta —válvula de alivio pegada, detector que no detecta— por sí
sola no produce ningún efecto: la máquina sigue trabajando. Lo que produce es
que, cuando ocurra la segunda falla, **no haya nada que la detenga**. El
riesgo que se trata no es el de esa falla sino el de la **falla múltiple**.

Por eso su tratamiento por defecto es *búsqueda de fallas* —probar
periódicamente que la protección responde— y por eso tiene que decidirse
antes que nada. En el modelo es `ModoFalla.evidente: bool`, y
`Consecuencia("oculta")` levanta un error que explica dónde va.

### 4.3 Criticidad: la escala es de la empresa

`evaluar()` **exige un método**. No hay escala por defecto, no hay fallback
silencioso. Sin método configurado, la criticidad es `"no evaluada"`, que es
un estado legítimo y visible — distinto de cero, que se lee como bajo riesgo.

Se ofrecen dos métodos de ejemplo, ambos con `EJEMPLO` en el nombre y ninguno
por defecto:

- **`PRIORIDAD_EJEMPLO`** (recomendado): tabla al estilo AIAG-VDA 2019, que
  pondera severidad → frecuencia → detección **sin multiplicarlas**.
- **`RPN_EJEMPLO`**: el RPN clásico, conservado porque hay plantas cuyo
  procedimiento lo exige.

El RPN multiplica escalas **ordinales**, lo que es estadísticamente
indefendible: un 8 de severidad no es «el doble» de un 4, es el escalón
siguiente de una lista. La consecuencia es verificable y está fijada en una
prueba:

```
severidad 2 × frecuencia 3 × detección 5 = 30   → "media"
severidad 5 × frecuencia 3 × detección 2 = 30   → "media"
```

El mismo número para una molestia y para algo que mata gente. AIAG-VDA
eliminó el RPN en 2019 por esto. El método ejemplo de prioridad sí los
separa: el segundo sale `"alta"`.

Cada evaluación guarda el **método y su versión**. Sin eso no hay forma de
saber si un «12» de hace dos años es comparable con un «12» de hoy.

### 4.4 La matriz de decisión

Seis estrategias: `cbm` · `restauracion` · `descarte` · `busqueda_fallas` ·
`operar_hasta_falla` · `rediseno`. Nunca devuelve «preventivo» a secas, y
cada dictamen viaja con el **camino** de preguntas que lo produjo.

Orden del árbol, que no es arbitrario:

1. **¿Es evidente?** Si no → búsqueda de fallas, o rediseño si no se puede
   verificar.
2. **¿Consecuencia de seguridad o ambiental?** Cambia el criterio de
   aceptación de la tarea.
3. **¿Degradación detectable con aviso suficiente?** → CBM. Primera en
   preferencia porque aprovecha la vida útil y no abre una máquina sana.
4. **¿Hay intervalo de edad?** → restauración o descarte. Esta es la pregunta
   que la mayoría de pautas OEM no pasa: Nowlan y Heap (United Airlines,
   1978) encontraron que el **89 %** de los ítems no tiene zona de desgaste
   identificable (patrones D, E, F), de modo que un límite por horas no
   previene nada. El código lo avisa cuando la respuesta es «no».
5. **¿Viable y costo-efectiva?**

**La guarda que no se negocia:**

> Con consecuencia de seguridad o ambiental, «operar hasta la falla» no puede
> salir nunca, en ninguna combinación de respuestas. Si ninguna tarea
> proactiva sirve, la salida es **rediseño**, y es obligatorio.

Está comprobado por fuerza bruta sobre las 3⁶ = 729 combinaciones de
respuestas, para fallas evidentes y ocultas.

### 4.5 `None` no es `False`

Las respuestas del árbol son tri-estado. `None` significa «nadie se lo
preguntó», que no es lo mismo que «se evaluó y la respuesta es no». Un plan
donde nadie se preguntó si la degradación era detectable no es un plan donde
se decidió que no lo era. Cuando quedan preguntas sin evaluar, el dictamen
sale del lado conservador y se marca `incompleta=True`.

### 4.6 Las siete preguntas de SAE JA1011

Implementadas como `PREGUNTAS` y verificadas por `completitud()`, que
devuelve qué falta en cada una y con qué id.

| | Pregunta | Qué la responde |
|---|---|---|
| Q1 | Funciones y estándares de desempeño en el contexto actual | Cada función declarada, con su estándar |
| Q2 | De qué maneras puede fallar | Al menos una falla funcional por función |
| Q3 | Qué causa cada falla funcional | Al menos un modo de falla por falla funcional |
| Q4 | Qué sucede cuando ocurre cada modo | El efecto descrito |
| Q5 | En qué forma importa cada falla | Evidente u oculta, y al menos una consecuencia |
| Q6 | Qué hacer para predecir o prevenir | Una decisión registrada por modo |
| Q7 | Qué hacer si no hay tarea proactiva adecuada | La acción por defecto justificada |

**`completo` es binario.** No hay porcentaje que redondee hacia arriba ni
«prácticamente completo». El criterio de JA1011 es binario a propósito,
porque la norma nació en respuesta a metodologías incompletas vendidas con
ese nombre.

Cuatro de las siete (Q1, Q2, Q3, Q5) sostienen la cadena *función → falla →
modo → consecuencia*. Si falta alguna, `rompe_cadena=True` y el resumen lo
dice con todas las letras: *esto todavía no es un análisis RCM*.

### 4.7 El contexto operacional no es un comentario

Un `Analisis` está amarrado a un activo **y a un contexto**. Dos bombas
idénticas, una impulsando agua limpia en superficie y la otra lodo con
sólidos a 4.200 m, no tienen la misma función, ni los mismos modos de falla
dominantes, ni la misma consecuencia si se detienen. Copiar un análisis sin
reconfirmar el contexto es el atajo con el que un plan se llena de tareas que
no aplican.

### 4.8 TPM: pilar 1, y nada más

`tpm.py` cubre Jishu Hozen. TPM tiene ocho pilares, y llamar «TPM
implementado» a una lista de verificación es la clase de afirmación que
vuelve inservible la palabra.

**Cinco clases de punto, no siete.** El encargo pedía también «detectar
anomalías» y «registrar anomalía». No son clases de punto: son lo que *pasa*
cuando un punto sale NOK. Un punto cuya actividad es «detectar anomalías» no
tiene criterio de aceptación posible y en campo se marca OK siempre.

Tres defensas contra la degradación conocida de una ronda CIL —deja de
ejecutarse y empieza a firmarse—:

| Defensa | Qué impide |
|---|---|
| `sin_acceso` es un resultado y rompe la ronda completa | Que el operador marque OK en un punto que no pudo ver |
| El tiempo se mide, no se declara | Una pauta de 30 s despachada en 4 no se ejecutó: se firmó. Criterio configurable de planta, **no normativo** |
| `nunca_vistos` | Un punto inaccesible no es descuido del operador: es defecto de la máquina o de la pauta |

### 4.9 La conexión TPM → RCM, y cuándo NO se cruza

El encargo pide que sea automática «cuando exista suficiente información».
La frase importante es la última, y es la que define el diseño.

```
texto libre del operador
   │ catalogo.clasificar()     ← no adivina: sin «Otro», en empate no elige
   ▼
TER.SOBRECALENTAMIENTO.RADIADOR
   │ enlazar(): coincidencia EXACTA de código y de activo
   ▼
modo de falla F1.1.1 del análisis RCM
```

Queda **sin enlazar**, y se cuenta, en cuatro casos: sin código; con código
que ningún modo declara; con análisis de otro activo; y con dos modos que
declaran el mismo código —ambigüedad que se resuelve en el análisis, no a la
suerte—.

Nunca se elige «el modo más parecido». Una anomalía enlazada al modo
equivocado contamina el MTBF por modo, la frecuencia histórica del análisis
y la decisión de estrategia que sale de ahí. Un enlace que falta se ve; uno
equivocado se suma con los demás.

### 4.10 RCM → TPM: tres condiciones declaradas, ninguna inferida

`plan.punto_tpm()` baja una tarea a la ronda autónoma sólo si: la estrategia
es **CBM**, la verificación es **sensorial** (vista, oído, tacto, olfato) y
está declarado que cae **dentro del alcance del operador**. Una restauración
no es una ronda de treinta segundos, y probar una protección no es mirarla.

El borrador baja con el **criterio vacío**: el análisis dice *qué* mirar, no
*qué significa que esté bien*.

### 4.11 El plan: lo que no se rellena

Una tarea generada con intervalo, límite y herramienta inventados se ve
terminada y no lo está. En campo eso se ejecuta: alguien lleva la llave
equivocada a 40 km.

| Campo | Por qué nace vacío |
|---|---|
| `intervalo_dias` / `intervalo_horas` | De «hay una edad a la que la probabilidad sube» no sale un número: sale que existe uno y hay que medirlo |
| `limite` + `fuente_limite` | Tiene que venir del OEM o de un estándar, nunca de esta herramienta. Un límite sin fuente sigue incompleto |
| `procedimiento` | Igual |

`operar_hasta_falla` **no genera tarea**: la decisión fue no programar nada.
El plan lista aparte lo que decidió no hacer, porque un plan que lo esconde
no se puede auditar.

### 4.12 FMECA: la frecuencia se cuenta, no se declara

Un FMECA se escribe en una sala con gente que opina; después la máquina
falla como le parece. `contrastar()` recorre el historial y cuenta, cruzando
por **código de catálogo** —la única llave estable: por texto libre,
«colmatado» y «tapado» se juntan a veces sí y a veces no— y devuelve:

- la frecuencia real de cada modo;
- los modos analizados que **nunca ocurrieron**: puede ser prevención que
  funciona o una fila copiada de otra máquina, y el dato no distingue;
- las causas del historial **sin modo que las cubra**: ésas sí son un hueco,
  y son la lista de trabajo de la próxima revisión;
- los informes que el catálogo **no pudo codificar**, que es la medida
  honesta de cuánto alcanza.

**Contar no corrige.** Un modo que nunca ocurrió no se borra ni se marca
inválido. Automatizarlo sería borrar tareas de seguridad por falta de
evidencia, que es justo lo que la guarda de 4.4 impide. `aplicar=True` es un
argumento aparte: medir y modificar son dos permisos distintos.

### 4.13 El tablero: `None` no es cero

Un tablero que muestra 0 % de cumplimiento sin ninguna ronda dice «lo
hicieron mal» cuando lo que pasa es que no hay dato, y así es como un
tablero deja de mirarse. Todo indicador incalculable devuelve `None`, y
`a_dict()` lo conserva como `null`.

**MTTR y disponibilidad quedan en `null` siempre.** FixMate registra cuándo
ocurrió una falla, no cuánto duró la reparación ni cuántas horas estuvo
detenida la máquina. Un MTTR inventado se usa para dimensionar un taller.

El MTBF no se recalcula aquí: sale de `prediccion`, que ya declara sus
mínimos. Dos fórmulas para la misma pregunta dan dos números distintos, que
es peor que no tener ninguno.

### 4.14 CLI y API

```
nefer fixmate rcm analizar  <a.json> [--indexar]   valida contra JA1011
nefer fixmate rcm listar                           modos en el índice
nefer fixmate rcm matriz    <a.json> [-o f.csv]    FMECA
nefer fixmate rcm tareas    <a.json>               el plan y sus huecos
nefer fixmate tpm checklist <p.json> [--indexar]   valida la pauta
nefer fixmate tpm ejecutar  <e.json> -p <p.json> [--rcm <a.json>]
nefer fixmate tpm pendientes                       anomalías abiertas
nefer fixmate tablero                              MTBF y recurrencia
```

`rcm analizar` sale **0** con las siete contestadas y **2** si falta algo.
Es código de salida, no texto: así entra en un CI sin que nadie parsee la
pantalla.

Los endpoints HTTP (`GET /rcm`, `/rcm/modos/{codigo}`, `/tpm/anomalias`,
`/tablero`) son **de lectura**. Crear o aprobar un análisis por HTTP
exigiría autenticación y control de versiones, y FixMate no tiene ninguna de
las dos: sin eso, cualquiera en la red del taller reescribe el plan de
mantenimiento sin dejar rastro. Los análisis se cargan con la CLI, que corre
con los permisos de quien la ejecuta.

## 5. Compatibilidad

- **No hay migración.** El código del activo es el mismo `codigo_equipo` que
  los informes ya traían. Declarar la excavadora EX-220 adopta de una vez
  todo su historial, con su MTBF y sus reincidencias ya calculables.
- `activos.desde_indice()` deduce la flota del historial existente para
  arrancar un piloto sin cargar nada. Todo lo que el historial no dice
  —marca, contexto, criticidad— **queda vacío**, nunca supuesto.
- Un informe antiguo sin análisis RCM se lee como **RCM no evaluado**. No se
  le inventa un análisis.
- Ningún campo nuevo es obligatorio en ningún fragmento existente.

## 6. Lo que esto NO hace

Dicho antes de que alguien lo suponga:

- **No garantiza un RCM correcto.** Exige que las siete preguntas estén
  respondidas; no puede juzgar si están bien respondidas. JA1011 requiere un
  facilitador y los mantenedores en la sala, y eso no es software.
- **TPM es sólo el pilar 1.** Jishu Hozen y parte de mantenimiento
  planificado. Los otros siete pilares no existen.
- **No hay costo-efectividad.** No existe un solo dato económico en el
  repositorio. `costo_efectiva=None` produce el aviso «Información económica
  insuficiente para determinar costo-efectividad» y nada más. No se declara
  ahorro.
- **No hay MTTR ni disponibilidad.** Ver 4.13.
- **Hay dos pantallas, y no cubren todo.** La ronda CIL
  (`docs/fixmate/ronda/`) corre en el teléfono del operador y el análisis RCM
  (`docs/fixmate/rcm/`) en la mesa de la oficina; las dos son espejos
  generados de Python y cruzados por pruebas. Lo que **no** tienen pantalla:
  crear o editar el análisis —se edita el JSON—, evaluar criticidad, armar la
  matriz FMECA y cerrar anomalías. Eso sigue siendo línea de comandos.
- **Las cuatro superficies comparten una sola piel.** Los tokens de color
  salen de la app de diagnóstico (`herramientas/piel.py`) y se copian a la
  página de entrada, a la ronda y al análisis; la capa común de componentes
  (`herramientas/piel/base.css`) no declara un solo color, y una prueba lo
  comprueba. Las dos pantallas nuevas eran oscuras y punto; ahora siguen al
  aparato, que es lo que hace falta a 4.200 m al sol.
- **El cruce ronda → análisis se puede hacer sin terminal.** La pantalla de
  RCM abre el archivo del teléfono y pone cada hallazgo sobre su modo de
  falla, con el mismo enganche que `anomalia.enlazar` —código exacto, mismo
  activo, un solo candidato— y diciendo el motivo de los que no enganchan.
  Codificar texto libre contra el catálogo sigue siendo del comando.
- **La API no escribe RCM ni TPM.** Ver 4.14.
- **Sigue sin haber mantenimiento predictivo por sensores**, y `prediccion.py`
  lo sigue diciendo en su encabezado.
- **El enganche automático TPM → RCM tiene el techo del catálogo.** Con las
  pistas dentro del texto indexado, una consulta con vocabulario de taller
  recupera el análisis (medido: 0,558 y 0,591, contra 0,000 sin ellas). Lo
  que el catálogo no codifica —«el motor sobrecalienta», dos palabras
  genéricas— tampoco llega al análisis: 0,016. Se agranda agrandando el
  catálogo con `catalogo.cargar()`.
- **No valida el juicio.** Verifica que las siete preguntas estén
  respondidas; no puede juzgar si están bien respondidas.

## 7. Pruebas

| Archivo | Pruebas | Qué fija |
|---|---|---|
| `test_fixmate_activos.py` | 13 | Compatibilidad: declarar un activo no migra ni inventa nada |
| `test_fixmate_criticidad.py` | 13 | Que no haya escala por defecto; que el defecto del RPN se reproduzca y se advierta |
| `test_fixmate_rcm.py` | 26 | Las cuatro negativas del modelo; la llave al catálogo; las 7 preguntas en binario |
| `test_fixmate_decision.py` | 24 | La guarda de seguridad por fuerza bruta sobre 729 combinaciones; el orden del árbol; motivo escrito siempre |
| `test_fixmate_tpm.py` | 21 | Las cinco clases con criterio; «no pude ver» rompe la ronda; el tiempo medido |
| `test_fixmate_anomalia.py` | 24 | Cuándo NO se enlaza con RCM — los cuatro casos |
| `test_fixmate_plan.py` | 17 | Lo que el plan no rellena; las tres condiciones para bajar a TPM |
| `test_fixmate_indexado.py` | 15 | El §6 sin tocar el motor; que un fragmento RCM no aporte pasos |
| `test_fixmate_fmeca.py` | 18 | Contar no corrige; el cruce por código, no por texto |
| `test_fixmate_tablero.py` | 20 | `None` no es cero, en los tres tableros |
| `test_fixmate_cli_rcm.py` | 18 | Los errores del cargador, que es su valor real |
| `test_fixmate_integracion_rcm_tpm.py` | 5 | INT-001 entero, y que la cadena se niegue donde no hay evidencia |
| `test_fixmate_cruce_ronda.py` | 12 | Que el teléfono y la oficina digan lo mismo de una ronda |
| `test_fixmate_ronda_navegador.py` | 13 | «No pude ver» igual de fácil de tocar que «OK», en un navegador real |
| `test_fixmate_cruce_rcm.py` | 18 | El árbol en las 729 combinaciones × 7 consecuencias × evidente/oculta: 10.206 dictámenes comparados |
| `test_fixmate_rcm_navegador.py` | 21 | La guarda de seguridad en pantalla; la ronda encima del análisis; que lo exportado vuelva a entrar |
| `test_fixmate_piel.py` | 15 | Que las cuatro superficies sean el mismo producto, y que la capa común no declare color |

## 8. Fases pendientes

| Fase | Contenido | Estado |
|---|---|---|
| 8 | TPM: checklist configurable, ejecución, anomalía | **hecha** · `tpm.py`, `anomalia.py` |
| 9 | Plan de tareas desde la decisión RCM | **hecha** · `plan.py` |
| 10 | Indexar RCM/TPM como fragmentos → integración con el motor | **hecha** · `indexado.py` |
| 11 | Cierre trazable → aprendizaje | **hecha** · `cierre.py`, `ingesta.py` |
| 12 | CLI `fixmate rcm` / `fixmate tpm`, API | **hecha** · `cli.py`, `api.py`, `cargador.py` |
| 13 | Exportación FMEA/FMECA | **hecha** · `fmeca.py` |
| 14 | Tablero de indicadores | **hecha** · `tablero.py` |
| — | Frontend para RCM y TPM | **pendiente** |
