# Manual de la ronda CIL

Para dos personas distintas:

- **El operador**, que hace la ronda al arranque del turno. Le bastan las
  secciones 1 a 4.
- **Quien escribe la pauta** —mantenimiento, confiabilidad—, que decide qué
  se mira y quién lo mira. Secciones 5 a 7.

---

## 1. Qué es esto, en una frase

Una ronda de **medio minuto** por la máquina antes de empezar el turno:
limpiar, inspeccionar, lubricar. Lo que encuentre sale en un archivo que se
manda a la oficina.

**Limpiar *es* inspeccionar.** La fuga, la grieta y el perno flojo se ven
cuando se quita la mugre, no antes. Por eso limpiar es el primer punto de
casi todas las pautas y no una tarea aparte.

## 2. Abrirla

Tres formas, todas sin red una vez abierta:

| Cómo | Para qué |
|---|---|
| `https://nilthonnn.github.io/nefer/fixmate/ronda/` | La más simple. Abra el enlace y agregue a la pantalla de inicio |
| El archivo `ronda-cil.html` | Si le llegó por WhatsApp o correo. Tóquelo y abre |
| `docs/fixmate/ronda/index.html` del repositorio | Desde la computadora |

**Agregarla al teléfono.** En Android: menú del navegador → «Agregar a
pantalla de inicio». En iPhone: compartir → «Añadir a pantalla de inicio».
Queda como una app y arranca sin señal.

## 2b. Instalarla en el celular Android

Es lo que conviene hacer una vez, en el taller, con señal. Después la ronda
abre **sin cobertura**, que es la condición real: interior mina, y el turno
no espera a que haya línea.

1. Abra <https://nilthonnn.github.io/nefer/fixmate/ronda/> en **Chrome**.
   También puede escanear el QR de `docs/fixmate/ronda/qr.svg`, que está
   hecho para imprimirlo y pegarlo en la sala de máquinas.
2. Toque **INSTALAR** en la barra de arriba. Si no aparece, el menú de tres
   puntos de Chrome trae «Instalar aplicación» o «Agregar a pantalla de
   inicio»; es lo mismo.
3. Queda un icono propio —tres paradas unidas por un recorrido— junto a los
   demás. Desde ahí abre a pantalla completa, sin la barra del navegador
   comiéndose la mitad.

Esa primera vez el teléfono se guarda la pantalla entera. A partir de ahí no
vuelve a necesitar red: ni para abrir, ni para hacer la ronda, ni para
guardar el archivo al terminar. Cuando haya señal y la pantalla cambie, se
trae la versión nueva sola.

**Si no quiere instalar nada**, la pantalla funciona igual dentro del
navegador, y el archivo `.html` suelto —el que viaja por WhatsApp— también:
ahí no hay copia automática, pero el archivo ya lo trae todo dentro.

### Si la mina no deja instalar desde el navegador

Hay un `.apk`, y hace exactamente lo mismo: la misma pantalla envuelta en una
aplicación. Existe para cuando la política del cliente no permite instalar
desde Chrome, o cuando los teléfonos se entregan configurados y la ronda
tiene que venir dentro.

Está en las publicaciones del repositorio, buscando `fixmate-ronda`:
<https://github.com/nilthonnn/nefer/releases?q=fixmate-ronda&expanded=true>

1. Descargue **`fixmate-ronda.apk`** desde el teléfono.
2. Ábralo desde Archivos o Descargas.
3. Android pedirá permitir instalar desde esa fuente: acepte.

No pide permiso de INTERNET —no puede salir a la red aunque quisiera— y el
archivo de la ronda se guarda en **Descargas** al tocar «Guardar». Cómo está
hecho, y por qué de esa manera, está en
[`movil/fixmate-ronda/LEEME.md`](../movil/fixmate-ronda/LEEME.md).

## 3. Hacer la ronda

**Primero, la pauta.** Toque **Abrir pauta del equipo** y elija el archivo
`.json` que le pasó mantenimiento. Si sólo quiere ver cómo funciona, hay un
botón de ejemplo — dice que es un taller inventado, porque lo es: la
excavadora EX-220 no existe y no sirve para registrar nada real.

