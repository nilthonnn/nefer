package pe.rdrental.actas;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.database.Cursor;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

import androidx.annotation.RequiresApi;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * El puente por el que el acta sale de la pagina y llega a Descargas.
 *
 * Una pagina dentro de un WebView no puede descargar lo que ella misma acaba
 * de generar: el PDF, el Excel y el .zip existen solo en memoria, y el
 * `DownloadListener` del contenedor nunca llega a verlos. Asi que los recibe
 * este puente.
 *
 * Llegan a trozos —medio mega cada uno— y no de una vez, por dos razones:
 * un acta de veinte fotos pasa de los diez megas, y una cadena de ese tamano
 * cruzando el puente de JavaScript es justo lo que revienta un telefono de
 * gama baja; y escribiendo segun llega no hace falta tener el archivo entero
 * dos veces en memoria.
 *
 * El contrato, visto desde la pagina:
 *
 *   var vale = Anfitrion.abrir(nombre, mime);   // "e12" o "ERROR:..."
 *   Anfitrion.trozo(vale, base64);              // tantas veces como haga falta
 *   var fin = Anfitrion.cerrar(vale);           // "OK:Descargas/..." o "ERROR:..."
 *
 * Si algo se tuerce a mitad, `cancelar` deja el telefono sin archivos a medias.
 */
public class Anfitrion {

  private static final String ETIQUETA = "ActasRD";
  /** Todas las actas caen en la misma carpeta: el operario sabe donde mirar. */
  static final String CARPETA = "RD RENTAL";
  /** Un acta no llega a esto ni de lejos; es el tope antes de dar por rota la pagina. */
  private static final long TOPE_BYTES = 256L * 1024 * 1024;

  private final Activity actividad;
  private final Map<String, Envio> enCurso = new HashMap<>();
  private final AtomicLong contador = new AtomicLong(1);

  Anfitrion(Activity actividad) {
    this.actividad = actividad;
  }

  private static class Envio {
    String nombre;
    OutputStream salida;
    Uri destino;      // Android 10 en adelante
    File archivo;     // hasta Android 9
    long escrito;
  }

  /** La version que el operario ve en la pagina, para que coincida con la del .apk. */
  @JavascriptInterface
  public String version() {
    return BuildConfig.VERSION_NAME + " (" + BuildConfig.VERSION_CODE + ")";
  }

  @JavascriptInterface
  public String abrir(String nombre, String mime) {
    String limpio = limpiarNombre(nombre);
    if (mime == null || mime.isEmpty()) {
      mime = "application/octet-stream";
    }
    try {
      Envio envio = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
          ? abrirEnMediaStore(limpio, mime)
          : abrirEnDescargas(limpio);
      String vale = "e" + contador.getAndIncrement();
      synchronized (enCurso) {
        enCurso.put(vale, envio);
      }
      return vale;
    } catch (Exception e) {
      Log.w(ETIQUETA, "no se pudo abrir " + limpio, e);
      return "ERROR:" + descripcion(e);
    }
  }

  @JavascriptInterface
  public String trozo(String vale, String base64) {
    Envio envio;
    synchronized (enCurso) {
      envio = enCurso.get(vale);
    }
    if (envio == null) {
      return "ERROR:el envío ya no está abierto";
    }
    try {
      byte[] datos = Base64.decode(base64, Base64.DEFAULT);
      envio.escrito += datos.length;
      if (envio.escrito > TOPE_BYTES) {
        throw new IllegalStateException("el archivo pasa de " + (TOPE_BYTES / 1048576) + " MB");
      }
      envio.salida.write(datos);
      return "";
    } catch (Exception e) {
      Log.w(ETIQUETA, "fallo al escribir " + envio.nombre, e);
      deshacer(vale, envio);
      return "ERROR:" + descripcion(e);
    }
  }

  @JavascriptInterface
  public String cerrar(String vale) {
    Envio envio;
    synchronized (enCurso) {
      envio = enCurso.remove(vale);
    }
    if (envio == null) {
      return "ERROR:el envío ya no está abierto";
    }
    try {
      envio.salida.flush();
      envio.salida.close();
      String nombreFinal = envio.nombre;
      if (envio.destino != null) {
        publicar(envio.destino);
        nombreFinal = nombrePublicado(envio.destino, envio.nombre);
      } else if (envio.archivo != null) {
        // Sin esto el archivo esta en el disco pero no aparece en el gestor
        // de archivos hasta que el telefono decida repasar la carpeta.
        MediaScannerConnection.scanFile(actividad,
            new String[]{envio.archivo.getAbsolutePath()}, null, null);
        nombreFinal = envio.archivo.getName();
      }
      final String ruta = "Descargas/" + CARPETA + "/" + nombreFinal;
      avisar(actividad.getString(R.string.guardado_en, CARPETA + "/" + nombreFinal));
      return "OK:" + ruta;
    } catch (Exception e) {
      Log.w(ETIQUETA, "fallo al cerrar " + envio.nombre, e);
      deshacer(vale, envio);
      return "ERROR:" + descripcion(e);
    }
  }

  @JavascriptInterface
  public void cancelar(String vale) {
    Envio envio;
    synchronized (enCurso) {
      envio = enCurso.remove(vale);
    }
    if (envio != null) {
      deshacer(vale, envio);
    }
  }

  // ---------- escritura ----------

