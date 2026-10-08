---
name: espejo
description: >-
  Mantiene al día lo que este repositorio GENERA —las pantallas de
  docs/fixmate, la piel compartida, el catálogo embebido— y comprueba que los
  espejos Python ↔ JavaScript sigan diciendo lo mismo. Invócala sin que te la
  pidan siempre que hayas tocado herramientas/piel/**, herramientas/rcm/**,
  herramientas/ronda/**, nefer/fixmate/*.py o ejemplos/rcm-tpm/*.json; antes
  de proponer un commit que incluya cualquiera de esas rutas; y cuando una
  prueba falle con «no esta al dia», «sale del generador» o «no puede
  envejecer». Un artefacto generado que se quedó atrás no da error donde se
  edita. Lo da tres pasos después, o no lo da nunca y viaja al teléfono de un
  operador.
allowed-tools: Bash, Glob, Grep, Read
---

# Espejo · lo generado, al día y cruzado

## Por qué existe

En este repositorio hay archivos que **nadie escribe a mano**: las dos
pantallas de `docs/fixmate/`, su manifiesto y su trabajador de servicio, la
piel compartida y el catálogo embebido en la app. Salen de un generador. Y
hay algoritmos escritos **dos veces** —en Python y en el JavaScript de las
pantallas— que tienen que decidir igual.

Las dos cosas fallan del mismo modo: **en silencio**. Editas
`herramientas/rcm/rcm-ui.js` y la pantalla publicada sigue siendo la de
antes. Cambias una constante en `decision.py` y el teléfono sigue con la
vieja. Nadie se entera hasta que dos personas comparan dos pantallas que
tendrían que decir lo mismo, o hasta que CI se pone rojo tres pasos después
del cambio que lo causó.

Esta skill cierra ese hueco con un orden fijo: mirar sin tocar, regenerar
sólo lo atrasado, y cruzar.

## Fase 1 · Reconocimiento (sin leer archivos grandes)

Descubre los generadores y sus guardas. **No abras ningún archivo generado**:
pesan entre 30 y 340 KB y no hace falta leerlos para saber si están al día.

```bash
ls herramientas/espejo-*.py herramientas/piel.py 2>/dev/null
git status --short -- docs/ herramientas/ nefer/fixmate/ ejemplos/
```

Luego, qué cambió respecto a la rama base, que es lo que decide qué hay que
regenerar:

```bash
git diff --name-only origin/main...HEAD -- herramientas/ nefer/fixmate/ ejemplos/
```

| Si tocaste… | Hay que regenerar |
|---|---|
| `herramientas/piel/**`, `docs/fixmate/app/index.html` (bloque de piel) | `piel.py`, `espejo-ronda.py`, `espejo-rcm.py` |
| `herramientas/rcm/**`, `ejemplos/rcm-tpm/analisis-ex220.json` | `espejo-rcm.py` |
| `herramientas/ronda/**`, `ejemplos/rcm-tpm/pauta-ex220.json` | `espejo-ronda.py` |
| `nefer/fixmate/{decision,rcm,criticidad}.py` | `espejo-rcm.py` |
| `nefer/fixmate/{tpm,anomalia}.py` | `espejo-ronda.py` |
| `nefer/fixmate/catalogo.py` | `espejo-catalogo.py` |

Ante la duda, la fase 2 lo dice sin adivinar.

## Fase 2 · Análisis (modo lectura, cero escrituras)

Cada generador contesta `--revisar` sin escribir nada. Es la forma barata de
saber qué está atrasado:

```bash
for g in herramientas/espejo-catalogo.py herramientas/espejo-rcm.py \
         herramientas/espejo-ronda.py herramientas/piel.py; do
  python3 "$g" --revisar 2>&1 | sed "s|^|$(basename $g): |"
done
```

Con eso arma el plan y **enséñalo antes de ejecutarlo** si hay más de dos
artefactos atrasados o si alguno está fuera de `docs/`.

Si todo está al día y no hay cambios en las rutas fuente: **detente aquí** y
dilo. Regenerar por costumbre ensucia el diff y esconde el cambio real.

## Fase 3 · Ejecución (sólo lo atrasado, en este orden)

El orden importa: la piel sale de la app de diagnóstico y la copian las dos
pantallas, así que va primero o las pantallas se regeneran con la piel vieja.

```bash
python3 herramientas/piel.py            # 1. la piel → página de entrada
python3 herramientas/espejo-catalogo.py # 2. el catálogo → app
python3 herramientas/espejo-ronda.py    # 3. la ronda
python3 herramientas/espejo-rcm.py      # 4. el análisis RCM
```

Ejecuta **sólo** los que la fase 2 marcó atrasados. Si tocaste el bloque de
piel de la app, corre los cuatro.

Y si algo cambió en `docs/fixmate/app/`, el archivo suelto hay que rehacerlo:

```bash
python3 herramientas/empaquetar-fixmate.py
```

## Fase 4 · Verificación

Las pruebas que importan son las que cruzan los dos lenguajes. Corren en
segundos:

```bash
python3 -m pytest -q \
  tests/test_fixmate_cruce.py tests/test_fixmate_cruce_rcm.py \
  tests/test_fixmate_cruce_ronda.py tests/test_fixmate_piel.py \
  tests/test_fixmate_espejo.py tests/test_fixmate_instalable.py \
  tests/test_publicacion_fixmate.py
```

Si tocaste la ronda o la pantalla RCM, añade las de navegador:

```bash
python3 -m pytest -q tests/test_fixmate_ronda_navegador.py \
  tests/test_fixmate_rcm_navegador.py tests/test_android_fixmate.py
```

Cierra enseñando qué cambió, sin volcar los archivos:

```bash
git diff --stat -- docs/
```

## Guardrails

**Nunca edites un archivo generado.** Si vas a cambiar algo de
`docs/fixmate/{ronda,rcm}/index.html`, `manifest.webmanifest`, `sw.js`, de
`docs/fixmate-app.html` o del bloque de piel de `docs/fixmate/index.html`, el
cambio va en `herramientas/` y se regenera. Editarlos a mano se pierde en la
siguiente corrida y mientras tanto la prueba del generador se pone roja.

**Rutas autorizadas para escribir:** `docs/fixmate/**` y `docs/fixmate-app.html`,
**y sólo a través de los generadores**. Cualquier otra ruta es fuera de alcance:
dilo y para.

**No leas archivos generados.** `--revisar` contesta la pregunta; `grep -c` y
`git diff --stat` dan el resto. Abrir un `index.html` de 86 KB gasta el
contexto sin decir nada que los generadores no digan mejor.

**Un cruce rojo DESPUÉS de regenerar no se arregla tocando la prueba.**
Significa que Python y el JavaScript decidieron distinto, y eso es el
hallazgo, no el obstáculo: el algoritmo está escrito a mano en los dos
lenguajes y uno de los dos se quedó atrás. Localiza la divergencia con el
caso que la prueba reporta y corrige el **lenguaje equivocado**. Si no sabes
cuál es el equivocado, para y pregunta: elegir mal aquí deja el teléfono y la
oficina diciendo cosas distintas sobre la misma máquina.

**Rollback.** Si tras regenerar algo falla y no es una divergencia real
—porque el fallo ya estaba antes—, devuelve lo generado y dilo:

```bash
git checkout -- docs/
```

Comprueba antes si el fallo preexistía, en vez de suponerlo:

```bash
git stash && python3 -m pytest -q <la prueba que falló>; git stash pop
```

**No toques `.github/workflows/`, `nefer/` ni `tests/`** desde esta skill. Si
el arreglo está ahí, dilo y sal: esta skill mantiene lo generado, no cambia
lo que lo genera.

## Formato de la respuesta

Siempre esta estructura, en este orden y sin más:

```
ESPEJO · <n> artefacto(s) regenerado(s)

Qué cambió en origen
  herramientas/rcm/rcm-ui.js · ejemplos/rcm-tpm/analisis-ex220.json

Artefactos
  ✓ al día     docs/fixmate/index.html          (piel)
  ✓ al día     docs/fixmate/ronda/              (ronda)
  ↻ regenerado docs/fixmate/rcm/                (rcm) · 86.1 KB

Diff
  docs/fixmate/rcm/index.html | 48 ++++++++++----
  docs/fixmate/rcm/sw.js      |  2 +-

Cruces
  ✓ 27 pasan  cruce_rcm      Python ↔ JS del árbol de decisión
  ✓ 12 pasan  cruce_ronda
  ✓ 15 pasan  piel
```

Si algo quedó rojo, en lugar de «Cruces» va:

```
DIVERGENCIA · <prueba> · <caso concreto que falló>
  Python dice: <...>
  JS dice:     <...>
  Lenguaje atrasado: <cuál, y por qué lo crees>
```

Nada de resúmenes de lo que hiciste paso a paso. El desarrollador quiere
saber qué quedó distinto y si los dos lados siguen de acuerdo.