**Después, su nombre.** Una ronda sin responsable no se puede discutir
después.

**Y la máquina.** Un punto a la vez, a pantalla completa. En cada uno:

- arriba, en qué punto va y cuánto lleva;
- el **sitio** donde pararse, en grande;
- el **criterio**: qué cuenta como que está bien;
- tres botones del mismo tamaño.

### Los tres botones

| Botón | Cuándo |
|---|---|
| **OK** | Cumple el criterio. Siguiente |
| **ANOMALÍA** | Algo no está como debe. Le pide que escriba qué vio |
| **NO PUDE VER** | No pudo mirarlo: guarda cerrada, máquina en marcha, falta andamio |

**«No pude ver» no es una falta suya, y por eso está ahí.** Si no estuviera,
la única salida sería marcar OK en algo que no vio — y un OK falso vale menos
que nada, porque alguien lo va a creer. Un punto que nunca se puede ver no es
un descuido del operador: es un defecto de la máquina o de la pauta, y así se
detecta.

Por eso una ronda con un punto sin ver sale **incompleta**, aunque haya
contestado los cinco.

### Lo que escribe en una anomalía

En sus palabras. No se corrige ni se encasilla: «suena a metal cada vuelta»
es mejor dato que elegir una opción de una lista. La oficina lo clasifica
después, con el análisis delante.

Si no escribe nada, queda el nombre del punto. Pero escriba: es lo que el
técnico va a leer.

## 4. Al terminar

Sale el resumen:

- **Ronda completa** o **incompleta**, con el conteo;
- un aviso si fue **demasiado rápida** (ver abajo);
- las anomalías, con su marca: las que puede resolver usted y las que
  requieren al técnico;
- el botón **Guardar el archivo de la ronda**.

**Mande el archivo.** Es un `.json` que se adjunta por WhatsApp o correo. La
ronda no sale del teléfono hasta que usted lo haga: no hay servidor detrás.

### El aviso de «demasiado rápida»

Si la pauta dice que cuesta 31 segundos y la ronda se despachó en 5, aparece
un aviso. **No es una acusación y no se lo dice a usted a mitad de la
máquina**: sale al final, para que el supervisor lo mire antes de darla por
buena.

El umbral —40 % del presupuesto— es un **criterio de la planta, no una
norma**. Se cambia en `nefer/fixmate/tpm.py`, en `FRACCION_SOSPECHOSA`.

---

## 5. Escribir una pauta

Un archivo `.json`. El mínimo:

```json
{
  "id": "cil-ex220",
  "activo_codigo": "EX-220",
  "nombre": "Ronda de arranque de turno",
  "frecuencia": "por_turno",
  "puntos": [
    {
      "clase": "limpiar",
      "punto": "Panal del radiador, lado admision",
      "criterio": "Se ve la luz a traves del panal; sin costra de tierra",
      "segundos": 8,
      "alcance_operador": true,
      "codigo_catalogo": "TER.SOBRECALENTAMIENTO.RADIADOR",
      "modo_falla_id": "F1.1.1"
    }
  ]
}
```

Hay un ejemplo completo en
[`ejemplos/rcm-tpm/pauta-ex220.json`](../ejemplos/rcm-tpm/pauta-ex220.json).

### Las cinco clases

`limpiar` · `inspeccionar` · `lubricar` · `ajustar` · `verificar`

No hay una clase «detectar anomalías»: eso es lo que **pasa** cuando un punto
sale NOK, no una clase de punto. Un punto cuya actividad fuera «detectar
anomalías» no tendría criterio de aceptación posible, y en campo se marcaría
OK siempre.

### Las cuatro reglas de una pauta que sirve

**1. Cada punto es un sitio físico, no un sistema.** «Revisar lubricación» no
es un punto; «visor de nivel del reductor» sí, porque el operador sabe dónde
pararse.

**2. El criterio se decide sin instrumento.** Si para contestar hace falta un
medidor, ese punto pertenece a la ruta del técnico, no a la ronda. Mezclarlos
hace que la ronda deje de cumplirse. La app **rechaza** un punto sin criterio.

