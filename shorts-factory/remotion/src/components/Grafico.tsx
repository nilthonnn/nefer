// Gráfico animado con la serie REAL: línea que se dibuja o barras que crecen.
// Marca el primer y el último valor: es el "antes y después" del guion.
// Todo el gráfico cabe por encima del 52 % de la altura: debajo van los
// subtítulos (su posición mínima es el 55 %) y nunca se tapan.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { formatear, longitud, proyectar, trazo } from "../lib/geometria";
import type { Diseno, PropsShort } from "../schema";

export const Grafico: React.FC<{ serie: PropsShort["serie"]; diseno: Diseno }> = ({ serie, diseno }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const W = 900, H = 560;
  const avance = interpolate(frame, [4, Math.max(8, durationInFrames * 0.75)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pts = proyectar(serie.puntos, W, H);
  const { acento, texto, resaltado } = diseno.colores;
  const primero = serie.puntos[0], ultimo = serie.puntos[serie.puntos.length - 1];
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 170 }}>
      <div style={{ fontSize: 50, fontWeight: 800, marginBottom: 24, textAlign: "center", padding: "0 60px", lineHeight: 1.1 }}>
        {serie.titulo} · {serie.pais}
      </div>
      <svg width={W} height={H + 80} viewBox={`-20 -40 ${W + 40} ${H + 80}`} style={{ overflow: "visible" }}>
        {diseno.estiloGrafico === "linea" ? (
          <>
            <path d={`${trazo(pts)} L${W},${H} L0,${H} Z`} fill={acento} opacity={0.15 * avance} />
            <path d={trazo(pts)} fill="none" stroke={acento} strokeWidth={10} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray={longitud(pts)} strokeDashoffset={longitud(pts) * (1 - avance)} />
          </>
        ) : (
          pts.map((p, i) => {
            const crece = interpolate(avance * pts.length - i, [0, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const ancho = (W / pts.length) * 0.7;
            return <rect key={i} x={p.x - ancho / 2} y={H - (H - p.y) * crece} width={ancho} height={(H - p.y) * crece}
              rx={6} fill={i === pts.length - 1 ? resaltado : acento} />;
          })
        )}
        <text x={0} y={H + 60} fill={texto} fontSize={40} opacity={0.8}>{primero.x}</text>
        <text x={W} y={H + 60} fill={texto} fontSize={40} opacity={0.8} textAnchor="end">{ultimo.x}</text>
        <text x={pts[0].x} y={pts[0].y - 26} fill={texto} fontSize={48} fontWeight={800}>{formatear(primero.y, serie.unidad)}</text>
        <text x={W} y={pts[pts.length - 1].y - 26} fill={resaltado} fontSize={64} fontWeight={900} textAnchor="end"
          opacity={avance > 0.9 ? 1 : 0}>{formatear(ultimo.y, serie.unidad)}</text>
      </svg>
    </AbsoluteFill>
  );
};
