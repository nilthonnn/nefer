// Barras horizontales que crecen: compara costos, potencias, rendimientos...
// La barra más larga se pinta en verde para guiar la mirada al dato clave.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { tema } from "../tema";

export type Barra = { etiqueta: string; valor: number };
export type PropsComparativa = {
  duracionSegundos: number;
  titulo: string;
  unidad: string;
  barras: Barra[];
  fuente: string;
};

export const Comparativa: React.FC<PropsComparativa> = ({ titulo, unidad, barras, fuente }) => {
  const frame = useCurrentFrame();
  const maximo = Math.max(1, ...barras.map((b) => b.valor));
  const ANCHO_MAX = 1100;
  return (
    <AbsoluteFill style={{ background: tema.fondo, fontFamily: tema.fuente, padding: 120 }}>
      <div style={{ color: tema.texto, fontSize: 72, fontWeight: 800, marginBottom: 80 }}>{titulo}</div>
      {barras.map((b, i) => {
        const crece = interpolate(frame, [10 + i * 12, 50 + i * 12], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const esMayor = b.valor === maximo;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", marginBottom: 44 }}>
            <div style={{ width: 420, color: tema.texto, fontSize: 44 }}>{b.etiqueta}</div>
            <div
              style={{
                height: 72,
                width: (b.valor / maximo) * ANCHO_MAX * crece,
                background: esMayor ? tema.acento2 : tema.acento,
                borderRadius: 8,
              }}
            />
            <div style={{ color: tema.texto, fontSize: 44, fontWeight: 700, marginLeft: 24, opacity: crece }}>
              {Math.round(b.valor * crece).toLocaleString("es-419")} {unidad}
            </div>
          </div>
        );
      })}
      {fuente ? (
        <div style={{ position: "absolute", bottom: 60, right: 80, color: tema.textoTenue, fontSize: 30 }}>
          Fuente: {fuente}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
