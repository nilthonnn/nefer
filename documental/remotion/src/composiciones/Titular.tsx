// Tarjeta de capítulo: antetítulo pequeño en ámbar y título grande que sube.
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { tema } from "../tema";

export type PropsTitular = { duracionSegundos: number; antetitulo: string; titulo: string };

export const Titular: React.FC<PropsTitular> = ({ antetitulo, titulo }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const entrada = spring({ frame, fps, config: { damping: 200 } });
  const salida = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const linea = interpolate(frame, [8, 30], [0, 260], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 30% 40%, ${tema.fondoSuave}, ${tema.fondo})`,
        fontFamily: tema.fuente,
        justifyContent: "center",
        padding: "0 160px",
        opacity: salida,
      }}
    >
      <div style={{ color: tema.acento, fontSize: 44, letterSpacing: 8, textTransform: "uppercase", opacity: entrada }}>
        {antetitulo}
      </div>
      <div style={{ height: 6, width: linea, background: tema.acento, margin: "28px 0" }} />
      <div
        style={{
          color: tema.texto,
          fontSize: 110,
          fontWeight: 800,
          lineHeight: 1.05,
          transform: `translateY(${(1 - entrada) * 60}px)`,
          opacity: entrada,
        }}
      >
        {titulo}
      </div>
    </AbsoluteFill>
  );
};
