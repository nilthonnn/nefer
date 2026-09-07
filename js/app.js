"use strict";

/* =========================================================================
 * Datos iniciales de la UI (el motor de cálculo vive en js/calc.js, cargado
 * antes que este archivo)
 * ========================================================================= */

const DEFAULT_ROWS = [
  { id: 1, desc: "Herramientas neumáticas de taller (promedio)", category: "tool_intermittent", flow: 4, unit: "cfm", qty: 3, usageFactorPct: 30, included: true },
  { id: 2, desc: "Instrumentación y control de planta", category: "instrumentation", flow: 0.3, unit: "m3min", qty: 10, usageFactorPct: 100, included: true },
  { id: 3, desc: "Sopladores de limpieza (blow guns)", category: "cleaning", flow: 5, unit: "cfm", qty: 2, usageFactorPct: 20, included: true },
  { id: 4, desc: "Cilindro/actuador neumático de proceso", category: "process", flow: 0.5, unit: "m3min", qty: 4, usageFactorPct: 60, included: true },
];

const DEFAULT_PARAMS = {
  projectName: "",
  clientName: "",
  preparedBy: "",
  driveType: "electric",
  altitude: 150,
  temp: 20,
  workingPressure: 7,
  margin: 20,
  compressorTech: "screw_oil",
  lineLoss: 0.5,
  includeStandby: false,
  dieselEngineTech: "turbo",
  mechanicalEfficiencyPct: 96,
  engineMarginPct: 15,
  specificFuelConsumptionGPerKWh: 210,
};

const STORAGE_KEY = "compressor-sizer:autosave";
const STORAGE_SAVED_KEY = "compressor-sizer:saved-project";
const STORAGE_DISCLAIMER_ACCEPTED_KEY = "compressor-sizer:disclaimer-accepted";

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
 * Render: tabla de demanda de aire
 * ========================================================================= */

const tableBody = document.getElementById("consumersTableBody");

