// Composición vertical completa: fondo en loop + escenas por frase + subtítulos + voz.
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { BRoll } from "./components/BRoll";
import { Cifra } from "./components/Cifra";
import { Contexto } from "./components/Contexto";
import { Fondo } from "./components/Fondo";
import { Grafico } from "./components/Grafico";
import { Subtitulos } from "./components/Subtitulos";
import { Transicion } from "./components/Transicion";
import { familia } from "./fuentes";
import type { PropsShort } from "./schema";

export const Short: React.FC<PropsShort> = (p) => {
  const fuente = familia(p.diseno.fuente);
  return (
    <AbsoluteFill style={{ fontFamily: fuente, color: p.diseno.colores.texto }}>
      <Fondo diseno={p.diseno} />
      {p.segmentos.map((s, i) => (
        <Sequence key={i} from={s.desde} durationInFrames={Math.max(1, s.hasta - s.desde)} layout="none">
          <Transicion tipo={p.diseno.transicion} activa={i > 0}>
            {s.tipo === "broll" ? <BRoll video={s.video} diseno={p.diseno} /> : null}
            {s.tipo === "grafico" ? <Grafico serie={p.serie} diseno={p.diseno} /> : null}
            {s.tipo === "cifra" ? <Cifra serie={p.serie} diseno={p.diseno} /> : null}
            {s.tipo === "texto" ? <Contexto serie={p.serie} diseno={p.diseno} /> : null}
          </Transicion>
        </Sequence>
      ))}
      <Subtitulos paginas={p.paginas} diseno={p.diseno} />
      <div style={{ position: "absolute", top: 70, left: 60, fontSize: 30, opacity: 0.75, fontFamily: "Inter, sans-serif" }}>
        {p.fuente}
      </div>
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};
