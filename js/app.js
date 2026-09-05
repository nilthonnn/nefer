"use strict";

/* =========================================================================
 * Datos iniciales de la UI (el motor de cálculo vive en js/calc.js, cargado
 * antes que este archivo)
 * ========================================================================= */

const DEFAULT_ROWS = [
  { id: 1, desc: "Iluminación general", category: "lighting", type: "resistive", power: 2, unit: "kw", qty: 1, pf: 1, efficiency: 1, startFactor: 1, harmonicSeverity: "medium", included: true },
  { id: 2, desc: "Tomacorrientes / electrónica", category: "electronics_vfd", type: "resistive", power: 3, unit: "kw", qty: 1, pf: 0.95, efficiency: 1, startFactor: 1, harmonicSeverity: "medium", included: true },
  { id: 3, desc: "Bomba de agua", category: "motor", type: "motor_dol", power: 5.5, unit: "hp", qty: 1, pf: 0.85, efficiency: 0.878, startFactor: 6, harmonicSeverity: "medium", included: true },
  { id: 4, desc: "Aire acondicionado", category: "motor", type: "motor_dol", power: 3, unit: "hp", qty: 2, pf: 0.82, efficiency: 0.855, startFactor: 6, harmonicSeverity: "medium", included: true },
];

const DEFAULT_PARAMS = {
  projectName: "",
  clientName: "",
  preparedBy: "",
  connectionType: "380_3f",
  voltage: 380,
  phases: "3",
  frequency: "60",
  margin: 20,
  genPF: 0.8,
  altitude: 0,
  temp: 25,
  engineTech: "turbo",
  regime: "standby",
  generatorXdPct: 15,
  performanceClass: "G3",
  customMaxDipPct: 15,
};

const STORAGE_KEY = "genset-sizer:autosave";
const STORAGE_SAVED_KEY = "genset-sizer:saved-project";
const STORAGE_UI_ADVANCED_COLS_KEY = "genset-sizer:ui-advanced-cols";
const STORAGE_DISCLAIMER_ACCEPTED_KEY = "genset-sizer:disclaimer-accepted";

/* =========================================================================
 * Utilidades de UI (formato/DOM; el cálculo puro está en calc.js)
 * ========================================================================= */

