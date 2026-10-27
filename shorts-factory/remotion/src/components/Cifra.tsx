// La cifra protagonista (último dato) contando desde cero.
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { formatear } from "../lib/geometria";
import type { Diseno, PropsShort } from "../schema";

export const Cifra: React.FC<{ serie: PropsShort["serie"]; diseno: Diseno }> = ({ serie, diseno }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ultimo = serie.puntos[serie.puntos.length - 1];
  const t = interpolate(frame, [0, fps * 0.8], [0, 1], { extrapolateRight: "clamp" });
  const suave = 1 - Math.pow(1 - t, 3);
  const pop = spring({ frame, fps, config: { damping: 12 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 380 }}>
      <div style={{ fontSize: 230, fontWeight: 900, color: diseno.colores.resaltado, transform: `scale(${0.8 + 0.2 * pop})`,
        textShadow: "0 8px 40px rgba(0,0,0,.35)" }}>
        {formatear(ultimo.y * suave, serie.unidad)}
      </div>
      <div style={{ fontSize: 50, fontWeight: 700, textAlign: "center", padding: "0 80px", opacity: t }}>
        {serie.titulo} · {serie.pais} · {ultimo.x}
      </div>
    </AbsoluteFill>
  );
};
