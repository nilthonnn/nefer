package pe.camal.pesaje;

import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

/**
 * Por donde salen el Excel y el acta del WebView al teléfono.
 *
 * <p>Hace falta porque en un WebView una descarga que la propia página inicia
 * —un enlace con {@code download} y una URL {@code blob:}— no llega a ningún
 * lado: {@code DownloadListener} no se dispara para {@code blob:}, así que el
 * botón parecería funcionar y no guardaría nada. En vez de interceptar la
 * descarga, la app web entrega los bytes aquí y esto los escribe.
 *
 * <p>Desde Android 10 se escribe por MediaStore, que no pide permiso y deja el
 * archivo en Descargas, visible para cualquier app. Antes de Android 10 se
 * escribe en la carpeta pública con el permiso declarado en el manifiesto.
 */
public class PuenteArchivos {

    private final Context contexto;

    PuenteArchivos(Context contexto) {
        this.contexto = contexto.getApplicationContext();
    }

    /**
     * Guarda un archivo en Descargas.
     *
     * <p>Se llama desde JavaScript y devuelve el resultado en el acto: la app
     * web enseña el aviso con lo que conteste. Cadena vacía es que salió bien;
     * cualquier otra cosa es el motivo, para poder decirlo en pantalla en vez
     * de dejar al operario mirando un botón que no hizo nada.
     *
     * @param nombre nombre con extensión, ya saneado por quien llama
     * @param base64 contenido del archivo
     * @param mime   tipo, para que el teléfono sepa con qué abrirlo
     */
    @JavascriptInterface
    public String guardar(String nombre, String base64, String mime) {
        if (nombre == null || base64 == null) {
            return "No llegó el archivo.";
        }
        // El nombre viene de la app, pero igual se limpia: un nombre con
        // barras escribiría fuera de Descargas.
        final String limpio = nombre.replaceAll("[/\\\\]", "_").trim();
        if (limpio.isEmpty()) {
            return "El archivo no tiene nombre.";
        }

        final byte[] datos;
        try {
            datos = Base64.decode(base64, Base64.DEFAULT);
        } catch (IllegalArgumentException e) {
            return "El archivo llegó dañado.";
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                return porMediaStore(limpio, mime, datos);
            }
            return enCarpetaPublica(limpio, datos);
        } catch (Exception e) {
            return "No se pudo guardar: " + e.getMessage();
        }
    }

    /** Android 10 en adelante: sin permisos, por el almacén de medios. */
    private String porMediaStore(String nombre, String mime, byte[] datos) throws Exception {
        ContentValues campos = new ContentValues();
        campos.put(MediaStore.Downloads.DISPLAY_NAME, nombre);
        campos.put(MediaStore.Downloads.MIME_TYPE, mime == null ? "application/octet-stream" : mime);
        campos.put(MediaStore.Downloads.IS_PENDING, 1);

        Uri destino = contexto.getContentResolver()
                .insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, campos);
        if (destino == null) {
            return "Descargas no aceptó el archivo.";
        }

        try (OutputStream salida = contexto.getContentResolver().openOutputStream(destino)) {
            if (salida == null) {
                contexto.getContentResolver().delete(destino, null, null);
                return "No se pudo abrir Descargas para escribir.";
            }
            salida.write(datos);
        } catch (Exception e) {
            // Un archivo a medio escribir con IS_PENDING puesto queda invisible
            // y ocupando sitio: se quita, y así el reintento no deja rastros.
            contexto.getContentResolver().delete(destino, null, null);
            throw e;
        }

        campos.clear();
        campos.put(MediaStore.Downloads.IS_PENDING, 0);
        contexto.getContentResolver().update(destino, campos, null, null);
        return "";
    }

    /** Android 9 y anteriores: carpeta pública de Descargas. */
    private String enCarpetaPublica(String nombre, byte[] datos) throws Exception {
        File carpeta = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS);
        if (carpeta == null || (!carpeta.exists() && !carpeta.mkdirs())) {
            return "No hay carpeta de Descargas.";
        }
        File archivo = new File(carpeta, nombre);
        try (FileOutputStream salida = new FileOutputStream(archivo)) {
            salida.write(datos);
        }
        return "";
    }

    /** Lo usa la app web para saber que está corriendo dentro del APK. */
    @JavascriptInterface
    public String version() {
        return BuildConfig.VERSION_NAME;
    }
}