function formatNumber(value, decimals = 1) {
  if (!Number.isFinite(value)) return "0";
  return value.toLocaleString("es", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

let rowIdCounter = 1;
function nextRowId() {
  return rowIdCounter++;
}

/* =========================================================================
 * Estado de la aplicación
 * ========================================================================= */

const state = {
  schemaVersion: CALC_SCHEMA_VERSION,
  rows: [],
  params: { ...DEFAULT_PARAMS },
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

function renderCategoryOptions(selected) {
  return Object.entries(CATEGORY_PRESETS)
    .map(([key, preset]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${preset.label}</option>`)
    .join("");
}

function renderHarmonicOptions(selected) {
  return Object.entries(HARMONIC_SEVERITY)
    .map(([key, preset]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${preset.label}</option>`)
    .join("");
}

function renderRows() {
  tableBody.innerHTML = "";
  state.rows.forEach((row) => {
    const computedRow = computeLoadRow(row);
    const isNonlinear = row.category === "electronics_vfd";
    const isHp = row.unit === "hp";
    const tr = document.createElement("tr");
    tr.dataset.id = String(row.id);
    tr.innerHTML = `
      <td><input type="text" data-field="desc" value="${escapeHtml(row.desc)}" placeholder="Descripción" /></td>
      <td>
        <select data-field="category">${renderCategoryOptions(row.category)}</select>
      </td>
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
      <td class="col-advanced"><input type="number" data-field="efficiency" value="${row.efficiency ?? 1}" min="0.3" max="1" step="0.01" ${isHp ? "" : "disabled"} title="${isHp ? "" : "Solo aplica cuando la unidad es HP"}" /></td>
      <td><input type="number" data-field="startFactor" value="${row.startFactor}" min="0" step="0.1" /></td>
      <td class="col-advanced">
        <select data-field="harmonicSeverity" ${isNonlinear ? "" : "disabled"} title="${isNonlinear ? "" : "Solo aplica a categoría Electrónica/VFD"}">${renderHarmonicOptions(row.harmonicSeverity)}</select>
      </td>
      <td class="readout">${formatNumber(computedRow.totalKW)}</td>
      <td class="readout">${formatNumber(computedRow.totalKVA)}</td>
      <td class="readout">${formatNumber(computedRow.startKVA)}</td>
      <td class="col-inc"><input type="checkbox" data-field="included" ${row.included !== false ? "checked" : ""} /></td>
      <td class="col-actions"><button class="row-remove-btn" data-action="remove" title="Eliminar fila">✕</button></td>
    `;
    tableBody.appendChild(tr);
  });
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
    `altitud ${formatNumber(state.params.altitude, 0)} msnm · ${formatNumber(state.params.temp, 0)} °C · ${summary.engineTech.label}`;

  document.getElementById("statHarmonicFraction").textContent = `${formatNumber(summary.harmonics.fractionPct, 1)}%`;
  document.getElementById("statHarmonicOversize").textContent = summary.harmonics.oversizeFactor > 1
    ? `sobredimensión ×${formatNumber(summary.harmonics.oversizeFactor, 2)} aplicada al alternador`
    : "sin sobredimensión adicional";

  document.getElementById("statDip").textContent = Number.isFinite(summary.dipPct) ? `${formatNumber(summary.dipPct, 1)}%` : "—";
  const perfClassLabel = PERFORMANCE_CLASS_PRESETS[state.params.performanceClass]?.label || "";
  document.getElementById("statDipDetail").textContent = summary.dipOk
    ? `dentro del límite (${perfClassLabel}, ≤${formatNumber(summary.maxDipPct, 0)}%)`
    : `⚠ excede el límite (${perfClassLabel}, ≤${formatNumber(summary.maxDipPct, 0)}%) — considera un generador fuera de este catálogo o una clase menos exigente`;

  document.getElementById("statRecommendedKVA").textContent = `${formatNumber(summary.recommendedKVA)} kVA`;
  document.getElementById("statRecommendedKW").textContent = `≈ ${formatNumber(summary.recommendedKW)} kW · régimen ${summary.regime.label.split(" —")[0]}`;

  document.getElementById("statSuggestedSize").textContent = summary.suggestedSize
    ? `${summary.suggestedSize} kVA`
    : "fuera de rango estándar";
  document.getElementById("statSuggestedSizeDetail").textContent = summary.dipOk
    ? "cumple carga continua y caída de tensión de arranque"
    : "⚠ no alcanza el catálogo de referencia a cumplir el %dip elegido";

  renderBreakdown(summary);
  renderReportMeta(summary);
}

function renderReportMeta(summary) {
  const today = new Date().toLocaleDateString("es");
  document.getElementById("coverProject").textContent = state.params.projectName || "—";
  document.getElementById("coverClient").textContent = state.params.clientName || "—";
  document.getElementById("coverDate").textContent = today;
  document.getElementById("coverPreparedBy").textContent = state.params.preparedBy || "—";
  document.getElementById("coverCapacity").textContent = summary.suggestedSize
    ? `${formatNumber(summary.recommendedKW)} kW (${summary.suggestedSize} kVA comercial)`
    : "—";
  document.getElementById("sigPreparedBy").textContent = state.params.preparedBy || "";
  document.getElementById("sigDate").textContent = today;
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
    category: "resistive",
    type: "resistive",
    power: 1,
    unit: "kw",
    qty: 1,
    pf: 1,
    efficiency: 1,
    startFactor: 1,
    harmonicSeverity: "medium",
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
  } else {
    row[field] = e.target.value;
  }

  // Tipo/categoría/unidad requieren re-render completo de la fila: el tipo puede
  // cambiar el factor de arranque sugerido, la categoría habilita/deshabilita el
  // selector de armónicos, y la unidad habilita/deshabilita el campo de eficiencia.
  if (field === "type" || field === "category" || field === "unit") {
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
  clientName: document.getElementById("clientName"),
  preparedBy: document.getElementById("preparedBy"),
  connectionType: document.getElementById("connectionType"),
  voltage: document.getElementById("voltage"),
  phases: document.getElementById("phases"),
  frequency: document.getElementById("frequency"),
  margin: document.getElementById("margin"),
  genPF: document.getElementById("genPF"),
  altitude: document.getElementById("altitude"),
  temp: document.getElementById("temp"),
  engineTech: document.getElementById("engineTech"),
  regime: document.getElementById("regime"),
  generatorXdPct: document.getElementById("generatorXdPct"),
  performanceClass: document.getElementById("performanceClass"),
  customMaxDipPct: document.getElementById("customMaxDipPct"),
};

Object.entries(paramInputs).forEach(([key, el]) => {
  if (!el) return;
  el.addEventListener("input", () => {
    state.params[key] = el.value;
    if (key === "connectionType") applyConnectionTypePreset();
    updateCustomDipVisibility();
    renderResults();
    persistAutosave();
  });
});

function updateCustomDipVisibility() {
  const wrap = document.getElementById("customMaxDipPctField");
  if (!wrap) return;
  wrap.hidden = state.params.performanceClass !== "G4";
}

// El "tipo de conexión" fija Tensión + Fases de forma consistente (evita
// combinaciones poco realistas como "220V trifásico sin aclarar si es Δ o
// con neutro"). Solo con "Personalizado" quedan editables a mano.
function applyConnectionTypePreset() {
  const preset = CONNECTION_TYPE_PRESETS[state.params.connectionType] || CONNECTION_TYPE_PRESETS.custom;
  const isCustom = state.params.connectionType === "custom";
  if (!isCustom) {
    state.params.voltage = preset.voltage;
    state.params.phases = preset.phases;
    if (paramInputs.voltage) paramInputs.voltage.value = preset.voltage;
    if (paramInputs.phases) paramInputs.phases.value = preset.phases;
  }
  if (paramInputs.voltage) paramInputs.voltage.disabled = !isCustom;
  if (paramInputs.phases) paramInputs.phases.disabled = !isCustom;
}

function applyParamsToInputs() {
  Object.entries(paramInputs).forEach(([key, el]) => {
    if (!el) return;
    el.value = state.params[key];
  });
  applyConnectionTypePreset();
  updateCustomDipVisibility();
}

// Preferencia de UI (no forma parte del proyecto): qué tan detallada se ve
// la tabla de cargas. Se recuerda entre sesiones, pero no viaja en
// guardar/exportar/importar — es solo una vista, no afecta el cálculo.
const toggleAdvancedColsEl = document.getElementById("toggleAdvancedCols");
const loadsTableEl = document.getElementById("loadsTable");

function applyAdvancedColsPreference(checked) {
  if (loadsTableEl) loadsTableEl.classList.toggle("show-advanced", checked);
  if (toggleAdvancedColsEl) toggleAdvancedColsEl.checked = checked;
}

(function initAdvancedColsPreference() {
  let checked = false;
  try {
    checked = localStorage.getItem(STORAGE_UI_ADVANCED_COLS_KEY) === "1";
  } catch (e) {
    // localStorage puede no estar disponible; se asume vista simple por defecto.
  }
  applyAdvancedColsPreference(checked);
})();

if (toggleAdvancedColsEl) {
  toggleAdvancedColsEl.addEventListener("change", () => {
    applyAdvancedColsPreference(toggleAdvancedColsEl.checked);
    try {
      localStorage.setItem(STORAGE_UI_ADVANCED_COLS_KEY, toggleAdvancedColsEl.checked ? "1" : "0");
    } catch (e) {
      // Se ignora silenciosamente si localStorage no está disponible.
    }
  });
}

/* =========================================================================
 * Persistencia: autosave, guardar/cargar, import/export
 * ========================================================================= */

// Proyectos guardados antes de que existiera "connectionType" solo tienen
// voltage/phases sueltos. Si calzan con un preset conocido lo usamos (sin
// cambiar sus valores); si no, "custom" preserva exactamente lo que tenían
// guardado en vez de pisarlo con el valor por defecto actual (380V).
function inferConnectionType(params) {
  if (params && params.connectionType) return params.connectionType;
  if (!params || params.voltage == null || params.phases == null) return DEFAULT_PARAMS.connectionType;
  const match = Object.entries(CONNECTION_TYPE_PRESETS).find(
    ([key, p]) => key !== "custom" && Number(p.voltage) === Number(params.voltage) && String(p.phases) === String(params.phases)
  );
  return match ? match[0] : "custom";
}

function migrateLoadedState(parsed) {
  const loadedVersion = Number(parsed.schemaVersion) || 0;
  state.rows = parsed.rows || [];
  state.params = { ...DEFAULT_PARAMS, ...parsed.params };
  state.params.connectionType = inferConnectionType(parsed.params);
  state.schemaVersion = CALC_SCHEMA_VERSION;
  rowIdCounter = Math.max(1, ...state.rows.map((r) => toNumber(r.id, 0) + 1));
  return loadedVersion !== CALC_SCHEMA_VERSION;
}

function persistAutosave() {
  try {
    state.schemaVersion = CALC_SCHEMA_VERSION;
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
    const wasMigrated = migrateLoadedState(parsed);
    if (wasMigrated) {
      // El aviso se muestra después de que el DOM esté listo (ver init()).
      window.__pendingMigrationNotice = true;
    }
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
    }, 6000);
  }
}

document.getElementById("btnSave").addEventListener("click", () => {
  try {
    state.schemaVersion = CALC_SCHEMA_VERSION;
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
    const wasMigrated = migrateLoadedState(parsed);
    applyParamsToInputs();
    renderAll();
    setSaveStatus(
      wasMigrated
        ? "Proyecto cargado — se calculó con una versión anterior del método y se recalculó con la metodología actual (ver README)."
        : "Proyecto cargado."
    );
  } catch (err) {
    setSaveStatus("No se pudo cargar el proyecto guardado.");
  }
});

document.getElementById("btnExportJSON").addEventListener("click", () => {
  state.schemaVersion = CALC_SCHEMA_VERSION;
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
      const wasMigrated = migrateLoadedState(parsed);
      applyParamsToInputs();
      renderAll();
      persistAutosave();
      setSaveStatus(
        wasMigrated
          ? "Proyecto importado — se calculó con una versión anterior del método y se recalculó con la metodología actual (ver README)."
          : "Proyecto importado correctamente."
      );
    } catch (err) {
      setSaveStatus("El archivo JSON no tiene un formato válido.");
    }
  };
  reader.readAsText(file);
  e.target.value = "";
});

