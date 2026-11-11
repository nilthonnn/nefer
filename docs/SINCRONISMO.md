# Sincronismo — grupos electrógenos en paralelo

Módulo `nefer/sincronismo/`, comando `nefer sincronismo`. Convierte lo que
un técnico de sincronismo hace todos los días en cálculo repetible y en
avisos que llegan **antes** del disparo.

Tres ejes, que son los que pide el puesto:

| Eje | Qué significa aquí | Comando |
|---|---|---|
| **Eficaz** | Decidir bien en el sitio: si se puede cerrar, por qué no, cuánto falta, y qué revisar primero | `verificar`, `reparto`, `diagnostico` |
| **Proactivo** | Encontrar lo que va a fallar sin que nadie pregunte: protecciones que faltan, ajustes que harán repartir mal a plena carga | `informe`, `protecciones`, `estatismo` |
| **Predictivo** | Ver la deriva en el registro y decir en qué **fecha** cruza el límite | `tendencia`, `informe -r` |

## Cómo se usa en un día de trabajo

```bash
# 1. Antes de salir: el informe de la planta, ordenado por urgencia
python -m nefer sincronismo informe planta.json -r registro.csv -o informe.md

# 2. En el tablero: ¿se puede cerrar?
python -m nefer sincronismo verificar --v-barra 480 --f-barra 60 \
    --v-gen 485 --f-gen 60.15 --angulo -4 --t-cierre 0.12 --kva 625

# 3. Antes de tocar consignas: ¿cómo repartirá al 75 %?
python -m nefer sincronismo estatismo planta.json --pct 75

# 4. Frente a una falla
python -m nefer sincronismo diagnostico "dispara por potencia inversa al cerrar"

# 5. Puesta en marcha: el protocolo con una columna por unidad
python -m nefer sincronismo protocolo planta.json -o protocolo.md
```

Con los datos de ejemplo (ficticios) de `ejemplos/sincronismo/` todo corre
sin preparar nada.

## Arquitectura

```
planta.json ─┬─► reparto.analizar_reparto ───┐
             ├─► reparto.predecir_estatismo ─┤
             └─► protecciones.revisar ───────┼─► informe.analizar ─► Markdown / JSON
registro.csv ─┬► tendencias.proyectar ───────┤     (detiene / programable / oportunidad)
              └► tendencias.reincidencias ───┘

lectura del sincronoscopio ─► verificacion.verificar ─► permitido / bloqueos / espera
descripción del síntoma ────► diagnostico.buscar ─────► causas en orden de descarte
                              diagnostico.exportar_markdown ─► manual indexable por FixMate
```

Solo biblioteca estándar: corre igual en la laptop de campo sin red.

| Archivo | Responsabilidad |
|---|---|
| `verificacion.py` | Permisivo de cierre ANSI 25. Juzga el ángulo **en el contacto** (orden + 360·deslizamiento·t_cierre), no en la orden. Ventanas por defecto de IEEE 1547-2018 tabla 5 según kVA, o las del fabricante. Secuencia de fases, barra muerta, tiempo de espera hasta ventana |
| `reparto.py` | Reparto actual en % de placa (no en kW), motorización, corriente reactiva circulante. Predicción por estatismo de kW (f) y kVAr (V), con unidad isócrona, y la consigna en vacío que reparte parejo |
| `protecciones.py` | Que existan 25, 32, 40, 27/59, 81O/U, y que sus ajustes caigan en la referencia de taller |
| `tendencias.py` | Recta de mínimos cuadrados sobre cada variable del registro; fecha de cruce con el límite; alarmas que reinciden y las que ya están vencidas |
| `diagnostico.py` | Guía de 7 síntomas del paralelo con causas ordenadas y la medición que confirma cada una |
| `informe.py` | Todo junto y priorizado; protocolo de puesta en marcha |
| `cli.py` | `nefer sincronismo …` |

## Los datos

### `planta.json`

