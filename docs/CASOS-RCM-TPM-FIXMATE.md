# Casos de prueba RCM + TPM

Casos funcionales ejecutables a mano contra la biblioteca. Cada uno dice qué
se hace, qué debe salir y **por qué importa** — un caso sin esa tercera línea
se convierte en un paso que nadie entiende y que se marca OK sin mirar.

Los casos marcados **pendiente** corresponden a fases no implementadas. No se
pueden ejecutar todavía y no se marcan como fallidos: no existen.

Estado al día de hoy: **todos ejecutables**, los RCM también desde la línea
de comandos. INT-001 está además fijado como prueba automática en
`tests/test_fixmate_integracion_rcm_tpm.py`.

---

## Preparación

Los datos de ejemplo están en [`ejemplos/rcm-tpm/`](../ejemplos/rcm-tpm/):
una excavadora inventada con lo justo para recorrer todos los casos. Para la
versión corta —qué teclear y qué tiene que salir— vea
[OPERACION-RCM-TPM.md](OPERACION-RCM-TPM.md).

```python
from nefer.fixmate.activos  import Activo
from nefer.fixmate.rcm      import Analisis, Consecuencia, Efecto, Referencia, completitud
from nefer.fixmate.decision import Decisiones, Respuestas
from nefer.fixmate.criticidad import PRIORIDAD_EJEMPLO
```

---

## RCM-001 · Crear activo

```python
ex = Activo("EX-220", "Excavadora hidráulica", "Komatsu", "PC220-8",
            categoria="excavadora",
            contexto="Interior mina, turno continuo, 4.200 m, polvo de sílice")
```

**Debe:** `ex.a_dict()["criticidad"] == "no evaluada"`.

**Importa porque:** un activo nuevo no nace con criticidad. Cero se leería
como bajo riesgo; «no evaluada» se lee como lo que es.

**Negativo:** `Activo("", "Excavadora")` levanta `ErrorActivo`. El código es
lo que está pintado en la máquina; sin él no hay con qué unir el historial.

---

## RCM-002 · Definir función

```python
a = Analisis(ex)
f = a.agregar_funcion(
    "Mantener la temperatura del refrigerante en régimen",
    "Entre 80 y 95 °C con carga continua al 100 %")
```

**Debe:** `completitud(a).respuestas[0].contestada is True`.

**Negativo:** `a.agregar_funcion("El motor debe funcionar", "")` levanta
`ErrorRCM`.

**Importa porque:** sin estándar no hay falla funcional verificable. «El
motor debe funcionar» no se puede fallar de ninguna manera medible, y de una
función así no sale ningún modo de falla útil.

---

## RCM-003 · Definir falla funcional

```python
ff = a.agregar_falla(f.id, "La temperatura supera 95 °C con carga continua")
```

**Debe:** `ff.id == "F1.1"`, y Q2 contestada.

**Negativo:** `a.agregar_falla("F9", "...")` levanta `ErrorRCM`.

**Importa porque:** una falla huérfana dice cómo falla algo que nadie declaró
que la máquina deba hacer.

---

## RCM-004 · Crear modo de falla enganchado al catálogo

```python
m = a.agregar_modo(ff.id, "Radiador obstruido por polvo de mina",
                   codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")
```

**Debe:** `m.ubicacion.sistema == "termico"`, `m.mecanismo == "Obstruccion"`,
heredados del catálogo sin reescribirlos.

**Negativo:** un código inexistente levanta `ErrorRCM` en vez de crearse.

**Importa porque:** es la llave que cose RCM con el motor de diagnóstico, con
el historial y —más adelante— con las anomalías TPM. Si cada módulo escribe
su propia versión de «radiador obstruido», no se pueden cruzar.

**Variante legítima:** un modo sin `codigo_catalogo` es válido. El catálogo no
cubre todo, y obligar a elegir una entrada parecida es el problema que el
catálogo evita no teniendo «Otro».

---

## RCM-005 · Registrar efecto

```python
m.efecto = Efecto(
    local="Sube la temperatura del refrigerante y el ECM reduce potencia",
    observa_operador="Aguja en rojo, pérdida de fuerza en pendiente",
    parametro="Temperatura refrigerante > 95 °C",
    alarma="Código de derate por temperatura",
    como_detectarlo="Inspección visual del panal a contraluz")
```

**Debe:** Q4 contestada.

**Importa porque:** el efecto es lo que permite que el técnico reconozca el
modo de falla en campo. Un modo sin efecto es una etiqueta de taxonomía.

---

## RCM-006 · Clasificar consecuencia

