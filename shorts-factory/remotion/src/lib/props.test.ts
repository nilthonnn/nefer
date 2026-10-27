// Pruebas de lógica pura con node (sin navegador): npm test
import assert from "node:assert/strict";
import { fase, formatear, palabraActiva, proyectar, trazo } from "./geometria.ts";
import { esquemaShort } from "../schema.ts";

const pts = proyectar([{ x: 2000, y: 1 }, { x: 2010, y: 3 }, { x: 2020, y: 2 }], 100, 50);
assert.equal(pts[0].x, 0);
assert.equal(pts[2].x, 100);
assert.ok(pts[1].y < pts[0].y, "valor mayor = más arriba");
assert.ok(trazo(pts).startsWith("M0.0,"));

assert.equal(fase(0, 450).toFixed(6), fase(450, 450).toFixed(6), "loop perfecto");

const ps = [{ inicio: 0, fin: 0.4 }, { inicio: 0.5, fin: 0.9 }];
assert.equal(palabraActiva(ps, 0.2), 0);
assert.equal(palabraActiva(ps, 0.6), 1);
assert.equal(palabraActiva(ps, 0.495), -1); // entre palabras (tras los 80 ms de tolerancia)

assert.equal(formatear(4.56, "%"), "4,6%");
assert.equal(formatear(4.0, "%"), "4%");
assert.equal(formatear(12543.2, "USD"), "US$12.543");
assert.equal(formatear(-0.35, "%"), "-0,4%");

const base = {
  fps: 30, duracionFrames: 300, audio: "a.wav", fuente: "x",
  diseno: { colores: { fondo1: "#000000", fondo2: "#111111", texto: "#ffffff", acento: "#ff0000", resaltado: "#00ff00" },
    fuente: "Inter", estiloSubtitulos: "caja", mayusculas: true, posicionSubtitulos: 0.6, fondo: "degradado",
    estiloGrafico: "linea", transicion: "zoom", intensidad: 0.05 },
  segmentos: [{ desde: 0, hasta: 300, tipo: "cifra", texto: "x", video: "" }],
  serie: { titulo: "t", pais: "p", unidad: "%", puntos: [{ x: 1, y: 1 }, { x: 2, y: 2 }] },
  paginas: [],
};
assert.ok(esquemaShort.safeParse(base).success);
const roto = { ...base, segmentos: [{ desde: 0, hasta: 300, tipo: "broll", texto: "", video: "" }] };
assert.equal(esquemaShort.safeParse(roto).success, false, "broll sin video se rechaza");
console.log("props.test.ts: ok");
