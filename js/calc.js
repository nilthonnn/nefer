"use strict";

/* =========================================================================
 * Motor de cálculo (js/calc.js)
 * -------------------------------------------------------------------------
 * Funciones y constantes puras, sin dependencia del DOM. Se cargan como
 * <script> clásico antes de js/app.js (comparten el scope global del
 * navegador, sin módulos ni build) y también se pueden requerir desde Node
 * (ver el guard de module.exports al final) para la suite de pruebas en
 * tests/calc.test.js.
 * ========================================================================= */

const HP_TO_KW = 0.746;

const STARTING_PRESETS = {
  resistive:        { label: "Sin arranque (resistiva/electrónica)", factor: 1 },
  motor_dol:        { label: "Motor - arranque directo (DOL)",         factor: 6 },
  motor_star_delta: { label: "Motor - arranque estrella-triángulo",    factor: 3 },
  motor_soft:       { label: "Motor - arranque suave (soft starter)",  factor: 3 },
  motor_vfd:        { label: "Motor - variador de frecuencia (VFD)",   factor: 1.2 },
  custom:           { label: "Personalizado",                         factor: null },
};

// Categoría de la carga: independiente del tipo de arranque. Determina si la
// carga aporta corriente no lineal (armónicos) para el cálculo de sobredimensión
// del alternador.
const CATEGORY_PRESETS = {
  motor:           { label: "Motor" },
  lighting:        { label: "Iluminación" },
  electronics_vfd: { label: "Electrónica / VFD (no lineal)" },
  resistive:       { label: "Resistiva" },
};

// Severidad de armónicos de una carga no lineal: pondera cuánto de su kVA se
// cuenta como "no lineal" al estimar la fracción total del sistema. Es una
// heurística de referencia (no un cálculo de THD real, ver IEEE 519) para
// decidir si conviene sobredimensionar el alternador o especificar un
// rectificador con filtro/reactancia.
const HARMONIC_SEVERITY = {
  low:    { label: "Baja (con reactancia de línea / filtro)", weight: 0.5 },
  medium: { label: "Media (rectificador 6 pulsos estándar)",  weight: 1.0 },
  high:   { label: "Alta (conmutada sin filtro)",              weight: 1.5 },
};

// Umbrales de fracción de carga no lineal -> sobredimensión adicional del
// alternador. Regla general de referencia: valida contra la guía del fabricante
// del alternador (p.ej. 2/3 de paso, reactancia subtransitoria) para cargas
// no lineales dominantes.
const HARMONIC_OVERSIZE_BRACKETS = [
  { maxFractionPct: 10, factor: 1.0 },
  { maxFractionPct: 30, factor: 1.1 },
  { maxFractionPct: 60, factor: 1.2 },
  { maxFractionPct: Infinity, factor: 1.35 },
];

// Régimen de operación (ISO 8528-1 / catálogos de fabricante): el mismo motor
// físico rinde distinta potencia nominal según el régimen. ESP y PRP no llevan
// ajuste adicional porque el margen de seguridad ya cubre el uso típico; COP
// exige holgura propia porque no admite ninguna sobrecarga transitoria.
const REGIME_PRESETS = {
  standby:    { label: "Standby (ESP) — emergencia, uso limitado",        factor: 1.00 },
  prime:      { label: "Prime (PRP) — fuente principal, carga variable",  factor: 1.00 },
  continuous: { label: "Continuous (COP) — 100% constante, sin sobrecarga", factor: 1.10 },
};

// Tipo de conexión: no entra en el cálculo de kVA/kW (que es independiente de
// la tensión), pero fija consistentemente Tensión + Fases en vez de dejarlos
// como dos campos sueltos que se puedan combinar de forma poco realista
// (p.ej. "220V trifásico" ambiguo). 380V trifásico + neutro (220V F-N) es el
// esquema estándar de baja tensión en Perú.
const CONNECTION_TYPE_PRESETS = {
  "220_1f": { label: "220V Monofásico (F-N)",                                    voltage: 220, phases: "1" },
  "220_3f": { label: "220V Trifásico (Δ, sin neutro)",                           voltage: 220, phases: "3" },
  "380_3f": { label: "380V Trifásico + Neutro (220V F-N) — estándar Perú",       voltage: 380, phases: "3" },
  "440_3f": { label: "440V Trifásico",                                          voltage: 440, phases: "3" },
  custom:   { label: "Personalizado",                                           voltage: null, phases: null },
};