const CSV_HEADER = [
  "Descripcion", "Categoria", "TipoArranque", "Potencia", "Unidad", "Cantidad",
  "cosPhi", "Eficiencia", "FactorArranque", "SeveridadArmonicos", "kW_total", "kVA_total", "kVA_arranque", "Incluida",
];

document.getElementById("btnExportCSV").addEventListener("click", () => {
  const lines = [CSV_HEADER.join(",")];
  state.rows.forEach((row) => {
    const c = computeLoadRow(row);
    lines.push([
      csvEscape(row.desc),
      row.category || "",
      row.type,
      row.power,
      row.unit,
      row.qty,
      row.pf,
      row.efficiency ?? 1,
      row.startFactor,
      row.harmonicSeverity || "",
      c.totalKW.toFixed(2),
      c.totalKVA.toFixed(2),
      c.startKVA.toFixed(2),
      row.included !== false ? "si" : "no",
    ].join(","));
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `${slugify(state.params.projectName) || "cargas-grupo-electrogeno"}.csv`);
});

// ---- Importación de CSV de cargas ----
// Parser tolerante RFC4180 (campos entrecomillados, comas y comillas escapadas).
function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field); field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      rows.push(row); row = [];
    } else {
      field += ch;
    }
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((cell) => cell.trim() !== ""));
}

