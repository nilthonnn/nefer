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

- **En el teléfono, solo**: cada corrección del técnico a un identificador
  (modelo, serie, CPL, WDG, módulo) queda en `campo.lector.aprendizaje` y se
  aplica la próxima vez («aprendido»); y lo leído se compara con las fichas
  existentes tolerando las confusiones del OCR («según la ficha de 064»).
  Ajustes › Aprendizaje del lector › Exportar / Importar lo pasa entre
  teléfonos.
- **Contigo (esta skill)**: con fotos de campo se mide, se encuentra qué falla
  y se escriben reglas y pruebas nuevas.

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

## Dónde estamos (2026-11-25)

19 fotos de campo, 67 campos: 3 % → **24 %** en primera visita y **31 %**
con fichas. Se leen bien las pantallas PowerCommand encuadradas y las placas
impresas de frente. No se leen: el probador UT673A (LCD de matriz de puntos),
las placas estampadas en relieve, las fotos en ángulo o con sol directo.
Para esas, el técnico escribe el valor: el lector propone, nunca impone.

## Consejo para el técnico (va en la app)

Foto de frente, que la placa o la pantalla llene el cuadro, sin reflejo (haz
sombra con la mano), y «Encuadrar y leer».
