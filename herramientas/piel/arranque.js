/* Lo que hace cada pantalla al abrirse, antes de pintar nada. Todo depende de
 * CÓMO llegó la pantalla al aparato, que son tres formas distintas:
 *
 *   - servida por el sitio, en un navegador;
 *   - como archivo suelto, bajado por WhatsApp (`file:`);
 *   - dentro del APK, servida por el cargador de assets de Android, que
 *     también habla https pero no tiene ni red ni carpetas hermanas.
 *
 * La tercera engaña: el protocolo dice `https` y parece el sitio. Se reconoce
 * por el puente nativo, que sólo existe ahí dentro.
 */
var EN_APK = typeof window.PuenteFixMate !== "undefined" && !!window.PuenteFixMate;

/* 1. Los enlaces entre herramientas sólo sirven si se abrió desde el sitio.
 *    Descargada como archivo suelto —que es como viaja por WhatsApp—
 *    apuntarían a carpetas que no existen en ese teléfono, y un enlace roto
 *    en la barra hace dudar del resto de la pantalla. Se quitan. */
/*    Dentro del APK pasa lo mismo por otro motivo: lo único que viaja es
 *    esta pantalla, así que las carpetas hermanas tampoco están. */
if (location.protocol === "file:" || EN_APK) {
  var vinculos = document.querySelector(".barra .vinculos");
  if (vinculos) vinculos.remove();
}

/* 2. Servida por http(s), se guarda en el teléfono para que abra sin señal.
 *    Es la condición de trabajo real: interior mina, sin cobertura, y el
 *    turno no espera a que haya línea. Si el navegador no lo permite —modo
 *    privado, versión vieja—, la pantalla sigue funcionando igual: el
 *    trabajador de servicio es una mejora, no un requisito. */
/*    Dentro del APK no se registra: los archivos ya son locales, no hay nada
 *    que guardar, y como sus peticiones no pasan por el cargador de assets
 *    intentaría salir a una red que la app no tiene permiso de usar. */
if (!EN_APK && "serviceWorker" in navigator &&
    location.protocol.indexOf("http") === 0) {
  navigator.serviceWorker.register("sw.js").catch(function () {
    /* Sin registro no hay copia local, y ya está: no se le dice nada al
       operador, porque no hay nada que pueda hacer al respecto. */
  });
}

/* 3. El botón de instalar, cuando el aparato lo ofrece.
 *
 *    Android avisa por su cuenta con un cartel discreto que casi nadie ve, y
 *    la otra vía es el menú de tres puntos del navegador: el operador no va
 *    a dar con eso, y sin instalar no hay copia local ni pantalla completa.
 *    Así que cuando Chrome dice que se puede, aparece el botón en la barra.
 *
 *    No se dibuja si el aparato no lo ofrece —ya instalada, en un navegador
 *    que no lo soporta, o en un escritorio—: un botón que no hace nada es
 *    peor que ninguno. */
window.addEventListener("beforeinstallprompt", function (e) {
  e.preventDefault();
  var barra = document.querySelector(".barra");
  if (!barra || document.getElementById("instalar")) return;
  var boton = document.createElement("button");
  boton.id = "instalar";
  boton.className = "instalar";
  boton.textContent = "Instalar";
  boton.onclick = function () {
    boton.disabled = true;
    if (e.prompt) e.prompt();
  };
  barra.appendChild(boton);
});

window.addEventListener("appinstalled", function () {
  var boton = document.getElementById("instalar");
  if (boton) boton.remove();
});