// Mapea variantes comunes de encabezado (con/sin tilde, mayúsculas, alias) a
// nuestros campos internos, para tolerar CSV de terceros además del propio.
const CSV_HEADER_ALIASES = {
  descripcion: "desc", descripción: "desc", description: "desc",
  categoria: "category", categoría: "category",
  tipoarranque: "type", tipo: "type", tipodearranque: "type",
  potencia: "power",
  unidad: "unit",
  cantidad: "qty", cant: "qty",
  cosphi: "pf", cosφ: "pf", fp: "pf", factorpotencia: "pf",
  eficiencia: "efficiency", "eficienciaη": "efficiency", rendimiento: "efficiency",
  factorarranque: "startFactor",
  severidadarmonicos: "harmonicSeverity", "severidadarmónicos": "harmonicSeverity", armonicos: "harmonicSeverity",
  incluida: "included",
};

function normalizeHeaderKey(key) {
  return String(key || "").trim().toLowerCase().replace(/\s+/g, "");
}

function findCategoryKeyByLabel(label) {
  const found = Object.entries(CATEGORY_PRESETS).find(([, p]) => p.label.toLowerCase() === label.toLowerCase());
  return found ? found[0] : null;
}

function findStartTypeKeyByLabel(label) {
  const found = Object.entries(STARTING_PRESETS).find(([, p]) => p.label.toLowerCase() === label.toLowerCase());
  return found ? found[0] : null;
}

