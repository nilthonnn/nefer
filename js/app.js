"use strict";

/* =========================================================================
 * Constantes y presets
 * ========================================================================= */

const HP_TO_KW = 0.746;

const STARTING_PRESETS = {
  resistive:        { label: "Resistiva / electrónica (sin arranque)", factor: 1 },
  motor_dol:        { label: "Motor - arranque directo (DOL)",         factor: 6 },
  motor_star_delta: { label: "Motor - arranque estrella-triángulo",    factor: 3 },
  motor_soft:       { label: "Motor - arranque suave (soft starter)",  factor: 3 },
  motor_vfd:        { label: "Motor - variador de frecuencia (VFD)",   factor: 1.2 },
  custom:           { label: "Personalizado",                         factor: null },
};

// Tamaños comerciales de referencia (kVA) - lista genérica orientativa.
const STANDARD_SIZES_KVA = [
  5, 8, 10, 15, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150, 175, 200,
  250, 300, 350, 400, 500, 600, 650, 700, 750, 800, 900, 1000, 1250, 1500, 1750, 2000, 2500,
];

const STORAGE_KEY = "genset-sizer:autosave";
const STORAGE_SAVED_KEY = "genset-sizer:saved-project";

const DEFAULT_ROWS = [
  { id: 1, desc: "Iluminación general", type: "resistive", power: 2, unit: "kw", qty: 1, pf: 1, startFactor: 1, included: true },
  { id: 2, desc: "Tomacorrientes / electrónica", type: "resistive", power: 3, unit: "kw", qty: 1, pf: 0.95, startFactor: 1, included: true },
  { id: 3, desc: "Bomba de agua", type: "motor_dol", power: 5.5, unit: "hp", qty: 1, pf: 0.85, startFactor: 6, included: true },
  { id: 4, desc: "Aire acondicionado", type: "motor_dol", power: 3, unit: "hp", qty: 2, pf: 0.85, startFactor: 6, included: true },
];