// Tecnología del motor: cambia qué tan rápido pierde potencia con la altitud y
// la temperatura. El multiplicador escala la tasa base (~1%/100msnm,
// ~1%/°C) usada por defecto para un motor turboalimentado.
const ENGINE_TECH_PRESETS = {
  aspirated:         { label: "Aspirado natural",      altitudeRateMultiplier: 1.8, tempRateMultiplier: 1.3 },
  turbo:             { label: "Turboalimentado",        altitudeRateMultiplier: 1.0, tempRateMultiplier: 1.0 },
  turbo_intercooler: { label: "Turbo + intercooler",    altitudeRateMultiplier: 0.6, tempRateMultiplier: 0.8 },
};

// Clases de rendimiento transitorio ISO 8528-5: definen la caída de tensión
// máxima aceptable al aplicar un escalón de carga (p.ej. arranque del motor
// más grande). G4 es "a medida": usa el %dip máximo que definas aparte.
const PERFORMANCE_CLASS_PRESETS = {
  G1: { label: "G1 — no crítico",                    maxDipPct: 25 },
  G2: { label: "G2 — comercial estándar",             maxDipPct: 20 },
  G3: { label: "G3 — industrial exigente",            maxDipPct: 15 },
  G4: { label: "G4 — a medida (definir con el proveedor)", maxDipPct: null },
};

// Tamaños comerciales de referencia (kVA) - lista genérica orientativa.
const STANDARD_SIZES_KVA = [
  5, 8, 10, 15, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150, 175, 200,
  250, 300, 350, 400, 500, 600, 650, 700, 750, 800, 900, 1000, 1250, 1500, 1750, 2000, 2500,
];

// =========================================================================
// Librería de cargas: equipos típicos del mercado con datos de placa de
// referencia (motores trifásicos jaula de ardilla NEMA/IEC estándar,
// soldadoras, bombas, compresores, HVAC, iluminación, hornos, etc.).
// Son valores orientativos de catálogo — siempre confirmar contra la placa
// del equipo real antes de una emisión de ingeniería final.
// =========================================================================