```json
{
  "planta": "Nombre",
  "f_nominal": 60,
  "limites": { "tiempo_sincronizacion_s": 30, "desbalance_kvar_pct": 10 },
  "cargas_a_predecir_pct": [25, 50, 75, 100],
  "unidades": [
    {
      "id": "GE-01", "kw_nominal": 500, "kva_nominal": 625,
      "kw": 300, "kvar": 160,
      "modo": "droop", "f_vacio": 62.4, "estatismo_pct": 4,
      "v_vacio": 494.4, "estatismo_v_pct": 3,
      "protecciones": { "32": { "pickup_pct": 10, "retardo_s": 3 }, "40": {}, "...": {} }
    }
  ]
}
```

Todo es opcional salvo `id` y `kw_nominal`: sin `kw` no hay reparto actual,
sin `f_vacio`/`estatismo_pct` no hay predicción, sin `protecciones` no se
revisan. Lo que falta se omite, no se inventa.

### `registro.csv`

```
fecha,equipo,variable,valor
2026-09-01,GE-01,tiempo_sincronizacion_s,12.5
2026-09-03,GE-02,alarma,32 potencia inversa
```

Se llena a mano en la ronda o se exporta del historial del controlador.
Variables con límite por defecto: `tiempo_sincronizacion_s`,
`intentos_sincronizacion`, `desbalance_kw_pct`, `desbalance_kvar_pct`,
`angulo_cierre_grados`. Cualquier otra se acepta y se proyecta si la planta
le declara límite.

## Reglas (las mismas del resto de nefer)

- **Ningún límite sale de la nada.** Las ventanas de cierre citan IEEE
  1547-2018; los límites de reparto, tendencia y protecciones se rotulan como
  criterio de taller y se cambian en la planta. El estudio de coordinación
  manda sobre la referencia de protecciones.
- **No se proyecta ruido.** Menos de 4 lecturas, o una recta con R² < 0.5, no
  dan fecha: se dice cuántas lecturas hay o que hay dispersión.
- **La guía no es antecedente.** Ordena causas posibles; la causa la confirma
  el técnico. Lo confirmado se cierra en FixMate (`nefer fixmate cerrar`) y
  así la flota lo aprende. La guía exportada
  (`ejemplos/sincronismo/guia-sintomas-paralelo.md`) se indexa con
  `nefer fixmate indexar` igual que un manual, y la búsqueda del teléfono la
  encuentra.

## Planta DSE + motor CAT a 380 V

```bash
python -m nefer sincronismo plantilla -n 3 --kw 400 --kva 500 \
    --modelo-controlador "8610 MKII" --modelo-motor C15 -o planta.json
```

Deja una planta de 380 V / 60 Hz con el controlador DSE y el motor CAT en cada
unidad. Lo que no se sabe queda en `null`, no se rellena con valores típicos.
Sin `kw_nominal` el análisis no arranca, y cada ajuste de protección vacío
aparece como «falta anotar».

El modo por defecto es `isocrono_compartido`: varias unidades en isócrono
que reparten la carga por el enlace entre controladores (en DSE, el enlace
MSC). Ahí la frecuencia queda en la nominal y la carga se reparte en
proporción a la placa de cada unidad. Si la planta trabaja en estatismo, se
usa `--modo droop` y se llenan `f_vacio` y `estatismo_pct`. El ajuste del
estatismo vive en el DSE: el motor CAT recibe la consigna de velocidad
desde el controlador (por J1939 o por señal analógica, según cómo esté
cableado).

El historial de eventos del DSE todavía no se importa solo. El formato de la
exportación cambia según el modelo y la versión de DSE Configuration Suite,
y aquí no se escribe un lector a ciegas: con una exportación real se hace el
importador que la convierta en `registro.csv`.

## Diagramas de conexión (TTA y sincronismo)

```bash
python -m nefer sincronismo diagrama sincronismo planta.json -o sincronismo.svg
python -m nefer sincronismo diagrama tta planta.json -o tta.svg
```

Salen en SVG: se abren en el navegador o el teléfono y se imprimen.

