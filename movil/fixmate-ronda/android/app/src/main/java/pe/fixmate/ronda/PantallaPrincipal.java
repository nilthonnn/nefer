package pe.fixmate.ronda;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.webkit.WebViewAssetLoader;

/**
 * La app entera: un WebView que sirve la ronda CIL desde dentro del APK.
 *
 * <p>Los archivos van servidos por https desde un dominio interno en vez de
 * cargarse como {@code file://}. No es un capricho: en {@code file://} el
 * almacenamiento del navegador queda en un origen opaco que Android puede
 * vaciar sin avisar. Con {@link WebViewAssetLoader} el origen es estable y la
 * pantalla se comporta igual que en Chrome.
 *
 * <p>Nada de esto sale a la red: el dominio no existe fuera del aparato y el
 * manifiesto no pide permiso de INTERNET. Es la condición de trabajo real
 * —interior mina, sin cobertura— convertida en una propiedad del programa en
 * vez de en una esperanza.
 */
public class PantallaPrincipal extends Activity {

    /** Dominio interno. Reservado por la IETF para esto, nunca resuelve fuera. */
    private static final String DOMINIO = "ronda.fixmate.localhost";
    private static final String INICIO = "https://" + DOMINIO + "/www/index.html";

    /** El mismo gris de la barra de FixMate. Ver res/values/colors.xml. */
    private static final int FONDO = 0xFF16191B;

    /** Codigo de la peticion al selector de archivos del sistema. */
    private static final int PEDIR_ARCHIVO = 2;

    private WebView vista;
    private long ultimoAtras = 0;

