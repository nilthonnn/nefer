// Registro de composiciones. Cada una recibe sus datos por --props (JSON) desde
// documental/visuales/remotion.py; la duración llega en `duracionSegundos` y se
// aplica con calculateMetadata para que la escena dure exactamente lo que la voz.
import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { Cifra, PropsCifra } from "./composiciones/Cifra";
import { Comparativa, PropsComparativa } from "./composiciones/Comparativa";
import { PantallaFinal, PropsPantallaFinal } from "./composiciones/PantallaFinal";
import { LineaTiempo, PropsLineaTiempo } from "./composiciones/LineaTiempo";
import { Titular, PropsTitular } from "./composiciones/Titular";
import { fotogramas } from "./tema";

const FPS = 30;
const ANCHO = 1920;
const ALTO = 1080;

type ConDuracion = { duracionSegundos: number };

// Genérica para que cada composición conserve el tipo exacto de sus props.
function metadatos<P extends ConDuracion>(): CalculateMetadataFunction<P> {
  return ({ props }) => ({ durationInFrames: fotogramas(props.duracionSegundos, FPS) });
}

export const Raiz: React.FC = () => (
  <>
    <Composition
      id="Titular"
      component={Titular}
      fps={FPS}
      width={ANCHO}
      height={ALTO}
      durationInFrames={150}
      defaultProps={{ duracionSegundos: 5, antetitulo: "Capítulo 1", titulo: "La batería que cambió todo" } as PropsTitular}
      calculateMetadata={metadatos<PropsTitular>()}
    />
    <Composition
      id="Cifra"
      component={Cifra}
      fps={FPS}
      width={ANCHO}
      height={ALTO}
      durationInFrames={150}
      defaultProps={{ duracionSegundos: 5, valor: 89, prefijo: "", sufijo: " %", decimales: 0, etiqueta: "cayó el precio del panel solar desde 2010", fuente: "IRENA" } as PropsCifra}
      calculateMetadata={metadatos<PropsCifra>()}
    />
    <Composition
      id="LineaTiempo"
      component={LineaTiempo}
      fps={FPS}
      width={ANCHO}
      height={ALTO}
      durationInFrames={240}
      defaultProps={{
        duracionSegundos: 8,
        titulo: "De Bell Labs a tu techo",
        hitos: [
          { anio: "1839", texto: "Becquerel descubre el efecto fotovoltaico" },
          { anio: "1954", texto: "Bell Labs presenta la primera celda de silicio" },
          { anio: "1958", texto: "El satélite Vanguard I vuela con paneles" },
        ],
      } as PropsLineaTiempo}
      calculateMetadata={metadatos<PropsLineaTiempo>()}
    />
    <Composition
      id="Comparativa"
      component={Comparativa}
      fps={FPS}
      width={ANCHO}
      height={ALTO}
      durationInFrames={210}
      defaultProps={{
        duracionSegundos: 7,
        titulo: "Costo por kWh almacenado",
        unidad: "USD",
        barras: [
          { etiqueta: "Plomo-ácido", valor: 150 },
          { etiqueta: "Litio LFP", valor: 90 },
        ],
        fuente: "",
      } as PropsComparativa}
      calculateMetadata={metadatos<PropsComparativa>()}
    />
    <Composition
      id="PantallaFinal"
      component={PantallaFinal}
      fps={FPS}
      width={ANCHO}
      height={ALTO}
      durationInFrames={600}
      defaultProps={{ duracionSegundos: 20, mensaje: "¿Seguimos investigando?", canal: "" } as PropsPantallaFinal}
      calculateMetadata={metadatos<PropsPantallaFinal>()}
    />
  </>
);
