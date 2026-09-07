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
    desc: "carga",
    category: "resistive",
    type: "resistive",
    power: 10,
    unit: "kw",
    qty: 1,
    pf: 1,
    efficiency: 1,
    startFactor: 1,
    harmonicSeverity: "medium",
    included: true,
    ...overrides,
  };
}

function baseParams(overrides = {}) {
  return {
    margin: 20,
    genPF: 0.8,
    altitude: 0,
    temp: 25,
    engineTech: "turbo",
    regime: "standby",
    generatorXdPct: 15,
    performanceClass: "G3",
    customMaxDipPct: 15,
    ...overrides,
  };
}

test("computeLoadRow: carga en kW no usa eficiencia", () => {
  const row = baseRow({ power: 10, unit: "kw", pf: 0.9, efficiency: 0.5, qty: 2 });
  const c = calc.computeLoadRow(row);
  assert.equal(c.totalKW, 20); // 10*2, eficiencia ignorada porque unit=kw
  assert.ok(Math.abs(c.totalKVA - 20 / 0.9) < 1e-9);
});

test("computeLoadRow: HP se convierte a kW eléctrico dividiendo por eficiencia", () => {
  const row = baseRow({ power: 10, unit: "hp", pf: 1, efficiency: 0.9, qty: 1 });
  const c = calc.computeLoadRow(row);
  const expectedKW = (10 * calc.HP_TO_KW) / 0.9;
  assert.ok(Math.abs(c.totalKW - expectedKW) < 1e-9, `esperado ${expectedKW}, obtuvo ${c.totalKW}`);
});

test("computeLoadRow: kVA de arranque = kVA nominal x factor de arranque", () => {
  const row = baseRow({ power: 10, unit: "kw", pf: 1, startFactor: 6 });
  const c = calc.computeLoadRow(row);
  assert.equal(c.startKVA, c.totalKVA * 6);
});

test("computeHarmonics: fracción y sobredimensión por tramos", () => {
  const rows = [
    baseRow({ category: "resistive", power: 8, unit: "kw", pf: 1 }),
    baseRow({ category: "electronics_vfd", power: 2, unit: "kw", pf: 1, harmonicSeverity: "medium" }),
  ];
  const computed = rows.map((r) => ({ ...r, ...calc.computeLoadRow(r) }));
  const sumKVA = computed.reduce((s, c) => s + c.totalKVA, 0);
  const h = calc.computeHarmonics(computed, sumKVA);
  assert.ok(Math.abs(h.fractionPct - 20) < 1e-9); // 2 de 10 kVA = 20%
  assert.equal(h.oversizeFactor, 1.1); // tramo 10-30%
});

test("computeSummary: caso por defecto de la app (regresión numérica)", () => {
  // Mismas 4 filas que DEFAULT_ROWS en js/app.js.
  const rows = [
    baseRow({ desc: "Iluminación", category: "lighting", type: "resistive", power: 2, unit: "kw", pf: 1, efficiency: 1, startFactor: 1 }),
    baseRow({ desc: "Tomacorrientes", category: "electronics_vfd", type: "resistive", power: 3, unit: "kw", pf: 0.95, efficiency: 1, startFactor: 1 }),
    baseRow({ desc: "Bomba", category: "motor", type: "motor_dol", power: 5.5, unit: "hp", pf: 0.85, efficiency: 0.878, startFactor: 6 }),
    baseRow({ desc: "AC", category: "motor", type: "motor_dol", power: 3, unit: "hp", qty: 2, pf: 0.82, efficiency: 0.855, startFactor: 6 }),
  ];
  const s = calc.computeSummary(rows, baseParams());
  assert.ok(Math.abs(s.sumKW - 14.908) < 0.01, `sumKW=${s.sumKW}`);
  assert.ok(Math.abs(s.recommendedKVA - 64.63) < 0.05, `recommendedKVA=${s.recommendedKVA}`);
  assert.equal(s.suggestedSize, 65);
  assert.equal(s.dipOk, true);
});

