/* Ruta aplicada: grupos electrógenos y plantas mineras.
   Además de las lecciones, este archivo trae los MODELOS DE PLANTA: cada ciclo,
   antes de que el PLC lea sus entradas, el modelo mira las salidas del ciclo
   anterior y mueve el proceso (el grupo gana velocidad, el interruptor cierra
   80 ms después de la orden, el ángulo de fase gira...). Así los retos se
   corrigen contra un proceso que responde, no contra entradas fijas. */

NIVELES.push({ id: "energia", nombre: "Grupos y minería", desc: "Grupos electrógenos, TTA, sincronismo, fajas y bombas de planta." });

/* ---------- utilidades de dibujo para los HMI ---------- */
var HM = {
  ln: function (x1, y1, x2, y2, on, w) { return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" style="stroke:' + (on ? "var(--on)" : "var(--ink3)") + ";stroke-width:" + (on ? (w || 4) : 2) + ';stroke-linecap:round"/>'; },
  tx: function (x, y, s, o) { o = o || {}; return '<text x="' + x + '" y="' + y + '" style="fill:' + (o.c || "var(--ink)") + ";font-size:" + (o.s || 11) + "px;font-weight:" + (o.w || 500) + ";text-anchor:" + (o.a || "middle") + (o.m ? ";font-family:var(--mono)" : "") + '">' + s + "</text>"; },
  /* interruptor: rojo = cerrado, verde = abierto (convención ANSI de los HMI de subestación) */
  brk: function (x, y, closed, name) {
    return '<rect x="' + (x - 10) + '" y="' + (y - 10) + '" width="20" height="20" rx="3" style="fill:' + (closed ? "var(--bad)" : "var(--canvas)") + ";stroke:" + (closed ? "var(--bad)" : "var(--on)") + ';stroke-width:2.5"/>' +
      HM.tx(x + 16, y + 4, name, { a: "start", w: 700, s: 11 }) + HM.tx(x + 16, y + 16, closed ? "cerrado" : "abierto", { a: "start", s: 9.5, c: closed ? "var(--bad)" : "var(--on)" });
  },
  gen: function (x, y, on, lbl) {
    return '<circle cx="' + x + '" cy="' + y + '" r="17" style="fill:' + (on ? "var(--good2)" : "var(--canvas)") + ";stroke:" + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:2.5"/>' +
      HM.tx(x, y + 5, "G~", { w: 800, s: 13, c: on ? "var(--on)" : "var(--ink2)" }) + (lbl ? HM.tx(x, y - 24, lbl, { w: 700 }) : "");
  },
  lamp: function (x, y, on, lbl, col) { return '<circle cx="' + x + '" cy="' + y + '" r="7" style="fill:' + (on ? (col || "#FFC83D") : "var(--lamp)") + ';stroke:var(--line)"/>' + HM.tx(x + 12, y + 4, lbl, { a: "start", s: 10.5 }); },
  falla: function (e, y) { return e.fault ? '<rect x="4" y="' + (y - 15) + '" width="392" height="22" rx="5" style="fill:var(--bad2)"/>' + HM.tx(200, y, "⚠ " + e.fault.replace(/&/g, "&amp;").replace(/</g, "&lt;"), { c: "var(--bad)", w: 700, s: 10.5 }) : ""; },
  svg: function (h, body) { return '<svg viewBox="0 0 400 ' + h + '" role="img" aria-label="Pantalla HMI del proceso">' + body + "</svg>"; }
};
/* interruptor con tiempo de maniobra: la realimentación sigue a la orden */
function maniobra(e, s, k, orden, fb, ms, permitido) {
  var quiere = !!e.v[orden] && permitido !== false, esta = !!e.forced[fb];
  if (quiere !== esta) { s[k] = (s[k] || 0) + e.dt; if (s[k] >= ms) { e.forced[fb] = quiere ? 1 : 0; s[k] = 0; } } else s[k] = 0;
}

var PLANTAS = {
  /* ---- grupo electrógeno: presión de aceite que sube 3 s después de arrancar ---- */
  grupo: {
    model: function (e) { var s = e.ps; if (e.v["%Q0.0"]) s.run = (s.run || 0) + e.dt; else s.run = 0;
      e.forced["%I0.2"] = (s.run >= 3000 && !e.pressed["%I0.2"]) ? 1 : 0; },
    hmi: function (e) {
      var s = e.ps, run = s.run || 0, rpm = run ? Math.min(1800, Math.round(run / 1500 * 1800)) : 0;
      if (e.v["%I0.4"]) rpm = 2050;
      var a = -120 + 240 * Math.min(rpm, 2100) / 2100, cx = 80, cy = 82, r = 52, pr = e.forced["%I0.2"] ? 1 : 0;
      var arc = ""; for (var i = 0; i <= 7; i++) { var t = (-120 + i * 240 / 7) * Math.PI / 180;
        arc += '<line x1="' + (cx + 44 * Math.sin(t)) + '" y1="' + (cy - 44 * Math.cos(t)) + '" x2="' + (cx + 52 * Math.sin(t)) + '" y2="' + (cy - 52 * Math.cos(t)) + '" style="stroke:var(--ink3);stroke-width:2"/>'; }
      var ar = a * Math.PI / 180;
      return HM.svg(170, '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" style="fill:var(--box);stroke:var(--line)"/>' + arc +
        '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + 46 * Math.sin(ar)) + '" y2="' + (cy - 46 * Math.cos(ar)) + '" style="stroke:' + (rpm > 1980 ? "var(--bad)" : "var(--acc)") + ';stroke-width:3.5;stroke-linecap:round"/>' +
        HM.tx(cx, cy + 26, rpm + " rpm", { w: 800, m: 1 }) + HM.tx(cx, cy + 40, "1800 rpm = 60 Hz", { s: 9, c: "var(--ink3)" }) +
        HM.tx(170, 26, "Grupo electrógeno G1", { a: "start", w: 800, s: 12 }) +
        HM.lamp(178, 48, e.v["%Q0.0"], "Solenoide de combustible", "var(--on)") +
        HM.lamp(178, 70, pr, pr ? "Presión de aceite OK" : (run ? "Presión de aceite BAJA" : "Sin presión (parado)"), pr ? "var(--on)" : "#FFC83D") +
        HM.lamp(178, 92, e.v["%I0.3"], "Temperatura de refrigerante alta", "var(--bad)") +
        HM.lamp(178, 114, e.v["%I0.4"], "Sobrevelocidad", "var(--bad)") +
        HM.lamp(178, 136, e.v["%Q0.1"], "ALARMA · parada por protección", "var(--bad)") + HM.falla(e, 162));
    }
  },
  /* ---- TTA: grupo que tarda 3 s en dar tensión e interruptores de 100 ms ---- */
  tta: {
    model: function (e) { var s = e.ps;
      if (e.v["%Q0.0"]) s.run = (s.run || 0) + e.dt; else s.run = 0;
      var gok = s.run >= 3000 && !e.pressed["%I0.1"];
      e.forced["%I0.1"] = gok ? 1 : 0;
      maniobra(e, s, "tr", "%Q0.1", "%I0.2", 100);
      maniobra(e, s, "tg", "%Q0.2", "%I0.3", 100, gok);
      if (!gok && e.forced["%I0.3"]) e.forced["%I0.3"] = 0;
      if (e.forced["%I0.2"] && e.forced["%I0.3"]) e.fault = "52R y 52G cerrados a la vez: la red queda en paralelo con el grupo sin sincronizar";
    },
    hmi: function (e) {
      var red = !!e.v["%I0.0"], g = !!e.forced["%I0.1"], r52 = !!e.forced["%I0.2"], g52 = !!e.forced["%I0.3"], run = e.ps.run || 0;
      var barra = (red && r52) || (g && g52), fuente = red && r52 ? "RED" : g && g52 ? "GRUPO" : "SIN ENERGÍA";
      var est = !e.v["%Q0.0"] ? "Parado" : !g ? "Arrancando… " + (run / 1000).toFixed(1) + " s" : g52 ? "En carga" : "En vacío (enfriamiento)";
      return HM.svg(200,
        '<rect x="62" y="10" width="56" height="30" rx="5" style="fill:' + (red ? "var(--good2)" : "var(--bad2)") + ";stroke:" + (red ? "var(--on)" : "var(--bad)") + ';stroke-width:2"/>' +
        HM.tx(90, 30, "RED", { w: 800, c: red ? "var(--on)" : "var(--bad)" }) + HM.tx(124, 30, red ? "tensión OK" : "FALLA DE RED", { a: "start", s: 9.5, w: 700, c: red ? "var(--ink3)" : "var(--bad)" }) +
        HM.ln(90, 40, 90, 66, red) + HM.brk(90, 76, r52, "52R") + HM.ln(90, 86, 90, 112, red && r52) +
        HM.gen(310, 30, g, "") + HM.tx(286, 34, est, { a: "end", s: 9.5, w: 700, c: g ? "var(--on)" : "var(--ink2)" }) +
        HM.ln(310, 47, 310, 66, g) + HM.brk(310, 76, g52, "52G") + HM.ln(310, 86, 310, 112, g && g52) +
        HM.ln(50, 112, 350, 112, barra, 6) + HM.tx(355, 116, "Barra", { a: "start", s: 9.5, c: "var(--ink3)" }) +
        HM.ln(200, 112, 200, 140, barra) + '<path d="M192 138 L200 150 L208 138 Z" style="fill:' + (barra ? "var(--on)" : "var(--ink3)") + '"/>' +
        HM.tx(200, 166, "Cargas críticas: chancado, bombas, sala eléctrica", { s: 10, c: "var(--ink2)" }) +
        HM.tx(200, 186, "Alimentadas por: " + fuente, { w: 800, s: 12, c: barra ? "var(--on)" : "var(--bad)" }) + HM.falla(e, 196));
    }
  },
  /* ---- sincronismo: G2 contra barra viva a 60 Hz; ángulo que gira con el deslizamiento ---- */
  sincro: {
    model: function (e) { var s = e.ps, fb = 6000;
      if (s.f2 == null) { s.f2 = 5940; s.ph = 150; }
      var cerrado = !!e.forced["%I0.2"];
      if (cerrado) { s.f2 = fb; s.ph = 0; }
      else {
        if (e.v["%Q0.1"]) s.f2 += 40 * e.dt / 1000;
        if (e.v["%Q0.2"]) s.f2 -= 40 * e.dt / 1000;
        s.f2 = Math.max(5700, Math.min(6300, s.f2));
        s.ph += 360 * ((s.f2 - fb) / 100) * e.dt / 1000; s.ph = ((s.ph + 180) % 360 + 360) % 360 - 180;
      }
      var orden = !!e.v["%Q0.0"];
      if (orden && !cerrado) { s.tc = (s.tc || 0) + e.dt;
        if (s.tc >= 80) { s.tc = 0; var df = s.f2 - fb;
          if (Math.abs(s.ph) > 15) e.fault = "Cierre fuera de sincronismo: Δφ = " + Math.round(s.ph) + "° al cerrar (máx. ±15°)";
          else if (df < -5 || df > 15) e.fault = "Cierre con deslizamiento fuera de ventana: Δf = " + (df / 100).toFixed(2) + " Hz";
          else if (!e.v["%I0.1"]) e.fault = "Cierre con diferencia de tensión fuera de rango (Tension_OK = 0)";
          e.forced["%I0.2"] = 1; } }
      else if (!orden && cerrado) { e.forced["%I0.2"] = 0; s.tc = 0; }
      else s.tc = 0;
      e.ana["%IW64"] = fb; e.ana["%IW66"] = Math.round(s.f2); e.ana["%IW68"] = Math.round(s.ph);
    },
    hmi: function (e) {
      var s = e.ps, ph = s.ph || 0, f2 = s.f2 || 5940, df = (f2 - 6000) / 100, cx = 95, cy = 92, r = 62, cerrado = !!e.forced["%I0.2"];
      var marks = ""; for (var a = 0; a < 360; a += 30) { var t = a * Math.PI / 180;
        marks += '<line x1="' + (cx + (r - 8) * Math.sin(t)) + '" y1="' + (cy - (r - 8) * Math.cos(t)) + '" x2="' + (cx + r * Math.sin(t)) + '" y2="' + (cy - r * Math.cos(t)) + '" style="stroke:var(--ink3);stroke-width:2"/>'; }
      var w = 10 * Math.PI / 180, sector = '<path d="M' + cx + " " + cy + " L" + (cx + r * Math.sin(-w)) + " " + (cy - r * Math.cos(-w)) + " A" + r + " " + r + " 0 0 1 " + (cx + r * Math.sin(w)) + " " + (cy - r * Math.cos(w)) + ' Z" style="fill:var(--good2);stroke:var(--on)"/>';
      var pr = ph * Math.PI / 180, ok = Math.abs(ph) <= 10;
      return HM.svg(190, '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" style="fill:var(--box);stroke:var(--line);stroke-width:2"/>' + sector + marks +
        '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + (r - 6) * Math.sin(pr)) + '" y2="' + (cy - (r - 6) * Math.cos(pr)) + '" style="stroke:' + (ok ? "var(--on)" : "var(--acc)") + ';stroke-width:4;stroke-linecap:round"/>' +
        '<circle cx="' + cx + '" cy="' + cy + '" r="5" style="fill:var(--ink)"/>' +
        HM.tx(cx - 50, cy + 74, "⟲ lento", { s: 9.5, c: "var(--ink3)" }) + HM.tx(cx + 50, cy + 74, "rápido ⟳", { s: 9.5, c: "var(--ink3)" }) + HM.tx(cx, 22, "SINCRONOSCOPIO", { s: 9, w: 800, c: "var(--ink3)" }) +
        HM.tx(190, 28, "Barra (G1 en servicio)", { a: "start", s: 10, c: "var(--ink2)" }) + HM.tx(390, 28, "60.00 Hz", { a: "end", w: 800, m: 1 }) +
        HM.tx(190, 48, "G2 entrante", { a: "start", s: 10, c: "var(--ink2)" }) + HM.tx(390, 48, (f2 / 100).toFixed(2) + " Hz", { a: "end", w: 800, m: 1 }) +
        HM.tx(190, 68, "Deslizamiento Δf", { a: "start", s: 10, c: "var(--ink2)" }) + HM.tx(390, 68, (df >= 0 ? "+" : "") + df.toFixed(2) + " Hz", { a: "end", w: 800, m: 1, c: df >= 0 && df <= 0.1 ? "var(--on)" : "var(--ink)" }) +
        HM.tx(190, 88, "Ángulo Δφ", { a: "start", s: 10, c: "var(--ink2)" }) + HM.tx(390, 88, Math.round(ph) + "°", { a: "end", w: 800, m: 1, c: ok ? "var(--on)" : "var(--ink)" }) +
        HM.lamp(196, 110, e.v["%Q0.1"], "Subir velocidad ▲", "var(--acc)") + HM.lamp(330, 110, e.v["%Q0.2"], "Bajar ▼", "var(--acc)") +
        HM.lamp(196, 130, e.v["%I0.1"], "ΔV dentro de rango", "var(--on)") +
        HM.brk(206, 156, cerrado, "52G2") + HM.tx(290, 160, cerrado ? "G2 en paralelo" : "G2 fuera de barra", { a: "start", s: 10, w: 700, c: cerrado ? "var(--on)" : "var(--ink2)" }) +
        HM.falla(e, 185));
    }
  },
  /* ---- arranque por demanda: G2 tarda 4 s en arrancar, sincronizar y entrar en barra ---- */
  demanda: {
    model: function (e) { var s = e.ps; if (e.v["%Q0.0"]) s.t = (s.t || 0) + e.dt; else s.t = 0; e.forced["%I0.0"] = s.t >= 4000 ? 1 : 0; },
    hmi: function (e) {
      var kw = e.ana["%IW64"] | 0, g2 = !!e.forced["%I0.0"], n = g2 ? 2 : 1, cap = n * 1000, pu = Math.round(kw / n / 10);
      var X = function (v) { return 30 + 340 * Math.min(v, 2000) / 2000; }, sob = kw > cap;
      var est2 = g2 ? "En barra · " + pu + " %" : e.v["%Q0.0"] ? "Arrancando / sincronizando…" : "Parado (reserva)";
      return HM.svg(170, HM.gen(60, 38, true, "") + HM.tx(84, 34, "G1 · 1000 kW", { a: "start", w: 700 }) + HM.tx(84, 48, "En barra · " + Math.round(kw / n / 10) + " %", { a: "start", s: 10, c: pu > 100 ? "var(--bad)" : "var(--on)" }) +
        HM.gen(240, 38, g2, "") + HM.tx(264, 34, "G2 · 1000 kW", { a: "start", w: 700 }) + HM.tx(264, 48, est2, { a: "start", s: 10, c: g2 ? "var(--on)" : "var(--ink2)" }) +
        '<rect x="30" y="82" width="340" height="22" rx="4" style="fill:var(--box);stroke:var(--line)"/>' +
        '<rect x="30" y="82" width="' + (X(kw) - 30) + '" height="22" rx="4" style="fill:' + (sob ? "var(--bad)" : "var(--acc)") + ';opacity:.85"/>' +
        [[700, "parar G2"], [800, "arrancar G2"], [1000, "límite G1"]].map(function (m, i) { var x = X(m[0]);
          return '<line x1="' + x + '" y1="76" x2="' + x + '" y2="110" style="stroke:var(--ink);stroke-dasharray:3 2"/>' + HM.tx(x, 122 + (i % 2) * 11, m[0] + " · " + m[1], { s: 8.5, c: "var(--ink2)" }); }).join("") +
        HM.tx(30, 72, "Demanda de la planta: " + kw + " kW", { a: "start", w: 800, s: 11.5 }) + HM.tx(370, 72, "capacidad en línea " + cap + " kW", { a: "end", s: 10, c: sob ? "var(--bad)" : "var(--ink2)" }) +
        HM.lamp(30, 152, e.v["%Q0.1"], "Deslastre de cargas no esenciales", "var(--bad)") + HM.falla(e, 166));
    }
  },
  /* ---- fajas: solo HMI (el proceso lo mueven los pulsadores y los pull-cord) ---- */
  faja: {
    hmi: function (e) {
      var off = -((e.t / 25) % 20), belt = function (x1, y1, x2, y2, on, n) {
        return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" style="stroke:' + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:9;stroke-linecap:round;opacity:.25"/>' +
          '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" style="stroke:' + (on ? "var(--on)" : "var(--ink3)") + ";stroke-width:3;stroke-dasharray:10 10;stroke-dashoffset:" + (on ? off : 0) + '"/>' +
          '<circle cx="' + x1 + '" cy="' + y1 + '" r="6" style="fill:var(--canvas);stroke:var(--ink2);stroke-width:2"/><circle cx="' + x2 + '" cy="' + y2 + '" r="6" style="fill:var(--canvas);stroke:var(--ink2);stroke-width:2"/>' +
          HM.tx((x1 + x2) / 2, Math.max(y1, y2) + 24, n, { w: 700, s: 10.5 }) + HM.tx((x1 + x2) / 2, Math.max(y1, y2) + 36, on ? "marcha" : "parada", { s: 9.5, c: on ? "var(--on)" : "var(--ink3)" });
      };
      var sir = e.v["%Q0.0"] && Math.floor(e.t / 300) % 2 === 0, pc2 = !e.v["%I0.2"], pc1 = !e.v["%I0.3"];
      return HM.svg(175, '<path d="M14 40 L66 40 L56 70 L24 70 Z" style="fill:var(--box);stroke:var(--ink2);stroke-width:2"/>' + HM.tx(40, 32, "Tolva", { s: 9.5, c: "var(--ink2)" }) +
        belt(30, 84, 80, 84, e.v["%Q0.3"], "Alimentador") + belt(100, 112, 220, 84, e.v["%Q0.2"], "CV‑01") + belt(240, 92, 345, 56, e.v["%Q0.1"], "CV‑02") +
        '<path d="M335 130 L370 66 L398 130 Z" style="fill:var(--box);stroke:var(--ink2);stroke-width:2"/>' + HM.tx(372, 146, "Pila de", { s: 9.5, c: "var(--ink2)" }) + HM.tx(372, 157, "gruesos", { s: 9.5, c: "var(--ink2)" }) +
        '<g transform="translate(150 22)"><path d="M0 6 h6 l8 -6 v20 l-8 -6 h-6 z" style="fill:' + (e.v["%Q0.0"] ? "#FFC83D" : "var(--lamp)") + ';stroke:var(--ink2)"/>' + (sir ? '<path d="M18 2 q6 8 0 16 M23 -2 q9 12 0 24" style="fill:none;stroke:#E6A200;stroke-width:2"/>' : "") + "</g>" +
        HM.tx(184, 36, e.v["%Q0.0"] ? "SIRENA DE PREARRANQUE" : "Sirena", { a: "start", s: 10, w: 700, c: e.v["%Q0.0"] ? "#B07800" : "var(--ink3)" }) +
        (pc2 ? HM.tx(292, 140, "⚠ pull‑cord CV‑02", { s: 10, w: 800, c: "var(--bad)" }) : "") + (pc1 ? HM.tx(160, 168, "⚠ pull‑cord CV‑01", { s: 10, w: 800, c: "var(--bad)" }) : "") + HM.falla(e, 170));
    }
  },
  /* ---- pozo de bombeo con interruptores de nivel ---- */
  bombas: {
    hmi: function (e) {
      var b = e.v["%I0.0"], a = e.v["%I0.1"], m = e.v["%I0.2"], lv = m ? 0.92 : a ? 0.76 : b ? 0.45 : 0.15;
      var top = 22, h = 130, y = top + h * (1 - lv), pa = e.v["%Q0.0"], pb = e.v["%Q0.1"];
      var sw = function (frac, on, lbl) { var yy = top + h * (1 - frac); return '<line x1="34" y1="' + yy + '" x2="48" y2="' + yy + '" style="stroke:var(--ink2);stroke-width:2"/><circle cx="52" cy="' + yy + '" r="4.5" style="fill:' + (on ? "var(--acc)" : "var(--canvas)") + ';stroke:var(--ink2)"/>' + HM.tx(30, yy + 4, lbl, { a: "end", s: 9.5, c: on ? "var(--acc)" : "var(--ink3)", w: 700 }); };
      var pump = function (x, on, n) { return '<circle cx="' + x + '" cy="140" r="15" style="fill:' + (on ? "var(--good2)" : "var(--canvas)") + ";stroke:" + (on ? "var(--on)" : "var(--ink3)") + ';stroke-width:2.5"/>' + HM.tx(x, 144, n, { w: 800, c: on ? "var(--on)" : "var(--ink2)" }) +
        HM.ln(x, 125, x, 30, on, 4) + HM.ln(x, 30, 380, 30, (pa || pb), 4) + HM.tx(x, 168, on ? "marcha" : "parada", { s: 9.5, c: on ? "var(--on)" : "var(--ink3)" }); };
      return HM.svg(176, '<rect x="60" y="' + top + '" width="150" height="' + h + '" style="fill:var(--canvas);stroke:var(--ink2);stroke-width:2"/>' +
        '<rect x="61" y="' + y + '" width="148" height="' + (top + h - y - 1) + '" style="fill:#6D7F8C;opacity:.55"/>' + HM.tx(135, top + h - 8, "Pozo de relaves / sumidero", { s: 9.5, c: "var(--ink)", w: 700 }) +
        sw(0.88, m, "Muy alto") + sw(0.7, a, "Alto") + sw(0.3, b, "Bajo") + pump(250, pa, "A") + pump(320, pb, "B") +
        HM.tx(384, 24, "a espesador", { a: "end", s: 9.5, c: "var(--ink2)" }) + HM.falla(e, 174));
    }
  }
};

/* ---------- lecciones de la ruta ---------- */
var TW = function (a, n, o) { return TAG(a, n, "plantw", "", o); };

LECCIONES.push(
/* ==================================================================== */
{ id: "grupo", nivel: "energia", titulo: "El grupo electrógeno visto desde el PLC", min: 25,
  teoria: `
<p>En una mina el grupo electrógeno no es un equipo “de emergencia” que se mira una vez al año: respalda
el chancado, las bombas de agua y relaves, la ventilación y las salas eléctricas, y en zonas aisladas puede ser
<b>la</b> fuente de energía. Un PLC S7‑1200/1500 suele <b>supervisar</b> uno o varios grupos (cada uno con su
controlador propio) y ejecutar la lógica de planta: transferencias, arranque por demanda, deslastre y alarmas.</p>
<h3>Señales típicas entre grupo y PLC</h3>
<table class="t">
<tr><th>Señal</th><th>Tipo</th><th>Comentario</th></tr>
<tr><td>Orden de arranque / parada</td><td>DQ</td><td>Al controlador del grupo, o directo al solenoide de combustible y al arrancador</td></tr>
<tr><td>Presión de aceite</td><td>DI / AI</td><td>Presostato o transductor 4‑20 mA</td></tr>
<tr><td>Temperatura de refrigerante</td><td>DI / AI</td><td>Termostato de alta o PT100</td></tr>
<tr><td>Sobrevelocidad</td><td>DI</td><td>Típicamente 110‑115 % de la nominal</td></tr>
<tr><td>Tensión y frecuencia</td><td>AI / red</td><td>Del analizador o del controlador por Modbus / PROFINET</td></tr>
<tr><td>Estado del interruptor 52G</td><td>DI</td><td>Contacto auxiliar: <b>siempre</b> leer la realimentación, no suponerla</td></tr>
</table>
<h3>Protecciones y la inhibición en el arranque</h3>
<p>Un motor diésel parado <b>no tiene presión de aceite</b>. Si la protección de baja presión estuviera activa desde
el primer instante, el grupo se dispararía en cada arranque. Por eso se <b>inhibe</b> durante unos segundos
(habitualmente 8‑15 s) tras la orden de marcha. Temperatura alta y sobrevelocidad, en cambio, actúan siempre.</p>
<p>Normas como <b>NFPA 110</b> e <b>ISO 8528‑4</b> piden además la parada por <b>falla de arranque</b>
(<i>overcrank</i>: ciclos de arranque y reposo limitados, y si el motor no arranca, alarma) y una
<b>parada de emergencia</b> cableada que corta el combustible sin pasar por el programa. El reto de esta lección se centra
en las tres protecciones de marcha; la falla de arranque es un buen ejercicio extra con un CTU y dos TON.</p>
<p>Las paradas por protección quedan <b>memorizadas</b> (Set/Reset) y solo se rearman con un reset y con la causa
desaparecida: así el operador sabe qué pasó y el grupo no rearranca solo con la falla presente.</p>
<div class="tip"><b>En altura:</b> a más de 3 000 m, como en las operaciones del sur del Perú (Quellaveco, en Moquegua),
el aire es menos denso: el motor y el alternador entregan menos potencia que la de placa (<i>derrateo</i>, según la
curva del fabricante) y el enfriamiento es menos eficaz. Los umbrales de carga del programa deben usar la potencia
<b>derrateada</b>, no la de catálogo.</div>
<p>El ejemplo tiene el error clásico: la protección de presión <b>no está inhibida</b>. Arranca el grupo y mira el HMI.</p>`,
  ejemplo: { planta: "grupo", tags: [TAG("%I0.0", "Arrancar", "push"), TAG("%I0.1", "Parar", "pushNC", "NC cableado"), TAG("%I0.2", "Presion_OK", "plant", "pulsa = simular falla", { falla: 1 }), TAG("%Q0.0", "Combustible"), TAG("%Q0.1", "Alarma")],
    prog: [SEG("Disparo por baja presión (¡sin inhibición!)", S(NO("%Q0.0"), NC("%I0.2"), SET("%Q0.1"))),
      SEG("Reset de alarma", S(NO("%I0.1"), NC("%Q0.0"), NO("%I0.0"), RST("%Q0.1"))),
      SEG("Marcha del grupo", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), NC("%Q0.1"), COIL("%Q0.0")))] },
  reto: { planta: "grupo",
    enunciado: "Protecciones del grupo. <code>\"Arrancar\" %I0.0</code> pone en marcha <code>\"Combustible\" %Q0.0</code> (autorretención) y <code>\"Parar\" %I0.1</code> (NC) lo detiene. Paran el grupo y memorizan <code>\"Alarma\" %Q0.1</code>: <b>temperatura alta</b> <code>%I0.3</code>, <b>sobrevelocidad</b> <code>%I0.4</code> y <b>baja presión de aceite</b> (<code>\"Presion_OK\" %I0.2</code> = 0), esta última <b>inhibida los primeros 8 s</b> tras arrancar. Con alarma no se puede arrancar. <code>\"Reset\" %I0.5</code> borra la alarma solo si ya no hay temperatura alta ni sobrevelocidad. <i>La planta sube la presión 3 s después de arrancar.</i>",
    tags: [TAG("%I0.0", "Arrancar", "push"), TAG("%I0.1", "Parar", "pushNC", "NC cableado"), TAG("%I0.2", "Presion_OK", "plant", "pulsa = simular falla", { falla: 1 }), TAG("%I0.3", "Temp_Alta", "switch"), TAG("%I0.4", "Sobrevelocidad", "push"), TAG("%I0.5", "Reset", "push"), TAG("%Q0.0", "Combustible"), TAG("%Q0.1", "Alarma")],
    inicio: [SEG("Inhibición de presión en el arranque", S()), SEG("Disparos (Set de la alarma)", S()), SEG("Reset de la alarma", S()), SEG("Marcha del grupo", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), COIL("%Q0.0")))],
    solucion: [SEG("Inhibición de presión en el arranque", S(NO("%Q0.0"), TON("T_Inhib", "T#8s"))),
      SEG("Disparos (Set de la alarma)", S(P([NO("%I0.3")], [NO("%I0.4")], [NO("T_Inhib.Q"), NC("%I0.2")]), SET("%Q0.1"))),
      SEG("Reset de la alarma", S(NO("%I0.5"), NC("%I0.3"), NC("%I0.4"), RST("%Q0.1"))),
      SEG("Marcha del grupo", S(P([NO("%I0.0")], [NO("%Q0.0")]), NO("%I0.1"), NC("%Q0.1"), COIL("%Q0.0")))],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Grupo parado, sin alarmas." },
      { in: { "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "Arrancar: el grupo arranca aunque aún no hay presión." },
      { in: { "%I0.0": 0 }, t: 9000, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "9 s después sigue en marcha (la presión subió a los 3 s)." },
      { in: { "%I0.2": 1 }, t: 200, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Cae la presión de aceite en marcha: parada y alarma." },
      { in: { "%I0.2": 0, "%I0.5": 1 }, t: 200, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Reset sin causas presentes: alarma borrada, sin rearranque." },
      { in: { "%I0.5": 0, "%I0.3": 1, "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Temperatura alta: no deja arrancar y alarma." },
      { in: { "%I0.0": 0, "%I0.5": 1 }, t: 200, ex: { "%Q0.1": 1 }, d: "Reset con la temperatura aún alta: la alarma sigue." },
      { in: { "%I0.3": 0 }, t: 200, ex: { "%Q0.1": 0 }, d: "Baja la temperatura y reset: alarma borrada." },
      { in: { "%I0.5": 0, "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 1 }, d: "Nuevo arranque." },
      { in: { "%I0.0": 0 }, t: 1000, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "1,2 s en marcha sin presión: la inhibición evita el disparo." },
      { in: { "%I0.4": 1 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Sobrevelocidad: parada inmediata y alarma." }
    ] },
  quiz: [
    { q: "¿Por qué se inhibe la protección de baja presión de aceite al arrancar?", o: ["Porque el presostato es lento", "Porque el motor parado no tiene presión y se dispararía en cada arranque", "Para ahorrar combustible"], a: 1, e: "La presión tarda unos segundos en subir; la inhibición evita el disparo falso." },
    { q: "¿Qué protección NO debe inhibirse durante el arranque?", o: ["Sobrevelocidad", "Baja presión de aceite"], a: 0, e: "Un embalamiento en el arranque es justamente cuando más daño hace." },
    { q: "A 3 500 m de altura, un grupo de placa 1 000 kW…", o: ["Entrega más potencia por el frío", "Entrega menos potencia: hay que aplicar el derrateo del fabricante", "Entrega lo mismo"], a: 1, e: "El aire es menos denso: menos potencia y menos enfriamiento." },
    { q: "¿Por qué el PLC debe leer el contacto auxiliar del 52G en vez de suponer su estado por la orden?", o: ["Por costumbre", "Porque el interruptor puede no haber cerrado (falla, disparo, resorte sin cargar)", "Porque la orden es analógica"], a: 1, e: "Orden ≠ estado. La realimentación es la verdad del campo." }
  ] },
/* ==================================================================== */
{ id: "tta", nivel: "energia", titulo: "TTA: transferencia automática red‑grupo", min: 35,
  teoria: `
<p>El <b>tablero de transferencia automática (TTA, en inglés ATS)</b> decide quién alimenta la barra de cargas
críticas: la <b>red</b> o el <b>grupo</b>. Es uno de los programas más pedidos en minería y en cualquier planta.</p>
<h3>Secuencia de una transferencia abierta (“abre antes de cerrar”)</h3>
<ol>
  <li><b>Supervisión de red:</b> un relé de tensión/frecuencia (funciones ANSI 27/59/81) da “Red OK”.</li>
  <li><b>Confirmación de falla:</b> si la red falta, se espera unos segundos (típico 1‑5 s) para no arrancar el grupo por un <b>microcorte</b>.</li>
  <li><b>Arranque del grupo</b> y espera de “Grupo OK” (tensión y frecuencia estables).</li>
  <li><b>Abrir 52R</b> (interruptor de red) y, con su realimentación abierta, <b>cerrar 52G</b>. La carga pasa al grupo.</li>
  <li><b>Retorno de red:</b> la red debe estar estable un tiempo (en planta 5‑30 min; aquí segundos) antes de retransferir: abrir 52G, confirmar, cerrar 52R.</li>
  <li><b>Enfriamiento:</b> el grupo sigue en vacío unos minutos antes de parar, para no dañar el turbo.</li>
</ol>
<div class="tip"><b>Enclavamiento triple:</b> 52R y 52G jamás cerrados a la vez sin sincronizar. Se enclavan
<b>mecánicamente</b>, <b>eléctricamente</b> (contactos auxiliares en las bobinas de cierre) y <b>en el PLC</b>,
usando la <b>realimentación</b> del otro interruptor, no solo su orden.</div>
<p><b>Supervisión de discrepancia:</b> si un interruptor no confirma la maniobra en su tiempo (por ejemplo 0,5 s),
el programa debe alarmar y bloquear la secuencia, no esperar para siempre. Y con <b>cargas de motores</b> la transición
abierta debe dejar decaer la tensión residual antes de reconectar (<i>transición con retardo</i> o monitor en fase), para
no cerrar contra un motor que aún gira desfasado. Los equipos de transferencia se fabrican según
<b>IEC 60947‑6‑1</b> (y UL 1008 en Norteamérica).</p>
<p>Variantes: <b>transición cerrada</b> (sincroniza y hace un paralelo breve, menos de 100 ms, sin corte), y
retransferencia manual. En sistemas de emergencia, normas como NFPA 110 exigen que el grupo tome carga en un
tiempo máximo (10 s para la clase más exigente), lo que limita los retardos que puedes programar.</p>
<p>En el ejemplo ya está la detección de falla con confirmación: apaga la red unos instantes y luego más de 3 s.</p>`,
  ejemplo: { planta: "tta", tags: [TAG("%I0.0", "Red_OK", "switch", "", { def: 1 }), TAG("%I0.1", "Grupo_OK", "plant"), TAG("%I0.2", "52R_Cerrado", "plant"), TAG("%I0.3", "52G_Cerrado", "plant"), TAG("%Q0.0", "Arranque_Grupo"), TAG("%Q0.1", "Cerrar_52R"), TAG("%Q0.2", "Cerrar_52G"), TAG("%M0.0", "Falla_Red_Conf")],
    prog: [SEG("Falla de red confirmada (3 s)", S(NC("%I0.0"), TON("T_FallaRed", "T#3s"), COIL("%M0.0"))),
      SEG("Arranque del grupo mientras dure la falla", S(NO("%M0.0"), COIL("%Q0.0"))),
      SEG("52R cerrado con red presente", S(NO("%I0.0"), NC("%I0.3"), COIL("%Q0.1")))] },
  reto: { planta: "tta",
    enunciado: "Programa la TTA completa. Falla de red (<code>\"Red_OK\" %I0.0</code> = 0) confirmada <b>3 s</b> → arrancar el grupo (<code>%Q0.0</code>). Con <code>\"Grupo_OK\" %I0.1</code> y <b>52R abierto</b> (<code>%I0.2</code> = 0) → cerrar 52G (<code>%Q0.2</code>). Red de vuelta y estable <b>10 s</b> → abrir 52G y, con 52G abierto (<code>%I0.3</code> = 0), cerrar 52R (<code>%Q0.1</code>). Tras retransferir, el grupo sigue <b>5 s</b> en enfriamiento y para. Un microcorte de 1 s no debe arrancar el grupo. <i>Pista: marcas para “falla confirmada”, “red estable” y “pedir grupo” (Set/Reset); TOF para el enfriamiento.</i>",
    tags: [TAG("%I0.0", "Red_OK", "switch", "", { def: 1 }), TAG("%I0.1", "Grupo_OK", "plant"), TAG("%I0.2", "52R_Cerrado", "plant"), TAG("%I0.3", "52G_Cerrado", "plant"), TAG("%Q0.0", "Arranque_Grupo"), TAG("%Q0.1", "Cerrar_52R"), TAG("%Q0.2", "Cerrar_52G"), TAG("%M0.0", "Falla_Red_Conf"), TAG("%M0.1", "Red_Estable"), TAG("%M0.2", "Pedir_Grupo")],
    inicio: [SEG("Falla de red confirmada", S()), SEG("Red estable", S()), SEG("Pedir grupo (Set)", S()), SEG("Liberar grupo (Reset)", S()), SEG("Arranque del grupo + enfriamiento", S()), SEG("Cerrar 52G", S()), SEG("Cerrar 52R", S(NO("%I0.0"), COIL("%Q0.1")))],
    solucion: [SEG("Falla de red confirmada", S(NC("%I0.0"), TON("T_FallaRed", "T#3s"), COIL("%M0.0"))),
      SEG("Red estable", S(NO("%I0.0"), TON("T_Retorno", "T#10s"), COIL("%M0.1"))),
      SEG("Pedir grupo (Set)", S(NO("%M0.0"), SET("%M0.2"))),
      SEG("Liberar grupo (Reset)", S(NO("%M0.1"), RST("%M0.2"))),
      SEG("Arranque del grupo + enfriamiento", S(NO("%M0.2"), TOF("T_Enfriar", "T#5s"), COIL("%Q0.0"))),
      SEG("Cerrar 52G", S(NO("%M0.2"), NO("%I0.1"), NC("%I0.2"), COIL("%Q0.2"))),
      SEG("Cerrar 52R", S(NC("%M0.2"), NO("%I0.0"), NC("%I0.3"), COIL("%Q0.1")))],
    nunca: [["%Q0.1", "%Q0.2"]],
    pasos: [
      { in: {}, t: 500, ex: { "%Q0.1": 1, "%I0.2": 1, "%Q0.0": 0, "%Q0.2": 0 }, d: "Red normal: la carga va por la red (52R cerrado)." },
      { in: { "%I0.0": 0 }, t: 1000, ex: { "%Q0.0": 0 }, d: "Microcorte de 1 s: el grupo NO arranca." },
      { in: { "%I0.0": 1 }, t: 500, ex: { "%Q0.1": 1, "%Q0.0": 0 }, d: "Vuelve la red: sigue por la red." },
      { in: { "%I0.0": 0 }, t: 2800, ex: { "%Q0.0": 0 }, d: "Falla de red: a los 2,8 s todavía se confirma." },
      { in: {}, t: 400, ex: { "%Q0.0": 1 }, d: "3,2 s: arranca el grupo." },
      { in: {}, t: 3500, ex: { "%Q0.2": 1, "%I0.3": 1, "%Q0.1": 0 }, d: "Grupo en tensión: 52G cerrado, la carga va por el grupo." },
      { in: { "%I0.0": 1 }, t: 5000, ex: { "%Q0.2": 1, "%Q0.1": 0 }, d: "Vuelve la red: a los 5 s todavía espera estabilidad." },
      { in: {}, t: 5500, ex: { "%Q0.2": 0, "%Q0.1": 1, "%I0.2": 1, "%Q0.0": 1 }, d: "10,5 s: retransferencia a red; el grupo queda en enfriamiento." },
      { in: {}, t: 5000, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Enfriamiento terminado: el grupo se detiene." }
    ] },
  quiz: [
    { q: "¿Para qué sirve el tiempo de confirmación de falla de red?", o: ["Para calentar el grupo", "Para no arrancar el grupo por un microcorte", "Para sincronizar"], a: 1, e: "Los huecos de tensión de 100 ms o 1 s son frecuentes y no justifican una transferencia." },
    { q: "En transición abierta, ¿cuándo se cierra el 52G?", o: ["Junto con la apertura de 52R", "Cuando la realimentación confirma 52R abierto y el grupo está OK", "Antes de abrir 52R"], a: 1, e: "Abre antes de cerrar, verificado con contactos auxiliares." },
    { q: "¿Por qué el grupo sigue girando en vacío después de retransferir?", o: ["Para enfriar el motor y el turbo antes de parar", "Para cargar la batería", "Por error de programa"], a: 0, e: "Parar un motor caliente con carga daña el turbo y los sellos." },
    { q: "Un paralelo red‑grupo sin transferencia cerrada diseñada para ello…", o: ["Es normal", "Es un cierre sin sincronizar: corrientes enormes y daño al grupo", "Mejora la calidad de energía"], a: 1, e: "Por eso se enclava de forma mecánica, eléctrica y por programa." }
  ] },
/* ==================================================================== */
{ id: "sincronismo", nivel: "energia", titulo: "Sincronismo de grupos en paralelo", min: 40,
  teoria: `
<p>Para conectar un grupo <b>G2</b> a una barra que ya alimenta otro grupo (o la red), en el instante del cierre
las dos tensiones deben ser prácticamente iguales. Hay que igualar <b>cuatro</b> cosas:</p>
<table class="t">
<tr><th>Condición</th><th>Ventana típica</th><th>Quién la ajusta</th></tr>
<tr><td>Secuencia de fases</td><td>Idéntica (se verifica en la puesta en marcha)</td><td>Cableado</td></tr>
<tr><td>Tensión (ΔV)</td><td>3 % a 10 % según potencia</td><td>Regulador de tensión (AVR)</td></tr>
<tr><td>Frecuencia (deslizamiento Δf)</td><td>0,1 a 0,3 Hz según potencia</td><td>Regulador de velocidad (gobernador)</td></tr>
<tr><td>Ángulo de fase (Δφ)</td><td>±10° a ±20° según potencia</td><td>Se espera a que el deslizamiento lo lleve a 0</td></tr>
</table>
<p>Las ventanas dependen del tamaño. <b>IEEE 1547‑2018</b> (tabla de límites de sincronización) admite
Δf 0,3 Hz, ΔV 10 % y Δφ 20° hasta 500 kVA; 0,2 Hz, 5 % y 15° de 500 a 1 500 kVA; y <b>0,1 Hz, 3 % y 10°</b>
por encima de 1 500 kVA. Para máquinas síncronas grandes, IEEE C50.12/C50.13 piden aún menos deslizamiento
(≈ 0,067 Hz). Los grupos de una planta minera suelen superar 1 500 kVA: el reto usa la ventana más estricta.</p>
<h3>Cómo se ve en el sincronoscopio</h3>
<p>Con Δf ≠ 0 el ángulo entre G2 y la barra <b>gira</b>: una vuelta cada 1/Δf segundos. Si G2 va más rápido, la aguja
gira hacia “rápido”. Se busca que G2 vaya <b>ligeramente más rápido</b> (deslizamiento positivo): así, al cerrar,
toma un poco de carga en vez de quedar motorizado (lo que dispararía la protección de potencia inversa, ANSI 32).</p>
<h3>El cierre con anticipo</h3>
<p>Un interruptor tarda en cerrar (aquí 80 ms). Mientras tanto el ángulo sigue avanzando:
<code>anticipo = 360° × Δf × t_cierre</code>. Con 0,1 Hz y 80 ms son 2,9°. Los sincronizadores automáticos
(ANSI 25A) dan la orden con ese adelanto; el relé de verificación de sincronismo (ANSI 25) solo <b>permite</b> el cierre
dentro de la ventana.</p>
<div class="tip"><b>En la práctica</b> la sincronización fina y el reparto de carga (kW por el gobernador, kVAr por el AVR,
en isócrono o en <i>droop</i>) los hacen los controladores de grupo. El PLC de planta coordina: pide sincronizar,
supervisa ventanas y tiempos, y bloquea si algo no cuadra. Programarlo tú mismo es la mejor forma de entender qué hacen.</div>
<p>El ejemplo es una <b>sincronización manual</b>: sube o baja la velocidad con los pulsadores, mira el sincronoscopio y
cierra cuando la aguja esté en la zona verde. Si cierras fuera de fase, el modelo de planta te lo dirá.</p>`,
  ejemplo: { planta: "sincro", tags: [TAG("%I0.3", "Subir_Manual", "push"), TAG("%I0.4", "Bajar_Manual", "push"), TAG("%I0.5", "Cerrar_Manual", "push"), TAG("%I0.6", "Abrir_52G2", "push"), TAG("%I0.1", "Tension_OK", "switch", "", { def: 1 }), TAG("%I0.2", "52G2_Cerrado", "plant"), TW("%IW64", "Frec_Barra", { div: 100, unit: "Hz" }), TW("%IW66", "Frec_G2", { div: 100, unit: "Hz" }), TW("%IW68", "Dif_Fase", { unit: "°" }), TAG("%Q0.0", "Cerrar_52G2"), TAG("%Q0.1", "Subir_Vel"), TAG("%Q0.2", "Bajar_Vel"), TAG("%MW10", "Dif_Frec")],
    prog: [SEG("Δf = f G2 − f barra (centésimas de Hz)", S(MATH("SUB", "%IW66", "%IW64", "%MW10"))),
      SEG("Subir velocidad a mano", S(NO("%I0.3"), NC("%I0.2"), COIL("%Q0.1"))),
      SEG("Bajar velocidad a mano", S(NO("%I0.4"), NC("%I0.2"), COIL("%Q0.2"))),
      SEG("Cerrar 52G2 a mano (¡mira el sincronoscopio!)", S(NO("%I0.5"), SET("%Q0.0"))),
      SEG("Abrir 52G2", S(NO("%I0.6"), RST("%Q0.0")))] },
  reto: { planta: "sincro",
    enunciado: "Sincronizador automático. Con <code>\"Modo_Sincro\" %I0.0</code> activo y <code>52G2</code> abierto (<code>%I0.2</code> = 0): calcula <code>Δf = Frec_G2 − Frec_Barra</code> en <code>%MW10</code> (centésimas de Hz); si <b>Δf &lt; 5</b> activa <code>\"Subir_Vel\" %Q0.1</code>; si <b>Δf &gt; 10</b> activa <code>\"Bajar_Vel\" %Q0.2</code>. Da la orden de cierre (<b>Set</b> de <code>\"Cerrar_52G2\" %Q0.0</code>) solo con <code>\"Tension_OK\" %I0.1</code>, <b>0 ≤ Δf ≤ 10</b> (0,1 Hz) y <b>−10 ≤ Dif_Fase ≤ 10</b> (<code>%IW68</code>, grados): la ventana de IEEE 1547 para más de 1 500 kVA. Al quitar Modo_Sincro, Reset del cierre. <i>El modelo de planta detecta cualquier cierre fuera de sincronismo.</i>",
    tags: [TAG("%I0.0", "Modo_Sincro", "switch"), TAG("%I0.1", "Tension_OK", "switch"), TAG("%I0.2", "52G2_Cerrado", "plant"), TW("%IW64", "Frec_Barra", { div: 100, unit: "Hz" }), TW("%IW66", "Frec_G2", { div: 100, unit: "Hz" }), TW("%IW68", "Dif_Fase", { unit: "°" }), TAG("%Q0.0", "Cerrar_52G2"), TAG("%Q0.1", "Subir_Vel"), TAG("%Q0.2", "Bajar_Vel"), TAG("%MW10", "Dif_Frec")],
    inicio: [SEG("Δf = f G2 − f barra", S(MATH("SUB", "%IW66", "%IW64", "%MW10"))), SEG("Subir velocidad", S()), SEG("Bajar velocidad", S()), SEG("Orden de cierre (verificación de sincronismo)", S()), SEG("Reset del cierre", S())],
    solucion: [SEG("Δf = f G2 − f barra", S(MATH("SUB", "%IW66", "%IW64", "%MW10"))),
      SEG("Subir velocidad", S(NO("%I0.0"), NC("%I0.2"), CMP("<", "%MW10", "5"), COIL("%Q0.1"))),
      SEG("Bajar velocidad", S(NO("%I0.0"), NC("%I0.2"), CMP(">", "%MW10", "10"), COIL("%Q0.2"))),
      SEG("Orden de cierre (verificación de sincronismo)", S(NO("%I0.0"), NO("%I0.1"), CMP(">=", "%MW10", "0"), CMP("<=", "%MW10", "10"), CMP(">=", "%IW68", "-10"), CMP("<=", "%IW68", "10"), SET("%Q0.0"))),
      SEG("Reset del cierre", S(NC("%I0.0"), RST("%Q0.0")))],
    nunca: [["%Q0.1", "%Q0.2"]],
    pasos: [
      { in: {}, t: 500, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0 }, d: "Sin Modo_Sincro: no se regula ni se cierra." },
      { in: { "%I0.0": 1 }, t: 1000, ex: { "%Q0.1": 1, "%Q0.0": 0 }, d: "Modo_Sincro: G2 está a 59,40 Hz → sube velocidad." },
      { in: {}, t: 20000, ex: { "%Q0.0": 0, "%IW66": [6004, 6010] }, d: "Sin Tension_OK no cierra; la frecuencia quedó en la ventana (60,04‑60,10 Hz)." },
      { in: { "%I0.1": 1 }, t: 30000, ex: { "%Q0.0": 1, "%I0.2": 1 }, d: "Con tensión OK cierra dentro de la ventana de fase: G2 en paralelo." },
      { in: { "%I0.0": 0 }, t: 300, ex: { "%Q0.0": 0, "%I0.2": 0 }, d: "Sin Modo_Sincro: se abre el 52G2." }
    ] },
  quiz: [
    { q: "¿Qué cuatro condiciones se igualan para sincronizar?", o: ["Corriente, potencia, factor de potencia y velocidad", "Secuencia de fases, tensión, frecuencia y ángulo", "Solo tensión y frecuencia"], a: 1, e: "Secuencia de fases (fija), ΔV, Δf y Δφ en el instante del cierre." },
    { q: "Con Δf = 0,1 Hz, ¿cada cuánto pasa la aguja del sincronoscopio por cero?", o: ["Cada 0,1 s", "Cada 10 s", "Cada 1 s"], a: 1, e: "Una vuelta cada 1/Δf = 10 s." },
    { q: "¿Por qué se prefiere que el grupo entrante vaya ligeramente más rápido?", o: ["Para que tome algo de carga y no quede motorizado (potencia inversa)", "Para que suene menos", "Da igual"], a: 0, e: "Con deslizamiento negativo el grupo absorbería potencia: dispara la protección 32." },
    { q: "El interruptor tarda 80 ms y Δf = 0,2 Hz. ¿Anticipo de cierre?", o: ["≈ 5,8°", "≈ 0,8°", "≈ 58°"], a: 0, e: "360 × 0,2 × 0,08 = 5,76°." },
    { q: "¿Qué diferencia hay entre ANSI 25 y 25A?", o: ["Ninguna", "25 verifica y permite el cierre; 25A además ajusta velocidad/tensión y da la orden", "25A es para motores"], a: 1, e: "Verificador de sincronismo frente a sincronizador automático." }
  ] },
/* ==================================================================== */
{ id: "demanda", nivel: "energia", titulo: "Grupos en paralelo: arranque por demanda y deslastre", min: 30,
  teoria: `
<p>Con varios grupos en paralelo no conviene tenerlos todos en marcha: un diésel con poca carga quema mal el
combustible y acumula hollín (<i>wet stacking</i>). La planta arranca el segundo grupo <b>solo cuando la demanda lo pide</b>
y lo para cuando sobra, con <b>histéresis</b> y <b>temporizaciones</b> para no arrancar y parar a cada pico:</p>
<ul>
  <li><b>Arranque de G2:</b> carga &gt; 80 % de lo que hay en línea, sostenida unos segundos.</li>
  <li><b>Parada de G2:</b> carga &lt; ~35 % del total en línea, sostenida más tiempo.</li>
  <li>Entre los dos umbrales, <b>se mantiene</b> lo que hay (Set/Reset).</li>
</ul>
<h3>Deslastre de cargas</h3>
<p>Si la demanda supera lo que los grupos en línea pueden entregar (por ejemplo, arranca un molino o una bomba grande mientras
el segundo grupo aún sincroniza), la frecuencia cae y todo puede salir de servicio. Se <b>deslastran</b> cargas no esenciales
(iluminación de patios, campamento, talleres) de inmediato y se reponen cuando hay capacidad.</p>
<div class="tip">El reparto de carga entre grupos en paralelo lo hacen los controladores (isócrono con líneas de reparto, o
<i>droop</i>). Aquí el PLC decide <b>cuántos</b> grupos hacen falta. La potencia medida suele llegar por Modbus TCP o PROFINET
desde el analizador o el controlador del grupo.</div>`,
  ejemplo: { planta: "demanda", tags: [TAG("%IW64", "Carga_kW", "analog", "", { min: 0, max: 2000, unit: "kW" }), TAG("%I0.0", "G2_En_Barra", "plant"), TAG("%Q0.0", "Pedir_G2"), TAG("%Q0.1", "Deslastre"), TAG("%Q0.2", "Aviso_80pct")],
    prog: [SEG("Aviso: G1 por encima del 80 %", S(CMP(">", "%IW64", "800"), COIL("%Q0.2"))), SEG("Pedir G2 a mano (complétalo en el reto)", S(CMP(">", "%IW64", "1500"), COIL("%Q0.0")))] },
  reto: { planta: "demanda",
    enunciado: "G1 (1000 kW) siempre en servicio. La demanda llega en <code>\"Carga_kW\" %IW64</code>. <b>Pedir G2</b> (Set de <code>%Q0.0</code>) cuando la carga sea <b>&gt; 800 kW durante 10 s</b>. <b>Liberar G2</b> (Reset) cuando sea <b>&lt; 700 kW durante 15 s</b>. <b>Deslastre</b> <code>%Q0.1</code> inmediato si la carga es <b>&gt; 1000 kW</b> y G2 aún no está en barra (<code>\"G2_En_Barra\" %I0.0</code>). <i>La planta tarda 4 s en arrancar y sincronizar G2.</i>",
    tags: [TAG("%IW64", "Carga_kW", "analog", "", { min: 0, max: 2000, unit: "kW" }), TAG("%I0.0", "G2_En_Barra", "plant"), TAG("%Q0.0", "Pedir_G2"), TAG("%Q0.1", "Deslastre")],
    inicio: [SEG("Pedir G2 por carga alta sostenida", S()), SEG("Liberar G2 por carga baja sostenida", S()), SEG("Deslastre de cargas no esenciales", S())],
    solucion: [SEG("Pedir G2 por carga alta sostenida", S(CMP(">", "%IW64", "800"), TON("T_Alta", "T#10s"), SET("%Q0.0"))),
      SEG("Liberar G2 por carga baja sostenida", S(CMP("<", "%IW64", "700"), TON("T_Baja", "T#15s"), RST("%Q0.0"))),
      SEG("Deslastre de cargas no esenciales", S(CMP(">", "%IW64", "1000"), NC("%I0.0"), COIL("%Q0.1")))],
    pasos: [
      { in: { "%IW64": 500 }, t: 1000, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "500 kW: basta G1." },
      { in: { "%IW64": 900 }, t: 5000, ex: { "%Q0.0": 0 }, d: "Pico de 900 kW durante 5 s…" },
      { in: { "%IW64": 500 }, t: 1000, ex: { "%Q0.0": 0 }, d: "…y baja: no se pidió G2." },
      { in: { "%IW64": 900 }, t: 9000, ex: { "%Q0.0": 0 }, d: "900 kW sostenidos: a los 9 s aún no." },
      { in: {}, t: 1500, ex: { "%Q0.0": 1 }, d: "10,5 s: se pide G2." },
      { in: { "%IW64": 750 }, t: 20000, ex: { "%Q0.0": 1 }, d: "750 kW (entre umbrales): G2 se mantiene." },
      { in: { "%IW64": 600 }, t: 14000, ex: { "%Q0.0": 1 }, d: "600 kW: a los 14 s todavía no se libera." },
      { in: {}, t: 1500, ex: { "%Q0.0": 0 }, d: "15,5 s: G2 liberado." },
      { in: { "%IW64": 1200 }, t: 200, ex: { "%Q0.1": 1 }, d: "Arranca una carga grande (1200 kW) sin G2: deslastre inmediato." },
      { in: {}, t: 10500, ex: { "%Q0.0": 1, "%Q0.1": 1 }, d: "A los 10,5 s se pide G2; sigue el deslastre mientras sincroniza." },
      { in: {}, t: 4200, ex: { "%I0.0": 1, "%Q0.1": 0 }, d: "G2 en barra: se reponen las cargas." }
    ] },
  quiz: [
    { q: "¿Por qué no tener siempre los dos grupos en marcha?", o: ["Por el ruido", "Un diésel con poca carga quema mal y acumula hollín (wet stacking), además de gastar más", "Porque no se pueden poner en paralelo"], a: 1, e: "Conviene que cada grupo trabaje cargado (típicamente sobre 30‑40 %)." },
    { q: "¿Para qué sirven los dos umbrales (800 / 700 kW)?", o: ["Histéresis: evitar arranques y paradas continuas", "Para medir mejor", "Son redundantes"], a: 0, e: "Entre ambos se conserva el estado." },
    { q: "¿Cuándo se deslastra?", o: ["Siempre que arranca G2", "Cuando la demanda supera la capacidad en línea, de inmediato", "Al final del turno"], a: 1, e: "Evita el colapso de frecuencia mientras llega la capacidad nueva." }
  ] },
/* ==================================================================== */
{ id: "faja", nivel: "energia", titulo: "Planta minera: fajas en cascada con pull‑cord", min: 35,
  teoria: `
<p>En una planta concentradora el mineral viaja por <b>fajas transportadoras</b>: del chancado primario a la pila de gruesos
y de ahí a la molienda. Las fajas se enclavan entre sí para no <b>atollar los chutes</b> (descargar sobre una faja parada).</p>
<h3>Reglas de oro</h3>
<ul>
  <li><b>Arranque contra el flujo:</b> primero la faja de aguas abajo (la que descarga a la pila), luego la anterior, y al final el alimentador.</li>
  <li><b>Parada a favor del flujo:</b> primero el alimentador; las fajas siguen un tiempo para <b>vaciarse</b>.</li>
  <li><b>Sirena de prearranque:</b> aviso audible y visible antes de mover cualquier faja cuyo recorrido completo no se vea desde el mando (lo exige, por ejemplo, MSHA 30 CFR 56.14201, y los reglamentos mineros nacionales piden lo equivalente). En planta dura lo suficiente para que el personal se retire, del orden de 10 a 30 s; el reto usa 5 s para que la práctica sea ágil.</li>
  <li><b>Pull‑cord (interruptor de tirón):</b> cable a lo largo de la faja; quien tira de él la detiene. Va cableado <b>NC</b>, y al dispararse para esa faja y todo lo que la alimenta. El interruptor <b>queda enclavado</b> y se rearma a mano en el propio interruptor (EN 620, ISO 13850): en el simulador, un toque lo dispara y otro lo rearma. Rearmarlo no vuelve a arrancar nada: hace falta una orden de marcha nueva.</li>
  <li>Otros enclavamientos reales: desalineamiento, velocidad cero (rotura o patinaje), chute atollado y rasgado de banda.</li>
</ul>
<div class="tip">El corrector comprueba en <b>cada ciclo</b> que nunca haya una faja en marcha descargando sobre otra parada, ni el
alimentador sin su faja. En planta eso es un chute atollado y horas de limpieza.</div>
<p>Los pull‑cord y las paradas de emergencia de fajas forman parte de la seguridad de las personas: en minería se
cablean a circuitos de seguridad (relé o PLC de seguridad). El programa estándar los lee para el
enclavamiento y el diagnóstico.</p>`,
  ejemplo: { planta: "faja", tags: [TAG("%I0.0", "Arranque", "push"), TAG("%I0.1", "Parada", "pushNC", "NC cableado"), TAG("%I0.2", "Pullcord_CV02", "pullcord"), TAG("%I0.3", "Pullcord_CV01", "pullcord"), TAG("%Q0.0", "Sirena"), TAG("%Q0.1", "CV02"), TAG("%Q0.2", "CV01"), TAG("%Q0.3", "Alimentador")],
    prog: [SEG("Sirena mientras se pulsa Arranque", S(NO("%I0.0"), COIL("%Q0.0"))), SEG("Solo CV‑02 con autorretención y pull‑cord", S(P([NO("%I0.0")], [NO("%Q0.1")]), NO("%I0.1"), NO("%I0.2"), COIL("%Q0.1")))] },
  reto: { planta: "faja",
    enunciado: "Secuencia de fajas. <code>\"Arranque\" %I0.0</code> memoriza la marcha del sistema; <code>\"Parada\" %I0.1</code> o cualquier pull‑cord (<code>%I0.2</code>, <code>%I0.3</code>, NC) la cancela. Al arrancar: <b>sirena</b> <code>%Q0.0</code> durante 5 s → <b>CV‑02</b> <code>%Q0.1</code> → 3 s después <b>CV‑01</b> <code>%Q0.2</code> → 3 s después <b>Alimentador</b> <code>%Q0.3</code>. Al parar: el alimentador para al instante, CV‑01 se vacía <b>5 s</b> y CV‑02 <b>10 s</b>. El pull‑cord de una faja la para de inmediato (y todo lo que descarga en ella). Nunca una faja en marcha sobre otra parada.",
    tags: [TAG("%I0.0", "Arranque", "push"), TAG("%I0.1", "Parada", "pushNC", "NC cableado"), TAG("%I0.2", "Pullcord_CV02", "pullcord"), TAG("%I0.3", "Pullcord_CV01", "pullcord"), TAG("%Q0.0", "Sirena"), TAG("%Q0.1", "CV02"), TAG("%Q0.2", "CV01"), TAG("%Q0.3", "Alimentador"), TAG("%M0.0", "Sistema_Marcha")],
    inicio: [SEG("Marcha del sistema", S()), SEG("Sirena de prearranque", S()), SEG("CV‑02 (aguas abajo)", S()), SEG("CV‑01", S()), SEG("Alimentador", S())],
    solucion: [SEG("Marcha del sistema", S(P([NO("%I0.0")], [NO("%M0.0")]), NO("%I0.1"), NO("%I0.2"), NO("%I0.3"), COIL("%M0.0"))),
      SEG("Sirena de prearranque", S(NO("%M0.0"), P([TON("T_Sirena", "T#5s")], [NC("T_Sirena.Q"), COIL("%Q0.0")]))),
      SEG("CV‑02 (aguas abajo)", S(NO("T_Sirena.Q"), TOF("T_Vac02", "T#10s"), NO("%I0.2"), COIL("%Q0.1"))),
      SEG("CV‑01", S(NO("%Q0.1"), NO("T_Sirena.Q"), TON("T_CV01", "T#3s"), TOF("T_Vac01", "T#5s"), NO("%I0.3"), NO("%Q0.1"), COIL("%Q0.2"))),
      SEG("Alimentador", S(NO("%Q0.2"), NO("T_CV01.Q"), TON("T_Alim", "T#3s"), NO("%M0.0"), COIL("%Q0.3")))],
    reglas: [{ si: "%Q0.2", sin: "%Q0.1", d: "CV‑01 en marcha descargando sobre CV‑02 parada: chute atollado" }, { si: "%Q0.3", sin: "%Q0.2", d: "Alimentador en marcha con CV‑01 parada: chute atollado" }],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0, "%Q0.2": 0, "%Q0.3": 0 }, d: "Planta parada." },
      { in: { "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "Arranque: suena la sirena, nada se mueve." },
      { in: { "%I0.0": 0 }, t: 4600, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "4,8 s: sigue la sirena." },
      { in: {}, t: 500, ex: { "%Q0.0": 0, "%Q0.1": 1, "%Q0.2": 0 }, d: "5,3 s: arranca CV‑02 (aguas abajo)." },
      { in: {}, t: 3100, ex: { "%Q0.2": 1, "%Q0.3": 0 }, d: "8,4 s: arranca CV‑01." },
      { in: {}, t: 3100, ex: { "%Q0.3": 1 }, d: "11,5 s: arranca el alimentador. Planta en marcha." },
      { in: { "%I0.1": 1 }, t: 100, ex: { "%Q0.3": 0, "%Q0.2": 1, "%Q0.1": 1 }, d: "Parada: el alimentador para; las fajas siguen vaciándose." },
      { in: { "%I0.1": 0 }, t: 5100, ex: { "%Q0.2": 0, "%Q0.1": 1 }, d: "5,2 s: CV‑01 vacía y parada; CV‑02 sigue." },
      { in: {}, t: 5000, ex: { "%Q0.1": 0 }, d: "10,2 s: CV‑02 vacía y parada." },
      { in: { "%I0.0": 1 }, t: 200, ex: { "%Q0.0": 1 }, d: "Nuevo arranque." },
      { in: { "%I0.0": 0 }, t: 11500, ex: { "%Q0.1": 1, "%Q0.2": 1, "%Q0.3": 1 }, d: "Planta en marcha otra vez." },
      { in: { "%I0.3": 1 }, t: 100, ex: { "%Q0.2": 0, "%Q0.3": 0, "%Q0.1": 1 }, d: "Pull‑cord de CV‑01: paran CV‑01 y el alimentador; CV‑02 se vacía." },
      { in: { "%I0.2": 1 }, t: 100, ex: { "%Q0.1": 0 }, d: "Pull‑cord de CV‑02: para CV‑02 de inmediato." }
    ] },
  quiz: [
    { q: "¿En qué orden arrancan las fajas?", o: ["A favor del flujo (alimentador primero)", "Contra el flujo (la de aguas abajo primero)", "Todas a la vez"], a: 1, e: "Así ninguna descarga sobre una faja parada." },
    { q: "¿Por qué las fajas siguen girando un tiempo después de parar el alimentador?", o: ["Para vaciarse y no arrancar luego cargadas", "Para enfriar el motor", "Para avisar al operador"], a: 0, e: "Arrancar una faja llena exige mucho par y puede derramar mineral." },
    { q: "El pull‑cord se cablea NC porque…", o: ["Es más barato", "Un cable cortado o suelto detiene la faja (falla segura)", "Lo exige el PLC"], a: 1, e: "Seguridad positiva, igual que los paros." }
  ] },
/* ==================================================================== */
{ id: "bombas", nivel: "energia", titulo: "Planta minera: bombas de pozo con alternancia", min: 30,
  teoria: `
<p>Pozos de relaves, sumideros de mina y cisternas de agua de proceso tienen casi siempre <b>dos bombas</b>:
una <b>principal (lead)</b> y una de <b>reserva (lag)</b>. Para repartir el desgaste, la principal se <b>alterna</b> en
cada ciclo, y con nivel muy alto trabajan las dos.</p>
<h3>Interruptores de nivel</h3>
<ul>
  <li><b>Bajo:</b> por debajo, la bomba se detiene (protege contra la marcha en seco).</li>
  <li><b>Alto:</b> arranca la bomba que esté de turno.</li>
  <li><b>Muy alto:</b> arranca también la segunda (y suele dar alarma de rebalse).</li>
</ul>
<p>Entre bajo y alto, la bomba conserva su estado: es otra <b>histéresis</b>, ahora hecha con interruptores físicos.</p>
<div class="tip"><b>Alternar</b> es un telerruptor: cada vez que termina un ciclo de bombeo (flanco negativo de la
demanda) cambia el bit de turno. Es la lección de flancos aplicada a un equipo real. En planta se añade la alternancia
por horas de marcha y el reemplazo automático si la principal falla (térmico, sin caudal).</div>`,
  ejemplo: { planta: "bombas", tags: [TAG("%I0.0", "Nivel_Bajo", "switch"), TAG("%I0.1", "Nivel_Alto", "switch"), TAG("%I0.2", "Nivel_Muy_Alto", "switch"), TAG("%Q0.0", "Bomba_A"), TAG("%Q0.1", "Bomba_B")],
    prog: [SEG("Una sola bomba con histéresis de nivel", S(NO("%I0.1"), SET("%Q0.0"))), SEG("", S(NC("%I0.0"), RST("%Q0.0")))] },
  reto: { planta: "bombas",
    enunciado: "Pozo con dos bombas. La <b>demanda</b> <code>%M0.0</code> se activa con <code>\"Nivel_Alto\" %I0.1</code> y se apaga cuando el agua baja de <code>\"Nivel_Bajo\" %I0.0</code>. Con demanda trabaja la bomba de turno: <b>A</b> <code>%Q0.0</code> si <code>\"Turno_B\" %M0.1</code> = 0, si no <b>B</b> <code>%Q0.1</code>. El turno <b>cambia al terminar cada ciclo</b> de bombeo. Con <code>\"Nivel_Muy_Alto\" %I0.2</code> funcionan las dos. <i>Pista: flanco N de la demanda y el telerruptor de la lección de flancos.</i>",
    tags: [TAG("%I0.0", "Nivel_Bajo", "switch"), TAG("%I0.1", "Nivel_Alto", "switch"), TAG("%I0.2", "Nivel_Muy_Alto", "switch"), TAG("%Q0.0", "Bomba_A"), TAG("%Q0.1", "Bomba_B"), TAG("%M0.0", "Demanda"), TAG("%M0.1", "Turno_B"), TAG("%M0.2", "Fin_Ciclo")],
    inicio: [SEG("Demanda: inicio con nivel alto", S()), SEG("Demanda: fin bajo nivel bajo", S()), SEG("Pulso de fin de ciclo", S()), SEG("Cambio de turno", S()), SEG("Bomba A", S()), SEG("Bomba B", S())],
    solucion: [SEG("Demanda: inicio con nivel alto", S(NO("%I0.1"), SET("%M0.0"))),
      SEG("Demanda: fin bajo nivel bajo", S(NC("%I0.0"), RST("%M0.0"))),
      SEG("Pulso de fin de ciclo", S(NE("%M0.0", "%M10.0"), COIL("%M0.2"))),
      SEG("Cambio de turno", S(P([NO("%M0.2"), NC("%M0.1")], [NC("%M0.2"), NO("%M0.1")]), COIL("%M0.1"))),
      SEG("Bomba A", S(P([NO("%M0.0"), NC("%M0.1")], [NO("%I0.2")]), COIL("%Q0.0"))),
      SEG("Bomba B", S(P([NO("%M0.0"), NO("%M0.1")], [NO("%I0.2")]), COIL("%Q0.1")))],
    pasos: [
      { in: {}, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Pozo vacío: bombas paradas." },
      { in: { "%I0.0": 1 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Se llena hasta el nivel bajo: aún paradas." },
      { in: { "%I0.1": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "Nivel alto: arranca la bomba A." },
      { in: { "%I0.1": 0 }, t: 100, ex: { "%Q0.0": 1 }, d: "Baja del nivel alto: A sigue bombeando." },
      { in: { "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Bajo el nivel bajo: A se detiene." },
      { in: { "%I0.0": 1, "%I0.1": 1 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 1 }, d: "Nuevo ciclo: ahora arranca la B (alternancia)." },
      { in: { "%I0.2": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 1 }, d: "Nivel muy alto: trabajan las dos." },
      { in: { "%I0.2": 0, "%I0.1": 0, "%I0.0": 0 }, t: 100, ex: { "%Q0.0": 0, "%Q0.1": 0 }, d: "Pozo vacío: paran las dos." },
      { in: { "%I0.0": 1, "%I0.1": 1 }, t: 100, ex: { "%Q0.0": 1, "%Q0.1": 0 }, d: "Siguiente ciclo: vuelve a ser la A." }
    ] },
  quiz: [
    { q: "¿Para qué se alternan las bombas?", o: ["Para repartir horas de marcha y desgaste, y saber que la reserva funciona", "Para bombear más", "Para ahorrar energía"], a: 0, e: "Una bomba de reserva que nunca gira suele fallar justo cuando se necesita." },
    { q: "¿Qué evento cambia el turno?", o: ["El flanco positivo de nivel alto", "El fin de cada ciclo de bombeo (flanco negativo de la demanda)", "Un temporizador de 1 s"], a: 1, e: "Así cada ciclo lo hace una bomba distinta." },
    { q: "¿Por qué la bomba para con el nivel bajo y no con el alto?", o: ["Por histéresis: bombea de alto a bajo y evita arranques continuos", "Porque el sensor alto falla", "Da igual"], a: 0, e: "La banda entre ambos niveles da ciclos largos." }
  ] }
);
