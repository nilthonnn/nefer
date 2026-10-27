"""Pipeline completo: un manejador por estado de la FSM.

Cada manejador lee los artefactos de las etapas anteriores desde el
registro (JSON) y devuelve los suyos. No hay estado en memoria entre etapas:
eso es lo que permite reanudar cualquier run tras un corte.
"""

from __future__ import annotations

import json
import random
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import qa
from ..audio import mezcla, motores
from ..errors import ErrorContenido
from ..logs import a_archivo, obtener, quitar
from ..memory import Memoria
from ..models import Guion, Narracion, Serie, Tendencia, Variacion
from ..publisher import seo
from ..publisher.cuota import Cuota
from ..scripts import generador
from ..settings import Settings
from ..sources import tendencias, worldbank
from ..visuals import render, variacion
from ..visuals.broll import BRoll
from .fsm import Estado, MaquinaEstados, Politica, Registro

log = obtener("pipeline")

POLITICAS = {
    Estado.TENDENCIA: Politica(intentos=3, espera_inicial=5),
    Estado.DATOS: Politica(intentos=3, espera_inicial=5),
    Estado.GUION: Politica(intentos=3, espera_inicial=10),
    Estado.VOZ: Politica(intentos=3, espera_inicial=5),
    Estado.VISUALES: Politica(intentos=2, espera_inicial=5),
    Estado.RENDER: Politica(intentos=2, espera_inicial=15),
    Estado.PUBLICACION: Politica(intentos=3, espera_inicial=30),
}


def nuevo_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


