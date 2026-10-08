---
name: espejo
description: >-
  Mantiene al día lo que este repositorio GENERA —las pantallas de
  docs/fixmate, su manifiesto y trabajador de servicio, la piel compartida,
  el catálogo embebido en la app— y comprueba que los espejos Python ↔
  JavaScript sigan decidiendo igual. Invócala sin que te la pidan siempre
  que hayas tocado herramientas/piel/**, herramientas/rcm/**,
  herramientas/ronda/**, nefer/fixmate/*.py o ejemplos/rcm-tpm/*.json; antes
  de proponer un commit que incluya cualquiera de esas rutas; y cuando una
  prueba falle con «no esta al dia», «sale del generador» o «no puede
  envejecer». Un artefacto generado que se quedó atrás no da error donde se
  edita. Lo da tres pasos después, o no lo da nunca y viaja al teléfono de
  un operador.
allowed-tools: Bash, Glob, Grep, Read
---

# Espejo · lo generado, al día y cruzado

## Qué protege esto

En este repositorio hay archivos que **nadie escribe a mano**: las dos
pantallas de `docs/fixmate/`, su manifiesto y su trabajador de servicio, la
piel compartida y el catálogo embebido en la app. Salen de un generador.

Y hay algoritmos escritos **dos veces** —el árbol de decisión de RCM, las
reglas de la ronda— en Python y en el JavaScript de las pantallas, porque
una corre en la oficina y la otra en un teléfono sin red. Tienen que decidir
igual.

Las dos cosas fallan del mismo modo: **en silencio**. Editas una fuente y la
pantalla publicada sigue siendo la de antes. Cambias una constante y el
teléfono se queda con la vieja. Nadie se entera hasta que dos personas
comparan dos pantallas que tendrían que decir lo mismo, o hasta que CI se
pone rojo tres pasos después del cambio que lo causó.

## Fase 1 · Qué está atrasado

Un solo comando. Descubre los generadores **mirando el disco**, no una lista
escrita aquí —una lista se queda atrás el día que alguien agrega uno, que es
el pecado que esta skill persigue—, y no escribe nada:

```bash
python3 .claude/skills/espejo/scripts/espejo.py
```

Sale `0` si todo está al día, `1` si hay algo atrasado, `2` si un generador
no se puede comprobar. Avisa aparte de dos cosas que conviene mirar: un
generador nuevo sin orden declarado, y uno sin `--revisar` —lo que genera
ése no lo vigila nadie—.

Si todo está al día y no tocaste rutas fuente, **detente y dilo**. Regenerar
por costumbre ensucia el diff y esconde el cambio real.

## Fase 2 · Ponerlo al día

```bash
python3 .claude/skills/espejo/scripts/espejo.py --regenerar
```

Corre **sólo los atrasados** y en orden de dependencia: la piel sale de la
app de diagnóstico y la copian las dos pantallas, así que va primero o se
regeneran con la piel vieja y hay que hacerlo todo dos veces.

Si cambió algo dentro de `docs/fixmate/app/`, el archivo suelto que viaja
por WhatsApp hay que rehacerlo aparte:

```bash
python3 herramientas/empaquetar-fixmate.py
```

## Fase 3 · Cruzar los dos lenguajes

Regenerar no demuestra que Python y el JavaScript decidan igual. Eso lo
demuestran los cruces, y corren en segundos:

```bash
python3 -m pytest -q tests/test_fixmate_cruce.py tests/test_fixmate_cruce_rcm.py \
  tests/test_fixmate_cruce_ronda.py tests/test_fixmate_piel.py \
  tests/test_fixmate_espejo.py tests/test_fixmate_instalable.py \
  tests/test_publicacion_fixmate.py tests/test_skill_espejo.py
```

Si tocaste la ronda o la pantalla RCM, añade las de navegador, que tardan
más pero conducen las pantallas de verdad:

```bash
python3 -m pytest -q tests/test_fixmate_ronda_navegador.py \
  tests/test_fixmate_rcm_navegador.py tests/test_android_fixmate.py
```

Cierra enseñando qué cambió, sin volcar los archivos:

```bash
git diff --stat -- docs/
```

## Dónde hace falta criterio, y no script

El script sabe qué está atrasado y en qué orden corregirlo. Lo que no puede
decidir es esto:

**Un cruce rojo DESPUÉS de regenerar no se arregla tocando la prueba.**
Significa que Python y el JavaScript decidieron distinto sobre el mismo
caso, y eso es el hallazgo, no el obstáculo. El algoritmo está escrito a
mano en los dos lenguajes y uno se quedó atrás. La prueba te da el caso
concreto: busca la divergencia y corrige el **lenguaje equivocado**. Si no
sabes cuál es, para y pregunta — elegir mal deja el teléfono y la oficina
diciendo cosas distintas sobre la misma máquina, que es el daño que todo
este andamiaje existe para impedir.

**Un fallo que ya estaba antes no es tuyo.** Compruébalo en vez de
suponerlo, y si lo era, devuelve lo generado y dilo:

```bash
git stash && python3 -m pytest -q <la prueba que falló>; git stash pop
git checkout -- docs/     # si hay que deshacer lo regenerado
```

## Guardrails

**Nunca edites un archivo generado.** Si hay que cambiar algo de
`docs/fixmate/{ronda,rcm}/*`, de `docs/fixmate-app.html` o del bloque de
piel de `docs/fixmate/index.html`, el cambio va en `herramientas/` y se
regenera. Editarlo a mano se pierde en la siguiente corrida, y mientras
tanto la prueba del generador se pone roja sin que nadie entienda por qué.
Por eso esta skill no lleva `Write` ni `Edit` en sus permisos: la regla no
depende de acordarse.

**Escribe sólo a través de los generadores**, y sólo en `docs/fixmate/**` y
`docs/fixmate-app.html`. Si el arreglo está en `nefer/`, en `tests/` o en
`.github/`, dilo y sal: esta skill mantiene lo generado, no cambia lo que lo
genera.

**No leas archivos generados.** Pesan entre 30 y 340 KB y no dicen nada que
el script no diga mejor. `--revisar`, `grep -c` y `git diff --stat` cubren
todo lo que hay que saber.

## Formato de la respuesta

```
ESPEJO · <n> artefacto(s) regenerado(s)

Origen
  herramientas/rcm/rcm-ui.js · ejemplos/rcm-tpm/analisis-ex220.json

Artefactos
  ✓ al día     piel.py             docs/fixmate/index.html
  ↻ regenerado espejo-rcm.py       docs/fixmate/rcm/ · 86.2 KB

Diff
  docs/fixmate/rcm/index.html | 48 ++++++++++----
  docs/fixmate/rcm/sw.js      |  2 +-

Cruces
  ✓ 27 pasan  cruce_rcm      Python ↔ JS del árbol de decisión
  ✓ 12 pasan  cruce_ronda
```

Si algo quedó rojo, en lugar de «Cruces»:

```
DIVERGENCIA · <prueba> · <el caso concreto que falló>
  Python dice: <...>
  JS dice:     <...>
  Atrasado:    <cuál de los dos, y por qué lo crees>
```

Nada de narrar los pasos. Quien lee quiere saber qué quedó distinto y si los
dos lados siguen de acuerdo.