- **Sincronismo**: un grupo por columna, cada uno con su TC, su interruptor
  52G, el sensado de tensión del generador **antes** del interruptor y el
  de barra **después**, el mando y el auxiliar 52a, el J1939 al ECM CAT, la
  polarización del AVR y el enlace MSC en cadena entre módulos. Abajo, las
  cinco verificaciones de cableado antes del primer cierre.
- **TTA**: red y grupo con KM1/KM2, enclavamiento mecánico y eléctrico,
  sensado de red y de grupo, TC de carga, módulo AMF (DSE7320 MKII por
  defecto) y las reglas del circuito de mando.

Los números de borne **no se inventan**: cambian por modelo y versión del
módulo. Se declaran en la planta (`"bornes": {"sensado_gen": "…",
"sensado_barra": "…", "interruptor": "…"}` por unidad, y `"tta": {"bornes":
{"sensado_red": …, "sensado_gen": …, "tc": …, "cerrar_red": …,
"cerrar_grupo": …}}`), y si no están, el diagrama remite a la publicación
DSE que los trae: 057-254 (DSE8610 MKII) o 057-253 (DSE7320 MKII).

Ejemplos generados: `ejemplos/sincronismo/diagrama-sincronismo.svg` y
`ejemplos/sincronismo/diagrama-tta.svg`.

## Láminas didácticas por capas

```bash
python -m nefer sincronismo lamina sincronismo planta.json -o lamina-sincronismo.html
python -m nefer sincronismo lamina tta planta.json -o lamina-tta.html
```

Una página HTML de un solo archivo (abre sin red, en el teléfono) con el
esquema de una unidad cableada de verdad —fusibles de TP, bornera
seccionable del TC, relés interpuestos K1/K2, bobinas de cierre YC y de
disparo YO, auxiliar 52a, paro de emergencia, J1939, enlace MSC, bias del
AVR; en la TTA, Q1/Q2, KM1/KM2 y la escalera con el enclavamiento cruzado—
y botones para ver **una capa a la vez**: potencia, medición, mando y
comunicación. Cada capa trae qué hace, cómo se verifica con el multímetro y
el error típico de campo. La secuencia de operación va paso a paso, y cada
paso enciende la capa que actúa.

Tiempos y umbrales quedan como «configurable», y los bornes remiten al
manual del módulo: una cifra típica en una lámina se copia como si fuera
la norma.

## Parámetros de configuración (sincronismo y TTA)

```bash
python -m nefer sincronismo parametros sincronismo planta.json --html -o parametros.html
python -m nefer sincronismo parametros tta planta.json --revisar
```

La hoja lista lo que se configura en el módulo —ventanas del sincronizador,
deslizamiento, tiempo de cierre, barra muerta, modo de reparto, estatismos,
rampas y nivel de apertura, arranque por demanda, protecciones 32/40/27/59/81,
falla de MSC; en la TTA, umbrales de red, temporizadores de falla, arranque,
calentamiento, transferencia, retorno y enfriamiento, salidas, auxiliares y
ejercicio— con qué hace cada uno, cómo decidir el valor, qué pasa si queda
mal y cómo se comprueba. La columna «valor ajustado» se llena frente a DSE
Configuration Suite (los nombres DSE orientan la búsqueda; el manual es el
057-238 para el 8610 MKII).

Con los valores en `planta.json` (bloque `"parametros": {"sincronismo": {…},
"tta": {…}}`), `--revisar` comprueba las reglas que relacionan unos con
otros: rampa que abre por debajo del pickup de la 32, ventanas más anchas
que IEEE 1547, deslizamiento negativo, adelanto del interruptor que se come
la ventana, 81O por debajo de la f en vacío, retorno de red más corto que la
confirmación de falla, tiempo muerto nulo, umbrales de red que no encierran
la nominal. Lo no declarado se lista; no se supone.

## Menú de fallas: RCM, árbol de decisión y AMEF

```bash
python -m nefer sincronismo fallas ejemplos/sincronismo/rcm-paralelo-tta.json -o menu-fallas.html
python -m nefer fixmate rcm analizar ejemplos/sincronismo/rcm-paralelo-tta.json   # SAE JA1011
python -m nefer fixmate rcm matriz ejemplos/sincronismo/rcm-paralelo-tta.json -o amef.csv
```

