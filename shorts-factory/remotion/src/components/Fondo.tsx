// Fondos generativos PERIÓDICOS: el último fotograma es idéntico al primero,
// así el loop automático del Short no tiene salto visual.
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { fase } from "../lib/geometria";
import type { Diseno } from "../schema";

export const Fondo: React.FC<{ diseno: Diseno }> = ({ diseno }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const a = fase(frame, durationInFrames);
  const { fondo1, fondo2, acento } = diseno.colores;
  if (diseno.fondo === "degradado") {
    const ang = 160 + Math.sin(a) * 25;
    return <AbsoluteFill style={{ background: `linear-gradient(${ang}deg, ${fondo1} 10%, ${fondo2} 90%)` }} />;
  }
  if (diseno.fondo === "reticula") {
    const paso = 90;
    const desp = ((frame / durationInFrames) * paso * 2) % paso; // 2 celdas por vuelta: periódico
    return (
      <AbsoluteFill style={{ background: fondo1 }}>
        <AbsoluteFill
          style={{
            backgroundImage: `linear-gradient(${fondo2} 2px, transparent 2px), linear-gradient(90deg, ${fondo2} 2px, transparent 2px)`,
            backgroundSize: `${paso}px ${paso}px`,
            backgroundPosition: `0 ${desp}px`,
            opacity: 0.7,
          }}
        />
        <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 40%, transparent 30%, ${fondo1} 85%)` }} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: fondo1, overflow: "hidden" }}>
      {[0, 1, 2].map((i) => {
        const r = 420 + i * 120;
        const x = width / 2 + Math.cos(a + (i * Math.PI * 2) / 3) * 260 - r / 2;
        const y = height * 0.42 + Math.sin(a + (i * Math.PI * 2) / 3) * 360 - r / 2;
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: r, height: r, borderRadius: "50%",
            background: i === 1 ? acento : fondo2, opacity: i === 1 ? 0.18 : 0.55, filter: "blur(90px)" }} />
        );
      })}
    </AbsoluteFill>
  );
};