function importLoadsFromCSV(text) {
  const table = parseCSV(text);
  if (table.length < 2) return { imported: [], skipped: 0 };

  const headerKeys = table[0].map((h) => CSV_HEADER_ALIASES[normalizeHeaderKey(h)] || normalizeHeaderKey(h));
  const imported = [];
  let skipped = 0;

  for (let i = 1; i < table.length; i++) {
    const cells = table[i];
    const record = {};
    headerKeys.forEach((key, idx) => { record[key] = cells[idx] !== undefined ? cells[idx].trim() : ""; });

    const power = toNumber(record.power, NaN);
    if (!record.desc || !Number.isFinite(power)) { skipped++; continue; }

    const unit = (record.unit || "kw").toLowerCase() === "hp" ? "hp" : "kw";
    const categoryKey = CATEGORY_PRESETS[record.category]
      ? record.category
      : (findCategoryKeyByLabel(record.category) || "resistive");
    const typeKey = STARTING_PRESETS[record.type]
      ? record.type
      : (findStartTypeKeyByLabel(record.type) || "resistive");
    const harmonicKey = HARMONIC_SEVERITY[record.harmonicSeverity] ? record.harmonicSeverity : "medium";

    imported.push({
      id: nextRowId(),
      desc: record.desc,
      category: categoryKey,
      type: typeKey,
      power,
      unit,
      qty: Math.max(0, toNumber(record.qty, 1)),
      pf: clamp(toNumber(record.pf, 1), 0.05, 1),
      efficiency: clamp(toNumber(record.efficiency, 1), 0.3, 1),
      startFactor: Math.max(0, toNumber(record.startFactor, STARTING_PRESETS[typeKey].factor ?? 1)),
      harmonicSeverity: harmonicKey,
      included: !record.included || /^(si|sí|s|yes|y|true|1)$/i.test(record.included),
    });
  }

  return { imported, skipped };
}

document.getElementById("btnImportCSV").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const { imported, skipped } = importLoadsFromCSV(String(reader.result));
    if (imported.length === 0) {
      setSaveStatus("No se encontraron filas válidas en el CSV.");
      return;
    }
    const replace = confirm(
      `Se leyeron ${imported.length} carga(s) válida(s)${skipped ? ` (${skipped} fila(s) omitida(s) por datos incompletos)` : ""}.\n\n` +
      `Aceptar = reemplazar el cuadro de cargas actual.\nCancelar = agregarlas al final del cuadro actual.`
    );
    state.rows = replace ? imported : [...state.rows, ...imported];
    renderAll();
    persistAutosave();
    setSaveStatus(`Importación completa: ${imported.length} carga(s)${skipped ? `, ${skipped} omitida(s)` : ""}.`);
  };
  reader.readAsText(file);
  e.target.value = "";
});