```python
m.evidente = True
m.consecuencias = (Consecuencia("produccion", "Se detiene el frente hasta enfriar"),)
```

**Debe:** Q5 contestada; `completitud(a).rompe_cadena is False`.

**Negativo:** `Consecuencia("oculta")` levanta `ErrorRCM` indicando que eso va
en `evidente=False`.

**Importa porque:** evidente u oculta es la **primera bifurcación** del
análisis, no una categoría más. Aceptarla como clase rompería la lógica de
decisión en silencio: una falla oculta no se trata con predictivo ni con
preventivo, sino con búsqueda de fallas, porque el riesgo es la falla
múltiple.

---

## RCM-007 · Seleccionar estrategia

```python
d = Decisiones()
dic = d.registrar(m, Respuestas(detectable=True, viable=True))
```

**Debe:** `dic.estrategia == "cbm"`, `dic.motivo` no vacío,
`len(dic.camino) >= 3`.

**Caso crítico (la guarda):**

```python
freno = a.agregar_modo(ff.id, "Manguera de freno fisurada",
                       consecuencias=(Consecuencia("seguridad"),))
g = d.registrar(freno, Respuestas(detectable=False, intervalo_edad=False,
                                  costo_efectiva=False))
```

**Debe:** `g.estrategia == "rediseno"` y `g.bloqueado_por_seguridad is True`.
**Nunca** `"operar_hasta_falla"`.

**Importa porque:** un árbol que permita cerrar un modo de falla de seguridad
con «operar hasta la falla» firma la omisión. Está comprobado por fuerza
bruta sobre las 729 combinaciones posibles de respuestas.

---

## RCM-008 · Evaluar criticidad con el método de la empresa

```python
m.evaluar_criticidad(PRIORIDAD_EJEMPLO,
                     {"severidad": 4, "frecuencia": 4, "deteccion": 2})
```

**Debe:** `m.criticidad.etiqueta == "alta"`; el método y la versión viajan en
el resultado.

**Negativo:** `evaluar(None, {...})` devuelve `"no evaluada"`, no un número.

**Contraste que hay que ver una vez:** con `RPN_EJEMPLO`, severidad 2 ×
frecuencia 3 × detección 5 y severidad 5 × frecuencia 3 × detección 2 dan
**el mismo 30**. Con `PRIORIDAD_EJEMPLO` el segundo sale `"alta"` y el
primero no.

**Importa porque:** el RPN multiplica escalas ordinales. AIAG-VDA lo eliminó
en 2019 por eso. Se conserva porque hay procedimientos que lo exigen, con su
advertencia pegada a cada resultado.

---

## RCM-009 · Completar el análisis

```python
c = completitud(a, d.por_modo)
```

**Debe:** `c.completo is True` sólo con las siete contestadas. Con seis,
`False` — no «casi completo», no un porcentaje.

**Importa porque:** el criterio de JA1011 es binario a propósito. La norma
nació porque a finales de los noventa se vendían metodologías incompletas
bajo el nombre RCM.

---

## RCM-010 · Generar la tarea desde la decisión

```python
from nefer.fixmate.plan import generar, falta_por_completar
plan = generar(a, d)
t = plan.tareas[0]
```

**Debe:** `t.disparador == "condicion"` y `falta_por_completar(t)` listar el
parámetro, el límite con su fuente y el procedimiento.

**Importa porque:** de «hay una edad a la que la probabilidad sube» no sale
un número. Ponerle 500 h porque suena razonable inventa el dato que
justificaba toda la tarea.

**Negativo:** un dictamen de `operar_hasta_falla` **no** genera tarea; el
modo aparece en `plan.sin_tarea`. Un plan que esconde lo que decidió no
hacer no se puede auditar.

---

## RCM-011 · Exportar la matriz FMEA/FMECA

```
nefer fixmate rcm matriz ejemplos/rcm-tpm/analisis-ex220.json -o fmeca.csv
```

**Debe:** una fila por modo, 30 columnas, `;` como separador, y la columna
`evidente` con el texto `no (oculta)` donde corresponda.

---

## RCM-012 · Contrastar el análisis contra el historial

```python
from nefer.fixmate import fmeca
c = fmeca.contrastar(a, indice)
```

**Debe:** `c.frecuencias` con lo contado, `c.nunca_ocurrieron` con los modos
que no aparecieron, `c.sin_cubrir` con las causas del historial que ningún
modo cubre, y `c.sin_codificar` con los informes que el catálogo no alcanzó.

**Importa porque:** dos escrituras distintas de la misma causa —«radiador
obstruido por tierra» y «radiador tapado con tierra»— cuentan como **una**,
porque el cruce va por código del catálogo. Por texto libre se juntarían a
veces sí y a veces no.

