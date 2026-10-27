// Paleta y tipografía compartidas por todas las escenas animadas.
// Se mantienen aquí, no en cada composición, para que el canal tenga una
// sola identidad visual reconocible de un video a otro.
export const tema = {
  fondo: "#0b1117",
  fondoSuave: "#141c25",
  texto: "#f2f4f5",
  textoTenue: "#9aa7b3",
  acento: "#f5b301", // ámbar solar
  acento2: "#2ec27e", // verde renovable
  fuente: "Inter, 'DejaVu Sans', sans-serif",
};

// Duración en fotogramas a partir de los segundos que manda Python.
export const fotogramas = (segundos: number, fps: number): number =>
  Math.max(1, Math.round(segundos * fps));