function renderCategoryOptions(selected) {
  return Object.entries(CONSUMER_CATEGORY_PRESETS)
    .map(([key, preset]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${preset.label}</option>`)
    .join("");
}

function renderRows() {
  tableBody.innerHTML = "";
  state.rows.forEach((row) => {
    const computedRow = computeConsumerRow(row);
    const tr = document.createElement("tr");
    tr.dataset.id = String(row.id);
    tr.innerHTML = `
      <td><input type="text" data-field="desc" value="${escapeHtml(row.desc)}" placeholder="Descripción" /></td>
      <td>
        <select data-field="category">${renderCategoryOptions(row.category)}</select>
      </td>
      <td><input type="number" data-field="flow" value="${row.flow}" min="0" step="0.01" /></td>
      <td>
        <select data-field="unit">
          <option value="m3min" ${row.unit === "m3min" ? "selected" : ""}>m³/min</option>
          <option value="cfm" ${row.unit === "cfm" ? "selected" : ""}>CFM</option>
        </select>
      </td>
      <td><input type="number" data-field="qty" value="${row.qty}" min="0" step="1" /></td>
      <td><input type="number" data-field="usageFactorPct" value="${row.usageFactorPct}" min="0" max="100" step="1" /></td>
      <td class="readout">${formatNumber(computedRow.nominalM3min, 2)}</td>
      <td class="readout">${formatNumber(computedRow.effectiveM3min, 2)}</td>
      <td class="col-inc"><input type="checkbox" data-field="included" ${row.included !== false ? "checked" : ""} /></td>
      <td class="col-actions"><button class="row-remove-btn" data-action="remove" title="Eliminar fila">✕</button></td>
    `;
    tableBody.appendChild(tr);
  });
}

/* =========================================================================
 * Render: resultados
 * ========================================================================= */

function isDieselMobile() {
  return state.params.driveType === "diesel_mobile";
}

// El tipo de accionamiento no es una preferencia de vista (como las
// columnas avanzadas): es parte del modelo de cálculo (afecta qué motor se
// dimensiona y qué catálogo de marcas se filtra), así que sí viaja en
// guardar/exportar/importar, y también decide qué se imprime — a diferencia
// de "Parámetros avanzados" (que siempre imprime todo), los campos y
// resultados del motor diésel solo imprimen si el accionamiento elegido es
// diésel (ver [hidden] en css/styles.css).
function applyDriveTypeVisibility() {
  const diesel = isDieselMobile();
  const dieselBlock = document.getElementById("dieselAdvancedBlock");
  if (dieselBlock) dieselBlock.hidden = !diesel;

  document.querySelectorAll(".electric-only-tile").forEach((el) => { el.hidden = diesel; });
  document.querySelectorAll(".diesel-only-tile").forEach((el) => { el.hidden = !diesel; });

  const title = document.getElementById("brandMatchesTitle");
  if (title) title.textContent = diesel
    ? "Compresores portátiles diésel de referencia por marca, filtrados por CFM"
    : "Compresores estacionarios de referencia por marca, filtrados por CFM";

  const summary = document.getElementById("advancedParamsSummary");
  if (summary) summary.textContent = diesel
    ? "Parámetros avanzados (tecnología del compresor, caída de presión, respaldo, motor diésel)"
    : "Parámetros avanzados (tecnología del compresor, caída de presión, respaldo)";
}

function renderResults() {
  const summary = computeSummary(state.rows, state.params);
  applyDriveTypeVisibility();

  document.getElementById("statNominal").textContent = `${formatNumber(summary.sumNominal * M3MIN_TO_CFM, 0)} CFM`;
  document.getElementById("statNominalCFM").textContent = `${formatNumber(summary.sumNominal, 2)} m³/min`;

  document.getElementById("statEffective").textContent = `${formatNumber(summary.sumEffective * M3MIN_TO_CFM, 0)} CFM`;
  document.getElementById("statEffectiveDetail").textContent = summary.sumNominal > 0
    ? `${formatNumber((summary.sumEffective / summary.sumNominal) * 100, 0)}% del consumo nominal · ${formatNumber(summary.sumEffective, 2)} m³/min`
    : "sin consumidores registrados";

  document.getElementById("statDesignDemand").textContent = `${formatNumber(summary.designDemandM3min * M3MIN_TO_CFM, 0)} CFM`;
  document.getElementById("statDesignDemandDetail").textContent = `margen de seguridad ${formatNumber(state.params.margin, 0)}% · ${formatNumber(summary.designDemandM3min, 2)} m³/min`;

  document.getElementById("statSiteAtm").textContent = `${formatNumber(summary.siteAtmKPa, 1)} kPa abs`;
  document.getElementById("statSiteAtmDetail").textContent = `altitud ${formatNumber(state.params.altitude, 0)} msnm · ${formatNumber(state.params.temp, 0)} °C`;

  document.getElementById("statDischarge").textContent = `${formatNumber(summary.dischargeGaugeBar, 2)} bar(g)`;
  document.getElementById("statDischargeDetail").textContent =
    `${formatNumber(summary.workingPressureBar, 1)} bar trabajo + ${formatNumber(summary.lineLossBar, 1)} bar de línea/filtros/secador`;

  document.getElementById("statCompRatio").textContent = `${formatNumber(summary.compressionRatio, 2)}×`;
  document.getElementById("statCompRatioDetail").textContent = summary.stageWarning
    ? `⚠ excede el límite práctico de 1 etapa para ${summary.tech.label} (≤${formatNumber(summary.tech.maxSingleStageRatio, 1)}×) — considera compresión en 2 etapas`
    : `dentro del límite de 1 etapa para ${summary.tech.label} (≤${formatNumber(summary.tech.maxSingleStageRatio, 1)}×)`;

  document.getElementById("statDensity").textContent = `${formatNumber((1 - summary.densityFactor) * 100, 1)}%`;
  document.getElementById("statDensityDetail").textContent = "reducción de densidad del aire de succión vs. referencia ISO 1217 (100 kPa, 20°C)";

  document.getElementById("statCatalogFAD").textContent = `${formatNumber(summary.requiredCatalogFADcfm, 0)} CFM`;
  document.getElementById("statCatalogFADDetail").textContent = `≈ ${formatNumber(summary.requiredCatalogFADm3min, 2)} m³/min · caudal de catálogo (FAD) a pedir al fabricante`;

  document.getElementById("statPower").textContent = `${formatNumber(summary.shaftPowerKW, 1)} kW`;
  document.getElementById("statPowerDetail").textContent = `eficiencia global asumida ${formatNumber(summary.tech.overallEfficiency * 100, 0)}% (${summary.tech.label})`;

  document.getElementById("statSuggestedSize").textContent = `${formatNumber(summary.suggestedSizeKW, 1)} kW`;
  const standbyNote = state.params.includeStandby
    ? ` · con respaldo N+1: considera 2× ${formatNumber(summary.suggestedSizeKW, 1)} kW (o un esquema base + trim)`
    : "";
  document.getElementById("statSuggestedSizeDetail").textContent = (summary.sizeFits
    ? "primer tamaño de catálogo de referencia que cubre la potencia estimada"
    : "⚠ fuera del catálogo de referencia — se requiere una unidad mayor a medida") + standbyNote;

  const ds = summary.dieselSizing;
  document.getElementById("statDieselDerating").textContent = `${formatNumber(ds.engineDeratingPct, 1)}%`;
  document.getElementById("statDieselDeratingDetail").textContent = `${ds.engineTech.label} · independiente del derating de succión del compresor`;

  document.getElementById("statDieselPower").textContent = `${formatNumber(ds.ratedEngineKWNeeded, 1)} kW`;
  document.getElementById("statDieselPowerDetail").textContent = `${formatNumber(ds.ratedEngineHPNeeded, 0)} HP · incluye transmisión (${formatNumber(ds.mechanicalEfficiency * 100, 0)}%) y margen (${formatNumber(ds.engineMargin * 100, 0)}%)`;

  document.getElementById("statFuelConsumption").textContent = `${formatNumber(ds.fuelConsumptionLPerHour, 1)} L/h`;
  document.getElementById("statFuelConsumptionDetail").textContent = `≈ ${formatNumber(ds.specificFuelConsumptionGPerKWh, 0)} g/kWh a potencia nominal`;

  const mc = summary.suggestedMobileClass;
  document.getElementById("statMobileClass").textContent = `${formatNumber(mc.cfm, 0)} CFM @ ${formatNumber(mc.pressureBar, 1)} bar`;
  document.getElementById("statMobileClassDetail").textContent = mc.fits
    ? "primera clase de catálogo que cubre caudal y presión"
    : "⚠ fuera del catálogo de referencia — se requiere una unidad mayor a medida";

  renderBreakdown(summary);
  renderBrandMatches(summary);
  renderReportMeta(summary);
}

function renderBrandMatches(summary) {
  const hint = document.getElementById("brandMatchesHint");
  if (hint) {
    hint.innerHTML = isDieselMobile()
      ? `Líneas de compresores <strong>portátiles a diésel</strong> reales (no un modelo puntual) cuyo rango de caudal publicado cubre — o está cerca de — la capacidad de catálogo requerida (<span id="matchTargetCFM">${formatNumber(summary.requiredCatalogFADcfm, 0)}</span> CFM). Confirma siempre el modelo exacto, la presión, la potencia del motor y el caudal certificado con el fabricante o distribuidor antes de comprar o alquilar.`
      : `Líneas de producto reales (no un modelo puntual) cuyo rango de capacidad publicado cubre — o está cerca de — la capacidad de catálogo requerida (<span id="matchTargetCFM">${formatNumber(summary.requiredCatalogFADcfm, 0)}</span> CFM). Confirma siempre el modelo exacto, la presión y el caudal certificado con el fabricante o distribuidor antes de comprar.`;
  }

  const container = document.getElementById("brandMatches");
  container.innerHTML = "";

  if (summary.requiredCatalogFADcfm <= 0) {
    container.innerHTML = '<p class="brand-match-empty">Agrega consumidores en la tabla para ver qué líneas de compresores cubren la capacidad requerida.</p>';
    return;
  }

  const matches = isDieselMobile() ? summary.matchingMobileDieselModels : summary.matchingBrandModels;
  if (matches.length === 0) {
    container.innerHTML = '<p class="brand-match-empty">Ninguna línea de este catálogo de referencia cubre esta capacidad — consulta directamente con el fabricante/distribuidor para un equipo fuera de este rango.</p>';
    return;
  }

  container.innerHTML = matches.map((m) => `
    <div class="brand-match ${m.exactFit ? "is-exact" : ""}">
      <div class="brand-match-info">
        <span class="brand-match-name">${escapeHtml(m.brand)}</span>
        <span class="brand-match-line">${escapeHtml(m.line)}</span>
      </div>
      <span class="brand-match-range">${formatNumber(m.cfmMin, 0)}–${formatNumber(m.cfmMax, 0)} CFM${m.exactFit ? " · dentro de rango" : " · cercano"}</span>
    </div>
  `).join("");
}

function renderReportMeta(summary) {
  const today = new Date().toLocaleDateString("es");
  document.getElementById("coverProject").textContent = state.params.projectName || "—";
  document.getElementById("coverClient").textContent = state.params.clientName || "—";
  document.getElementById("coverDate").textContent = today;
  document.getElementById("coverPreparedBy").textContent = state.params.preparedBy || "—";
  document.getElementById("coverCapacity").textContent = isDieselMobile()
    ? `${formatNumber(summary.suggestedMobileClass.cfm, 0)} CFM @ ${formatNumber(summary.suggestedMobileClass.pressureBar, 1)} bar — motor diésel ${formatNumber(summary.dieselSizing.ratedEngineKWNeeded, 0)} kW (${formatNumber(summary.dieselSizing.ratedEngineHPNeeded, 0)} HP)`
    : `${formatNumber(summary.requiredCatalogFADcfm, 0)} CFM FAD @ ${formatNumber(summary.dischargeGaugeBar, 1)} bar — ${formatNumber(summary.suggestedSizeKW, 1)} kW`;
  document.getElementById("sigPreparedBy").textContent = state.params.preparedBy || "";
  document.getElementById("sigDate").textContent = today;
}

function renderBreakdown(summary) {
  const container = document.getElementById("breakdownBars");
  container.innerHTML = "";

  if (summary.computed.length === 0) {
    container.innerHTML = '<p class="hint">Agrega consumidores en la tabla para ver el desglose.</p>';
    return;
  }

  const maxValue = Math.max(...summary.computed.map((c) => c.nominalM3min), 1e-9);

  summary.computed.forEach((c) => {
    const runRow = document.createElement("div");
    runRow.className = "bar-row";
    runRow.innerHTML = `
      <span class="bar-label" title="${escapeHtml(c.desc)}">${escapeHtml(c.desc || "(sin nombre)")}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${(c.effectiveM3min / maxValue) * 100}%"></span></span>
      <span class="bar-value">${formatNumber(c.effectiveM3min * M3MIN_TO_CFM, 0)} CFM</span>
    `;
    container.appendChild(runRow);

    if (c.nominalM3min > c.effectiveM3min + 1e-6) {
      const nominalRow = document.createElement("div");
      nominalRow.className = "bar-row";
      nominalRow.innerHTML = `
        <span class="bar-label">&nbsp;&nbsp;↳ nominal (sin factor de uso)</span>
        <span class="bar-track"><span class="bar-fill is-nominal" style="width:${(c.nominalM3min / maxValue) * 100}%"></span></span>
        <span class="bar-value">${formatNumber(c.nominalM3min * M3MIN_TO_CFM, 0)} CFM</span>
      `;
      container.appendChild(nominalRow);
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
    category: "process",
    flow: 1,
    unit: "m3min",
    qty: 1,
    usageFactorPct: 100,
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
  } else if (field === "category") {
    row.category = e.target.value;
    const preset = CONSUMER_CATEGORY_PRESETS[row.category];
    if (preset) row.usageFactorPct = preset.defaultUsageFactorPct;
  } else {
    row[field] = e.target.value;
  }

  // Categoría requiere re-render completo de la fila: cambia el factor de
  // uso sugerido que se muestra en el input.
  if (field === "category") {
    renderRows();
  } else {
    updateRowReadouts(tr, row);
  }
  renderResults();
  persistAutosave();
});

function updateRowReadouts(tr, row) {
  const computedRow = computeConsumerRow(row);
  const cells = tr.querySelectorAll("td.readout");
  cells[0].textContent = formatNumber(computedRow.nominalM3min, 2);
  cells[1].textContent = formatNumber(computedRow.effectiveM3min, 2);
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
  driveType: document.getElementById("driveType"),
  altitude: document.getElementById("altitude"),
  temp: document.getElementById("temp"),
  workingPressure: document.getElementById("workingPressure"),
  margin: document.getElementById("margin"),
  compressorTech: document.getElementById("compressorTech"),
  lineLoss: document.getElementById("lineLoss"),
  dieselEngineTech: document.getElementById("dieselEngineTech"),
  mechanicalEfficiencyPct: document.getElementById("mechanicalEfficiencyPct"),
  engineMarginPct: document.getElementById("engineMarginPct"),
  specificFuelConsumptionGPerKWh: document.getElementById("specificFuelConsumptionGPerKWh"),
};

Object.entries(paramInputs).forEach(([key, el]) => {
  if (!el) return;
  el.addEventListener("input", () => {
    state.params[key] = el.value;
    renderResults();
    persistAutosave();
  });
});

const includeStandbyEl = document.getElementById("includeStandby");
if (includeStandbyEl) {
  includeStandbyEl.addEventListener("change", () => {
    state.params.includeStandby = includeStandbyEl.checked;
    renderResults();
    persistAutosave();
  });
}

// Selector de ubicación de referencia (Perú): solo un atajo de UI que
// rellena "Altitud del sitio" con un valor típico; el usuario puede seguir
// editando la altitud libremente después. No forma parte del estado
// guardado del proyecto (igual que la preferencia de columnas avanzadas).
const locationPresetEl = document.getElementById("locationPreset");
function populateLocationPresets() {
  if (!locationPresetEl) return;
  locationPresetEl.innerHTML = '<option value="">— Elegir para rellenar la altitud —</option>' +
    PERU_LOCATION_PRESETS.map((p, idx) => `<option value="${idx}">${escapeHtml(p.label)}</option>`).join("");
}
if (locationPresetEl) {
  locationPresetEl.addEventListener("change", () => {
    const preset = PERU_LOCATION_PRESETS[Number(locationPresetEl.value)];
    if (!preset) return;
    state.params.altitude = preset.altitude;
    paramInputs.altitude.value = preset.altitude;
    renderResults();
    persistAutosave();
  });
}

function applyParamsToInputs() {
  Object.entries(paramInputs).forEach(([key, el]) => {
    if (!el) return;
    el.value = state.params[key];
  });
  if (includeStandbyEl) includeStandbyEl.checked = !!state.params.includeStandby;
}

/* =========================================================================
 * Persistencia: autosave, guardar/cargar, import/export
 * ========================================================================= */

function migrateLoadedState(parsed) {
  const loadedVersion = Number(parsed.schemaVersion) || 0;
  state.rows = parsed.rows || [];
  state.params = { ...DEFAULT_PARAMS, ...parsed.params };
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
  downloadBlob(blob, `${slugify(state.params.projectName) || "proyecto-compresor"}.json`);
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
  "Descripcion", "Categoria", "Caudal", "Unidad", "Cantidad", "FactorUsoPct", "m3min_nominal", "m3min_efectivo", "Incluida",
];

document.getElementById("btnExportCSV").addEventListener("click", () => {
  const lines = [CSV_HEADER.join(",")];
  state.rows.forEach((row) => {
    const c = computeConsumerRow(row);
    lines.push([
      csvEscape(row.desc),
      row.category || "",
      row.flow,
      row.unit,
      row.qty,
      row.usageFactorPct,
      c.nominalM3min.toFixed(3),
      c.effectiveM3min.toFixed(3),
      row.included !== false ? "si" : "no",
    ].join(","));
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `${slugify(state.params.projectName) || "demanda-aire-comprimido"}.csv`);
});

// ---- Importación de CSV de demanda ----
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
  caudal: "flow", flujo: "flow", consumo: "flow",
  unidad: "unit",
  cantidad: "qty", cant: "qty",
  factorusopct: "usageFactorPct", factordeuso: "usageFactorPct", simultaneidad: "usageFactorPct",
  incluida: "included",
};

function normalizeHeaderKey(key) {
  return String(key || "").trim().toLowerCase().replace(/\s+/g, "");
}

function findCategoryKeyByLabel(label) {
  const found = Object.entries(CONSUMER_CATEGORY_PRESETS).find(([, p]) => p.label.toLowerCase() === label.toLowerCase());
  return found ? found[0] : null;
}

function importConsumersFromCSV(text) {
  const table = parseCSV(text);
  if (table.length < 2) return { imported: [], skipped: 0 };

  const headerKeys = table[0].map((h) => CSV_HEADER_ALIASES[normalizeHeaderKey(h)] || normalizeHeaderKey(h));
  const imported = [];
  let skipped = 0;

  for (let i = 1; i < table.length; i++) {
    const cells = table[i];
    const record = {};
    headerKeys.forEach((key, idx) => { record[key] = cells[idx] !== undefined ? cells[idx].trim() : ""; });

    const flow = toNumber(record.flow, NaN);
    if (!record.desc || !Number.isFinite(flow)) { skipped++; continue; }

    const unit = (record.unit || "m3min").toLowerCase() === "cfm" ? "cfm" : "m3min";
    const categoryKey = CONSUMER_CATEGORY_PRESETS[record.category]
      ? record.category
      : (findCategoryKeyByLabel(record.category) || "process");

    imported.push({
      id: nextRowId(),
      desc: record.desc,
      category: categoryKey,
      flow,
      unit,
      qty: Math.max(0, toNumber(record.qty, 1)),
      usageFactorPct: clamp(toNumber(record.usageFactorPct, CONSUMER_CATEGORY_PRESETS[categoryKey].defaultUsageFactorPct), 0, 100),
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
    const { imported, skipped } = importConsumersFromCSV(String(reader.result));
    if (imported.length === 0) {
      setSaveStatus("No se encontraron filas válidas en el CSV.");
      return;
    }
    const replace = confirm(
      `Se leyeron ${imported.length} consumidor(es) válido(s)${skipped ? ` (${skipped} fila(s) omitida(s) por datos incompletos)` : ""}.\n\n` +
      `Aceptar = reemplazar la tabla de demanda actual.\nCancelar = agregarlos al final de la tabla actual.`
    );
    state.rows = replace ? imported : [...state.rows, ...imported];
    renderAll();
    persistAutosave();
    setSaveStatus(`Importación completa: ${imported.length} consumidor(es)${skipped ? `, ${skipped} omitida(s)` : ""}.`);
  };
  reader.readAsText(file);
  e.target.value = "";
});

/* =========================================================================
 * Librería de consumos (modal)
 * ========================================================================= */

const libraryDialog = document.getElementById("libraryDialog");
const libSearchInput = document.getElementById("libSearch");
const libCategorySelect = document.getElementById("libCategoryFilter");
const libListEl = document.getElementById("libList");

// Íconos por grupo: SVG en línea, minimalistas (solo trazo, sin relleno) y
// mínimos en bytes — nada de librerías de íconos ni peticiones externas, para
// no sumar peso ni dependencias a una app que ya es 100% sin build.
const LIBRARY_GROUP_ICON_PATHS = {
  "Herramientas de taller": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2Z"/>',
  "Minería subterránea": '<path d="M3 21 12 3l9 18Z"/><path d="M8 15h8"/>',
  "Construcción": '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>',
  "Pintura y acabados": '<path d="M4 21c1.5-4 3-6 6-6s4 2 4 4-2 3-3 2 0-3 2-3c3 0 5-2 7-6"/><circle cx="18" cy="6" r="2"/>',
  "Instrumentación y control": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
  "Proceso industrial": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11Z"/>',
};
const LIBRARY_GROUP_ICON_FALLBACK = '<circle cx="12" cy="12" r="1.4"/>';

function libraryGroupIcon(group) {
  const paths = LIBRARY_GROUP_ICON_PATHS[group] || LIBRARY_GROUP_ICON_FALLBACK;
  return `<svg class="lib-group-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

function libraryItemToRow(item) {
  const preset = CONSUMER_CATEGORY_PRESETS[item.category];
  return {
    id: nextRowId(),
    desc: item.name,
    category: item.category,
    flow: item.flow,
    unit: item.unit,
    qty: 1,
    usageFactorPct: preset ? preset.defaultUsageFactorPct : 100,
    included: true,
  };
}

function formatLibrarySpec(item) {
  const flowLabel = `${formatNumber(item.flow, item.unit === "cfm" ? 1 : 2)} ${item.unit === "cfm" ? "CFM" : "m³/min"}`;
  const preset = CONSUMER_CATEGORY_PRESETS[item.category];
  const parts = [flowLabel];
  if (preset) parts.push(`uso típico ${preset.defaultUsageFactorPct}%`);
  if (item.note) parts.push(item.note);
  return parts.join(" · ");
}

function populateLibraryCategoryFilter() {
  const groups = [...new Set(CONSUMER_LIBRARY.map((item) => item.group))];
  libCategorySelect.innerHTML = '<option value="">Todos los grupos</option>' +
    groups.map((g) => `<option value="${escapeHtml(g)}">${escapeHtml(g)}</option>`).join("");
}

function renderLibraryList() {
  const query = libSearchInput.value.trim().toLowerCase();
  const groupFilter = libCategorySelect.value;

  const filtered = CONSUMER_LIBRARY.filter((item) => {
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
      const globalIdx = CONSUMER_LIBRARY.indexOf(item);
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
  const item = CONSUMER_LIBRARY[Number(btn.dataset.libIndex)];
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
const btnCloseDisclaimer = document.getElementById("btnCloseDisclaimer");

function isDisclaimerAccepted() {
  try {
    return localStorage.getItem(STORAGE_DISCLAIMER_ACCEPTED_KEY) === "1";
  } catch (e) {
    return false;
  }
}

// Antes de aceptar, este es un modal de consentimiento real: no debe poder
// cerrarse con "✕" ni con Escape, solo con "Entiendo y acepto" — si no, un
// usuario podría operar la app entera (incluido imprimir un informe) en la
// misma sesión sin haber confirmado que leyó el aviso. Una vez aceptado,
// reabrirlo desde el pie de página es solo para releerlo, así que ahí sí se
// puede cerrar libremente.
function updateDisclaimerCloseability() {
  btnCloseDisclaimer.hidden = !isDisclaimerAccepted();
}

disclaimerDialog.addEventListener("cancel", (e) => {
  if (!isDisclaimerAccepted()) e.preventDefault();
});

document.getElementById("btnAcceptDisclaimer").addEventListener("click", () => {
  try {
    localStorage.setItem(STORAGE_DISCLAIMER_ACCEPTED_KEY, "1");
  } catch (e) {
    // Se ignora silenciosamente si localStorage no está disponible; el aviso
    // simplemente volverá a mostrarse en la próxima visita.
  }
  updateDisclaimerCloseability();
  disclaimerDialog.close();
});

btnCloseDisclaimer.addEventListener("click", () => disclaimerDialog.close());
document.getElementById("btnOpenDisclaimer").addEventListener("click", () => {
  updateDisclaimerCloseability();
  disclaimerDialog.showModal();
});

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
  populateLocationPresets();
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
  updateDisclaimerCloseability();
  if (!isDisclaimerAccepted()) {
    disclaimerDialog.showModal();
  }
}

init();
