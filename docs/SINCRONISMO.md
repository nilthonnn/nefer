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
