// Miniatura estática 1280×720: el dato más impactante a la izquierda, el
// título a la derecha y la fuente abajo. Un solo fotograma (`remotion still`).
import React from "react";
import { AbsoluteFill } from "remotion";
import { familia } from "./fuentes";
import type { PropsMiniatura } from "./schema";

export const Miniatura: React.FC<PropsMiniatura> = (p) => {
  const fuente = familia(p.tipografia);
  const c = p.colores;
  // Cifras largas ("1.234,5 %") se achican para no salirse del bloque.
  const tamanoCifra = p.cifra.length <= 5 ? 260 : p.cifra.length <= 8 ? 200 : 150;
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${c.fondo1} 0%, ${c.fondo2} 100%)`,
        color: c.texto,
        fontFamily: fuente,
        flexDirection: "row",
        alignItems: "center",
        padding: "0 70px",
        gap: 50,
      }}
    >
      <div style={{ flex: "0 0 48%", display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
        <div
          style={{
            fontSize: tamanoCifra,
            fontWeight: 900,
            lineHeight: 1,
            color: c.resaltado,
            textShadow: "0 10px 40px rgba(0,0,0,.45)",
            whiteSpace: "nowrap",
          }}
        >
          {p.cifra}
        </div>
        {p.contexto ? (
          <div style={{ marginTop: 24, fontSize: 38, fontWeight: 700, color: c.acento, lineHeight: 1.15 }}>{p.contexto}</div>
        ) : null}
      </div>
      <div style={{ flex: 1, fontSize: 64, fontWeight: 800, lineHeight: 1.08, textShadow: "0 6px 24px rgba(0,0,0,.4)" }}>
        {p.titulo}
      </div>
      <div style={{ position: "absolute", left: 70, bottom: 34, fontSize: 24, opacity: 0.75, fontFamily: "Inter, sans-serif" }}>
        {p.fuente}
      </div>
    </AbsoluteFill>
  );
};
