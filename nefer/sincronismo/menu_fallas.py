"""Menu de fallas: el analisis RCM de la planta, para recorrerlo falla por falla.

No es un motor nuevo. Toma un analisis RCM en el formato de FixMate (el
mismo que valida `nefer fixmate rcm analizar` contra SAE JA1011) y lo
convierte en una pagina de un solo archivo donde cada modo de falla muestra:

- funcion, falla funcional, causa, efecto y consecuencias (las siete
  preguntas de RCM, respondidas);
- la AMEF: severidad, ocurrencia y deteccion con el texto de cada nivel, el
  NPR (S x O x D) y, al lado, la prioridad de accion al estilo AIAG-VDA. Las
  dos, porque el NPR multiplica escalas ordinales y dos riesgos muy
  distintos pueden dar el mismo numero (ver `fixmate/criticidad.py`); la
  prioridad de accion no tiene ese defecto. Se muestra el NPR porque muchos
  procedimientos lo piden, con la advertencia encima;
- el arbol de decision RCM recorrido pregunta por pregunta, con la respuesta
  y a donde llevo, hasta la estrategia: el mismo `decision.decidir()` que
  usa FixMate, incluida la regla de que con consecuencia de seguridad
  «operar hasta la falla» no es una salida;
- la tarea propuesta, las fuentes y, si corresponde, las causas a descartar
  de la guia de sintomas del paralelo.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from ..fixmate import cargador, fmeca
from ..fixmate.criticidad import PRIORIDAD_EJEMPLO, RPN_EJEMPLO, evaluar
from . import diagnostico, plan_accion

COLOR_ESTRATEGIA = {
    "cbm": "#059669", "restauracion": "#2563eb", "descarte": "#7c3aed",
    "busqueda_fallas": "#b45309", "operar_hasta_falla": "#6b7280",
    "rediseno": "#b91c1c",
}


def datos(ruta: str | Path) -> dict:
    """Todo lo que la pagina necesita, ya calculado en Python."""
    crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    analisis, decisiones = cargador.analisis_y_decisiones(ruta)
    filas = fmeca.filas(analisis, decisiones)

    extras = [md for fd in crudo["funciones"] for ffd in fd["fallas"] for md in ffd["modos"]]
    guia = {s.id: s for s in diagnostico.GUIA}
    niveles = {f.clave: {n.valor: (n.etiqueta, n.descripcion) for n in f.niveles}
               for f in RPN_EJEMPLO.factores}

    amef = {f.modo_id: f for f in plan_accion.amef(ruta)}
    plan = plan_accion.plan(list(amef.values()), analisis.fecha)
    resumen_plan = plan_accion.resumen(list(amef.values()))

    modos = []
    for modo, fila, extra in zip(analisis.modos, filas, extras):
        af = amef.get(modo.id)
        v = dict(modo.criticidad.valores) or dict(extra.get("criticidad") or {})
        npr = evaluar(RPN_EJEMPLO, v) if v else None
        ap = evaluar(PRIORIDAD_EJEMPLO, v) if v else None
        d = decisiones.get(modo.id)
        sintoma = guia.get(extra.get("sintoma_guia", ""))
        modos.append({
            "id": modo.id,
            "sistema": modo.ubicacion.sistema,
            "componente": modo.ubicacion.componente,
            "funcion": fila["funcion"], "estandar": fila["estandar"],
            "falla": fila["falla_funcional"], "modo": modo.descripcion,
            "causa": modo.causa, "mecanismo": modo.mecanismo,
            "evidente": modo.evidente,
            "efecto": {"local": modo.efecto.local, "observa": modo.efecto.observa_operador,
                       "parametro": modo.efecto.parametro, "alarma": modo.efecto.alarma},
            "consecuencias": [c.a_dict() for c in modo.consecuencias],
            "grave": modo.grave if isinstance(getattr(modo, "grave", None), bool)
                     else any(c.grave for c in modo.consecuencias),
            "sod": {k: {"valor": v[k], "nivel": niveles[k][v[k]][0],
                        "texto": niveles[k][v[k]][1]} for k in v},
            "npr": npr.valor if npr else None,
            "npr_etiqueta": npr.etiqueta if npr else "no evaluada",
            "ap": ap.etiqueta if ap else "no evaluada",
            "estrategia": d.estrategia if d else None,
            "estrategia_rotulo": d.rotulo if d else "Sin decidir",
            "motivo": d.motivo if d else "",
            "por_defecto": bool(d and d.por_defecto),
            "camino": [p.a_dict() for p in d.camino] if d else [],
            "tarea": extra.get("tarea_propuesta", ""),
            "fuentes": [{"url": r.referencia, "nota": r.nota} for r in modo.evidencia],
            "estado": modo.estado,
            "guia": ({"id": sintoma.id, "titulo": sintoma.titulo,
                      "causas": [c.causa for c in sintoma.causas]} if sintoma else None),
            "controles": extra.get("controles_actuales") or {},
            "acciones": list(extra.get("plan_accion") or []),
            "residual": ({"s": af.severidad_r, "o": af.ocurrencia_r, "d": af.deteccion_r,
                          "npr": af.npr_r, "ap": af.ap_r, "reduccion": af.reduccion_npr_pct}
                         if af and af.npr_r is not None else None),
            "observaciones": [o.__dict__ for o in af.observaciones] if af else [],
            "codigo": (af.codigo_catalogo if af else ""),
        })

    return {
        "activo": {"codigo": analisis.activo.codigo, "nombre": analisis.activo.nombre,
                   "modelo": analisis.activo.modelo},
        "contexto": crudo.get("contexto", ""),
        "fecha": analisis.fecha, "revision": crudo.get("revision", ""),
        "advertencia_npr": RPN_EJEMPLO.advertencia,
        "umbrales_npr": [list(u) for u in RPN_EJEMPLO.umbrales],
        "colores": COLOR_ESTRATEGIA,
        "modos": modos,
        "plan": plan,
        "resumen_plan": resumen_plan,
    }


CSS = """
:root{--fondo:#f4f6f8;--panel:#fff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db;
--acento:#2563eb;--alta:#b91c1c;--media:#b45309;--baja:#15803d}
@media (prefers-color-scheme:dark){:root{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;
--suave:#9ca3af;--borde:#334155;--acento:#60a5fa;--alta:#f87171;--media:#fbbf24;--baja:#4ade80}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
header{padding:16px;max-width:1200px;margin:0 auto}
h1{font-size:1.4rem;margin:0 0 4px}.sub{color:var(--suave);margin:0}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:8px 12px}
.kpi b{display:block;font-size:1.3rem}
.cuerpo{display:grid;grid-template-columns:330px 1fr;gap:14px;max-width:1200px;margin:0 auto;padding:0 16px 16px}
@media (max-width:820px){.cuerpo{grid-template-columns:1fr}}
nav{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:10px;
max-height:80vh;overflow:auto;position:sticky;top:8px}
@media (max-width:820px){nav{position:static;max-height:46vh}}
nav input,nav select{width:100%;padding:8px;border:1px solid var(--borde);border-radius:8px;
background:var(--fondo);color:var(--tinta);font:inherit;margin-bottom:6px}
nav h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--suave);margin:10px 4px 4px}
nav button{display:flex;gap:8px;align-items:flex-start;width:100%;text-align:left;
background:none;border:1px solid transparent;border-radius:8px;padding:7px;color:var(--tinta);
font:inherit;cursor:pointer}
nav button:hover{background:var(--fondo)}
nav button[aria-current=true]{border-color:var(--acento);background:var(--fondo)}
.chip{flex:none;min-width:38px;text-align:center;border-radius:999px;padding:1px 6px;
font-size:.78rem;font-weight:700;color:#fff}
.chip.alta{background:var(--alta)}.chip.media{background:var(--media)}.chip.baja{background:var(--baja)}
.det{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:16px;min-width:0}
.det h2{margin:0 0 4px;font-size:1.2rem}
.migas{color:var(--suave);font-size:.88rem}
.rejilla{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:12px 0}
.caja{border:1px solid var(--borde);border-radius:8px;padding:10px}
.caja b{display:block;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--suave)}
.sod{display:grid;grid-template-columns:repeat(3,1fr) 1.2fr 1.2fr;gap:8px;margin:12px 0}
@media (max-width:620px){.sod{grid-template-columns:repeat(2,1fr)}}
.f{border:1px solid var(--borde);border-radius:8px;padding:8px;text-align:center}
.f .n{font-size:1.6rem;font-weight:800}.f small{display:block;color:var(--suave)}
.barra{height:6px;border-radius:3px;background:var(--borde);margin-top:4px}
.barra i{display:block;height:100%;border-radius:3px;background:var(--acento)}
.aviso{font-size:.8rem;color:var(--suave);border-left:3px solid var(--media);padding-left:8px}
.arbol{list-style:none;padding:0;margin:8px 0}
.arbol li{position:relative;padding:0 0 14px 28px}
.arbol li:before{content:"";position:absolute;left:9px;top:22px;bottom:0;border-left:2px solid var(--borde)}
.arbol li:last-child:before{display:none}
.arbol .q{position:absolute;left:0;top:2px;width:20px;height:20px;border-radius:50%;
background:var(--acento);color:#fff;font-size:.75rem;display:flex;align-items:center;justify-content:center}
.resp{display:inline-block;border-radius:6px;padding:0 6px;font-weight:700;font-size:.8rem;margin-left:6px}
.resp.si{background:#dcfce7;color:#166534}.resp.no{background:#fee2e2;color:#991b1b}
.resp.otro{background:#e5e7eb;color:#374151}
.cons{color:var(--suave);font-size:.88rem}
.estr{border-radius:10px;padding:12px;color:#fff;margin:6px 0 12px}
.estr b{font-size:1.05rem}
a{color:var(--acento)}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--borde);padding:6px;text-align:left;font-size:.9rem}
.pareto i{display:inline-block;height:10px;border-radius:3px;background:var(--acento);vertical-align:middle}
.tabla{overflow-x:auto}
section{max-width:1200px;margin:0 auto;padding:0 16px 24px}
.antesdespues{display:grid;grid-template-columns:1fr auto 1fr 1fr;gap:8px;align-items:center;margin:10px 0}
@media (max-width:620px){.antesdespues{grid-template-columns:1fr}.flecha{display:none}}
.flecha{font-size:2rem;color:var(--suave)}
.obs li{color:var(--alta)}.ok{color:var(--baja);font-weight:600}
.chip.no{background:#6b7280}
#tamef td,#tamef th{font-size:.8rem;min-width:70px}
details.sec{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:10px 14px;margin:10px 0}
details.sec summary{cursor:pointer;font-weight:700;font-size:1.05rem}
"""

JS = r"""
const D = JSON.parse(document.getElementById('datos').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let actual = null;

function menu() {
  const q = $('#buscar').value.toLowerCase();
  const orden = $('#orden').value;
  let ms = D.modos.filter(m => (m.modo + ' ' + m.sistema + ' ' + m.falla + ' ' + m.componente)
      .toLowerCase().includes(q));
  if (orden === 'npr') ms.sort((a, b) => (b.npr ?? -1) - (a.npr ?? -1));
  const grupos = {};
  ms.forEach(m => { const g = orden === 'npr' ? 'Por NPR, de mayor a menor' : m.sistema;
                    (grupos[g] = grupos[g] || []).push(m); });
  $('#lista').innerHTML = Object.entries(grupos).map(([g, xs]) =>
    `<h3>${esc(g)}</h3>` + xs.map(m =>
      `<button data-id="${m.id}" aria-current="${m.id === actual}">
        <span class="chip ${m.npr_etiqueta}">${m.npr ?? '—'}</span>
        <span>${esc(m.modo)}<br><small style="color:var(--suave)">${esc(m.sistema)} · ${m.evidente ? 'evidente' : 'OCULTA'}${m.grave ? ' · seguridad' : ''}</small></span>
      </button>`).join('')).join('') || '<p>Ninguna falla coincide.</p>';
  document.querySelectorAll('#lista button').forEach(b =>
    b.addEventListener('click', () => mostrar(b.dataset.id, true)));
}

function respuesta(r) {
  const k = r === 'si' ? 'si' : r === 'no' ? 'no' : 'otro';
  return `<span class="resp ${k}">${esc(r)}</span>`;
}

function mostrar(id, desplazar) {
  actual = id;
  const m = D.modos.find(x => x.id === id);
  const sod = ['severidad', 'frecuencia', 'deteccion'].map(k => {
    const f = m.sod[k]; const nom = {severidad:'Severidad (S)', frecuencia:'Ocurrencia (O)', deteccion:'Deteccion (D)'}[k];
    return f ? `<div class="f"><small>${nom}</small><div class="n">${f.valor}</div>
      <div class="barra"><i style="width:${f.valor*20}%"></i></div><small>${esc(f.nivel)}: ${esc(f.texto)}</small></div>` : '';
  }).join('');
  const color = D.colores[m.estrategia] || '#6b7280';
  const camino = m.camino.map((p, i) => `<li><span class="q">${i+1}</span>
      <b>${esc(p.pregunta)}</b>${respuesta(p.respuesta)}<div class="cons">→ ${esc(p.consecuencia)}</div></li>`).join('');
  const guia = m.guia ? `<div class="caja"><b>Causas a descartar en campo (guia ${m.guia.id})</b>
      <ol>${m.guia.causas.map(c => `<li>${esc(c)}</li>`).join('')}</ol></div>` : '';
  const fuentes = m.fuentes.map(f => `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.url.replace(/^https?:\/\//,'').slice(0,60))}</a>${f.nota ? ' — ' + esc(f.nota) : ''}</li>`).join('');
  $('#detalle').innerHTML = `
    <div class="migas">${esc(m.sistema)} › ${esc(m.componente)} · ${esc(m.id)} · estado: ${esc(m.estado)}</div>
    <h2>${esc(m.modo)}</h2>
    <div class="rejilla">
      <div class="caja"><b>1 · Funcion</b>${esc(m.funcion)}<br><small>Estandar: ${esc(m.estandar)}</small></div>
      <div class="caja"><b>2 · Falla funcional</b>${esc(m.falla)}</div>
      <div class="caja"><b>3 · Modo y causa</b>${esc(m.modo)}${m.causa ? '<br><small>Causa: ' + esc(m.causa) + '</small>' : ''}</div>
      <div class="caja"><b>4 · Efecto</b>${esc(m.efecto.local)}<br><small>Lo que ve el operador: ${esc(m.efecto.observa)}${m.efecto.alarma ? ' · Alarma: ' + esc(m.efecto.alarma) : ''}</small></div>
      <div class="caja"><b>5 · Consecuencia</b>${m.consecuencias.map(c => esc(c.clase) + ': ' + esc(c.descripcion)).join('<br>')}<br><small>${m.evidente ? 'Falla evidente' : 'Falla OCULTA: nadie la nota hasta que se necesita la funcion'}</small></div>
    </div>
    <h3>AMEF: severidad, ocurrencia, deteccion</h3>
    <div class="sod">${sod}
      <div class="f"><small>NPR = S × O × D</small><div class="n">${m.npr ?? '—'}</div><span class="chip ${m.npr_etiqueta}">${esc(m.npr_etiqueta)}</span></div>
      <div class="f"><small>Prioridad de accion (AIAG-VDA)</small><div class="n" style="font-size:1.2rem;margin:6px 0">${esc(m.ap)}</div><small>severidad primero, sin multiplicar</small></div>
    </div>
    <p class="aviso">${esc(D.advertencia_npr)}</p>
    <h3>6 y 7 · Arbol de decision RCM</h3>
    <ol class="arbol">${camino}</ol>
    <div class="estr" style="background:${color}"><b>${esc(m.estrategia_rotulo)}</b>${m.por_defecto ? ' · accion por defecto' : ''}<br>${esc(m.motivo)}</div>
    <div class="rejilla">
      <div class="caja"><b>Tarea propuesta (RCM)</b>${esc(m.tarea) || '—'}</div>${guia}
    </div>
    <h3>Solucion: controles, plan de accion y riesgo residual</h3>
    <div class="rejilla">
      <div class="caja"><b>Control de prevencion actual</b>${esc(m.controles.prevencion) || '—'}</div>
      <div class="caja"><b>Control de deteccion actual</b>${esc(m.controles.deteccion) || '—'}</div>
    </div>
    <div class="tabla"><table><tr><th>Accion</th><th>Tipo</th><th>Responsable</th><th>Plazo</th><th>Intervalo</th><th>Como se verifica</th></tr>
    ${m.acciones.map(a => `<tr><td>${esc(a.accion)}</td><td>${esc(a.tipo)}</td><td>${esc(a.responsable)}</td><td>${esc(a.plazo_dias)} d</td><td>${esc(a.intervalo || '—')}</td><td>${esc(a.verificacion)}</td></tr>`).join('') || '<tr><td colspan="6">Sin acciones</td></tr>'}</table></div>
    ${m.residual ? `<div class="antesdespues">
      <div class="f"><small>Antes</small><div class="n">${m.npr}</div><small>S${m.sod.severidad.valor} · O${m.sod.frecuencia.valor} · D${m.sod.deteccion.valor} · prioridad ${esc(m.ap)}</small></div>
      <div class="flecha">→</div>
      <div class="f"><small>Despues de las acciones</small><div class="n">${m.residual.npr}</div><small>S${m.residual.s} · O${m.residual.o} · D${m.residual.d} · prioridad ${esc(m.residual.ap)}</small></div>
      <div class="f"><small>Reduccion del NPR</small><div class="n">${m.residual.reduccion} %</div><small>la severidad solo baja con rediseño</small></div>
    </div>` : ''}
    ${m.observaciones.length ? `<ul class="obs">${m.observaciones.map(o => `<li><b>${esc(o.regla)}</b> ${esc(o.texto)}</li>`).join('')}</ul>` : '<p class="ok">El plan cumple las reglas R1–R7 (IEC 60812 / AIAG-VDA / SAE JA1011).</p>'}
    <h3>Fuentes</h3><ul>${fuentes}</ul>`;
  menu();
  if (desplazar && window.innerWidth < 820) $('#detalle').scrollIntoView({behavior: 'smooth'});
}

function tablas() {
  const ap = {alta: 0, media: 1, baja: 2};
  $('#tplan').innerHTML = `<tr><th>#</th><th>Prioridad</th><th>S</th><th>Accion</th><th>Falla</th><th>Tipo</th><th>Responsable</th><th>Fecha objetivo</th><th>Intervalo</th><th>Verificacion</th></tr>` +
    D.plan.map((a, i) => `<tr><td>${i+1}</td><td><span class="chip ${a.prioridad}">${esc(a.prioridad)}</span></td><td>${a.severidad}</td><td>${esc(a.accion)}</td>
      <td><a href="#" data-id="${a.modo_id}">${esc(a.modo_falla)}</a></td><td>${esc(a.tipo)}</td><td>${esc(a.responsable)}</td>
      <td>${esc(a.fecha_objetivo)}</td><td>${esc(a.intervalo || '—')}</td><td>${esc(a.verificacion)}</td></tr>`).join('');
  $('#tamef').innerHTML = `<tr><th>Sistema</th><th>Funcion</th><th>Falla funcional</th><th>Efecto</th><th>S</th><th>Modo / causa</th><th>Prevencion actual</th><th>O</th><th>Deteccion actual</th><th>D</th><th>NPR</th><th>AP</th><th>Estrategia</th><th>Acciones</th><th>S'</th><th>O'</th><th>D'</th><th>NPR'</th><th>AP'</th></tr>` +
    D.modos.map(m => `<tr><td>${esc(m.sistema)}</td><td>${esc(m.funcion)}</td><td>${esc(m.falla)}</td><td>${esc(m.efecto.local)}</td>
      <td>${m.sod.severidad.valor}</td><td><a href="#" data-id="${m.id}">${esc(m.modo)}</a><br><small>${esc(m.causa)}</small></td>
      <td>${esc(m.controles.prevencion)}</td><td>${m.sod.frecuencia.valor}</td><td>${esc(m.controles.deteccion)}</td><td>${m.sod.deteccion.valor}</td>
      <td><b>${m.npr}</b></td><td><span class="chip ${m.ap}">${esc(m.ap)}</span></td><td>${esc(m.estrategia_rotulo)}</td>
      <td>${m.acciones.map(a => '• ' + esc(a.accion)).join('<br>')}</td>
      <td>${m.residual?.s ?? ''}</td><td>${m.residual?.o ?? ''}</td><td>${m.residual?.d ?? ''}</td><td><b>${m.residual?.npr ?? ''}</b></td>
      <td>${m.residual ? `<span class="chip ${m.residual.ap}">${esc(m.residual.ap)}</span>` : ''}</td></tr>`).join('');
  document.querySelectorAll('#tplan a, #tamef a').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); mostrar(a.dataset.id, false); window.scrollTo({top: 0, behavior: 'smooth'}); }));
}