test("computeSummary: régimen Continuous agrega 10% respecto a Standby", () => {
  const rows = [baseRow({ power: 50, unit: "kw", pf: 0.9, startFactor: 1 })];
  const standby = calc.computeSummary(rows, baseParams({ regime: "standby" }));
  const continuous = calc.computeSummary(rows, baseParams({ regime: "continuous" }));
  assert.ok(Math.abs(continuous.recommendedKVA / standby.recommendedKVA - 1.10) < 1e-9);
});

test("computeSummary: motor aspirado derating más que turboalimentado a la misma altitud", () => {
  const rows = [baseRow({ power: 50, unit: "kw", pf: 0.9, startFactor: 1 })];
  const params = { altitude: 3000, temp: 25 };
  const aspirated = calc.computeSummary(rows, baseParams({ ...params, engineTech: "aspirated" }));
  const turbo = calc.computeSummary(rows, baseParams({ ...params, engineTech: "turbo" }));
  const intercooler = calc.computeSummary(rows, baseParams({ ...params, engineTech: "turbo_intercooler" }));
  assert.ok(aspirated.deratingPct > turbo.deratingPct, "aspirado debe derating más que turbo");
  assert.ok(turbo.deratingPct > intercooler.deratingPct, "turbo debe derating más que turbo+intercooler");
});

test("findSuggestedSize: sube de tamaño cuando el %dip no cumple con el criterio elegido", () => {
  // Un solo motor grande DOL: peakStartKVA ~= su propio kVA de arranque.
  const rows = [baseRow({ category: "motor", type: "motor_dol", power: 150, unit: "hp", pf: 0.85, efficiency: 0.9, startFactor: 6 })];
  const params = baseParams({ margin: 0, generatorXdPct: 17, performanceClass: "G4", customMaxDipPct: 8 });
  const s = calc.computeSummary(rows, params);

  const naiveSize = calc.STANDARD_SIZES_KVA.find((sz) => sz >= s.recommendedKVA);
  assert.ok(s.suggestedSize > naiveSize, "el criterio de %dip debe exigir un tamaño mayor que el redondeo simple");
  assert.ok(s.dipPct <= 8 + 1e-9, `dipPct=${s.dipPct} debe quedar dentro del 8% pedido`);
  assert.equal(s.dipOk, true);
});

test("findSuggestedSize: marca dipOk=false si ningún tamaño del catálogo alcanza", () => {
  const rows = [baseRow({ category: "motor", type: "motor_dol", power: 1500, unit: "hp", pf: 0.85, efficiency: 0.9, startFactor: 6 })];
  const params = baseParams({ margin: 0, generatorXdPct: 17, performanceClass: "G4", customMaxDipPct: 5 });
  const s = calc.computeSummary(rows, params);
  assert.equal(s.dipOk, false);
  assert.equal(s.suggestedSize, calc.STANDARD_SIZES_KVA[calc.STANDARD_SIZES_KVA.length - 1]);
});

test("computeSummary: sin cargas, no produce NaN/Infinity", () => {
  const s = calc.computeSummary([], baseParams());
  assert.equal(s.sumKW, 0);
  assert.equal(s.sumKVA, 0);
  assert.equal(s.recommendedKVA, 0);
  assert.ok(Number.isFinite(s.recommendedKVA));
  assert.ok(s.suggestedSize === null || Number.isFinite(s.suggestedSize));
});

test("computeSummary: filas con included=false no cuentan en el total", () => {
  const rows = [
    baseRow({ power: 10, unit: "kw", pf: 1, included: true }),
    baseRow({ power: 999, unit: "kw", pf: 1, included: false }),
  ];
  const s = calc.computeSummary(rows, baseParams());
  assert.equal(s.sumKW, 10);
});

test("CONNECTION_TYPE_PRESETS: cada preset trae voltaje+fases coherentes, salvo 'custom'", () => {
  for (const [key, preset] of Object.entries(calc.CONNECTION_TYPE_PRESETS)) {
    if (key === "custom") {
      assert.equal(preset.voltage, null);
      assert.equal(preset.phases, null);
    } else {
      assert.ok(preset.voltage > 0, `${key} debe tener voltaje > 0`);
      assert.ok(preset.phases === "1" || preset.phases === "3", `${key} debe ser monofásico o trifásico`);
    }
  }
  assert.ok(calc.CONNECTION_TYPE_PRESETS["380_3f"], "debe existir el estándar peruano 380V trifásico + neutro");
});