/* =========================================================================
 * Utilidades
 * ========================================================================= */

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function toNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatNumber(value, decimals = 1) {
  if (!Number.isFinite(value)) return "0";
  return value.toLocaleString("es", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

let rowIdCounter = 1;
function nextRowId() {
  return rowIdCounter++;
}

/* =========================================================================
 * Motor de cálculo (funciones puras, sin dependencia del DOM)
 * ========================================================================= */

function computeLoadRow(row) {
  const qty = Math.max(0, toNumber(row.qty, 0));
  const pf = clamp(toNumber(row.pf, 1), 0.05, 1);
  const powerValue = Math.max(0, toNumber(row.power, 0));
  const unitKW = row.unit === "hp" ? powerValue * HP_TO_KW : powerValue;

  const totalKW = unitKW * qty;
  const totalKVA = pf > 0 ? totalKW / pf : 0;

  const startFactor = Math.max(0, toNumber(row.startFactor, 1));
  const startKVA = totalKVA * startFactor;

  return { unitKW, totalKW, totalKVA, startFactor, startKVA };
}

function computeSummary(rows, params) {
  const includedRows = rows.filter((r) => r.included !== false);
  const computed = includedRows.map((r) => ({ ...r, ...computeLoadRow(r) }));

  let sumKW = 0;
  let sumKVA = 0;
  computed.forEach((c) => {
    sumKW += c.totalKW;
    sumKVA += c.totalKVA;
  });

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

  const altitude = Math.max(0, toNumber(params.altitude, 0));
  const temp = toNumber(params.temp, 25);
  const altitudeExcess = Math.max(0, altitude - 1000);
  const tempExcess = Math.max(0, temp - 25);
  // Regla general de referencia: ~1%/100msnm sobre 1000msnm y ~1%/°C sobre 25°C. Tope 50% por seguridad numérica.
  const deratingPct = clamp((altitudeExcess / 100) * 1 + tempExcess * 1, 0, 50);
  const deratingFactor = 1 - deratingPct / 100;

  const recommendedKVA = deratingFactor > 0 ? beforeDerating / deratingFactor : beforeDerating;
  const genPF = clamp(toNumber(params.genPF, 0.8), 0.5, 1);
  const recommendedKW = recommendedKVA * genPF;

  const suggestedSize = STANDARD_SIZES_KVA.find((s) => s >= recommendedKVA - 1e-9) || null;

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
    recommendedKVA,
    recommendedKW,
    suggestedSize,
  };
}

/* =========================================================================
 * Estado de la aplicación
 * ========================================================================= */

const state = {
  rows: [],
  params: {
    projectName: "",
    voltage: 220,
    phases: "3",
    frequency: "60",
    margin: 20,
    genPF: 0.8,
    altitude: 0,
    temp: 25,
  },
};

/* =========================================================================
 * Render: tabla de cargas
 * ========================================================================= */

const tableBody = document.getElementById("loadsTableBody");

function renderStartTypeOptions(selected) {
  return Object.entries(STARTING_PRESETS)
    .map(([key, preset]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${preset.label}</option>`)
    .join("");
}

function renderRows() {
  tableBody.innerHTML = "";
  state.rows.forEach((row) => {
    const computedRow = computeLoadRow(row);
    const tr = document.createElement("tr");
    tr.dataset.id = String(row.id);
    tr.innerHTML = `
      <td><input type="text" data-field="desc" value="${escapeHtml(row.desc)}" placeholder="Descripción" /></td>
      <td>
        <select data-field="type">${renderStartTypeOptions(row.type)}</select>
      </td>
      <td><input type="number" data-field="power" value="${row.power}" min="0" step="0.1" /></td>
      <td>
        <select data-field="unit">
          <option value="kw" ${row.unit === "kw" ? "selected" : ""}>kW</option>
          <option value="hp" ${row.unit === "hp" ? "selected" : ""}>HP</option>
        </select>
      </td>
      <td><input type="number" data-field="qty" value="${row.qty}" min="0" step="1" /></td>
      <td><input type="number" data-field="pf" value="${row.pf}" min="0.1" max="1" step="0.01" /></td>
      <td><input type="number" data-field="startFactor" value="${row.startFactor}" min="0" step="0.1" /></td>
      <td class="readout">${formatNumber(computedRow.totalKW)}</td>
      <td class="readout">${formatNumber(computedRow.totalKVA)}</td>
      <td class="readout">${formatNumber(computedRow.startKVA)}</td>
      <td class="col-inc"><input type="checkbox" data-field="included" ${row.included !== false ? "checked" : ""} /></td>
      <td class="col-actions"><button class="row-remove-btn" data-action="remove" title="Eliminar fila">✕</button></td>
    `;
    tableBody.appendChild(tr);
  });
}

function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* =========================================================================
 * Render: resultados
 * ========================================================================= */

function renderResults() {
  const summary = computeSummary(state.rows, state.params);

  document.getElementById("statRunningKW").textContent = `${formatNumber(summary.sumKW)} kW`;
  document.getElementById("statRunningKVA").textContent = `${formatNumber(summary.sumKVA)} kVA`;
  document.getElementById("statGlobalPF").textContent = formatNumber(summary.globalPF, 2);

  document.getElementById("statPeakStart").textContent = `${formatNumber(summary.peakStartKVA)} kVA`;
  document.getElementById("statPeakSource").textContent = summary.worst
    ? `impulsado por: ${summary.worst.desc || "carga sin nombre"}`
    : "sin cargas registradas";

  document.getElementById("statDerating").textContent = `${formatNumber(summary.deratingPct, 1)}%`;
  document.getElementById("statDeratingDetail").textContent =
    `altitud ${formatNumber(state.params.altitude, 0)} msnm · ${formatNumber(state.params.temp, 0)} °C`;

  document.getElementById("statRecommendedKVA").textContent = `${formatNumber(summary.recommendedKVA)} kVA`;
  document.getElementById("statRecommendedKW").textContent = `≈ ${formatNumber(summary.recommendedKW)} kW`;

  document.getElementById("statSuggestedSize").textContent = summary.suggestedSize
    ? `${summary.suggestedSize} kVA`
    : "fuera de rango estándar";

  renderBreakdown(summary);
}

function renderBreakdown(summary) {
  const container = document.getElementById("breakdownBars");
  container.innerHTML = "";

  if (summary.computed.length === 0) {
    container.innerHTML = '<p class="hint">Agrega cargas en la tabla para ver el desglose.</p>';
    return;
  }

  const maxValue = Math.max(...summary.computed.map((c) => Math.max(c.totalKVA, c.startKVA)), 1);

  summary.computed.forEach((c) => {
    const runRow = document.createElement("div");
    runRow.className = "bar-row";
    runRow.innerHTML = `
      <span class="bar-label" title="${escapeHtml(c.desc)}">${escapeHtml(c.desc || "(sin nombre)")}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${(c.totalKVA / maxValue) * 100}%"></span></span>
      <span class="bar-value">${formatNumber(c.totalKVA)} kVA</span>
    `;
    container.appendChild(runRow);

    if (c.startKVA > c.totalKVA + 1e-6) {
      const startRow = document.createElement("div");
      startRow.className = "bar-row";
      startRow.innerHTML = `
        <span class="bar-label">&nbsp;&nbsp;↳ arranque</span>
        <span class="bar-track"><span class="bar-fill is-start" style="width:${(c.startKVA / maxValue) * 100}%"></span></span>
        <span class="bar-value">${formatNumber(c.startKVA)} kVA</span>
      `;
      container.appendChild(startRow);
    }
  });
}

function renderAll() {
  renderRows();
  renderResults();
}

/* =========================================================================
 * Manejo de eventos: tabla
 * ========================================================================= */

document.getElementById("btnAddRow").addEventListener("click", () => {
  state.rows.push({
    id: nextRowId(),
    desc: "",
    type: "resistive",
    power: 1,
    unit: "kw",
    qty: 1,
    pf: 1,
    startFactor: 1,
    included: true,
  });
  renderAll();
  persistAutosave();
});

tableBody.addEventListener("input", (e) => {
  const field = e.target.dataset.field;
  if (!field) return;
  const tr = e.target.closest("tr");
  const id = Number(tr.dataset.id);
  const row = state.rows.find((r) => r.id === id);
  if (!row) return;

  if (field === "included") {
    row.included = e.target.checked;
  } else if (field === "type") {
    row.type = e.target.value;
    const preset = STARTING_PRESETS[row.type];
    if (preset && preset.factor !== null) {
      row.startFactor = preset.factor;
    }
  } else if (["power", "qty", "pf", "startFactor"].includes(field)) {
    row[field] = e.target.value;
  } else {
    row[field] = e.target.value;
  }

  // Si cambió el tipo, hay que re-renderizar toda la fila para reflejar el nuevo factor de arranque.
  if (field === "type") {
    renderRows();
  } else {
    updateRowReadouts(tr, row);
  }
  renderResults();
  persistAutosave();
});

function updateRowReadouts(tr, row) {
  const computedRow = computeLoadRow(row);
  const cells = tr.querySelectorAll("td.readout");
  cells[0].textContent = formatNumber(computedRow.totalKW);
  cells[1].textContent = formatNumber(computedRow.totalKVA);
  cells[2].textContent = formatNumber(computedRow.startKVA);
}

tableBody.addEventListener("click", (e) => {
  if (e.target.dataset.action === "remove") {
    const tr = e.target.closest("tr");
    const id = Number(tr.dataset.id);
    state.rows = state.rows.filter((r) => r.id !== id);
    renderAll();
    persistAutosave();
  }
});

/* =========================================================================
 * Manejo de eventos: parámetros
 * ========================================================================= */

const paramInputs = {
  projectName: document.getElementById("projectName"),
  voltage: document.getElementById("voltage"),
  phases: document.getElementById("phases"),
  frequency: document.getElementById("frequency"),
  margin: document.getElementById("margin"),
  genPF: document.getElementById("genPF"),
  altitude: document.getElementById("altitude"),
  temp: document.getElementById("temp"),
};

Object.entries(paramInputs).forEach(([key, el]) => {
  el.addEventListener("input", () => {
    state.params[key] = el.value;
    renderResults();
    persistAutosave();
  });
});

function applyParamsToInputs() {
  Object.entries(paramInputs).forEach(([key, el]) => {
    el.value = state.params[key];
  });
}

/* =========================================================================
 * Persistencia: autosave, guardar/cargar, import/export
 * ========================================================================= */

function persistAutosave() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (err) {
    // localStorage puede no estar disponible (modo privado, contexto restringido); se ignora silenciosamente.
  }
}

function loadAutosave() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.rows)) return false;
    state.rows = parsed.rows;
    state.params = { ...state.params, ...parsed.params };
    rowIdCounter = Math.max(1, ...state.rows.map((r) => toNumber(r.id, 0) + 1));
    return true;
  } catch (err) {
    return false;
  }
}

function setSaveStatus(message) {
  const el = document.getElementById("saveStatus");
  el.textContent = message;
  if (message) {
    setTimeout(() => {
      if (el.textContent === message) el.textContent = "";
    }, 4000);
  }
}

document.getElementById("btnSave").addEventListener("click", () => {
  try {
    localStorage.setItem(STORAGE_SAVED_KEY, JSON.stringify(state));
    setSaveStatus("Proyecto guardado en este navegador.");
  } catch (err) {
    setSaveStatus("No se pudo guardar: almacenamiento local no disponible.");
  }
});

document.getElementById("btnLoad").addEventListener("click", () => {
  try {
    const raw = localStorage.getItem(STORAGE_SAVED_KEY);
    if (!raw) {
      setSaveStatus("No hay ningún proyecto guardado todavía.");
      return;
    }
    const parsed = JSON.parse(raw);
    state.rows = parsed.rows || [];
    state.params = { ...state.params, ...parsed.params };
    rowIdCounter = Math.max(1, ...state.rows.map((r) => toNumber(r.id, 0) + 1));
    applyParamsToInputs();
    renderAll();
    setSaveStatus("Proyecto cargado.");
  } catch (err) {
    setSaveStatus("No se pudo cargar el proyecto guardado.");
  }
});

document.getElementById("btnExportJSON").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  downloadBlob(blob, `${slugify(state.params.projectName) || "proyecto-grupo-electrogeno"}.json`);
});

document.getElementById("btnImportJSON").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result);
      if (!parsed || !Array.isArray(parsed.rows)) throw new Error("formato inválido");
      state.rows = parsed.rows;
      state.params = { ...state.params, ...parsed.params };
      rowIdCounter = Math.max(1, ...state.rows.map((r) => toNumber(r.id, 0) + 1));
      applyParamsToInputs();
      renderAll();
      persistAutosave();
      setSaveStatus("Proyecto importado correctamente.");
    } catch (err) {
      setSaveStatus("El archivo JSON no tiene un formato válido.");
    }
  };
  reader.readAsText(file);
  e.target.value = "";
});

document.getElementById("btnExportCSV").addEventListener("click", () => {
  const header = ["Descripcion", "Tipo", "Potencia", "Unidad", "Cantidad", "cosPhi", "FactorArranque", "kW_total", "kVA_total", "kVA_arranque", "Incluida"];
  const lines = [header.join(",")];
  state.rows.forEach((row) => {
    const c = computeLoadRow(row);
    const preset = STARTING_PRESETS[row.type];
    lines.push([
      csvEscape(row.desc),
      csvEscape(preset ? preset.label : row.type),
      row.power,
      row.unit,
      row.qty,
      row.pf,
      row.startFactor,
      c.totalKW.toFixed(2),
      c.totalKVA.toFixed(2),
      c.startKVA.toFixed(2),
      row.included !== false ? "si" : "no",
    ].join(","));
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `${slugify(state.params.projectName) || "cargas-grupo-electrogeno"}.csv`);
});

document.getElementById("btnReset").addEventListener("click", () => {
  if (!confirm("¿Reiniciar el proyecto actual? Se perderán los cambios no guardados.")) return;
  state.rows = DEFAULT_ROWS.map((r) => ({ ...r, id: nextRowId() }));
  state.params = {
    projectName: "",
    voltage: 220,
    phases: "3",
    frequency: "60",
    margin: 20,
    genPF: 0.8,
    altitude: 0,
    temp: 25,
  };
  applyParamsToInputs();
  renderAll();
  persistAutosave();
});

document.getElementById("btnPrint").addEventListener("click", () => window.print());

function csvEscape(value) {
  const str = String(value ?? "");
  if (/[",\n]/.test(str)) return `"${str.replace(/"/g, '""')}"`;
  return str;
}

function slugify(str) {
  return String(str || "")
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* =========================================================================
 * Inicialización
 * ========================================================================= */

function init() {
  const restored = loadAutosave();
  if (!restored) {
    state.rows = DEFAULT_ROWS.map((r) => ({ ...r, id: nextRowId() }));
  }
  applyParamsToInputs();
  renderAll();
}

init();
