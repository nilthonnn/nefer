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

const M3MIN_TO_CFM = 35.3147;

// Presión atmosférica estándar a nivel del mar (ISA/ICAO) — usada en la
// fórmula barométrica para estimar la presión del sitio según su altitud.
const SEA_LEVEL_PRESSURE_KPA = 101.325;

// Condiciones de referencia ISO 1217 (ed. 4, 2009) para el caudal nominal
// (FAD) de catálogo de un compresor de desplazamiento: 100 kPa absolutos,
// 20°C, 0% HR. Nótese que son distintas de la atmósfera estándar (101.325
// kPa) — es la referencia contra la que los fabricantes certifican su FAD
// en el banco de pruebas, normalmente a nivel del mar.
const ISO1217_REF_PRESSURE_KPA = 100;
const ISO1217_REF_TEMP_C = 20;

// Categoría del consumo de aire: fija un factor de uso/simultaneidad típico
// (independiente y editable por fila) para pasar de consumo nominal (placa)
// a consumo efectivo promedio del sistema.
const CONSUMER_CATEGORY_PRESETS = {
  tool_intermittent: { label: "Herramienta neumática (uso intermitente)", defaultUsageFactorPct: 30 },
  tool_continuous:   { label: "Herramienta / equipo de uso continuo",      defaultUsageFactorPct: 80 },
  process:           { label: "Proceso / equipo fijo",                    defaultUsageFactorPct: 100 },
  instrumentation:   { label: "Instrumentación y control",                defaultUsageFactorPct: 100 },
  mining_drilling:   { label: "Perforación / minería subterránea",        defaultUsageFactorPct: 50 },
  cleaning:          { label: "Limpieza / soplado (blow gun)",            defaultUsageFactorPct: 20 },
};

// Tecnología del compresor: define la eficiencia global "de cable a aire"
// (potencia isotérmica ideal / potencia eléctrica real, calibrada contra
// datos típicos de catálogo — p.ej. ~6.5 kW por m3/min a 7 bar(g) para
// tornillo lubricado, la regla de mercado "~4 CFM/HP a 100 psig") y la
// relación de compresión práctica máxima en una sola etapa antes de requerir
// una segunda etapa con interenfriamiento.
const COMPRESSOR_TECH_PRESETS = {
  screw_oil:     { label: "Tornillo lubricado (oil-injected)",      overallEfficiency: 0.72, maxSingleStageRatio: 10 },
  screw_oilfree: { label: "Tornillo libre de aceite (oil-free)",    overallEfficiency: 0.65, maxSingleStageRatio: 4.5 },
  reciprocating: { label: "Pistón (reciprocante)",                  overallEfficiency: 0.68, maxSingleStageRatio: 7 },
  centrifugal:   { label: "Centrífugo (dinámico)",                  overallEfficiency: 0.70, maxSingleStageRatio: 3 },
};

// Tamaños comerciales de referencia (kW de motor) - pasos IEC/NEMA típicos
// de catálogos de compresores de tornillo/pistón.
const STANDARD_SIZES_KW = [
  4, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160,
  200, 250, 315, 355, 400, 450, 500,
];

// Ubicaciones de referencia en Perú (altitud típica en msnm) — solo un
// atajo de UI para rellenar el campo "Altitud del sitio"; no forma parte
// del estado guardado del proyecto (ver js/app.js).
const PERU_LOCATION_PRESETS = [
  { label: "Costa / Lima (~150 msnm)", altitude: 150 },
  { label: "Trujillo / Chiclayo — costa norte (~40 msnm)", altitude: 40 },
  { label: "Arequipa (~2,335 msnm)", altitude: 2335 },
  { label: "Huancayo (~3,259 msnm)", altitude: 3259 },
  { label: "Cusco (~3,399 msnm)", altitude: 3399 },
  { label: "La Oroya (~3,745 msnm)", altitude: 3745 },
  { label: "Puno / Juliaca (~3,825 msnm)", altitude: 3825 },
  { label: "Cerro de Pasco (~4,338 msnm)", altitude: 4338 },
  { label: "La Rinconada, Puno — minería de gran altitud (~5,100 msnm)", altitude: 5100 },
  { label: "Iquitos / Pucallpa — selva (~120 msnm)", altitude: 120 },
];