test("csvEscape: antepone comilla simple a valores que empiezan como fórmula (mitigación CSV injection)", () => {
  assert.equal(calc.csvEscape("=1+1"), "'=1+1");
  assert.equal(calc.csvEscape("+1+1"), "'+1+1");
  assert.equal(calc.csvEscape("-5% offset"), "'-5% offset");
  assert.equal(calc.csvEscape("@SUM(A1)"), "'@SUM(A1)");
  // Un valor que además necesita comillas por contener comas queda con AMBAS
  // protecciones: la comilla simple anti-fórmula y las comillas dobles CSV.
  assert.equal(calc.csvEscape('=HYPERLINK("http://evil")'), '"\'=HYPERLINK(""http://evil"")"');
});

test("csvEscape: no altera texto normal y sigue citando comas/comillas/saltos de línea", () => {
  assert.equal(calc.csvEscape("Bomba de agua"), "Bomba de agua");
  assert.equal(calc.csvEscape("Carga, con coma"), '"Carga, con coma"');
  assert.equal(calc.csvEscape('Con "comillas"'), '"Con ""comillas"""');
  assert.equal(calc.csvEscape("=1+1,con coma"), '"\'=1+1,con coma"');
});

test("L_TO_US_GAL: convierte litros a galones estadounidenses correctamente", () => {
  assert.ok(Math.abs(calc.L_TO_US_GAL - 0.264172) < 1e-9);
  assert.ok(Math.abs(100 * calc.L_TO_US_GAL - 26.4172) < 1e-6);
  // 1 galón estadounidense = 3.785411784 L (cifra de referencia conocida)
  assert.ok(Math.abs(1 / calc.L_TO_US_GAL - 3.785411784) < 1e-3);
});

test("estimateFuelConsumptionLPerHour: coincide con los puntos de referencia exactos de la tabla", () => {
  assert.equal(calc.estimateFuelConsumptionLPerHour(30), 7.7);
  assert.equal(calc.estimateFuelConsumptionLPerHour(200), 42.4);
  assert.equal(calc.estimateFuelConsumptionLPerHour(1000), 192.0);
});

test("estimateFuelConsumptionLPerHour: interpola entre puntos y es monótonamente creciente", () => {
  const mid = calc.estimateFuelConsumptionLPerHour(175 + (200 - 175) / 2); // punto medio 175-200
  assert.ok(mid > calc.estimateFuelConsumptionLPerHour(175) && mid < calc.estimateFuelConsumptionLPerHour(200));
  let prev = 0;
  for (const size of calc.STANDARD_SIZES_KVA) {
    const v = calc.estimateFuelConsumptionLPerHour(size);
    assert.ok(v > prev, `el consumo debe crecer con el tamaño (${size} kVA)`);
    prev = v;
  }
});

test("estimateFuelConsumptionLPerHour: sin tamaño válido devuelve 0", () => {
  assert.equal(calc.estimateFuelConsumptionLPerHour(0), 0);
  assert.equal(calc.estimateFuelConsumptionLPerHour(-5), 0);
});

test("computeSummary: incluye fuelConsumptionLPerHour coherente con el tamaño sugerido", () => {
  const rows = [
    { desc: "Bomba", category: "motor", type: "motor_dol", power: 5.5, unit: "hp", qty: 1, pf: 0.85, efficiency: 0.878, startFactor: 6, included: true },
  ];
  const s = calc.computeSummary(rows, baseParams());
  assert.ok(s.suggestedSize, "debe haber un tamaño sugerido para este caso");
  assert.equal(s.fuelConsumptionLPerHour, calc.estimateFuelConsumptionLPerHour(s.suggestedSize));
  assert.ok(s.fuelConsumptionLPerHour > 0);
});