const LOAD_LIBRARY = [
  // ---- Motores eléctricos trifásicos (jaula de ardilla, 4 polos) ----
  { group: "Motores eléctricos", name: "Motor trifásico 1 HP", category: "motor", type: "motor_dol", power: 1, unit: "hp", pf: 0.80, efficiency: 0.825 },
  { group: "Motores eléctricos", name: "Motor trifásico 2 HP", category: "motor", type: "motor_dol", power: 2, unit: "hp", pf: 0.81, efficiency: 0.840 },
  { group: "Motores eléctricos", name: "Motor trifásico 3 HP", category: "motor", type: "motor_dol", power: 3, unit: "hp", pf: 0.82, efficiency: 0.855 },
  { group: "Motores eléctricos", name: "Motor trifásico 5 HP", category: "motor", type: "motor_dol", power: 5, unit: "hp", pf: 0.82, efficiency: 0.875 },
  { group: "Motores eléctricos", name: "Motor trifásico 7.5 HP", category: "motor", type: "motor_dol", power: 7.5, unit: "hp", pf: 0.83, efficiency: 0.885 },
  { group: "Motores eléctricos", name: "Motor trifásico 10 HP", category: "motor", type: "motor_dol", power: 10, unit: "hp", pf: 0.83, efficiency: 0.895 },
  { group: "Motores eléctricos", name: "Motor trifásico 15 HP", category: "motor", type: "motor_star_delta", power: 15, unit: "hp", pf: 0.84, efficiency: 0.902 },
  { group: "Motores eléctricos", name: "Motor trifásico 20 HP", category: "motor", type: "motor_star_delta", power: 20, unit: "hp", pf: 0.84, efficiency: 0.908 },
  { group: "Motores eléctricos", name: "Motor trifásico 25 HP", category: "motor", type: "motor_star_delta", power: 25, unit: "hp", pf: 0.85, efficiency: 0.912 },
  { group: "Motores eléctricos", name: "Motor trifásico 30 HP", category: "motor", type: "motor_star_delta", power: 30, unit: "hp", pf: 0.85, efficiency: 0.917 },
  { group: "Motores eléctricos", name: "Motor trifásico 40 HP", category: "motor", type: "motor_star_delta", power: 40, unit: "hp", pf: 0.86, efficiency: 0.920 },
  { group: "Motores eléctricos", name: "Motor trifásico 50 HP", category: "motor", type: "motor_soft", power: 50, unit: "hp", pf: 0.86, efficiency: 0.924 },
  { group: "Motores eléctricos", name: "Motor trifásico 60 HP", category: "motor", type: "motor_soft", power: 60, unit: "hp", pf: 0.86, efficiency: 0.928 },
  { group: "Motores eléctricos", name: "Motor trifásico 75 HP", category: "motor", type: "motor_soft", power: 75, unit: "hp", pf: 0.87, efficiency: 0.931 },
  { group: "Motores eléctricos", name: "Motor trifásico 100 HP", category: "motor", type: "motor_soft", power: 100, unit: "hp", pf: 0.87, efficiency: 0.935 },
  { group: "Motores eléctricos", name: "Motor trifásico 125 HP (con VFD)", category: "motor", type: "motor_vfd", power: 125, unit: "hp", pf: 0.87, efficiency: 0.937 },
  { group: "Motores eléctricos", name: "Motor monofásico 1 HP (taller)", category: "motor", type: "motor_dol", power: 1, unit: "hp", pf: 0.75, efficiency: 0.72 },
  { group: "Motores eléctricos", name: "Motor monofásico 2 HP (taller)", category: "motor", type: "motor_dol", power: 2, unit: "hp", pf: 0.76, efficiency: 0.75 },

  // ---- Soldadoras eléctricas ----
  { group: "Soldadoras eléctricas", name: "Soldadora inversora MMA/TIG monofásica 160A", category: "electronics_vfd", type: "resistive", power: 5.0, unit: "kw", pf: 0.70, harmonicSeverity: "medium", note: "Inversor IGBT; entrada monofásica 220V" },
  { group: "Soldadoras eléctricas", name: "Soldadora inversora MMA/TIG monofásica 200A", category: "electronics_vfd", type: "resistive", power: 6.5, unit: "kw", pf: 0.70, harmonicSeverity: "medium" },
  { group: "Soldadoras eléctricas", name: "Soldadora inversora MIG/MAG trifásica 300A", category: "electronics_vfd", type: "resistive", power: 11, unit: "kw", pf: 0.75, harmonicSeverity: "medium" },
  { group: "Soldadoras eléctricas", name: "Soldadora inversora MIG/MAG trifásica 400A", category: "electronics_vfd", type: "resistive", power: 15, unit: "kw", pf: 0.75, harmonicSeverity: "high" },
  { group: "Soldadoras eléctricas", name: "Soldadora de transformador convencional 200A (no inversora)", category: "resistive", type: "resistive", power: 8, unit: "kw", pf: 0.60, note: "Tecnología antigua: PF bajo, sin electrónica de potencia relevante" },
  { group: "Soldadoras eléctricas", name: "Soldadora por puntos (resistencia) 25 kVA", category: "resistive", type: "resistive", power: 20, unit: "kw", pf: 0.75, note: "Ciclo de trabajo bajo en la práctica; ajusta cantidad/inclusión según uso real" },

  // ---- Bombeo y compresión de aire ----
  { group: "Bombeo y compresión", name: "Bomba centrífuga 3 HP", category: "motor", type: "motor_dol", power: 3, unit: "hp", pf: 0.82, efficiency: 0.855 },
  { group: "Bombeo y compresión", name: "Bomba centrífuga 5 HP", category: "motor", type: "motor_dol", power: 5, unit: "hp", pf: 0.82, efficiency: 0.875 },
  { group: "Bombeo y compresión", name: "Bomba centrífuga 10 HP", category: "motor", type: "motor_star_delta", power: 10, unit: "hp", pf: 0.83, efficiency: 0.895 },
  { group: "Bombeo y compresión", name: "Bomba sumergible de pozo 7.5 HP", category: "motor", type: "motor_dol", power: 7.5, unit: "hp", pf: 0.83, efficiency: 0.885 },
  { group: "Bombeo y compresión", name: "Compresor de aire (pistón) 2 HP", category: "motor", type: "motor_dol", power: 2, unit: "hp", pf: 0.81, efficiency: 0.840 },
  { group: "Bombeo y compresión", name: "Compresor de aire (pistón) 5 HP", category: "motor", type: "motor_dol", power: 5, unit: "hp", pf: 0.82, efficiency: 0.875 },
  { group: "Bombeo y compresión", name: "Compresor de aire (tornillo) 25 HP", category: "motor", type: "motor_star_delta", power: 25, unit: "hp", pf: 0.85, efficiency: 0.912 },
  { group: "Bombeo y compresión", name: "Compresor de aire (tornillo) 50 HP", category: "motor", type: "motor_soft", power: 50, unit: "hp", pf: 0.86, efficiency: 0.924 },

  // ---- HVAC ----
  { group: "Climatización (HVAC)", name: "Aire acondicionado split 18,000 BTU/h", category: "motor", type: "motor_dol", power: 1.6, unit: "kw", pf: 0.85, startFactorOverride: 5 },
  { group: "Climatización (HVAC)", name: "Aire acondicionado split 24,000 BTU/h", category: "motor", type: "motor_dol", power: 2.2, unit: "kw", pf: 0.85, startFactorOverride: 5 },
  { group: "Climatización (HVAC)", name: "Chiller / paquete industrial (compresor 15 HP)", category: "motor", type: "motor_star_delta", power: 15, unit: "hp", pf: 0.84, efficiency: 0.902 },

  // ---- Iluminación ----
  { group: "Iluminación", name: "Luminaria LED industrial 150 W (por punto)", category: "lighting", type: "resistive", power: 0.15, unit: "kw", pf: 0.90 },
  { group: "Iluminación", name: "Luminaria haluro metálico 400 W (con corrección)", category: "lighting", type: "resistive", power: 0.42, unit: "kw", pf: 0.90 },
  { group: "Iluminación", name: "Reflector halógeno 500 W", category: "lighting", type: "resistive", power: 0.5, unit: "kw", pf: 1.0 },

  // ---- Herramientas y cargas varias ----
  { group: "Herramientas y varios", name: "Taladro / esmeril eléctrico portátil", category: "resistive", type: "resistive", power: 0.8, unit: "kw", pf: 0.95 },
  { group: "Herramientas y varios", name: "Grúa / polipasto eléctrico de izaje 10 HP", category: "motor", type: "motor_dol", power: 10, unit: "hp", pf: 0.83, efficiency: 0.895, startFactorOverride: 7, note: "Arranque más severo por carga de izaje" },
  { group: "Herramientas y varios", name: "Cargador de batería industrial 10 kW", category: "electronics_vfd", type: "resistive", power: 10, unit: "kw", pf: 0.85, harmonicSeverity: "high" },
  { group: "Herramientas y varios", name: "Horno de resistencia industrial 30 kW", category: "resistive", type: "resistive", power: 30, unit: "kw", pf: 0.98 },
  { group: "Herramientas y varios", name: "Horno de inducción 50 kW", category: "electronics_vfd", type: "resistive", power: 50, unit: "kw", pf: 0.85, harmonicSeverity: "high" },
  { group: "Herramientas y varios", name: "UPS / rectificador de sala de control 5 kW", category: "electronics_vfd", type: "resistive", power: 5, unit: "kw", pf: 0.90, harmonicSeverity: "medium" },
  { group: "Herramientas y varios", name: "Tablero de cómputo / oficina (carga TI) 3 kW", category: "electronics_vfd", type: "resistive", power: 3, unit: "kw", pf: 0.95, harmonicSeverity: "low" },
];

