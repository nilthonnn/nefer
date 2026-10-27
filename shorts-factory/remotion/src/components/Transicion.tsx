// Entrada de cada escena (0,27 s): deslizar, zoom o barrido. El cambio de
// plano en cada frase es lo que mantiene la atención en formato corto.
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const Transicion: React.FC<{ tipo: "deslizar" | "zoom" | "barrido"; activa: boolean; children: React.ReactNode }> = ({
  tipo, activa, children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = activa ? spring({ frame, fps, durationInFrames: Math.round(fps * 0.27), config: { damping: 200 } }) : 1;
  let estilo: React.CSSProperties = {};
  if (tipo === "deslizar") estilo = { transform: `translateY(${(1 - t) * 100}%)` };
  if (tipo === "zoom") estilo = { transform: `scale(${interpolate(t, [0, 1], [1.25, 1])})`, opacity: t };
  if (tipo === "barrido") estilo = { transform: `translateX(${(1 - t) * -100}%)`, filter: `blur(${(1 - t) * 18}px)` };
  return <AbsoluteFill style={estilo}>{children}</AbsoluteFill>;
};
