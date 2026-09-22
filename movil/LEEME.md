# La app del camal como APK de Android

La app de pesaje es un archivo HTML que ya funciona sin señal y se instala
desde el navegador. Esto la envuelve en un APK, que es lo que hace falta
cuando el teléfono tiene que tenerla como una aplicación más: icono propio,
sin barra de navegador, sin depender de que alguien recuerde una dirección, y
repartible por WhatsApp o por cable en un camal sin cobertura.

## Qué hay dentro

Un WebView y nada más. Sin Capacitor, sin Cordova, sin Node:

```
movil/android/
  settings.gradle, build.gradle, gradle.properties, gradlew
  app/build.gradle                  copia docs/camal a los assets antes de compilar
  app/src/main/AndroidManifest.xml  sin permiso de INTERNET: la app no habla con nadie
  app/src/main/java/pe/camal/pesaje/
      PantallaPrincipal.java        el WebView y el botón de atrás
      PuenteArchivos.java           por donde salen el Excel y el acta
  app/src/main/res/                 icono, tema y textos
```

La app web no se copia a mano: `app/build.gradle` la trae de `docs/camal/` en
cada compilación, y CI se niega a compilar si `docs/camal/` no coincide con
`app-camal.cuerpo.html`. Un APK con una versión vieja dentro no se nota hasta
que alguien está pesando.

### Tres decisiones que conviene conocer

**Los archivos van servidos por https, no como `file://`.** `WebViewAssetLoader`
sirve los assets desde `https://camal.localhost/`. En `file://` el
almacenamiento del navegador queda en un origen opaco que Android puede vaciar
sin avisar, y ahí vive la jornada entera.

**Las descargas pasan por un puente nativo.** En un WebView, una descarga que
la propia página inicia —un enlace con `download` y una URL `blob:`— no llega
a ningún lado: ni siquiera dispara el escuchador de descargas de Android. El
botón parecería funcionar y no guardaría nada. Así que la app entrega los
bytes en base64 a `PuenteCamal.guardar()` y Java los escribe en Descargas: por
MediaStore desde Android 10, y en la carpeta pública antes.

**No se pide permiso de INTERNET.** No es un olvido: la app no habla con nadie.
Todo viaja dentro del APK y la jornada se queda en el teléfono.

## Compilar y descargar

### Lo normal: que lo compile GitHub

Cada vez que cambia la app o el proyecto Android, el flujo
`.github/workflows/apk-camal.yml` compila el APK, comprueba lo que lleva
dentro y lo publica.

Salen dos formas de descargarlo:

- **Una publicación**, con dirección directa:
  `https://github.com/nilthonnn/nefer/releases/download/camal-v<N>/camal-pesaje.apk`,
  donde `<N>` es el número de la compilación. Esa dirección se abre desde el
  teléfono sin más. El resumen de la ejecución la escribe entera.
- **Un artifact** `camal-pesaje-apk` en la propia ejecución, por si se prefiere
  bajarlo desde Actions.

También se puede lanzar a mano desde **Actions → apk del camal → Run workflow**.

### Por qué la publicación no se marca como «latest»

`/releases/latest/download/…` es una sola dirección por repositorio, y aquí ya
la usa el APK de las actas de RD RENTAL, con su QR impreso en un taller.
Marcar esta como «latest» rompería aquella. Por eso cada compilación publica
con su etiqueta propia —`camal-v12`— y la dirección lleva esa etiqueta.

### Qué se comprueba antes de publicar

Un APK que compila puede estar vacío por dentro: si la tarea que copia la app
web no hizo nada, lo que se instala es una pantalla en negro que nadie ve
hasta tenerla en la mano. Así que el flujo, antes de publicar, abre el APK
como zip y compara archivo por archivo lo que lleva dentro contra
`docs/camal/`; si falta uno, sobra uno o alguno difiere, falla. Comprueba
también que el `index.html` de dentro traiga el puente y las pantallas, lista
los permisos declarados y verifica la firma.

### En tu propia máquina

Hace falta un JDK 17 y el SDK de Android (API 34 y build-tools 34):

```bash
python3 demos/camal/construir.py          # regenera docs/camal
cd movil/android
./gradlew assembleDebug
# app/build/outputs/apk/debug/camal-pesaje-3.0-debug.apk
```

## Instalarlo en el teléfono

1. Pasa el `.apk` al celular (cable, WhatsApp, correo, tarjeta).
2. Ábrelo desde **Archivos** o **Descargas**.
3. Android pide permiso para instalar de esta fuente la primera vez:
   *Ajustes › Instalar apps desconocidas › (la app desde la que lo abriste) ›
   Permitir*. Es el aviso normal de cualquier app que no viene de Play.
4. Queda con el icono de la balanza, como una app más.

Android puede avisar de que «no se comprobó» la app: es la firma de
depuración, no un problema del archivo. Para que deje de avisar hay que
firmarla con una clave propia.

## Firmar para repartirla de verdad

Sin llave propia, cada compilación firma con una **provisional** que se
fabrica en el momento. El APK se instala igual, pero como la llave cambia en
cada compilación, una versión nueva no se puede instalar encima de la
anterior: hay que desinstalar primero. Para arreglarlo se pone una llave
propia en los *secrets* del repositorio —`ANDROID_ALMACEN_BASE64`,
`ANDROID_CLAVE_ALMACEN`, `ANDROID_ALIAS`, `ANDROID_CLAVE_LLAVE`—, las mismas
que ya usa el APK de las actas.

Para crearla:

```bash
keytool -genkeypair -v -keystore camal.jks -keyalg RSA -keysize 2048 \
        -validity 10000 -alias camal
```

**Esa clave no se versiona ni se pierde**: sin ella no se puede publicar una
actualización de la misma app, nunca, y hay que empezar con otro identificador.
Guardarla en el gestor de contraseñas de la empresa, no en el repositorio.

Después, en `app/build.gradle`, un `signingConfig` que lea la ruta y las
contraseñas de variables de entorno —para CI, de los *secrets* del repositorio—
y `./gradlew assembleRelease`.

## Lo que el APK no arregla

Sigue siendo la misma app, así que sigue guardando la jornada **en ese
teléfono**. Si se desinstala la app o se borran sus datos, se va. El Excel y el
acta son el respaldo: conviene exportar al cerrar cada jornada.

## Cómo se comprueba

El APK en sí sólo lo compila CI. Lo que se puede probar sin Android —y es lo
que de verdad se rompe— se prueba aquí:

```bash
python3 demos/camal/probar_puente.py salidas/
```

Finge el puente nativo tal como lo verá la app dentro del APK, recoge los
bytes que le entregaría a Java, los decodifica y abre el Excel con openpyxl y
el acta con pypdf: si un byte se estropeara al cruzar, el archivo abriría roto
en la oficina tres días después. Comprueba también el botón de atrás del
teléfono, que es JavaScript de este lado aunque lo dispare Android.
