import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { esquemaShort, type PropsShort } from "./schema";
import { Short } from "./Short";

const ejemplo: PropsShort = {
  fps: 30,
  duracionFrames: 300,
  audio: "",
  fuente: "Fuente: Banco Mundial · FP.CPI.TOTL.ZG",
  diseno: {
    colores: { fondo1: "#0b1020", fondo2: "#1b2a4a", texto: "#ffffff", acento: "#4cc9f0", resaltado: "#ffd60a" },
    fuente: "Montserrat", estiloSubtitulos: "caja", mayusculas: true, posicionSubtitulos: 0.62,
    fondo: "orbitas", estiloGrafico: "linea", transicion: "zoom", intensidad: 0.06,
  },
  segmentos: [
    { desde: 0, hasta: 90, tipo: "cifra", texto: "", video: "" },
    { desde: 90, hasta: 210, tipo: "grafico", texto: "", video: "" },
    { desde: 210, hasta: 300, tipo: "texto", texto: "Y por eso", video: "" },
  ],
  serie: { titulo: "Inflación anual", pais: "Argentina", unidad: "%",
    puntos: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023].map((x, i) => ({ x, y: [26, 40, 25, 34, 53, 42, 48, 72, 133][i] })) },
  paginas: [{ desde: 0, hasta: 1.2, palabras: [{ texto: "133%", inicio: 0, fin: 0.6, enfasis: true }, { texto: "de", inicio: 0.6, fin: 1.1, enfasis: false }] }],
};

// La duración y los fps los manda Python en las props (dependen de la voz).
const metadatos: CalculateMetadataFunction<PropsShort> = ({ props }) => ({
  durationInFrames: props.duracionFrames,
  fps: props.fps,
});

export const Raiz: React.FC = () => (
  <Composition
    id="Short"
    component={Short}
    schema={esquemaShort}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={ejemplo}
    calculateMetadata={metadatos}
  />
);
