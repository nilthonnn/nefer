package pe.rdrental.actas;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.ViewGroup;
import android.webkit.ConsoleMessage;
import android.webkit.PermissionRequest;
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
 * La aplicacion entera es la misma app web que se publica: esta clase solo la
 * pone en pantalla.
 *
 * Lo que aporta el contenedor, y que el navegador no puede dar, es esto:
 *
 *  1. Los archivos van dentro del .apk y se sirven como `https://` —no como
 *     `file://`—, y por eso el telefono concede la camara. Es lo que hace
 *     WebViewAssetLoader, y es la razon de ser de este contenedor.
 *  2. El PDF, el Excel y el .zip se escriben en Descargas de verdad, por el
 *     puente {@link Anfitrion}. Un WebView no descarga solo lo que la pagina
 *     genera en memoria.
 *  3. No pide permiso de INTERNET: la app no puede salir a la red aunque se
 *     lo propusiera.
 */
public class MainActivity extends Activity {

  /** No existe en el DNS: solo la resuelve el cargador de assets de aqui. */
  static final String DOMINIO = "actas.rdrental.local";
  static final String INICIO = "https://" + DOMINIO + "/app/index.html";
  private static final String ETIQUETA = "ActasRD";

  private static final int PIDE_CAMARA = 71;
  private static final int PIDE_ESCRITURA = 72;
  private static final int ELIGE_ARCHIVO = 73;

  private WebView vista;
  private WebViewAssetLoader cargador;
  private PermissionRequest permisoWebPendiente;
  private ValueCallback<Uri[]> respuestaArchivos;

  @Override
  protected void onCreate(Bundle guardado) {
    super.onCreate(guardado);

    cargador = new WebViewAssetLoader.Builder()
        .setDomain(DOMINIO)
        .setHttpAllowed(false)
        .addPathHandler("/app/", new WebViewAssetLoader.AssetsPathHandler(this))
        .build();

    vista = new WebView(this);
    vista.setLayoutParams(new ViewGroup.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    vista.setBackgroundColor(getColor(R.color.fondo));
    setContentView(vista);

    WebSettings ajustes = vista.getSettings();
    ajustes.setJavaScriptEnabled(true);
    ajustes.setDomStorageEnabled(true);
    ajustes.setDatabaseEnabled(true);
    // La vista previa de la camara es un <video autoplay>: sin esto no arranca
    // hasta que alguien lo toca, y el operario ve un rectangulo negro.
    ajustes.setMediaPlaybackRequiresUserGesture(false);
    // Nada de leer el disco del telefono: todo lo que la app necesita esta
    // dentro del .apk y se sirve por el cargador de assets.
    ajustes.setAllowFileAccess(false);
    ajustes.setAllowContentAccess(false);
    ajustes.setSupportZoom(false);
    ajustes.setBuiltInZoomControls(false);
    ajustes.setDisplayZoomControls(false);
    // El acta esta medida en pixeles: si el telefono trae la letra en grande,
    // las casillas de foto dejan de cuadrar con el formato.
    ajustes.setTextZoom(100);
    ajustes.setUserAgentString(
        ajustes.getUserAgentString() + " ActasRDRental/" + BuildConfig.VERSION_NAME);

    vista.setWebViewClient(new WebViewClient() {
      @Override
      public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest peticion) {
        return cargador.shouldInterceptRequest(peticion.getUrl());
      }

      @Override
      public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest peticion) {
        Uri destino = peticion.getUrl();
        if (DOMINIO.equals(destino.getHost())) {
          return false;
        }
        // Un enlace a fuera —un manual, una direccion de correo— sale al
        // navegador del telefono; dentro de la app no entra nada de la red.
        try {
          startActivity(new Intent(Intent.ACTION_VIEW, destino));
        } catch (Exception e) {
          Log.w(ETIQUETA, "sin aplicacion para " + destino, e);
        }
        return true;
      }
    });

