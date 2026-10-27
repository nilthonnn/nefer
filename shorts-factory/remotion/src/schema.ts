// Configuración tipada del render (equivalente TypeScript de settings.py).
// Python construye estas props; Zod las valida antes de dibujar un solo
// fotograma, así un error de datos falla con un mensaje claro y no con un
// video roto.
import { z } from "zod";

const color = z.string().regex(/^#[0-9a-fA-F]{6}$/, "color hexadecimal #rrggbb");

export const FUENTES = ["Inter", "Montserrat", "Anton", "BebasNeue", "Poppins", "Oswald"] as const;

export const esquemaDiseno = z.object({
  colores: z.object({ fondo1: color, fondo2: color, texto: color, acento: color, resaltado: color }),
  fuente: z.enum(FUENTES),
  estiloSubtitulos: z.enum(["caja", "pop", "subrayado"]),
  mayusculas: z.boolean(),
  posicionSubtitulos: z.number().min(0.45).max(0.8),
  fondo: z.enum(["degradado", "reticula", "orbitas"]),
  estiloGrafico: z.enum(["linea", "barras"]),
  transicion: z.enum(["deslizar", "zoom", "barrido"]),
  intensidad: z.number().min(0.03).max(0.12),
});

export const esquemaPalabra = z.object({
  texto: z.string().min(1),
  inicio: z.number().min(0),
  fin: z.number().min(0),
  enfasis: z.boolean(),
});

export const esquemaShort = z
  .object({
    fps: z.union([z.literal(30), z.literal(60)]),
    duracionFrames: z.number().int().positive(),
    audio: z.string(),
    diseno: esquemaDiseno,
    segmentos: z
      .array(
        z.object({
          desde: z.number().int().min(0),
          hasta: z.number().int().positive(),
          tipo: z.enum(["broll", "grafico", "cifra", "texto"]),
          texto: z.string(),
          video: z.string(),
        }),
      )
      .min(1),
    serie: z.object({
      titulo: z.string(),
      pais: z.string(),
      unidad: z.string(),
      puntos: z.array(z.object({ x: z.number(), y: z.number() })).min(2),
    }),
    paginas: z.array(
      z.object({ desde: z.number(), hasta: z.number(), palabras: z.array(esquemaPalabra).min(1) }),
    ),
    fuente: z.string(),
  })
  .superRefine((p, ctx) => {
    p.segmentos.forEach((s, i) => {
      if (s.hasta <= s.desde) ctx.addIssue({ code: "custom", message: `segmento ${i}: hasta <= desde` });
      if (s.tipo === "broll" && !s.video) ctx.addIssue({ code: "custom", message: `segmento ${i}: broll sin video` });
    });
  });

export type PropsShort = z.infer<typeof esquemaShort>;
export type Diseno = z.infer<typeof esquemaDiseno>;
export type Palabra = z.infer<typeof esquemaPalabra>;
