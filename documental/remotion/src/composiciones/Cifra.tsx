// Cifra protagonista que cuenta desde cero, con etiqueta y fuente al pie.
// La fuente es obligatoria en la práctica: un dato sin respaldo resta
// credibilidad y YouTube premia el contenido que aporta valor verificable.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { tema } from "../tema";

export type PropsCifra = {
  duracionSegundos: number;
  valor: number;
  prefijo: string;
  sufijo: string;
  decimales: number;
  etiqueta: string;
  fuente: string;
};

export const Cifra: React.FC<PropsCifra> = ({ valor, prefijo, sufijo, decimales, etiqueta, fuente }) => {
  const frame = useCurrentFrame();
  const avance = interpolate(frame, [0, 45], [0, 1], { extrapolateRight: "clamp" });
  // Curva de salida suave: el contador frena al llegar al valor final.
  const suave = 1 - Math.pow(1 - avance, 3);
  const numero = (valor * suave).toLocaleString("es-419", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
  return (
    <AbsoluteFill
      style={{ background: tema.fondo, fontFamily: tema.fuente, alignItems: "center", justifyContent: "center" }}
    >
      <div style={{ color: tema.acento, fontSize: 260, fontWeight: 900, letterSpacing: -6 }}>
        {prefijo}
        {numero}
        {sufijo}
      </div>
      <div
        style={{
          color: tema.texto,
          fontSize: 58,
          maxWidth: 1400,
          textAlign: "center",
          opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        {etiqueta}
      </div>
      {fuente ? (
        <div style={{ position: "absolute", bottom: 60, right: 80, color: tema.textoTenue, fontSize: 30 }}>
          Fuente: {fuente}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
