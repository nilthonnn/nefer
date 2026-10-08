# El puente se llama desde JavaScript por reflexion: si el ofuscador le cambia
# el nombre a un metodo, el boton de guardar deja de hacer nada y no hay error
# en ninguna parte. Hoy `minifyEnabled` esta en false y esto no se aplica;
# queda escrito para el dia que alguien lo encienda.
-keepclassmembers class pe.fixmate.ronda.PuenteArchivos {
    @android.webkit.JavascriptInterface <methods>;
}