class Pipeline:
    def __init__(self, cfg: Settings, yt: Any = None, motor_voz: Any = None, proveedor_llm: Any = None,
                 sesion_http: Any = None) -> None:
        self.cfg = cfg
        self.memoria = Memoria(cfg.dir_estado)
        # Inyectables en pruebas (dobles de YouTube, voz, LLM y HTTP).
        self.yt, self.motor_voz, self.proveedor_llm, self.sesion_http = yt, motor_voz, proveedor_llm, sesion_http

    def dir_run(self, run_id: str) -> Path:
        return self.cfg.dir_runs / run_id

    def maquina(self, run_id: str) -> MaquinaEstados:
        return MaquinaEstados(
            self.dir_run(run_id) / "estado.json",
            {
                Estado.INICIADO: self.iniciar, Estado.TENDENCIA: self.tendencia, Estado.DATOS: self.datos,
                Estado.GUION: self.guion, Estado.VOZ: self.voz, Estado.VISUALES: self.visuales,
                Estado.RENDER: self.render, Estado.QA: self.qa, Estado.PUBLICACION: self.publicar,
            },
            POLITICAS,
        )

    def ejecutar(self, opciones: dict[str, Any]) -> Registro:
        run_id = opciones.pop("run_id", None) or nuevo_id()
        return self._correr(Registro(run_id=run_id, opciones=opciones))

    def reanudar(self, run_id: str) -> Registro:
        m = self.maquina(run_id)
        return self._correr(m.reanudar(m.cargar(m.ruta)))

    def _correr(self, r: Registro) -> Registro:
        manejador = a_archivo(self.dir_run(r.run_id) / "auditoria.jsonl")
        try:
            log.info("run %s: %s", r.run_id, r.estado)
            return self.maquina(r.run_id).ejecutar(r)
        finally:
            quitar(manejador)

    # --- etapas ---------------------------------------------------------------
    def iniciar(self, r: Registro) -> dict:
        semilla = r.opciones.get("semilla") or self.cfg.semilla or random.SystemRandom().randrange(1, 2**31)
        v = variacion.elegir(semilla, self.memoria.firmas_recientes())
        log.info("diseño: %s", v.firma())
        return {"variacion": v.model_dump()}

    def tendencia(self, r: Registro) -> dict:
        tema = r.opciones.get("tema")
        if tema:
            t = Tendencia(titulo=tema, fuente="manual")
        else:
            cubiertos = [e.get("tema", "") for e in self.memoria.entradas(60)]
            t = tendencias.buscar(cubiertos, sesion=self.sesion_http)
        log.info("tema: %s (%s)", t.titulo, t.fuente)
        return {"tendencia": t.model_dump()}

    def datos(self, r: Registro) -> dict:
        archivo = r.opciones.get("serie_archivo")
        if archivo:  # serie local (pruebas o datos propios ya verificados)
            serie = Serie.model_validate_json(Path(archivo).read_text(encoding="utf-8"))
        else:
            t = Tendencia.model_validate(r.artefactos["tendencia"])
            indicador, pais = worldbank.elegir(t.titulo, self.memoria.indicadores_recientes())
            serie = worldbank.descargar(indicador, pais, sesion=self.sesion_http)
        log.info("dato: %s · %s (%d puntos)", serie.indicador, serie.pais_nombre, len(serie.puntos))
        return {"serie": serie.model_dump()}

    def guion(self, r: Registro) -> dict:
        t = Tendencia.model_validate(r.artefactos["tendencia"])
        serie = Serie.model_validate(r.artefactos["serie"])
        rng = random.Random(r.artefactos["variacion"]["semilla"])
        g, ev = generador.escribir(self.cfg, t, serie, self.memoria, self.proveedor_llm, rng)
        if not ev.ok and g.generador != "plantilla":
            raise ErrorContenido("guion inválido: " + "; ".join(ev.errores))
        (self.dir_run(r.run_id) / "guion.json").write_text(g.model_dump_json(indent=2), encoding="utf-8")
        return {"guion": g.model_dump(), "evaluacion": {"errores": ev.errores, "avisos": ev.avisos, "puntaje": ev.puntaje}}

    def voz(self, r: Registro) -> dict:
        g = Guion.model_validate(r.artefactos["guion"])
        v = Variacion.model_validate(r.artefactos["variacion"])
        motor = self.motor_voz or motores.crear(self.cfg)
        n = mezcla.narrar(g, motor, v, self.cfg, self.dir_run(r.run_id) / "audio")
        log.info("voz %s: %.2f s, %d palabras (tiempos %s)", n.motor, n.duracion, len(n.palabras),
                 "exactos" if n.exacta else "estimados")
        return {"narracion": json.loads(n.model_dump_json()), "voz_publicable": bool(getattr(motor, "publicable", False))}

    def visuales(self, r: Registro) -> dict:
        g = Guion.model_validate(r.artefactos["guion"])
        n = Narracion.model_validate(r.artefactos["narracion"])
        brolls: dict[int, str] = {}
        creditos: list[str] = []
        ids: list[str] = []
        clave = Settings.secreto(self.cfg.pexels_api_key)
        pendientes = [i for i, f in enumerate(g.frases) if f.visual == "broll"]
        if pendientes and not clave:
            log.warning("sin PEXELS_API_KEY: las escenas de b-roll usan fondo generativo")
        elif pendientes:
            usados = {i for e in self.memoria.entradas() for i in e.get("broll", [])}
            pexels = BRoll(clave, usados, self.sesion_http)
            for i in pendientes:
                inicio = n.frases[i][0]
                fin = n.frases[i + 1][0] if i + 1 < len(n.frases) else n.duracion
                destino = self.dir_run(r.run_id) / f"broll{i:02d}.mp4"
                hallado = pexels.obtener(g.frases[i].broll_busqueda, destino, fin - inicio + 0.5, self.cfg.fps)
                if hallado:
                    ruta, vid, autor = hallado
                    brolls[i] = ruta.name
                    ids.append(vid)
                    creditos.append(f"Video: {autor} (Pexels)" if autor else "Video: Pexels")
        return {"brolls": brolls, "broll_ids": ids, "creditos": sorted(set(creditos))}

    def render(self, r: Registro) -> dict:
        g = Guion.model_validate(r.artefactos["guion"])
        n = Narracion.model_validate(r.artefactos["narracion"])
        serie = Serie.model_validate(r.artefactos["serie"])
        v = Variacion.model_validate(r.artefactos["variacion"])
        brolls = {int(k): f"runs/{r.run_id}/{f}" for k, f in r.artefactos.get("brolls", {}).items()}
        segs = render.segmentos(g, n, brolls)
        dir_run = self.dir_run(r.run_id)
        render.preparar_public(self.cfg, r.run_id, [n.audio, *[dir_run / Path(f).name for f in brolls.values()]])
        datos = render.props(r.run_id, g, n, serie, v, segs, self.cfg.fps)
        salida = dir_run / "short.mp4"
        render.renderizar(self.cfg, datos, salida)
        return {"video": str(salida)}

    def qa(self, r: Registro) -> dict:
        info = qa.revisar(Path(r.artefactos["video"]), self.cfg.duracion_max, self.cfg.fps, self.cfg.lufs)
        motivos = []
        if r.artefactos["guion"].get("generador") == "plantilla":
            motivos.append("guion de plantilla (solo pruebas)")
        if not r.artefactos.get("voz_publicable"):
            motivos.append("voz de desarrollo (espeak)")
        if r.artefactos.get("evaluacion", {}).get("errores"):
            motivos.append("el guion tiene errores de heurística")
        return {"qa": info, "publicable": not motivos, "motivos_no_publicable": motivos}

    def publicar(self, r: Registro) -> dict:
        destino = r.opciones.get("publicar", "no")
        render.limpiar_public(self.cfg, r.run_id)
        if destino == "no":
            log.info("publicación desactivada (--publicar no)")
            return {"publicado": False}
        if not r.artefactos.get("publicable"):
            raise ErrorContenido("No publicable: " + "; ".join(r.artefactos.get("motivos_no_publicable", [])))
        from ..publisher import youtube

        g = Guion.model_validate(r.artefactos["guion"])
        serie = Serie.model_validate(r.artefactos["serie"])
        t = Tendencia.model_validate(r.artefactos["tendencia"])
        v = Variacion.model_validate(r.artefactos["variacion"])
        creditos = [*r.artefactos.get("creditos", []), mezcla.creditos_musica(self.cfg, v.semilla)]
        meta = youtube.cuerpo(self.cfg, seo.titulo(g), seo.descripcion(g, serie, t, creditos), seo.etiquetas(g, serie), destino)
        Cuota(self.cfg.dir_estado, self.cfg.youtube_cuota_diaria).reservar(self.cfg.youtube_costo_subida)
        res = youtube.subir(self.cfg, Path(r.artefactos["video"]), meta, yt=self.yt)
        self.memoria.registrar(
            run_id=r.run_id, tema=t.titulo, titulo=g.titulo, narracion=g.texto, indicador=serie.indicador_id,
            variacion=v.firma(), broll=r.artefactos.get("broll_ids", []), video_id=res.video_id, privacidad=res.privacidad,
        )
        log.info("publicado: %s (%s)", res.url, res.privacidad)
        return {"publicado": True, "subida": res.model_dump()}
