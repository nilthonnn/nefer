"use strict";

// Suite de regresión del motor de cálculo (js/calc.js), contra la
// implementación REAL usada por la app (no una reimplementación aparte).
// Sin dependencias: usa node:test y node:assert (Node ≥18).
//
// Ejecutar:
//   node --test tests/

const test = require("node:test");
const assert = require("node:assert/strict");
const calc = require("../js/calc.js");

function baseRow(overrides = {}) {
  return {
    desc: "consumo",
    category: "process",
    flow: 1,
    unit: "m3min",
    qty: 1,
    usageFactorPct: 100,
    included: true,
    ...overrides,
  };
}

function baseParams(overrides = {}) {
  return {
    margin: 20,
    altitude: 0,
    temp: 20,
    workingPressure: 7,
    lineLoss: 0.5,
    compressorTech: "screw_oil",
    ...overrides,
  };
}

test("atmPressureKPa: nivel del mar = 101.325 kPa y decrece con la altitud", () => {
  assert.ok(Math.abs(calc.atmPressureKPa(0) - 101.325) < 0.001);
  assert.ok(calc.atmPressureKPa(2335) < calc.atmPressureKPa(0));
  assert.ok(calc.atmPressureKPa(4338) < calc.atmPressureKPa(2335));
  // Cerro de Pasco (~4,338 msnm): referencia conocida ~59 kPa.
  assert.ok(Math.abs(calc.atmPressureKPa(4338) - 58.97) < 0.5);
});

test("airDensityCorrectionFactor: ligeramente > 1 a nivel del mar y 20°C (la atmósfera estándar de 101.325 kPa es algo más densa que la referencia ISO 1217 de 100 kPa)", () => {
  const f = calc.airDensityCorrectionFactor(0, 20);
  assert.ok(f > 1 && f < 1.02, `factor fuera de rango esperado: ${f}`);
});

test("airDensityCorrectionFactor: decrece con la altitud y con la temperatura", () => {
  const sea = calc.airDensityCorrectionFactor(0, 20);
  const alt = calc.airDensityCorrectionFactor(4338, 20);
  const hot = calc.airDensityCorrectionFactor(0, 35);
  assert.ok(alt < sea, "más altitud debe reducir la densidad relativa");
  assert.ok(hot < sea, "más temperatura debe reducir la densidad relativa");
});

test("computeConsumerRow: CFM se convierte a m3/min", () => {
  const row = baseRow({ flow: 35.3147, unit: "cfm", qty: 1, usageFactorPct: 100 });
  const c = calc.computeConsumerRow(row);
  assert.ok(Math.abs(c.unitM3min - 1) < 1e-6);
});

test("computeConsumerRow: factor de uso reduce el consumo efectivo, no el nominal", () => {
  const row = baseRow({ flow: 10, unit: "m3min", qty: 2, usageFactorPct: 30 });
  const c = calc.computeConsumerRow(row);
  assert.equal(c.nominalM3min, 20);
  assert.ok(Math.abs(c.effectiveM3min - 6) < 1e-9);
});

test("computeSummary: caso por defecto sin cargas no produce NaN/Infinity", () => {
  const s = calc.computeSummary([], baseParams());
  assert.equal(s.sumEffective, 0);
  assert.equal(s.designDemandM3min, 0);
  assert.equal(s.shaftPowerKW, 0);
  assert.ok(Number.isFinite(s.suggestedSizeKW));
});

test("computeSummary: filas con included=false no cuentan en el total", () => {
  const rows = [
    baseRow({ flow: 5, unit: "m3min", usageFactorPct: 100, included: true }),
    baseRow({ flow: 999, unit: "m3min", usageFactorPct: 100, included: false }),
  ];
  const s = calc.computeSummary(rows, baseParams());
  assert.equal(s.sumEffective, 5);
});

test("computeSummary: la misma demanda de diseño exige más FAD de catálogo y más potencia en altura que a nivel del mar", () => {
  const rows = [baseRow({ flow: 10, unit: "m3min", usageFactorPct: 100 })];
  const sea = calc.computeSummary(rows, baseParams({ altitude: 0 }));
  const cerroDePasco = calc.computeSummary(rows, baseParams({ altitude: 4338 }));

  assert.ok(cerroDePasco.densityFactor < sea.densityFactor);
  assert.ok(
    cerroDePasco.requiredCatalogFADm3min > sea.requiredCatalogFADm3min,
    "a mayor altitud se requiere más FAD de catálogo para la misma demanda real"
  );
  assert.ok(
    cerroDePasco.compressionRatio > sea.compressionRatio,
    "a la misma presión manométrica de trabajo, la relación de compresión (absoluta) sube con la altitud"
  );
  assert.ok(
    cerroDePasco.shaftPowerKW > sea.shaftPowerKW,
    "se requiere más potencia en altura para entregar la misma demanda de diseño"
  );
});

