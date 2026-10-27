// Pantalla final de YouTube (5–20 s). Deja libres los huecos donde YouTube
// coloca los elementos de pantalla final (video sugerido a la izquierda,
// botón de suscripción a la derecha) y solo dibuja el llamado a la acción.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { tema } from "../tema";

export type PropsPantallaFinal = { duracionSegundos: number; mensaje: string; canal: string };

export const PantallaFinal: React.FC<PropsPantallaFinal> = ({ mensaje, canal }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const hueco = { width: 760, height: 428, border: `3px dashed ${tema.fondoSuave}`, borderRadius: 16 };
  return (
    <AbsoluteFill style={{ background: tema.fondo, fontFamily: tema.fuente, opacity: op }}>
      <div style={{ textAlign: "center", marginTop: 110, color: tema.texto, fontSize: 70, fontWeight: 800 }}>
        {mensaje}
      </div>
      <div style={{ textAlign: "center", color: tema.acento, fontSize: 40, marginTop: 16 }}>{canal}</div>
      <div style={{ position: "absolute", top: 420, left: 160, ...hueco }} />
      <div
        style={{
          position: "absolute",
          top: 520,
          right: 300,
          width: 240,
          height: 240,
          borderRadius: "50%",
          border: `3px dashed ${tema.fondoSuave}`,
        }}
      />
    </AbsoluteFill>
  );
};
