// Escena de contexto: indicador y país con una mini curva de fondo.
// (El texto hablado ya va en los subtítulos; aquí no se duplica.)
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { proyectar, trazo } from "../lib/geometria";
import type { Diseno, PropsShort } from "../schema";

export const Contexto: React.FC<{ serie: PropsShort["serie"]; diseno: Diseno }> = ({ serie, diseno }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const pts = proyectar(serie.puntos, 1080, 500);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 380, opacity: op }}>
      <svg width={1080} height={500} style={{ position: "absolute", top: 520, opacity: 0.25 }}>
        <path d={trazo(pts)} fill="none" stroke={diseno.colores.acento} strokeWidth={14} />
      </svg>
      <div style={{ fontSize: 44, letterSpacing: 6, textTransform: "uppercase", color: diseno.colores.acento }}>{serie.pais}</div>
      <div style={{ fontSize: 76, fontWeight: 900, textAlign: "center", padding: "0 70px", lineHeight: 1.1 }}>{serie.titulo}</div>
    </AbsoluteFill>
  );
};