`rcm-paralelo-tta.json` es un análisis RCM de la planta (3 grupos en paralelo
+ TTA) en el formato de FixMate: 6 funciones, 12 fallas funcionales y 19 modos
de falla tomados de fuentes públicas (batería y cargador, módulo fuera de
AUTO, combustible, refrigerante, wet stacking, diodos rotativos, polaridad
del TC de compensación, gobernador inestable, 52G que no cierra, cierre
fuera de fase, potencia inversa al cerrar, reparto inestable, 32/40
deshabilitadas, contactos soldados, mando de la TTA, sensado de red,
enclavamiento, bornes flojos). Cada modo cita su fuente; la ocurrencia es una
**propuesta** y se reemplaza con el historial propio.

El menú es una página de un solo archivo: buscar o agrupar por sistema u
ordenar por NPR, y por cada falla las siete preguntas de RCM, la AMEF
(S, O, D con el texto de cada nivel), el **NPR** y, al lado, la **prioridad
de acción** AIAG-VDA —porque el NPR multiplica escalas ordinales y, por
ejemplo, el cierre fuera de fase (severidad 5) sale con NPR medio—, el árbol
de decisión recorrido pregunta por pregunta hasta la estrategia, la tarea
propuesta, las causas a descartar de la guía de síntomas y el Pareto de
riesgo de toda la planta. Todo sale del motor RCM de FixMate: con
consecuencia de seguridad, «operar hasta la falla» no es una salida.

## AMEF completa, plan de acción y auditoría

```bash
python -m nefer sincronismo amef -o amef-completa.csv --plan plan-accion.csv
python -m nefer sincronismo auditoria --html -o auditoria.html
```

Cada modo de falla del análisis lleva sus **controles actuales** (prevención y
detección), su **plan de acción** (acción, tipo, responsable, plazo,
intervalo y cómo se verifica) y su **re-evaluación** (S', O', D' después de
las acciones). `amef` exporta la AMEF completa con las columnas de IEC 60812 /
AIAG-VDA y el plan ordenado por prioridad de acción, severidad y NPR, con
fecha objetivo. El plan se revisa con siete reglas: prioridad alta con
acciones (R1), responsable, plazo y verificación (R2), la severidad solo baja
con rediseño (R3), re-evaluación coherente (R4), falla oculta con prueba
periódica (R5), acción coherente con la estrategia RCM (R6) y severidad
crítica que no queda en prioridad alta sin escalar (R7). En el ejemplo, el
NPR total baja de 600 a 236 y las prioridades altas de 12 a 2.

`auditoria` ejecuta cada función del módulo con los datos de ejemplo
(ISO/IEC 25010, completitud), compara cálculos con respuestas conocidas
(corrección) y revisa el análisis contra SAE JA1011, IEC 60812:2018,
AIAG-VDA 2019, ISO 14224, IEEE 1547-2018, IEEE C37.2 y NFPA 110 como
referencia. El resultado vigente está en
[AUDITORIA-SINCRONISMO.md](AUDITORIA-SINCRONISMO.md). Es una autoevaluación
reproducible, no una certificación.

## Lo que falta (siguiente etapa)

1. **Lectura directa del controlador.** Hoy los datos entran por JSON/CSV.
   El paso siguiente es leer por Modbus TCP/RTU los registros del controlador
   (ComAp, DSE, Woodward, etc.: el mapa de registros cambia por marca y se
   declara por archivo) y alimentar `registro.csv` solo.
2. **Pantalla en la app de campo.** El permisivo y el estatismo son cálculo
   puro, fáciles de espejar a JavaScript como FixMate, con la misma prueba de
   cruce Python ↔ JS.
3. **Enlace con RCM/TPM.** Cada hallazgo `detiene` del informe puede abrir
   una anomalía TPM (`nefer/fixmate/anomalia.py`) para que el ciclo
   anomalía → diagnóstico → cierre → aprendizaje lo recorra igual que el resto.
