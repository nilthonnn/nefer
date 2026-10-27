// Clip de stock con movimiento de cámara (Ken Burns) y oscurecido para que
// los subtítulos siempre se lean.
import React from "react";
import { AbsoluteFill, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { Diseno } from "../schema";

export const BRoll: React.FC<{ video: string; diseno: Diseno }> = ({ video, diseno }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const k = interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateRight: "clamp" });
  const escala = 1 + diseno.intensidad * k;
  const pan = (diseno.intensidad * 400) * (k - 0.5);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${escala}) translateX(${pan}px)` }}>
        <OffthreadVideo src={staticFile(video)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${diseno.colores.fondo1}55 0%, ${diseno.colores.fondo1}aa 100%)` }} />
    </AbsoluteFill>
  );
};
