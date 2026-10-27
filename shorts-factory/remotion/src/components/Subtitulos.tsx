// Subtítulos cinéticos: 1–3 palabras, palabra activa resaltada (caja, pop o
// subrayado) y palabras de énfasis en color de acento.
import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { palabraActiva } from "../lib/geometria";
import type { Diseno, PropsShort } from "../schema";

export const Subtitulos: React.FC<{ paginas: PropsShort["paginas"]; diseno: Diseno }> = ({ paginas, diseno }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const t = frame / fps;
  const pagina = paginas.find((p) => t >= p.desde && t < p.hasta);
  if (!pagina) return null;
  const activa = palabraActiva(pagina.palabras, t);
  const entrada = spring({ frame: frame - Math.round(pagina.desde * fps), fps, durationInFrames: 5, config: { damping: 14 } });
  const { texto, acento, resaltado, fondo1 } = diseno.colores;
  const tam = pagina.palabras.length >= 3 ? 84 : 104;
  return (
    <AbsoluteFill style={{ top: height * diseno.posicionSubtitulos, height: "auto", alignItems: "center" }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px 22px", padding: "0 70px",
        transform: `scale(${0.85 + 0.15 * entrada})` }}>
        {pagina.palabras.map((w, i) => {
          const esActiva = i === activa;
          const color = esActiva && diseno.estiloSubtitulos !== "caja" ? resaltado : w.enfasis ? acento : texto;
          const estilo: React.CSSProperties = {
            fontSize: tam, fontWeight: 900, lineHeight: 1.05, color,
            textTransform: diseno.mayusculas ? "uppercase" : "none",
            WebkitTextStroke: "3px rgba(0,0,0,.55)", paintOrder: "stroke fill",
            textShadow: "0 6px 24px rgba(0,0,0,.45)", padding: "4px 16px", borderRadius: 14,
            display: "inline-block",
          };
          if (esActiva && diseno.estiloSubtitulos === "caja") Object.assign(estilo, { background: resaltado, color: fondo1, WebkitTextStroke: "0" });
          if (esActiva && diseno.estiloSubtitulos === "pop") estilo.transform = "scale(1.15) rotate(-2deg)";
          if (esActiva && diseno.estiloSubtitulos === "subrayado") estilo.boxShadow = `inset 0 -16px 0 ${acento}`;
          return <span key={i} style={estilo}>{w.texto}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};
