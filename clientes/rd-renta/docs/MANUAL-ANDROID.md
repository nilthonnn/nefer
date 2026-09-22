# La aplicación de Android

Cómo llega al teléfono, qué lleva dentro, qué permisos pide y cómo se publica
una versión nueva.

---

## 1. Para el operario: instalarla

1. Abra **https://nilthonnn.github.io/nefer/rd-rental/** en el teléfono, o
   escanee el código QR que está impreso en el taller.
2. Toque **Descargar para Android**. Baja un archivo llamado
   `rd-rental-actas.apk`.
3. Toque el archivo descargado. Android avisa de que viene de fuera de la
   tienda: **Ajustes → Permitir de esta fuente**, y vuelva atrás.
4. **Instalar**. Si Play Protect pregunta, **Instalar de todas formas**: es lo
   normal en una aplicación de empresa que no está en Google Play.
5. Ábrala desde su icono. La primera vez que toque una casilla de foto,
   **conceda la cámara**. Queda concedida.

Las actas salen en **Descargas › RD RENTAL**. Desde ahí se mandan por WhatsApp
o por correo como cualquier otro archivo.

---

## 2. Qué es en realidad

No es una aplicación distinta. Es **la misma app web** que se publica en
`docs/app/`, metida dentro de un contenedor de Android de dos clases:
`MainActivity` y `Anfitrion`. La app web no sabe que está dentro de un `.apk`
más allá de un detalle: que existe un puente para guardar archivos.

Ese contenedor está ahí por tres cosas que el navegador no puede dar:

| | Por qué hace falta |
|---|---|
| **La cámara** | Los archivos van dentro del `.apk` y se sirven como `https://actas.rdrental.local/app/…` —no como `file://`—, y por eso Android los trata como un origen seguro y concede la cámara. Es lo que hace `WebViewAssetLoader`, y es la razón de ser del contenedor. |
| **Las descargas** | Una página dentro de un `WebView` no puede descargar lo que ella misma acaba de generar: el PDF, el Excel y el `.zip` existen sólo en memoria. Se los pasa al puente `Anfitrion`, que los escribe en Descargas. |
| **Que no se borre** | Lo guardado en el navegador desaparece si alguien borra los datos de navegación. Los datos de la aplicación son suyos. |

### El puente, por dentro

El acta viaja **a trozos de medio mega**, no de una vez. Un acta de veinte
fotos pasa de los diez megas, y una cadena de ese tamaño cruzando el puente de
JavaScript de golpe es justo lo que tumba un teléfono de gama baja.

```js
var vale = Anfitrion.abrir(nombre, mime);   // "e12" o "ERROR:..."
Anfitrion.trozo(vale, base64);              // tantas veces como haga falta
var fin  = Anfitrion.cerrar(vale);          // "OK:Descargas/..." o "ERROR:..."
```

Mientras se escribe, el archivo queda marcado como pendiente: si el teléfono se
apaga a mitad, nadie se encuentra un acta truncada en Descargas.

---

## 3. Permisos

| Permiso | Para qué | Cuándo se pide |
|---|---|---|
| `CAMERA` | La cámara integrada, que es como se toman las fotos con el equipo delante. | La primera vez que se toca una casilla de foto. |
| `WRITE_EXTERNAL_STORAGE` | Escribir en Descargas **sólo hasta Android 9**. De Android 10 en adelante se escribe por MediaStore y no hace falta permiso ninguno. | Al abrir la aplicación, en teléfonos viejos. |

En la lista de permisos del teléfono aparecerá también
`READ_EXTERNAL_STORAGE`, igualmente hasta Android 9: no está declarado en el
manifiesto, lo añade la compilación porque el permiso de escritura lo implica.

**No pide `INTERNET`.** La aplicación no puede salir a la red aunque se lo
propusiera: no lo tiene concedido. Las fotos, los datos del equipo y las actas
no salen del teléfono.

---

## 4. Para quien la publica: compilar

El `.apk` **no se compila a mano**. Lo compila
`.github/workflows/apk.yml` en cada empuje a `main` que toque
`clientes/rd-renta/android/` o `clientes/rd-renta/docs/app/`, y lo deja
publicado siempre en la misma dirección:

```
https://github.com/nilthonnn/nefer/releases/download/android/rd-rental-actas.apk
```

Esa dirección es la del botón de la página y la del código QR impreso. No
cambia nunca; lo que cambia es el archivo que hay detrás.

Antes de publicar, la compilación comprueba tres cosas que un `.apk` que
compila puede seguir incumpliendo:

1. Que dentro va **exactamente** la misma app web que se publica en Pages
   (archivo por archivo, byte a byte).
2. Que esa app trae el puente (`window.Anfitrion`, `CONTEXTO.enAndroid`).
3. Que el `.apk` está bien firmado (`apksigner verify`). Sale con firma v2
   solamente, que es la que Android 7 en adelante pide; la v1 sólo hace falta
   por debajo de eso, y la aplicación no baja de Android 7.

Si algo de eso falla, no se publica nada. Lo que se instalaría, si no, es una
pantalla en negro.

### Compilarla a mano, si hace falta

Hace falta un JDK 17 y el SDK de Android:

```bash
cd clientes/rd-renta/android
gradle :app:assembleDebug
# el .apk queda en app/build/outputs/apk/debug/
```

La versión de depuración se instala **al lado** de la buena
(`pe.rdrental.actas.pruebas`), así que se puede probar sin desinstalar la que
usa el operario.

---

## 5. La llave de firma

Android no instala nada sin firma, y sólo deja actualizar una aplicación con
una versión firmada con **la misma** llave.

Mientras el repositorio no tenga una llave propia, cada compilación sale
firmada con una distinta, y eso significa que **para poner una versión nueva
hay que desinstalar la anterior** — y con ella se van las actas a medias que
haya en el teléfono.

Se arregla una sola vez:

```bash
herramientas/crear-llave-android.sh
```

Imprime cuatro valores. Se pegan en
`Settings → Secrets and variables → Actions` del repositorio:

- `ANDROID_ALMACEN_BASE64`
- `ANDROID_CLAVE_ALMACEN`
- `ANDROID_ALIAS`
- `ANDROID_CLAVE_LLAVE`

Desde el siguiente empuje, el `.apk` se actualiza encima del anterior sin
desinstalar nada.

> **Guarde el archivo `.jks` con copia de seguridad.** Si se pierde, no hay
> forma de publicar una actualización: habría que empezar con otra aplicación
> y desinstalar la vieja en todos los teléfonos. No entra en el repositorio
> —está en `.gitignore`— y viaja sólo como secreto.

---

## 6. Qué mirar cuando algo falla

| Síntoma | Dónde mirar |
|---|---|
| La app abre en negro | La tarea `copiarWeb` no encontró `docs/app/`. La comprobación de la compilación lo detecta antes de publicar. |
| «App no instalada» al actualizar | Firma distinta. Desinstale la anterior, o ponga la llave propia (§5). |
| La cámara sale denegada | Ajustes › Aplicaciones › RD RENTAL Actas › Permisos › Cámara. |
| No aparece el archivo exportado | Descargas › RD RENTAL. En Android 9 y anteriores, compruebe el permiso de almacenamiento. |
| Hay que saber qué versión tiene | Dentro de la app, hoja **Comprobación**: dice la versión de la app y la del contenedor. |
