// Línea de tiempo horizontal: los hitos aparecen uno a uno, repartidos a lo
// largo de la duración de la escena para acompañar la narración.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { tema } from "../tema";

export type Hito = { anio: string; texto: string };
export type PropsLineaTiempo = { duracionSegundos: number; titulo: string; hitos: Hito[] };

export const LineaTiempo: React.FC<PropsLineaTiempo> = ({ titulo, hitos }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const n = Math.max(1, hitos.length);
  // Cada hito entra en su tramo; el último tramo se deja para contemplar.
  const tramo = (durationInFrames * 0.8) / n;
  const progresoLinea = interpolate(frame, [0, durationInFrames * 0.8], [0, 100], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: tema.fondo, fontFamily: tema.fuente, padding: "120px 120px" }}>
      <div style={{ color: tema.texto, fontSize: 72, fontWeight: 800 }}>{titulo}</div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 560, height: 6, background: tema.fondoSuave }}>
        <div style={{ width: `${progresoLinea}%`, height: "100%", background: tema.acento }} />
      </div>
      {hitos.map((h, i) => {
        const inicio = i * tramo;
        const op = interpolate(frame, [inicio, inicio + 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const izquierda = 120 + ((1920 - 240) / n) * i;
        const arriba = i % 2 === 0;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: izquierda,
              width: (1920 - 240) / n - 40,
              top: arriba ? 300 : 600,
              opacity: op,
              transform: `translateY(${(1 - op) * (arriba ? -30 : 30)}px)`,
            }}
          >
            <div style={{ color: tema.acento, fontSize: 64, fontWeight: 900 }}>{h.anio}</div>
            <div style={{ color: tema.texto, fontSize: 36, lineHeight: 1.25 }}>{h.texto}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