test("computeSummary: relación de compresión dispara la advertencia de 2 etapas cuando supera el límite de la tecnología", () => {
  const rows = [baseRow({ flow: 5, unit: "m3min", usageFactorPct: 100 })];
  // oil-free: maxSingleStageRatio = 4.5. 7 bar(g) a nivel del mar da ratio ~8.9 -> excede.
  const s = calc.computeSummary(rows, baseParams({ altitude: 0, workingPressure: 7, lineLoss: 0, compressorTech: "screw_oilfree" }));
  assert.equal(s.stageWarning, true);

  const s2 = calc.computeSummary(rows, baseParams({ altitude: 0, workingPressure: 7, lineLoss: 0, compressorTech: "screw_oil" }));
  assert.equal(s2.stageWarning, false);
});

test("findSuggestedSize: toma el primer tamaño de catálogo que cubre la potencia estimada", () => {
  const r1 = calc.findSuggestedSize(20);
  assert.equal(r1.size, 22);
  assert.equal(r1.fits, true);

  const r2 = calc.findSuggestedSize(10000);
  assert.equal(r2.fits, false);
  assert.equal(r2.size, calc.STANDARD_SIZES_KW[calc.STANDARD_SIZES_KW.length - 1]);
});

test("computeIdealAdiabaticPowerKW: orden de magnitud consistente con la regla de mercado (~6.5 kW/m3-min a 7 bar(g), tornillo lubricado)", () => {
  const p1 = calc.SEA_LEVEL_PRESSURE_KPA;
  const p2 = p1 + 7 * 100; // 7 bar(g) -> kPa
  const ideal = calc.computeIdealAdiabaticPowerKW(1, p1, p2); // 1 m3/min
  const tech = calc.COMPRESSOR_TECH_PRESETS.screw_oil;
  const shaft = ideal / tech.overallEfficiency;
  assert.ok(shaft > 5.5 && shaft < 7.5, `potencia estimada por m3/min fuera de rango esperado: ${shaft}`);
});

test("computeSummary: margen de seguridad escala linealmente la demanda de diseño", () => {
  const rows = [baseRow({ flow: 10, unit: "m3min", usageFactorPct: 100 })];
  const noMargin = calc.computeSummary(rows, baseParams({ margin: 0 }));
  const withMargin = calc.computeSummary(rows, baseParams({ margin: 25 }));
  assert.ok(Math.abs(withMargin.designDemandM3min / noMargin.designDemandM3min - 1.25) < 1e-9);
});

test("csvEscape: antepone comilla simple a valores que empiezan como fórmula (mitigación CSV injection)", () => {
  assert.equal(calc.csvEscape("=1+1"), "'=1+1");
  assert.equal(calc.csvEscape("+1+1"), "'+1+1");
  assert.equal(calc.csvEscape("-5% offset"), "'-5% offset");
  assert.equal(calc.csvEscape("@SUM(A1)"), "'@SUM(A1)");
  assert.equal(calc.csvEscape('=HYPERLINK("http://evil")'), '"\'=HYPERLINK(""http://evil"")"');
});

test("csvEscape: no altera texto normal y sigue citando comas/comillas/saltos de línea", () => {
  assert.equal(calc.csvEscape("Perforadora jackleg"), "Perforadora jackleg");
  assert.equal(calc.csvEscape("Consumo, con coma"), '"Consumo, con coma"');
  assert.equal(calc.csvEscape('Con "comillas"'), '"Con ""comillas"""');
});

test("PERU_LOCATION_PRESETS: incluye ubicaciones de costa y de gran altitud", () => {
  const altitudes = calc.PERU_LOCATION_PRESETS.map((p) => p.altitude);
  assert.ok(altitudes.some((a) => a < 200), "debe incluir una ubicación de costa");
  assert.ok(altitudes.some((a) => a > 4000), "debe incluir una ubicación de gran altitud (típico de minería andina)");
});