  @RequiresApi(Build.VERSION_CODES.Q)
  private Envio abrirEnMediaStore(String nombre, String mime) throws Exception {
    ContentResolver resolucion = actividad.getContentResolver();
    ContentValues datos = new ContentValues();
    datos.put(MediaStore.Downloads.DISPLAY_NAME, nombre);
    datos.put(MediaStore.Downloads.MIME_TYPE, mime);
    datos.put(MediaStore.Downloads.RELATIVE_PATH,
              Environment.DIRECTORY_DOWNLOADS + "/" + CARPETA);
    // Mientras se escribe queda marcado como a medias: si el telefono se
    // apaga en mitad, nadie se encuentra un acta truncada en Descargas.
    datos.put(MediaStore.Downloads.IS_PENDING, 1);

    Uri destino = resolucion.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, datos);
    if (destino == null) {
      throw new IllegalStateException("Descargas no admitió el archivo");
    }
    OutputStream salida = resolucion.openOutputStream(destino);
    if (salida == null) {
      resolucion.delete(destino, null, null);
      throw new IllegalStateException("no se pudo abrir el archivo para escribir");
    }
    Envio envio = new Envio();
    envio.nombre = nombre;
    envio.destino = destino;
    envio.salida = salida;
    return envio;
  }

  private Envio abrirEnDescargas(String nombre) throws Exception {
    File carpeta = new File(
        Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), CARPETA);
    if (!carpeta.isDirectory() && !carpeta.mkdirs()) {
      throw new IllegalStateException("sin permiso para escribir en Descargas");
    }
    File archivo = sinPisar(carpeta, nombre);
    Envio envio = new Envio();
    envio.nombre = nombre;
    envio.archivo = archivo;
    envio.salida = new FileOutputStream(archivo);
    return envio;
  }

  @RequiresApi(Build.VERSION_CODES.Q)
  private void publicar(Uri destino) {
    ContentValues fin = new ContentValues();
    fin.put(MediaStore.Downloads.IS_PENDING, 0);
    actividad.getContentResolver().update(destino, fin, null, null);
  }

  /** Descargas renombra sola si ya existe; se pregunta con que nombre quedo. */
  private String nombrePublicado(Uri destino, String porOmision) {
    Cursor c = null;
    try {
      c = actividad.getContentResolver().query(
          destino, new String[]{MediaStore.Downloads.DISPLAY_NAME}, null, null, null);
      if (c != null && c.moveToFirst()) {
        String nombre = c.getString(0);
        if (nombre != null && !nombre.isEmpty()) {
          return nombre;
        }
      }
    } catch (Exception e) {
      Log.d(ETIQUETA, "no se pudo leer el nombre final", e);
    } finally {
      if (c != null) {
        c.close();
      }
    }
    return porOmision;
  }

  private void deshacer(String vale, Envio envio) {
    synchronized (enCurso) {
      enCurso.remove(vale);
    }
    try {
      if (envio.salida != null) {
        envio.salida.close();
      }
    } catch (Exception ignorado) {
      /* ya no importa: lo que viene es borrarlo */
    }
    try {
      if (envio.destino != null) {
        actividad.getContentResolver().delete(envio.destino, null, null);
      } else if (envio.archivo != null && envio.archivo.exists()) {
        //noinspection ResultOfMethodCallIgnored
        envio.archivo.delete();
      }
    } catch (Exception e) {
      Log.d(ETIQUETA, "no se pudo retirar el archivo a medias", e);
    }
  }

  // ---------- nombres ----------

  /**
   * El nombre viene de la pagina. Se queda en un nombre de archivo y nada mas:
   * sin barras, sin subir de carpeta y sin quedarse vacio.
   */
  static String limpiarNombre(String nombre) {
    String base = nombre == null ? "" : nombre.trim();
    int barra = Math.max(base.lastIndexOf('/'), base.lastIndexOf('\\'));
    if (barra >= 0) {
      base = base.substring(barra + 1);
    }
    base = base.replaceAll("[\\p{Cntrl}\"*/:<>?\\\\|]", "_");
    while (base.startsWith(".")) {
      base = base.substring(1);
    }
    if (base.isEmpty()) {
      base = "acta.bin";
    }
    if (base.length() > 120) {
      int punto = base.lastIndexOf('.');
      String extension = punto > 0 && base.length() - punto <= 10 ? base.substring(punto) : "";
      base = base.substring(0, 120 - extension.length()) + extension;
    }
    return base;
  }

  private static File sinPisar(File carpeta, String nombre) {
    File candidato = new File(carpeta, nombre);
    if (!candidato.exists()) {
      return candidato;
    }
    int punto = nombre.lastIndexOf('.');
    String cuerpo = punto > 0 ? nombre.substring(0, punto) : nombre;
    String extension = punto > 0 ? nombre.substring(punto) : "";
    for (int n = 2; n < 1000; n++) {
      candidato = new File(carpeta, cuerpo + " (" + n + ")" + extension);
      if (!candidato.exists()) {
        return candidato;
      }
    }
    return new File(carpeta, cuerpo + "-" + System.currentTimeMillis() + extension);
  }

  private static String descripcion(Exception e) {
    String mensaje = e.getMessage();
    if (mensaje == null || mensaje.isEmpty()) {
      mensaje = e.getClass().getSimpleName();
    }
    return mensaje.replace('\n', ' ');
  }

  private void avisar(final String texto) {
    actividad.runOnUiThread(new Runnable() {
      @Override public void run() {
        Toast.makeText(actividad, texto, Toast.LENGTH_LONG).show();
      }
    });
  }
}
