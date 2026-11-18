// Valida un JSON de props contra el esquema Zod del render, sin navegador.
//   node --experimental-strip-types src/lib/validar-props.ts props.json
// Imprime {"ok": bool, "problemas": [{"ruta", "mensaje"}]} y sale con 0 aunque
// las props no sean válidas: un código distinto de 0 significa que el propio
// validador falló (JSON ilegible, archivo inexistente).
import { readFileSync } from "node:fs";
import { esquemaShort } from "../schema.ts";

const ruta = process.argv[2];
if (!ruta) {
  console.error("uso: validar-props.ts <props.json>");
  process.exit(2);
}
const datos: unknown = JSON.parse(readFileSync(ruta, "utf8"));
const r = esquemaShort.safeParse(datos);
const problemas = r.success
  ? []
  : r.error.issues.map((i) => ({ ruta: i.path.map(String).join("."), mensaje: i.message }));
console.log(JSON.stringify({ ok: r.success, problemas }));
