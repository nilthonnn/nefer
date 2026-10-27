// Funciones puras (sin React) usadas por los componentes: se prueban con node.

export type P = { x: number; y: number };

/** Proyecta la serie a un rectángulo (y crece hacia arriba) con 8 % de aire. */
export function proyectar(puntos: P[], ancho: number, alto: number): P[] {
  const xs = puntos.map((p) => p.x);
  const ys = puntos.map((p) => p.y);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const aire = (y1 - y0 || Math.abs(y1) || 1) * 0.08;
  y0 -= aire;
  y1 += aire;
  return puntos.map((p) => ({
    x: ((p.x - x0) / (x1 - x0 || 1)) * ancho,
    y: alto - ((p.y - y0) / (y1 - y0)) * alto,
  }));
}

export function trazo(pts: P[]): string {
  return pts.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

export function longitud(pts: P[]): number {
  let total = 0;
  for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  return total;
}

/** Fase periódica 0..2π: el último fotograma coincide con el primero (loop perfecto). */
export function fase(frame: number, total: number, vueltas = 1): number {
  return ((frame % total) / total) * Math.PI * 2 * vueltas;
}

/** Índice de la palabra activa en el segundo t (o -1 entre palabras). */
export function palabraActiva(palabras: { inicio: number; fin: number }[], t: number): number {
  for (let i = palabras.length - 1; i >= 0; i--) {
    if (t >= palabras[i].inicio) return t <= palabras[i].fin + 0.08 || i === palabras.length - 1 ? i : -1;
  }
  return -1;
}

/**
 * Número con coma decimal y punto de miles (como lo escribe el guion), sin
 * depender del locale del navegador: así el gráfico y los subtítulos
 * muestran exactamente la misma cifra.
 */
export function numero(valor: number, decimales: number): string {
  // Redondeo decimal "humano" (0,35 → 0,4): toFixed redondea el binario (0,3).
  const redondeado = Number(`${Math.round(Number(`${Math.abs(valor)}e${decimales}`))}e-${decimales}`);
  const [entero, frac] = redondeado.toFixed(decimales).split(".");
  const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const limpio = frac && /[1-9]/.test(frac) ? `${miles},${frac.replace(/0+$/, "")}` : miles;
  return (valor < 0 ? "-" : "") + limpio;
}

export function formatear(valor: number, unidad: string): string {
  const n = numero(valor, Math.abs(valor) >= 100 ? 0 : 1);
  if (unidad.startsWith("%")) return `${n}%`;
  if (unidad === "USD") return `US$${n}`;
  return n;
}