/* =========================================================================
 * Utilidades
 * ========================================================================= */

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

// Mitigación de "CSV/Formula Injection" (OWASP): si el valor empieza con un
// carácter que Excel/Sheets interpreta como inicio de fórmula (=, +, -, @, o
// tab/CR), se antepone una comilla simple para forzarlo a texto plano al
// abrir el archivo — evita que una descripción de carga maliciosa se
// ejecute como fórmula en la hoja de cálculo de quien reciba el CSV
// exportado (usado por "Exportar CSV de cargas" en js/app.js).
function csvEscape(value) {
  let str = String(value ?? "");
  if (/^[=+\-@\t\r]/.test(str)) str = `'${str}`;
  if (/[",\n]/.test(str)) return `"${str.replace(/"/g, '""')}"`;
  return str;
}

function toNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/* =========================================================================
 * Cálculo por carga
 * ========================================================================= */

function computeLoadRow(row) {
  const qty = Math.max(0, toNumber(row.qty, 0));
  const pf = clamp(toNumber(row.pf, 1), 0.05, 1);
  const powerValue = Math.max(0, toNumber(row.power, 0));
  // La potencia en HP es un rating mecánico de SALIDA del motor; el kW eléctrico
  // consumido (lo que debe suministrar el generador) es mayor por la eficiencia
  // de conversión. Para cargas en kW (iluminación, electrónica, resistivas) el
  // valor ya representa consumo eléctrico directo, así que la eficiencia no aplica.
  const efficiency = clamp(toNumber(row.efficiency, 1), 0.3, 1);
  const unitKW = row.unit === "hp" ? (powerValue * HP_TO_KW) / efficiency : powerValue;

  const totalKW = unitKW * qty;
  const totalKVA = pf > 0 ? totalKW / pf : 0;

  const startFactor = Math.max(0, toNumber(row.startFactor, 1));
  const startKVA = totalKVA * startFactor;

  return { unitKW, totalKW, totalKVA, startFactor, startKVA };
}

function harmonicOversizeFactor(fractionPct) {
  const bracket = HARMONIC_OVERSIZE_BRACKETS.find((b) => fractionPct <= b.maxFractionPct);
  return bracket ? bracket.factor : 1;
}

function computeHarmonics(computed, sumKVA) {
  let nonlinearWeightedKVA = 0;
  computed.forEach((c) => {
    if (c.category === "electronics_vfd") {
      const severity = HARMONIC_SEVERITY[c.harmonicSeverity] || HARMONIC_SEVERITY.medium;
      nonlinearWeightedKVA += c.totalKVA * severity.weight;
    }
  });
  const fractionPct = sumKVA > 0 ? clamp((nonlinearWeightedKVA / sumKVA) * 100, 0, 100) : 0;
  const oversizeFactor = harmonicOversizeFactor(fractionPct);
  return { nonlinearWeightedKVA, fractionPct, oversizeFactor };
}

// Caída de tensión aproximada al arrancar la carga crítica, con el generador
// candidato `candidateKVA` ya en régimen con el resto de cargas (método
// simplificado de preselección, ISO 8528-5 / guías de fabricante):
//   %dip = X"d(%) × kVA_arranque_carga_crítica / kVA_generador_candidato
function computeVoltageDipPct(peakStartKVA, xdPct, candidateKVA) {
  if (!(candidateKVA > 0)) return Infinity;
  return (xdPct * peakStartKVA) / candidateKVA;
}

// Recorre el catálogo comercial en orden ascendente y devuelve el primer
// tamaño que cubre la demanda continua (>= recommendedKVA) Y cuyo %dip de
// arranque queda dentro del límite de la clase de rendimiento elegida. Si
// maxDipPct es null (clase G4 sin límite definido) no se aplica el segundo
// criterio.
function findSuggestedSize(recommendedKVA, peakStartKVA, xdPct, maxDipPct) {
  for (const size of STANDARD_SIZES_KVA) {
    if (size < recommendedKVA - 1e-9) continue;
    const dipPct = computeVoltageDipPct(peakStartKVA, xdPct, size);
    if (maxDipPct == null || dipPct <= maxDipPct) {
      return { size, dipPct, dipOk: true };
    }
  }
  // Ningún tamaño del catálogo de referencia cumple ambos criterios: se
  // informa el último candidato (el mayor del catálogo) marcado como no apto,
  // para que quede visible que se requiere una unidad fuera de este catálogo
  // o una clase de rendimiento menos exigente.
  const largest = STANDARD_SIZES_KVA[STANDARD_SIZES_KVA.length - 1];
  return { size: largest, dipPct: computeVoltageDipPct(peakStartKVA, xdPct, largest), dipOk: false };
}

/* =========================================================================
 * Resumen del sistema
 * ========================================================================= */

function computeSummary(rows, params) {
  const includedRows = rows.filter((r) => r.included !== false);
  const computed = includedRows.map((r) => ({ ...r, ...computeLoadRow(r) }));

  let sumKW = 0;
  let sumKVA = 0;
  computed.forEach((c) => {
    sumKW += c.totalKW;
    sumKVA += c.totalKVA;
  });

  const harmonics = computeHarmonics(computed, sumKVA);

  // Carga que produce el mayor salto de arranque (kVA arranque - kVA nominal).
  // Se asume que esta carga arranca de última, con el resto ya en régimen: peor caso típico.
  let worst = null;
  computed.forEach((c) => {
    const delta = c.startKVA - c.totalKVA;
    const worstDelta = worst ? worst.startKVA - worst.totalKVA : -Infinity;
    if (delta > worstDelta) worst = c;
  });

  const peakStartKVA = worst ? sumKVA - worst.totalKVA + worst.startKVA : sumKVA;

  const margin = clamp(toNumber(params.margin, 0), 0, 300) / 100;
  const beforeDerating = peakStartKVA * (1 + margin);

  const engineTech = ENGINE_TECH_PRESETS[params.engineTech] || ENGINE_TECH_PRESETS.turbo;
  const altitude = Math.max(0, toNumber(params.altitude, 0));
  const temp = toNumber(params.temp, 25);
  const altitudeExcess = Math.max(0, altitude - 1000);
  const tempExcess = Math.max(0, temp - 25);
  // Regla general de referencia: ~1%/100msnm sobre 1000msnm y ~1%/°C sobre 25°C,
  // escalada por la tecnología del motor (turboalimentado = línea base ×1.0).
  // Tope 50% por seguridad numérica.
  const deratingPct = clamp(
    (altitudeExcess / 100) * engineTech.altitudeRateMultiplier + tempExcess * engineTech.tempRateMultiplier,
    0, 50
  );
  const deratingFactor = 1 - deratingPct / 100;

  const beforeHarmonics = deratingFactor > 0 ? beforeDerating / deratingFactor : beforeDerating;
  const afterHarmonics = beforeHarmonics * harmonics.oversizeFactor;

  const regime = REGIME_PRESETS[params.regime] || REGIME_PRESETS.standby;
  const recommendedKVA = afterHarmonics * regime.factor;

  const genPF = clamp(toNumber(params.genPF, 0.8), 0.5, 1);
  const recommendedKW = recommendedKVA * genPF;

  const xdPct = Math.max(0, toNumber(params.generatorXdPct, 15));
  const perfClass = PERFORMANCE_CLASS_PRESETS[params.performanceClass] || PERFORMANCE_CLASS_PRESETS.G3;
  const maxDipPct = perfClass.maxDipPct === null ? toNumber(params.customMaxDipPct, 15) : perfClass.maxDipPct;

  const sizing = findSuggestedSize(recommendedKVA, peakStartKVA, xdPct, maxDipPct);

  const globalPF = sumKVA > 0 ? sumKW / sumKVA : 1;

  return {
    computed,
    sumKW,
    sumKVA,
    globalPF,
    worst,
    peakStartKVA,
    margin,
    beforeDerating,
    deratingPct,
    deratingFactor,
    engineTech,
    harmonics,
    beforeHarmonics,
    regime,
    recommendedKVA,
    recommendedKW,
    xdPct,
    maxDipPct,
    suggestedSize: sizing.size,
    dipPct: sizing.dipPct,
    dipOk: sizing.dipOk,
  };
}

// Versión del esquema de cálculo/estado guardado. Incrementar cada vez que un
// cambio en la metodología (computeLoadRow/computeSummary) altera el
// resultado de proyectos ya guardados, para poder avisar al usuario en vez de
// recalcular en silencio.
const CALC_SCHEMA_VERSION = 2;

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    HP_TO_KW,
    STARTING_PRESETS,
    CATEGORY_PRESETS,
    HARMONIC_SEVERITY,
    HARMONIC_OVERSIZE_BRACKETS,
    CONNECTION_TYPE_PRESETS,
    REGIME_PRESETS,
    ENGINE_TECH_PRESETS,
    PERFORMANCE_CLASS_PRESETS,
    STANDARD_SIZES_KVA,
    LOAD_LIBRARY,
    CALC_SCHEMA_VERSION,
    clamp,
    toNumber,
    csvEscape,
    computeLoadRow,
    harmonicOversizeFactor,
    computeHarmonics,
    computeVoltageDipPct,
    findSuggestedSize,
    computeSummary,
  };
}