**3. El orden es el recorrido.** Se camina una vez alrededor de la máquina,
no tres.

**4. El presupuesto en segundos cabe en medio minuto.** Es lo que hace que la
ronda se haga todos los días, que es la única forma en que sirve de algo. Una
pauta de tres minutos perfecta que se ejecuta los martes vale menos que una
de treinta segundos que se ejecuta siempre.

### `alcance_operador`: quién arregla qué

Se decide **aquí, en frío**, por quien conoce el bloqueo, la herramienta y el
repuesto. No se le pregunta al operador en campo con la máquina parada y el
supervisor mirando: ahí la respuesta cómoda está garantizada.

- `true` → la anomalía sale como **programable**: la resuelve el operador.
- `false` → sale como **detiene**: va el técnico.

### `codigo_catalogo` y `modo_falla_id`: el puente con RCM

Opcionales. Cuando están, la anomalía llega a la oficina ya enganchada al
modo de falla del análisis RCM, sin que nadie escriba el enlace.

Los códigos salen de `nefer/fixmate/catalogo.py`. Para verlos:

```bash
python3 -c "from nefer.fixmate.catalogo import DE_FABRICA; \
  [print(e.codigo, '·', e.causa) for e in DE_FABRICA]"
```

## 6. Qué hace la oficina con el archivo

```bash
nefer fixmate tpm ejecutar ronda-recibida.json \
  -p pauta-ex220.json \
  --rcm analisis-ex220.json
```

Ahí es donde pasan las dos cosas que el teléfono **no** hace:

1. **Codificar el texto libre** contra el catálogo ISO 14224.
2. **Enganchar** la anomalía con el modo de falla del análisis RCM.

Las dos necesitan datos que viven en la oficina. El teléfono hereda el código
sólo cuando la pauta ya lo declara.

Y sin tocar la terminal: el mismo archivo se puede abrir en la
[pantalla de análisis RCM](MANUAL-ANALISIS-RCM.md), en **Evidencia de campo**,
y se ve en qué modo de falla cayó cada hallazgo —y cuáles no engancharon, con
el motivo—. Ahí el enganche es el que no necesita catálogo: código exacto y
mismo activo. Codificar el texto libre sigue siendo del comando.

## 7. Lo que esta app NO hace

- **No clasifica contra el catálogo.** Ver arriba. El catálogo son 41
  entradas con sus pistas y su ponderación, y meterlo aquí sería una tercera
  copia que mantener.
- **No manda nada sola.** No hay servidor detrás. Usted exporta el archivo y
  lo manda; si no lo hace, la ronda se queda en el teléfono.
- **No saca fotos.** Está previsto en el modelo de datos, no construido.
- **No lleva historial de rondas anteriores.** Cada ronda es un archivo. El
  cumplimiento y la reincidencia los calcula la oficina sobre los archivos
  recibidos.
- **No valida que la pauta sea buena.** Rechaza un punto sin criterio y una
  clase inventada; no puede juzgar si el criterio está bien escrito.

---

## Por qué el teléfono y la oficina no se contradicen

La ronda se decide dos veces: en el JavaScript de esta app, que corre sin
red, y en `nefer/fixmate/tpm.py`, que corre cuando llega el archivo.

Dos copias que se separan **no dan error en ninguna parte**: el teléfono dice
que la ronda está completa, la oficina dice que no, las dos pantallas se ven
razonables, y nadie se entera.

Por eso:

- las constantes se **generan** desde Python con
  `herramientas/espejo-ronda.py`;
- el algoritmo está escrito a mano en los dos, pero
  `tests/test_fixmate_cruce_ronda.py` **corre este mismo JavaScript** y
  compara sus respuestas con las de Python, caso por caso;
- una prueba falla si la app publicada no es la que sale del generador.

La única diferencia deliberada —que el teléfono no codifica contra el
catálogo— está documentada y tiene su propia prueba. Si el teléfono empezara
a codificar, o la oficina dejara de hacerlo, se pone roja.