**Lo que NO hace:** sin `aplicar=True` no toca el análisis. Medir y
modificar son dos permisos distintos.

---

## TPM-001 · Crear la pauta de mantenimiento autónomo

```
nefer fixmate tpm checklist ejemplos/rcm-tpm/pauta-ex220.json
```

**Debe:** listar los puntos con su clase, criterio y alcance, y el
presupuesto en segundos. Los puntos fuera del alcance del operador salen
marcados `[TECNICO]`.

**Negativo:** `clase: "detectar anomalias"` se rechaza. No es una clase de
punto: es lo que pasa cuando un punto sale NOK, y no tiene criterio de
aceptación posible.

**Negativo:** un punto sin criterio se rechaza. Sin criterio, cada operador
juzga otra cosa y la pauta no mide nada.

---

## TPM-002 · Ejecutar la pauta

```
nefer fixmate tpm ejecutar ejemplos/rcm-tpm/ronda-ex220-hallazgo.json \
  -p ejemplos/rcm-tpm/pauta-ex220.json
```

**Debe:** decir `Ronda COMPLETA` o `Ronda INCOMPLETA`, con el conteo y los
segundos contra el presupuesto.

**Caso que hay que ver una vez:** una ronda con un punto en `sin_acceso`
sale **INCOMPLETA** aunque los demás estén. La alternativa real a «no pude
ver» es un OK falso, y un OK falso contamina la ronda entera.

**Segundo caso:** una ronda entera despachada a un segundo por punto se
marca sospechosa de firma. El criterio (0,4 del presupuesto) es
**configurable de planta, no normativo**, y la app lo dice.

---

## TPM-003 · Registrar anomalía

Un punto `nok` genera la anomalía sola, con la severidad derivada del
alcance declarado en la pauta: dentro del alcance → `programable`; fuera →
`detiene`.

**Importa porque:** el alcance se decidió en frío al escribir la pauta, por
quien conoce el bloqueo y el repuesto. Preguntárselo al operador en campo,
con la máquina parada, garantiza la respuesta cómoda.

**Negativo:** un `sin_acceso` **no** genera anomalía. No se encontró un
defecto: se encontró que no se pudo mirar.

---

## TPM-004 · Vincular la anomalía con el modo de falla RCM

```
nefer fixmate tpm ejecutar ejemplos/rcm-tpm/ronda-ex220-hallazgo.json \
  -p ejemplos/rcm-tpm/pauta-ex220.json --rcm ejemplos/rcm-tpm/analisis-ex220.json
```

**Debe:** imprimir `modo F1.1.1` cuando el enganche se logró.

**Los cuatro casos en que NO se engancha, y se ve:**

| Caso | Resultado |
|---|---|
| El catálogo no codifica el texto | `sin enlazar a RCM` |
| Hay código pero ningún modo lo declara | `codigo X, sin modo que lo declare` |
| El análisis es de otro activo | sin enlazar |
| Dos modos declaran el mismo código | sin enlazar: la ambigüedad se resuelve en el análisis |

**Importa porque:** una anomalía enlazada al modo equivocado contamina el
MTBF por modo y la decisión de estrategia que sale de ahí. Un enlace que
falta se ve; uno equivocado se suma con los demás.

---

## TPM-005 · Generar la acción

La anomalía llega al cierre por el mismo camino que cualquier caso, y el
informe guarda `anomalia_id` y `modo_falla_id`. `anomalia.cerrar()` exige
decir qué se hizo: una anomalía cerrada en blanco es una anomalía borrada.

---

## INT-001 · El recorrido completo

```
ronda → anomalía → diagnóstico → modo RCM → estrategia → tarea
      → cierre → historial → aprendizaje → contraste → tablero
```

Fijado en `tests/test_fixmate_integracion_rcm_tpm.py`. Nueve pasos
verificados, y cuatro pruebas más que comprueban lo contrario: que la cadena
**se niega a cerrarse** donde no hay evidencia.

**El paso que más conviene mirar:** con cuatro casos en el historial, el
clasificador bayesiano **no se entrena** —hacen falta doce— y declara por
qué en vez de inventar un porcentaje. El aprendizaje real que sí ocurrió es
otro: el cierre ya se recupera como evidencia para el próximo que pregunte.

---

## Pendiente

| Caso | Contenido | Por qué |
|---|---|---|
| UI-001 | Registrar la ronda desde el teléfono | No hay frontend para TPM |
| API-001 | Crear un análisis por HTTP | Exige autenticación y control de versiones, que FixMate no tiene |
