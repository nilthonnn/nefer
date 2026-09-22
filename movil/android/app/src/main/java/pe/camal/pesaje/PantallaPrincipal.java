package pe.camal.pesaje;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.webkit.WebViewAssetLoader;

/**
 * La app entera: un WebView que sirve la app de pesaje desde dentro del APK.
 *
 * <p>Los archivos van servidos por https desde un dominio interno en vez de
 * cargarse como {@code file://}. No es un capricho: en {@code file://} el
 * almacenamiento del navegador queda en un origen opaco que Android puede
 * vaciar sin avisar, y ahí vive la jornada. Con {@link WebViewAssetLoader} el
 * origen es estable y {@code localStorage} se comporta como en Chrome.
 *
 * <p>Nada de esto sale a la red: el dominio no existe fuera del aparato y el
 * manifiesto no pide permiso de INTERNET.
 */
public class PantallaPrincipal extends Activity {

    /** Dominio interno. Reservado por la IETF para esto, nunca resuelve fuera. */
    private static final String DOMINIO = "camal.localhost";
    private static final String INICIO = "https://" + DOMINIO + "/www/index.html";

    private WebView vista;
    private long ultimoAtras = 0;

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(0xFF1A1E25);
            getWindow().setNavigationBarColor(0xFF1A1E25);
        }

        final WebViewAssetLoader cargador = new WebViewAssetLoader.Builder()
                .setDomain(DOMINIO)
                .addPathHandler("/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        vista = new WebView(this);
        vista.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        vista.setBackgroundColor(0xFF1A1E25);

        WebSettings ajustes = vista.getSettings();
        ajustes.setJavaScriptEnabled(true);
        ajustes.setDomStorageEnabled(true);          // sin esto no hay jornada guardada
        ajustes.setDatabaseEnabled(true);
        ajustes.setAllowFileAccess(false);           // no hace falta: todo va por el cargador
        ajustes.setAllowContentAccess(false);
        ajustes.setSupportZoom(false);
        ajustes.setMediaPlaybackRequiresUserGesture(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            // El contenido es local y va por https interno: no hay mezcla que permitir.
            ajustes.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }

        vista.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest peticion) {
                return cargador.shouldInterceptRequest(peticion.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest peticion) {
                // La app no tiene enlaces fuera. Si algún día los tiene, que no
                // se abran dentro del WebView haciéndose pasar por la app.
                return !DOMINIO.equals(peticion.getUrl().getHost());
            }
        });

        // El puente por el que salen el Excel y el acta. En un WebView una
        // descarga `blob:` no dispara nada —ni DownloadListener—, así que la
        // app web entrega los bytes por aquí y esto los escribe en Descargas.
        vista.addJavascriptInterface(new PuenteArchivos(this), "PuenteCamal");

        setContentView(vista);

        if (estado != null) {
            vista.restoreState(estado);
        } else {
            vista.loadUrl(INICIO);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle estado) {
        super.onSaveInstanceState(estado);
        vista.saveState(estado);
    }

    /**
     * El botón de atrás del teléfono navega dentro de la app, no la cierra.
     *
     * <p>La app web responde {@code atras()}: devuelve cierto si le quedaba
     * pantalla a la que volver. Cuando ya está en la jornada hace falta tocar
     * dos veces para salir — cerrar de un toque a media pesada sería perder el
     * hilo de lo que se está contando.
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
        if (vista != null) {
            ((ViewGroup) vista.getParent()).removeView(vista);
            vista.destroy();
            vista = null;
        }
        super.onDestroy();
    }
}
