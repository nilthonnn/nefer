// Tipografías empaquetadas con el proyecto (@fontsource, licencia OFL): el
// render no depende de la red ni de Google Fonts, y siempre usa el mismo
// archivo de fuente (resultados reproducibles). @remotion/fonts retrasa la
// captura de fotogramas hasta que la fuente está cargada.
import anton from "@fontsource/anton/files/anton-latin-400-normal.woff2";
import bebas from "@fontsource/bebas-neue/files/bebas-neue-latin-400-normal.woff2";
import inter from "@fontsource/inter/files/inter-latin-800-normal.woff2";
import montserrat from "@fontsource/montserrat/files/montserrat-latin-800-normal.woff2";
import oswald from "@fontsource/oswald/files/oswald-latin-700-normal.woff2";
import poppins from "@fontsource/poppins/files/poppins-latin-800-normal.woff2";
import { loadFont } from "@remotion/fonts";
import type { FUENTES } from "./schema";

type Fuente = (typeof FUENTES)[number];

const ARCHIVOS: Record<Fuente, { url: string; peso: string }> = {
  Inter: { url: inter, peso: "800" },
  Montserrat: { url: montserrat, peso: "800" },
  Anton: { url: anton, peso: "400" },
  BebasNeue: { url: bebas, peso: "400" },
  Poppins: { url: poppins, peso: "800" },
  Oswald: { url: oswald, peso: "700" },
};

const cargadas = new Set<Fuente>();

export function familia(f: Fuente): string {
  const nombre = `SF ${f}`;
  if (!cargadas.has(f)) {
    cargadas.add(f);
    loadFont({ family: nombre, url: ARCHIVOS[f].url, weight: ARCHIVOS[f].peso, format: "woff2" });
  }
  return `"${nombre}", "DejaVu Sans", sans-serif`;
}