/* =========================================================================
 * Librería de cargas (modal)
 * ========================================================================= */

const libraryDialog = document.getElementById("libraryDialog");
const libSearchInput = document.getElementById("libSearch");
const libCategorySelect = document.getElementById("libCategoryFilter");
const libListEl = document.getElementById("libList");

// Íconos por grupo: SVG en línea, minimalistas (solo trazo, sin relleno) y
// mínimos en bytes — nada de librerías de íconos ni peticiones externas, para
// no sumar peso ni dependencias a una app que ya es 100% sin build.
const LIBRARY_GROUP_ICON_PATHS = {
  "Motores eléctricos": '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
  "Soldadoras eléctricas": '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>',
  "Bombeo y compresión": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11Z"/>',
  "Climatización (HVAC)": '<path d="M12 2v20M4.2 6.5l15.6 11M19.8 6.5 4.2 17.5"/>',
  "Iluminación": '<circle cx="12" cy="10" r="5"/><path d="M12 15v4M9.5 21.5h5"/>',
  "Herramientas y varios": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2Z"/>',
};
const LIBRARY_GROUP_ICON_FALLBACK = '<circle cx="12" cy="12" r="1.4"/>';

function libraryGroupIcon(group) {
  const paths = LIBRARY_GROUP_ICON_PATHS[group] || LIBRARY_GROUP_ICON_FALLBACK;
  return `<svg class="lib-group-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

function libraryItemToRow(item) {
  const preset = STARTING_PRESETS[item.type];
  const startFactor = item.startFactorOverride ?? (preset && preset.factor !== null ? preset.factor : 1);
  return {
    id: nextRowId(),
    desc: item.name,
    category: item.category,
    type: item.type,
    power: item.power,
    unit: item.unit,
    qty: 1,
    pf: item.pf,
    efficiency: item.efficiency ?? 1,
    startFactor,
    harmonicSeverity: item.harmonicSeverity || "medium",
    included: true,
  };
}

function formatLibrarySpec(item) {
  const powerLabel = `${formatNumber(item.power, item.unit === "hp" ? 1 : 2)} ${item.unit === "hp" ? "HP" : "kW"}`;
  const parts = [powerLabel, `cos φ ${formatNumber(item.pf, 2)}`];
  if (item.unit === "hp" && item.efficiency) {
    parts.push(`η ${formatNumber(item.efficiency * 100, 0)}%`);
  }
  const preset = STARTING_PRESETS[item.type];
  const startFactor = item.startFactorOverride ?? (preset ? preset.factor : null);
  if (startFactor && startFactor > 1) {
    parts.push(`arranque ×${formatNumber(startFactor, 1)}`);
  }
  if (item.category === "electronics_vfd") {
    const sev = HARMONIC_SEVERITY[item.harmonicSeverity || "medium"];
    parts.push(`no lineal: ${sev.label.split(" (")[0].toLowerCase()}`);
  }
  return parts.join(" · ");
}

function populateLibraryCategoryFilter() {
  const groups = [...new Set(LOAD_LIBRARY.map((item) => item.group))];
  libCategorySelect.innerHTML = '<option value="">Todos los grupos</option>' +
    groups.map((g) => `<option value="${escapeHtml(g)}">${escapeHtml(g)}</option>`).join("");
}

function renderLibraryList() {
  const query = libSearchInput.value.trim().toLowerCase();
  const groupFilter = libCategorySelect.value;

  const filtered = LOAD_LIBRARY.filter((item) => {
    if (groupFilter && item.group !== groupFilter) return false;
    if (!query) return true;
    return item.name.toLowerCase().includes(query) || item.group.toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    libListEl.innerHTML = '<p class="lib-empty">No se encontraron equipos que coincidan con la búsqueda.</p>';
    return;
  }

  const groupsInOrder = [...new Set(filtered.map((item) => item.group))];
  libListEl.innerHTML = groupsInOrder.map((group) => {
    const items = filtered.filter((item) => item.group === group);
    const itemsHtml = items.map((item) => {
      const globalIdx = LOAD_LIBRARY.indexOf(item);
      return `
        <div class="lib-item">
          <div class="lib-item-info">
            <span class="lib-item-name">${escapeHtml(item.name)}</span>
            <span class="lib-item-spec">${escapeHtml(formatLibrarySpec(item))}</span>
          </div>
          <button class="lib-item-add" data-lib-index="${globalIdx}">+ Añadir</button>
        </div>
      `;
    }).join("");
    return `<div class="lib-group-title">${libraryGroupIcon(group)}${escapeHtml(group)}</div>${itemsHtml}`;
  }).join("");
}

document.getElementById("btnOpenLibrary").addEventListener("click", () => {
  libSearchInput.value = "";
  libCategorySelect.value = "";
  renderLibraryList();
  libraryDialog.showModal();
  libSearchInput.focus();
});

document.getElementById("btnCloseLibrary").addEventListener("click", () => libraryDialog.close());

libraryDialog.addEventListener("click", (e) => {
  if (e.target === libraryDialog) libraryDialog.close(); // clic en el backdrop
});

libSearchInput.addEventListener("input", renderLibraryList);
libCategorySelect.addEventListener("change", renderLibraryList);

libListEl.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-lib-index]");
  if (!btn) return;
  const item = LOAD_LIBRARY[Number(btn.dataset.libIndex)];
  if (!item) return;
  state.rows.push(libraryItemToRow(item));
  renderAll();
  persistAutosave();
  const original = btn.textContent;
  btn.textContent = "✓ Agregado";
  setTimeout(() => { btn.textContent = original; }, 1200);
});

populateLibraryCategoryFilter();

/* =========================================================================
 * Aviso legal / exención de responsabilidad
 * ========================================================================= */

const disclaimerDialog = document.getElementById("disclaimerDialog");

function isDisclaimerAccepted() {
  try {
    return localStorage.getItem(STORAGE_DISCLAIMER_ACCEPTED_KEY) === "1";
  } catch (e) {
    return false;
  }
}

document.getElementById("btnAcceptDisclaimer").addEventListener("click", () => {
  try {
    localStorage.setItem(STORAGE_DISCLAIMER_ACCEPTED_KEY, "1");
  } catch (e) {
    // Se ignora silenciosamente si localStorage no está disponible; el aviso
    // simplemente volverá a mostrarse en la próxima visita.
  }
  disclaimerDialog.close();
});

document.getElementById("btnCloseDisclaimer").addEventListener("click", () => disclaimerDialog.close());
document.getElementById("btnOpenDisclaimer").addEventListener("click", () => disclaimerDialog.showModal());

document.getElementById("btnReset").addEventListener("click", () => {
  if (!confirm("¿Reiniciar el proyecto actual? Se perderán los cambios no guardados.")) return;
  state.rows = DEFAULT_ROWS.map((r) => ({ ...r, id: nextRowId() }));
  state.params = { ...DEFAULT_PARAMS };
  state.schemaVersion = CALC_SCHEMA_VERSION;
  applyParamsToInputs();
  renderAll();
  persistAutosave();
});

document.getElementById("btnPrint").addEventListener("click", () => window.print());

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
  if (window.__pendingMigrationNotice) {
    setSaveStatus("Este proyecto se guardó con una versión anterior del método de cálculo; los resultados mostrados ya están recalculados con la metodología actual (ver README).");
    window.__pendingMigrationNotice = false;
  }
  if (!isDisclaimerAccepted()) {
    disclaimerDialog.showModal();
  }
}

init();
