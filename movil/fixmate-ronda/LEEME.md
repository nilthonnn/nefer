# La ronda CIL como APK de Android

La ronda ya funciona sin señal y se instala desde el navegador: es una app
web con manifiesto y trabajador de servicio. Esto la envuelve en un APK, que
es lo que hace falta cuando el teléfono tiene que tenerla como una aplicación
más — repartible por WhatsApp o por cable, instalable por el administrador de
dispositivos de la mina, y sin depender de que alguien abra Chrome y acepte
un cartel.

**Si no hay una razón para el APK, no hace falta el APK.** Instalada desde
<https://nilthonnn.github.io/nefer/fixmate/ronda/> hace exactamente lo mismo:
icono propio, pantalla completa, sin red. El APK existe para cuando la
política del cliente no deja instalar desde el navegador, o cuando el
teléfono se entrega configurado y la ronda tiene que venir dentro.

## Qué hay dentro

Un WebView y nada más. Sin Capacitor, sin Cordova, sin Node:

```
movil/fixmate-ronda/android/
  settings.gradle, build.gradle, gradle.properties
  app/build.gradle                  copia docs/fixmate/ronda a los assets antes de compilar
  app/src/main/AndroidManifest.xml  sin permiso de INTERNET: la ronda no habla con nadie
  app/src/main/java/pe/fixmate/ronda/
      PantallaPrincipal.java        el WebView y el botón de atrás
      PuenteArchivos.java           por donde sale el archivo de la ronda
  app/src/main/res/                 icono, tema y textos
```

La pantalla no se copia a mano: `app/build.gradle` la trae de
`docs/fixmate/ronda/` en cada compilación, y CI se niega a compilar si esa
carpeta no está al día respecto de `herramientas/ronda/`. Un APK con una
pauta vieja dentro no se nota hasta que alguien está en el socavón.

### Cuatro decisiones que conviene conocer

**Los archivos van servidos por https, no como `file://`.**
`WebViewAssetLoader` los sirve desde `https://ronda.fixmate.localhost/`. En
`file://` el almacenamiento del navegador queda en un origen opaco que
Android puede vaciar sin avisar.

**El archivo de la ronda sale por un puente nativo.** En un WebView, una
descarga que la propia página inicia —un enlace con `download` y una URL
`blob:`— no llega a ningún lado: ni siquiera dispara el escuchador de
descargas de Android. El botón parecería funcionar y la ronda del turno no
quedaría guardada en ninguna parte. Así que la pantalla entrega los bytes en
base64 a `PuenteFixMate.guardar()` y Java los escribe en Descargas: por
MediaStore desde Android 10, y en la carpeta pública con permiso antes.

**El trabajador de servicio se queda fuera, con dos candados.** Dentro del
APK no tiene nada que guardar —los archivos ya son locales— y sus peticiones
no pasan por el cargador de assets, así que intentaría salir a una red que la
app no tiene permiso de usar. Se excluye al copiar **y** la pantalla no lo
registra cuando detecta el puente. Uno solo de los dos se deshace de un
descuido.

**El botón de atrás no cierra la ronda de un toque.** La pantalla responde
`atras()`: cierto si tenía un diálogo que cerrar. Si no, hacen falta dos
toques. Perder una ronda a medias es perder el turno: los puntos contestados
viven en la pantalla, no en un archivo.

## Cómo se compila

En CI, no en el portátil de nadie: `.github/workflows/apk-fixmate.yml`. El
SDK de Android son cientos de megas, y una compilación a mano es una
compilación que sólo sabe hacer una persona.

Cada empuje a `main` que toque la ronda deja una publicación nueva con el
`.apk` dentro. Antes de publicar, la compilación comprueba que lo que viaja
dentro es byte por byte la pantalla publicada, que lleva el puente, y que el
trabajador de servicio no se coló.

Para compilarlo en una máquina con el SDK puesto:

```bash
python3 herramientas/espejo-ronda.py          # la pantalla, al día
cd movil/fixmate-ronda/android
gradle :app:assembleRelease -PnombreVersion=1.0-local
```

## La firma

Sin llave propia el `.apk` sale firmado con una provisional que se fabrica en
cada compilación, y entonces **una versión nueva no se puede instalar encima
de la anterior**: hay que desinstalar, y eso borra lo que haya. Con las cuatro
claves puestas en el repositorio —las mismas que usan los otros dos APK— se
actualiza encima. Se crea con `herramientas/crear-llave-android.sh`.

## Lo que este APK no hace

- **No trae el análisis RCM ni el diagnóstico.** Es la ronda del operador y
  nada más. Las otras dos pantallas se usan desde el navegador, donde además
  se instalan igual.
- **No sincroniza.** El archivo de la ronda sale a Descargas y de ahí lo
  manda quien lo tenga, por donde pueda. No hay servidor al que subirlo, y
  mientras no lo haya, decir «sincroniza» sería mentir.
