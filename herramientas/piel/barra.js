/* Los enlaces entre herramientas sólo sirven si la pantalla se abrió desde
 * el sitio. Descargada como archivo suelto —que es como viaja por WhatsApp—
 * apuntarían a carpetas que no existen en ese teléfono, y un enlace roto en
 * la barra hace dudar del resto de la pantalla. Se quitan. */
if (location.protocol === "file:") {
  var vinculos = document.querySelector(".barra .vinculos");
  if (vinculos) vinculos.remove();
}