    /**
     * El WebView esperando los archivos que el operador elija.
     *
     * <p>Hay que contestarle SIEMPRE, incluso con {@code null}: mientras no
     * se le contesta, el WebView considera que hay un selector abierto y no
     * abre otro. Dejarlo sin contestar una vez —el operador toca «atras» en
     * el selector— deja el boton muerto hasta que se cierra la app.
     */
    private ValueCallback<Uri[]> esperandoArchivo;

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);

        getWindow().setStatusBarColor(FONDO);
        getWindow().setNavigationBarColor(FONDO);

        final WebViewAssetLoader cargador = new WebViewAssetLoader.Builder()
                .setDomain(DOMINIO)
                .addPathHandler("/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        vista = new WebView(this);
        vista.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        vista.setBackgroundColor(FONDO);

        WebSettings ajustes = vista.getSettings();
        ajustes.setJavaScriptEnabled(true);
        ajustes.setDomStorageEnabled(true);
        ajustes.setAllowFileAccess(false);           // no hace falta: todo va por el cargador
        // El selector del sistema devuelve `content://`, y el WebView tiene
        // que poder leer de ahi el archivo que el operador eligio. Con esto
        // en false, «Abrir pauta del equipo» abria el selector y despues no
        // cargaba nada. `file://` sigue cerrado: el contenido de la app va
        // por el cargador de assets y no hace falta.
        ajustes.setAllowContentAccess(true);
        ajustes.setSupportZoom(false);
        ajustes.setMediaPlaybackRequiresUserGesture(true);
        // El contenido es local y va por https interno: no hay mezcla que permitir.
        ajustes.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        vista.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest peticion) {
                return cargador.shouldInterceptRequest(peticion.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest peticion) {
                // La ronda no tiene enlaces fuera —la barra se los quita al
                // detectar el puente—. Si alguno apareciera, que no se abra
                // aquí dentro haciéndose pasar por la app.
                return !DOMINIO.equals(peticion.getUrl().getHost());
            }
        });

        // Por donde ENTRA la pauta. En un WebView, un `<input type="file">`
        // no hace absolutamente nada si la app no implementa esto: ni abre
        // selector, ni da error, ni avisa. El operador tocaba «Abrir pauta
        // del equipo» y no pasaba nada — y como el APK existe para las minas
        // que no dejan instalar desde el navegador, y esa es la unica forma
        // de meterle una pauta, ahi la ronda no arrancaba.
        vista.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> callback,
                                             FileChooserParams parametros) {
                // Si quedo uno sin contestar, se le contesta ahora: dos
                // selectores a medias dejan el boton muerto.
                if (esperandoArchivo != null) {
                    esperandoArchivo.onReceiveValue(null);
                }
                esperandoArchivo = callback;
                try {
                    // El intento que arma el propio WebView ya trae el filtro
                    // que declara la pantalla (`accept=".json"`), asi que no
                    // se escribe aqui otra vez: una segunda copia del filtro
                    // se queda atras el dia que la pantalla cambie.
                    startActivityForResult(parametros.createIntent(), PEDIR_ARCHIVO);
                    return true;
                } catch (RuntimeException sinSelector) {
                    // Un telefono de faena puede no tener ninguna aplicacion
                    // que atienda el selector. Se dice, en vez de dejar la
                    // pantalla esperando algo que no va a llegar.
                    esperandoArchivo = null;
                    callback.onReceiveValue(null);
                    Toast.makeText(PantallaPrincipal.this, R.string.sin_selector,
                                   Toast.LENGTH_LONG).show();
                    return true;
                }
            }
        });

        // El puente por el que SALE el archivo de la ronda. En un WebView una
        // descarga `blob:` no dispara nada —ni DownloadListener—, así que la
        // pantalla entrega los bytes por aquí y esto los escribe en Descargas.
        vista.addJavascriptInterface(new PuenteArchivos(this), "PuenteFixMate");

        setContentView(vista);

        // `restoreState` devuelve null cuando el Bundle no traía estado del
        // WebView —lo hay: Android puede recrear la actividad con un Bundle
        // que no lo incluya—, y entonces la pantalla se queda en blanco.
        if (estado == null || vista.restoreState(estado) == null) {
            vista.loadUrl(INICIO);
        }

        pedirPermisoDeEscrituraSiHaceFalta();
    }

    /**
     * Desde Android 10 se escribe por MediaStore y no hace falta permiso.
     * Antes sí, y declararlo en el manifiesto no basta desde Android 6: hay
     * que pedirlo en caliente.
     *
     * <p>Se pide al arrancar y no al exportar porque el puente contesta al
     * instante y un diálogo de permiso no: pedirlo entonces obligaría a tocar
     * el botón dos veces sin explicar por qué.
     */
    private void pedirPermisoDeEscrituraSiHaceFalta() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) return;
        if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                == PackageManager.PERMISSION_GRANTED) return;
        requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 1);
    }

    /**
     * Lo que eligio el operador en el selector, de vuelta al WebView.
     *
     * <p>Se contesta en los dos casos: con los archivos si eligio, y con
     * {@code null} si cancelo. Lo segundo no es cortesia: sin eso el WebView
     * se queda creyendo que el selector sigue abierto y no vuelve a abrirlo.
     */
    @Override
    protected void onActivityResult(int peticion, int resultado, Intent datos) {
        if (peticion != PEDIR_ARCHIVO) {
            super.onActivityResult(peticion, resultado, datos);
            return;
        }
        if (esperandoArchivo == null) return;
        esperandoArchivo.onReceiveValue(
                WebChromeClient.FileChooserParams.parseResult(resultado, datos));
        esperandoArchivo = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle estado) {
        super.onSaveInstanceState(estado);
        vista.saveState(estado);
    }

    /**
     * El botón de atrás del teléfono no cierra la ronda de un toque.
     *
     * <p>La pantalla responde {@code atras()}: cierto si tenía algo que
     * cerrar —el diálogo de la nota—. Si no, hacen falta dos toques. Cerrar
     * de un toque a mitad de una ronda es perder el turno entero, y el
     * operador no tiene cómo recuperarlo: los puntos ya contestados viven en
     * la pantalla, no en un archivo.
     */
    @Override
    public void onBackPressed() {
        vista.evaluateJavascript(
                "(typeof atras === 'function') ? atras() : false",
                valor -> {
                    if ("true".equals(valor)) return;
                    long ahora = System.currentTimeMillis();
                    if (ahora - ultimoAtras < 2000) {
                        finish();
                    } else {
                        ultimoAtras = ahora;
                        Toast.makeText(this, R.string.salir_dos_veces, Toast.LENGTH_SHORT).show();
                    }
                });
    }

    @Override
    protected void onDestroy() {
        // Si la app se cierra con el selector abierto, el callback se queda
        // colgado con una referencia a esta actividad.
        if (esperandoArchivo != null) {
            esperandoArchivo.onReceiveValue(null);
            esperandoArchivo = null;
        }
        if (vista != null) {
            ((ViewGroup) vista.getParent()).removeView(vista);
            vista.destroy();
            vista = null;
        }
        super.onDestroy();
    }
}