function pareto() {
  const ms = [...D.modos].sort((a, b) => (b.npr ?? 0) - (a.npr ?? 0));
  const max = Math.max(...ms.map(m => m.npr || 0), 1);
  $('#pareto').innerHTML = `<tr><th>NPR</th><th>Modo de falla</th><th>Sistema</th><th>Prioridad</th><th>Estrategia</th><th>NPR despues</th></tr>` +
    ms.map(m => `<tr><td class="pareto"><i style="width:${Math.round(80*(m.npr||0)/max)}px;background:var(--${m.npr_etiqueta})"></i> ${m.npr ?? '—'}</td>
      <td><a href="#" data-id="${m.id}">${esc(m.modo)}</a></td><td>${esc(m.sistema)}</td><td>${esc(m.ap)}</td><td>${esc(m.estrategia_rotulo)}</td><td>${m.residual ? m.residual.npr + ' (' + esc(m.residual.ap) + ')' : '—'}</td></tr>`).join('');
  document.querySelectorAll('#pareto a').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); mostrar(a.dataset.id, false); window.scrollTo({top: 0, behavior: 'smooth'}); }));
}

$('#buscar').addEventListener('input', menu);
$('#orden').addEventListener('change', menu);
pareto();
tablas();
const primero = [...D.modos].sort((a, b) => (b.npr ?? 0) - (a.npr ?? 0))[0];
mostrar(primero.id, false);
"""


def pagina(ruta: str | Path) -> str:
    d = datos(ruta)
    ms = d["modos"]
    n_ocultos = sum(1 for m in ms if not m["evidente"])
    n_graves = sum(1 for m in ms if m["grave"])
    n_alta = sum(1 for m in ms if m["ap"] == "alta")
    reparto: dict[str, int] = {}
    for m in ms:
        reparto[m["estrategia_rotulo"]] = reparto.get(m["estrategia_rotulo"], 0) + 1
    kpis = [("Modos de falla", len(ms)), ("Ocultos", n_ocultos),
            ("Con consecuencia de seguridad", n_graves), ("Prioridad alta", n_alta)]
    kpis += sorted(reparto.items(), key=lambda x: -x[1])
    rp = d["resumen_plan"]
    kpis += [("NPR total antes → despues", f"{rp['npr_total_inicial']} → {rp['npr_total_residual']}"),
             ("Prioridad alta antes → despues", f"{rp['ap_inicial']['alta']} → {rp['ap_residual']['alta']}")]
    datos_json = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    a = d["activo"]
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Menu de fallas RCM</title><style>{CSS}</style></head><body>
<header>
<h1>Menu de fallas — RCM y AMEF</h1>
<p class="sub">{escape(a['nombre'])} · {escape(a['modelo'])} · revision {escape(d['revision'])} ({escape(d['fecha'])})</p>
<p class="sub">{escape(d['contexto'])}</p>
<div class="kpis">{''.join(f'<div class="kpi"><b>{v}</b>{escape(k)}</div>' for k, v in kpis)}</div>
</header>
<div class="cuerpo">
<nav aria-label="Fallas">
<input id="buscar" type="search" placeholder="Buscar falla, sistema o componente">
<select id="orden" aria-label="Ordenar"><option value="sistema">Agrupar por sistema</option>
<option value="npr">Ordenar por NPR</option></select>
<div id="lista"></div>
</nav>
<main class="det" id="detalle"></main>
</div>
<section>
<details class="sec" open><summary>Plan de accion priorizado ({len(d['plan'])} acciones)</summary>
<p class="sub">Orden: prioridad de accion, luego severidad, luego NPR. Fecha objetivo = fecha del analisis + plazo.
NPR total {d['resumen_plan']['npr_total_inicial']} → {d['resumen_plan']['npr_total_residual']}
({d['resumen_plan']['reduccion_pct']} % menos) · prioridad alta {d['resumen_plan']['ap_inicial']['alta']} →
{d['resumen_plan']['ap_residual']['alta']}.</p>
<div class="tabla"><table id="tplan"></table></div></details>
<details class="sec"><summary>AMEF completa (IEC 60812 / AIAG-VDA)</summary>
<div class="tabla"><table id="tamef"></table></div></details>
<h2>Pareto de riesgo (NPR)</h2><div class="tabla"><table id="pareto"></table></div>
<p class="sub" style="margin-top:12px">Generado por <code>nefer sincronismo fallas</code> sobre el motor RCM de FixMate
(SAE JA1011). Escalas de criticidad de EJEMPLO: reescriba sus niveles con lo que significan en su planta,
y reemplace la ocurrencia propuesta con el historial propio.</p></section>
<script type="application/json" id="datos">{datos_json}</script>
<script>{JS}</script>
</body></html>
"""
