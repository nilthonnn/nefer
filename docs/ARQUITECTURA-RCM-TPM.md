# Arquitectura RCM + TPM en FixMate

Documento de diseño. Dice **qué hay hoy**, **qué se agregó**, **qué evidencia
exige cada cosa** y, sobre todo, **qué NO hace**. Se actualiza en cada fase;
lo que todavía no está implementado aparece marcado como tal y no se describe
en presente.

Estado: **Fase 6–7 entregadas** (modelo de datos + motor de decisión RCM).
TPM, plan de tareas, integración con el motor de diagnóstico, CLI, API y
exportación FMECA están **pendientes**.

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

## 4. Lo que se agregó en esta fase

```
nefer/fixmate/activos.py      Activo · Ubicacion · Flota · desde_indice()
nefer/fixmate/criticidad.py   Metodo configurable · Factor · Nivel · evaluar()
nefer/fixmate/rcm.py          Funcion · FallaFuncional · ModoFalla · Efecto
                              · Consecuencia · Analisis · las 7 preguntas
nefer/fixmate/decision.py     Respuestas · Dictamen · decidir() · Decisiones
```

Ningún archivo existente cambió de comportamiento. Las 671 pruebas previas
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
- **No hay TPM todavía.** Ni checklist ni anomalía. Está pendiente.
- **No hay plan de tareas todavía.** La decisión dice *qué estrategia*; no
  genera aún la tarea con su intervalo, herramienta y repuesto.
- **No hay costo-efectividad.** No existe un solo dato económico en el
  repositorio. `costo_efectiva=None` produce el aviso «Información económica
  insuficiente para determinar costo-efectividad» y nada más. No se declara
  ahorro.
- **No hay integración con el motor de diagnóstico todavía.** Los análisis
  aún no se indexan como fragmentos; eso es la fase siguiente.
- **No hay CLI, API ni frontend** para RCM todavía.
- **Sigue sin haber mantenimiento predictivo por sensores**, y `prediccion.py`
  lo sigue diciendo en su encabezado.

## 7. Pruebas

| Archivo | Pruebas | Qué fija |
|---|---|---|
| `test_fixmate_activos.py` | 13 | Compatibilidad: declarar un activo no migra ni inventa nada |
| `test_fixmate_criticidad.py` | 13 | Que no haya escala por defecto; que el defecto del RPN se reproduzca y se advierta |
| `test_fixmate_rcm.py` | 26 | Las cuatro negativas del modelo; la llave al catálogo; las 7 preguntas en binario |
| `test_fixmate_decision.py` | 24 | La guarda de seguridad por fuerza bruta sobre 729 combinaciones; el orden del árbol; motivo escrito siempre |

## 8. Fases pendientes

| Fase | Contenido | Estado |
|---|---|---|
| 8 | TPM: checklist configurable, ejecución, anomalía | pendiente |
| 9 | Plan de tareas desde la decisión RCM | pendiente |
| 10 | Indexar RCM/TPM como fragmentos → integración con el motor | pendiente |
| 11 | Cierre con `failure_mode_id` → aprendizaje | pendiente |
| 12 | CLI `fixmate rcm` / `fixmate tpm`, API, frontend | pendiente |
| 13 | Exportación FMEA/FMECA | pendiente |
| 14 | Tablero de indicadores RCM/TPM | pendiente |
