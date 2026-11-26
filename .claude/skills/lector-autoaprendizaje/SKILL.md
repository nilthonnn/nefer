---
name: lector-autoaprendizaje
description: Mejorar el lector de fotos de la app de actas de campo (OCR de placas, pantallas del controlador, probador de baterías y horómetro) a partir de fotos reales de campo y del aprendizaje exportado por los teléfonos. Úsala cuando el usuario mande fotos de placas o pantallas, cuando diga que el lector no lee algo, o cuando traiga un archivo aprendizaje-lector.json. Mide antes y después, y nunca promete una precisión que no se midió.
---

# Autoaprendizaje del lector de fotos

Código: `clientes/campo/docs/app/index.html`, bloque `MANT.lector`
(`prepararImagen`, `leerFoto`, `LEE` / `placa` / `placaGrupo` / `panel`,
`aprender` / `ajustar`). Medición: `clientes/campo/herramientas/medir-lector.py`.
Pruebas: `clientes/campo/tests/test_lector.py`.

El lector aprende por dos vías:

- **En el teléfono, solo, y con evidencia** (`campo.lector.aprendizaje`):
  - **Nota**: la primera corrección del técnico a un identificador (modelo,
    serie, CPL, WDG, módulo). No cambia lo leído; lo recuerda al lado
    («la vez anterior lo corrigió a …»).
  - **Regla**: la misma corrección confirmada **2 veces** (`PROMOVER`) **y**
    explicada por un error de lectura con nombre (`patronDe`: confusión
    O/0, I/1, S/5, B/8… o un carácter mal leído). Sólo entonces se propone
    sola («aprendido»). Si lo escrito no se parece a lo leído no es error del
    lector (otra placa, otro equipo): queda en nota para siempre.
  - **Descarte**: lo que el técnico desmarca se anota; con 2 descartes iguales
    la propuesta llega sin marcar y lo dice (callejón sin salida conocido).
  - **Nada que parezca una clave** (`pareceSecreto`) se guarda ni se importa.
  - Además, lo leído se compara con las fichas existentes tolerando las
    confusiones del OCR («según la ficha de 064»). Ajustes › Aprendizaje del
    lector › Exportar / Importar lo pasa entre teléfonos.
- **Contigo (esta skill)**: con fotos de campo se mide, se encuentra qué falla
  y se escriben reglas y pruebas nuevas. Una regla del código también se
  «promueve» sólo con evidencia: una prueba que pasa, el patrón de fallo con
  nombre y al menos un intento descartado anotado (qué no funcionó y por qué).

## Lo leído se valida antes de llegar al técnico (`revisar`)

- Fuera de lo posible (`RANGOS`: Hz 45–65, RPM 600–4000, SOH 0–100 %…) o un
  horómetro menor al ya registrado → llega **sin marcar** y con el motivo.
- Confianza del motor < 45 % → «lectura de baja confianza (NN %)».
- El preprocesado tiene dos variantes: umbral local (por defecto) y, si
  aquél lee poco, **contraste** (grises → contraste ×2 → mediana 3×3 →
  nitidez). Se queda con la que mejor lee.

## La prueba con carga se lee por evidencia (`MANT.validaciones.diagnosticar`)

Cada hallazgo separa **medido** / **puede indicar** (con confianza alta,
media o investigar) / **supuesto** (conocimiento general, no medido) /
**verificar**. Sin el dato de placa (voltaje, Hz, RPM, kVA, voltaje de
baterías) no se interpreta: se dice qué falta. Nunca decide: el técnico
confirma y responde por la seguridad. Se aprendió de métodos de diagnóstico
de maquinaria; las skills de vibración no aplican (necesitan sensores).

## Qué no se usa y por qué

- Leer las fotos con un servicio de visión en la nube: las fotos son del
  cliente y no salen del teléfono.
- Instalar skills de terceros sin revisarlas: se toman las ideas y se
  reescriben aquí, con pruebas.

## Pasos

1. **Las fotos no entran al repositorio.** Son equipos del cliente (y a veces
   llevan logos de empresas). Cópialas a una carpeta de trabajo fuera del repo.
2. **Nómbralas** `NN_<casilla>.jpg` (c05 placa del grupo, c12 motor, g01
   alternador, c19 etiqueta de batería, c21 probador, c06 horómetro, g03–g07
   pantallas, c01 frente/TAG).
3. **Escribe `verdad.json`** sólo con lo que se lee con certeza en cada foto.
   Si dudas de un carácter, no lo pongas. Opcional: `_fichas` y `_tag_de`
   para medir el escenario «equipo ya registrado».
4. **Mide**: `python herramientas/medir-lector.py CARPETA --salida TEXTOS`.
   Repite con fichas si las pusiste. Anota los dos números.
5. **Clasifica cada fallo** mirando el texto leído:
   - *El valor no está en el texto* → es lectura: encuadre (la foto entera
     casi nunca se lee), giro, reflejo, pantalla de matriz de puntos, placa
     estampada. Prueba variantes de `prepararImagen` con un script aparte
     antes de cambiar la app.
   - *El valor está pero no se propuso* → es interpretación: añade el rótulo o
     la unidad a `placa` / `panel` (primero por rótulo, luego por unidad;
     exige un dígito en códigos y rangos en números).
6. **Prueba en texto, no en imagen**: añade a `tests/test_lector.py` el texto
   con el formato real y **los números de serie alterados**.
7. **Vuelve a medir** y compara con el paso 4. No subas una regla que baje
   la medición de otra foto.
8. **Aprendizaje de los teléfonos**: si el usuario trae
   `aprendizaje-lector.json`, busca correcciones repetidas (mismo `leido` →
   `usado` en muchos equipos): son confusiones del OCR que conviene volver
   regla (`confusiones`) o rótulos que faltan. El archivo lleva series de
   equipos del cliente: no lo subas.
9. **Commit** `fix(lector): …` con la medición antes y después en el mensaje.

## Dónde estamos (2026-11-26)

Foto entera, sin encuadrar ni fichas, las mismas 19 fotos: **18 % → 25 %**
(12 → 17 de 67 campos) al añadir la pasada de contraste; tarda ~3 s más
por foto difícil. Mejoraron la placa del alternador en vertical y la placa
del grupo con poco contraste.

### Medición anterior (2026-11-25)

19 fotos de campo, 67 campos: 3 % → **24 %** en primera visita y **31 %**
con fichas. Se leen bien las pantallas PowerCommand encuadradas y las placas
impresas de frente. No se leen: el probador UT673A (LCD de matriz de puntos),
las placas estampadas en relieve, las fotos en ángulo o con sol directo.
Para esas, el técnico escribe el valor: el lector propone, nunca impone.

## Consejo para el técnico (va en la app)

Foto de frente, que la placa o la pantalla llene el cuadro, sin reflejo (haz
sombra con la mano), y «Encuadrar y leer».