// =========================================================================
// Librería de consumos: equipos/consumidores de aire comprimido típicos
// (talleres, minería subterránea, construcción, pintura, instrumentación,
// proceso), con caudal de referencia orientativo. Valores de "aire libre"
// (free air / ANR) típicos de catálogo — siempre confirmar contra la ficha
// técnica del fabricante antes de una emisión de ingeniería final.
// =========================================================================

const CONSUMER_LIBRARY = [
  // ---- Herramientas neumáticas de taller ----
  { group: "Herramientas de taller", name: "Llave de impacto 1/2\"", category: "tool_intermittent", flow: 4, unit: "cfm" },
  { group: "Herramientas de taller", name: "Amoladora / esmeril neumático", category: "tool_intermittent", flow: 5, unit: "cfm" },
  { group: "Herramientas de taller", name: "Taladro neumático", category: "tool_intermittent", flow: 3.5, unit: "cfm" },
  { group: "Herramientas de taller", name: "Pistola de sopleteo (blow gun) regulada", category: "cleaning", flow: 4, unit: "cfm" },
  { group: "Herramientas de taller", name: "Llave de carraca (ratchet) neumática", category: "tool_intermittent", flow: 3, unit: "cfm" },

  // ---- Minería subterránea (Perú: gran altitud) ----
  { group: "Minería subterránea", name: "Perforadora jackleg", category: "mining_drilling", flow: 100, unit: "cfm", note: "Consumo típico 80-125 CFM @ 6 bar; usar el dato del fabricante para el modelo real" },
  { group: "Minería subterránea", name: "Perforadora stoper", category: "mining_drilling", flow: 110, unit: "cfm" },
  { group: "Minería subterránea", name: "Martillo neumático / rompedor de roca", category: "mining_drilling", flow: 55, unit: "cfm" },
  { group: "Minería subterránea", name: "Columna/carro de perforación (jumbo neumático pequeño)", category: "mining_drilling", flow: 180, unit: "cfm" },
  { group: "Minería subterránea", name: "Ventilador auxiliar neumático de frente", category: "process", flow: 60, unit: "cfm" },

  // ---- Construcción ----
  { group: "Construcción", name: "Vibrador neumático para concreto", category: "tool_intermittent", flow: 15, unit: "cfm" },
  { group: "Construcción", name: "Martillo demoledor neumático", category: "tool_intermittent", flow: 35, unit: "cfm" },
  { group: "Construcción", name: "Pistola neumática de clavos/grapas", category: "tool_intermittent", flow: 2.5, unit: "cfm" },
  { group: "Construcción", name: "Compactadora/apisonadora neumática", category: "tool_intermittent", flow: 20, unit: "cfm" },

  // ---- Pintura y acabados ----
  { group: "Pintura y acabados", name: "Pistola de pintura HVLP", category: "tool_intermittent", flow: 10, unit: "cfm" },
  { group: "Pintura y acabados", name: "Pistola de pintura convencional (alta presión)", category: "tool_intermittent", flow: 14, unit: "cfm" },
  { group: "Pintura y acabados", name: "Cabina de sopleteo industrial", category: "process", flow: 40, unit: "cfm" },

  // ---- Instrumentación y control ----
  { group: "Instrumentación y control", name: "Actuador neumático de válvula on/off (por punto)", category: "instrumentation", flow: 0.15, unit: "m3min" },
  { group: "Instrumentación y control", name: "Posicionador / válvula de control (por punto)", category: "instrumentation", flow: 0.08, unit: "m3min" },
  { group: "Instrumentación y control", name: "Purga continua de instrumento (por punto)", category: "instrumentation", flow: 0.02, unit: "m3min" },

  // ---- Proceso industrial ----
  { group: "Proceso industrial", name: "Transporte neumático / air lift (línea pequeña)", category: "process", flow: 3, unit: "m3min" },
  { group: "Proceso industrial", name: "Agitación por aire (air sparging, tanque pequeño)", category: "process", flow: 1.2, unit: "m3min" },
  { group: "Proceso industrial", name: "Soplador de limpieza de línea/tanque", category: "cleaning", flow: 6, unit: "m3min" },
  { group: "Proceso industrial", name: "Cilindro/actuador neumático de proceso (ciclo típico)", category: "process", flow: 0.4, unit: "m3min" },
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
// abrir el archivo — evita que una descripción de consumo maliciosa se
// ejecute como fórmula en la hoja de cálculo de quien reciba el CSV
// exportado (usado por "Exportar CSV de demanda" en js/app.js).
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
 * Física de sitio: presión atmosférica y corrección de densidad
 * ========================================================================= */

// Fórmula barométrica de la Atmósfera Estándar Internacional (ISA/ICAO),
// válida en la tropósfera (0-11,000 msnm, rango que cubre todo el
// territorio peruano habitado). Devuelve la presión atmosférica absoluta
// del sitio en kPa a partir de su altitud.
function atmPressureKPa(altitudeM) {
  const h = Math.max(0, toNumber(altitudeM, 0));
  const ratio = Math.pow(1 - 2.25577e-5 * h, 5.2559);
  return SEA_LEVEL_PRESSURE_KPA * Math.max(ratio, 0);
}

// Factor de corrección de densidad del aire de succión del sitio respecto a
// las condiciones de referencia ISO 1217 (100 kPa, 20°C). Por gas ideal, la
// densidad es proporcional a P/T: un sitio en altura (menor P) y/o más
// caliente (mayor T) tiene aire menos denso, así que el mismo compresor
// (volumen barrido fijo) ingiere menos masa de aire y entrega menos caudal
// "normal" del que indica su placa de catálogo (certificada a nivel del
// mar). No se modela humedad relativa (efecto secundario, ~1-2%).
function airDensityCorrectionFactor(altitudeM, tempC) {
  const siteP = atmPressureKPa(altitudeM);
  const siteTK = toNumber(tempC, ISO1217_REF_TEMP_C) + 273.15;
  const refTK = ISO1217_REF_TEMP_C + 273.15;
  if (siteTK <= 0) return 1;
  return (siteP / siteTK) / (ISO1217_REF_PRESSURE_KPA / refTK);
}

/* =========================================================================
 * Cálculo por consumidor
 * ========================================================================= */

function computeConsumerRow(row) {
  const qty = Math.max(0, toNumber(row.qty, 0));
  const usageFactor = clamp(toNumber(row.usageFactorPct, 100), 0, 100) / 100;
  const flowValue = Math.max(0, toNumber(row.flow, 0));
  const unitM3min = row.unit === "cfm" ? flowValue / M3MIN_TO_CFM : flowValue;

  const nominalM3min = unitM3min * qty;
  const effectiveM3min = nominalM3min * usageFactor;

  return { unitM3min, nominalM3min, effectiveM3min, usageFactor };
}

/* =========================================================================
 * Potencia de compresión (adiabática ideal / eficiencia global) y tamaño
 * comercial sugerido
 * ========================================================================= */

const ADIABATIC_K = 1.4; // aire seco, k = Cp/Cv

// Potencia isentrópica ideal (kW) para comprimir Q1 (m3/min, a condiciones
// de succión del sitio) desde P1 hasta P2 (ambas absolutas, kPa), modelo de
// una etapa equivalente. Es la referencia física que después se divide por
// la eficiencia global de "cable a aire" del tipo de compresor para llegar
// a la potencia eléctrica estimada. Nota: una compresión real en 2 etapas
// con interenfriamiento consume algo menos que este modelo de 1 etapa
// equivalente — es, a propósito, una estimación conservadora (ver README).
function computeIdealAdiabaticPowerKW(q1M3min, p1KPa, p2KPa) {
  if (!(q1M3min > 0) || !(p1KPa > 0) || !(p2KPa > p1KPa)) return 0;
  const q1M3s = q1M3min / 60;
  const ratio = p2KPa / p1KPa;
  const exponent = (ADIABATIC_K - 1) / ADIABATIC_K;
  return p1KPa * q1M3s * (ADIABATIC_K / (ADIABATIC_K - 1)) * (Math.pow(ratio, exponent) - 1);
}

function findSuggestedSize(shaftPowerKW) {
  for (const size of STANDARD_SIZES_KW) {
    if (size >= shaftPowerKW - 1e-9) return { size, fits: true };
  }
  const largest = STANDARD_SIZES_KW[STANDARD_SIZES_KW.length - 1];
  return { size: largest, fits: false };
}

/* =========================================================================
 * Resumen del sistema
 * ========================================================================= */

function computeSummary(rows, params) {
  const includedRows = rows.filter((r) => r.included !== false);
  const computed = includedRows.map((r) => ({ ...r, ...computeConsumerRow(r) }));

  let sumNominal = 0;
  let sumEffective = 0;
  computed.forEach((c) => {
    sumNominal += c.nominalM3min;
    sumEffective += c.effectiveM3min;
  });

  const margin = clamp(toNumber(params.margin, 0), 0, 300) / 100;
  const designDemandM3min = sumEffective * (1 + margin);

  const altitude = Math.max(0, toNumber(params.altitude, 0));
  const temp = toNumber(params.temp, ISO1217_REF_TEMP_C);
  const siteAtmKPa = atmPressureKPa(altitude);
  const densityFactor = airDensityCorrectionFactor(altitude, temp);

  // Caudal nominal de catálogo (FAD a condiciones de referencia ISO 1217)
  // que hay que pedir para que, instalado en el sitio, entregue la demanda
  // de diseño real.
  const requiredCatalogFADm3min = densityFactor > 0 ? designDemandM3min / densityFactor : designDemandM3min;

  const workingPressureBar = Math.max(0, toNumber(params.workingPressure, 7));
  const lineLossBar = Math.max(0, toNumber(params.lineLoss, 0.5));
  const dischargeGaugeBar = workingPressureBar + lineLossBar;
  const dischargeAbsKPa = siteAtmKPa + dischargeGaugeBar * 100;
  const compressionRatio = siteAtmKPa > 0 ? dischargeAbsKPa / siteAtmKPa : Infinity;

  const tech = COMPRESSOR_TECH_PRESETS[params.compressorTech] || COMPRESSOR_TECH_PRESETS.screw_oil;
  const stageWarning = compressionRatio > tech.maxSingleStageRatio;

  const idealPowerKW = computeIdealAdiabaticPowerKW(requiredCatalogFADm3min, siteAtmKPa, dischargeAbsKPa);
  const shaftPowerKW = tech.overallEfficiency > 0 ? idealPowerKW / tech.overallEfficiency : idealPowerKW;

  const sizing = findSuggestedSize(shaftPowerKW);

  return {
    computed,
    sumNominal,
    sumEffective,
    margin,
    designDemandM3min,
    altitude,
    temp,
    siteAtmKPa,
    densityFactor,
    requiredCatalogFADm3min,
    workingPressureBar,
    lineLossBar,
    dischargeGaugeBar,
    dischargeAbsKPa,
    compressionRatio,
    tech,
    stageWarning,
    idealPowerKW,
    shaftPowerKW,
    suggestedSizeKW: sizing.size,
    sizeFits: sizing.fits,
  };
}

// Versión del esquema de cálculo/estado guardado. Incrementar cada vez que
// un cambio en la metodología (computeConsumerRow/computeSummary) altere el
// resultado de proyectos ya guardados, para poder avisar al usuario en vez
// de recalcular en silencio.
const CALC_SCHEMA_VERSION = 1;

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    M3MIN_TO_CFM,
    SEA_LEVEL_PRESSURE_KPA,
    ISO1217_REF_PRESSURE_KPA,
    ISO1217_REF_TEMP_C,
    CONSUMER_CATEGORY_PRESETS,
    COMPRESSOR_TECH_PRESETS,
    STANDARD_SIZES_KW,
    PERU_LOCATION_PRESETS,
    CONSUMER_LIBRARY,
    ADIABATIC_K,
    CALC_SCHEMA_VERSION,
    clamp,
    toNumber,
    csvEscape,
    atmPressureKPa,
    airDensityCorrectionFactor,
    computeConsumerRow,
    computeIdealAdiabaticPowerKW,
    findSuggestedSize,
    computeSummary,
  };
}
