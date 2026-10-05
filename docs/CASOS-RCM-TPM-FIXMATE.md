# Casos de prueba RCM + TPM

Casos funcionales ejecutables a mano contra la biblioteca. Cada uno dice qué
se hace, qué debe salir y **por qué importa** — un caso sin esa tercera línea
se convierte en un paso que nadie entiende y que se marca OK sin mirar.

Los casos marcados **pendiente** corresponden a fases no implementadas. No se
pueden ejecutar todavía y no se marcan como fallidos: no existen.

Estado al día de hoy: **RCM-001 a RCM-009 ejecutables**. TPM-001 a TPM-005 e
INT-001, pendientes.

---

## Preparación

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

## Pendientes

Estos casos corresponden a fases no implementadas. Se listan para que el
alcance quede a la vista, no como pruebas que fallan.

| Caso | Contenido | Fase |
|---|---|---|
| TPM-001 | Crear checklist de mantenimiento autónomo por equipo | 8 |
| TPM-002 | Ejecutar checklist y registrar resultado | 8 |
| TPM-003 | Registrar anomalía | 8 |
| TPM-004 | Vincular anomalía con `failure_mode_id` de RCM | 8 |
| TPM-005 | Generar acción desde la anomalía | 8 |
| RCM-010 | Generar tarea de mantenimiento desde la decisión | 9 |
| RCM-011 | Exportar la matriz FMEA/FMECA | 13 |
| INT-001 | TPM → FixMate → RCM → tarea → cierre → aprendizaje | 10–11 |