    vista.setWebChromeClient(new WebChromeClient() {
      @Override
      public void onPermissionRequest(final PermissionRequest peticion) {
        runOnUiThread(new Runnable() {
          @Override public void run() { resolverPermisoWeb(peticion); }
        });
      }

      @Override
      public void onPermissionRequestCanceled(PermissionRequest peticion) {
        if (permisoWebPendiente == peticion) {
          permisoWebPendiente = null;
        }
      }

      @Override
      public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> respuesta,
                                       FileChooserParams parametros) {
        if (respuestaArchivos != null) {
          respuestaArchivos.onReceiveValue(null);
        }
        respuestaArchivos = respuesta;
        try {
          startActivityForResult(parametros.createIntent(), ELIGE_ARCHIVO);
          return true;
        } catch (Exception e) {
          respuestaArchivos = null;
          Log.w(ETIQUETA, "no hay selector de archivos", e);
          return false;
        }
      }

      @Override
      public boolean onConsoleMessage(ConsoleMessage mensaje) {
        Log.d(ETIQUETA, mensaje.message() + " (" + mensaje.lineNumber() + ")");
        return true;
      }
    });

    vista.addJavascriptInterface(new Anfitrion(this), "Anfitrion");

    // Hasta Android 9 escribir en Descargas exige permiso, y pedirlo en mitad
    // de una exportacion deja el archivo a medias. Se pide al abrir.
    if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P
        && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
           != PackageManager.PERMISSION_GRANTED) {
      requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE},
                         PIDE_ESCRITURA);
    }

    if (guardado != null) {
      vista.restoreState(guardado);
    } else {
      vista.loadUrl(INICIO);
    }
  }

  /**
   * La pagina pide la camara. Se le concede si la aplicacion ya tiene el
   * permiso del sistema; si no, se pide primero y se contesta despues.
   */
  private void resolverPermisoWeb(PermissionRequest peticion) {
    boolean quiereCamara = false;
    for (String recurso : peticion.getResources()) {
      if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(recurso)) {
        quiereCamara = true;
      }
    }
    // Micrófono, ubicacion, MIDI: nada de eso hace falta para levantar un acta.
    if (!quiereCamara) {
      peticion.deny();
      return;
    }
    if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
      peticion.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
      return;
    }
    permisoWebPendiente = peticion;
    requestPermissions(new String[]{Manifest.permission.CAMERA}, PIDE_CAMARA);
  }

  @Override
  public void onRequestPermissionsResult(int codigo, String[] permisos, int[] resultados) {
    if (codigo == PIDE_CAMARA) {
      PermissionRequest peticion = permisoWebPendiente;
      permisoWebPendiente = null;
      if (peticion == null) {
        return;
      }
      boolean concedido = resultados.length > 0
          && resultados[0] == PackageManager.PERMISSION_GRANTED;
      if (concedido) {
        peticion.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
      } else {
        peticion.deny();
        Toast.makeText(this, R.string.sin_permiso_camara, Toast.LENGTH_LONG).show();
      }
      return;
    }
    if (codigo == PIDE_ESCRITURA) {
      return;
    }
    super.onRequestPermissionsResult(codigo, permisos, resultados);
  }

  @Override
  protected void onActivityResult(int codigo, int resultado, Intent datos) {
    if (codigo == ELIGE_ARCHIVO) {
      if (respuestaArchivos != null) {
        respuestaArchivos.onReceiveValue(
            WebChromeClient.FileChooserParams.parseResult(resultado, datos));
        respuestaArchivos = null;
      }
      return;
    }
    super.onActivityResult(codigo, resultado, datos);
  }

  @Override
  public void onBackPressed() {
    if (vista != null && vista.canGoBack()) {
      vista.goBack();
      return;
    }
    // Un acta a medias no se pierde por un toque de mas en «atras»: la app se
    // va al fondo, con su estado intacto, en vez de cerrarse.
    moveTaskToBack(true);
  }

  @Override
  protected void onSaveInstanceState(Bundle estado) {
    super.onSaveInstanceState(estado);
    if (vista != null) {
      vista.saveState(estado);
    }
  }

  @Override protected void onPause() { if (vista != null) vista.onPause(); super.onPause(); }
  @Override protected void onResume() { super.onResume(); if (vista != null) vista.onResume(); }

  @Override
  protected void onDestroy() {
    if (vista != null) {
      vista.destroy();
      vista = null;
    }
    super.onDestroy();
  }
}
