import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shortsfactory.errors import ErrorAutenticacion, ErrorCuota, ErrorTransitorio
from shortsfactory.models import Tendencia
from shortsfactory.publisher import seo, youtube
from shortsfactory.publisher.cuota import Cuota
from shortsfactory.settings import Settings

from conftest import guion_bueno


def test_seo_respeta_limites(serie):
    g = guion_bueno(hashtags=["#inflacion", "#economia", "#datos", "#mas", "#otro"])
    assert seo.titulo(g).endswith("#Shorts") and len(seo.titulo(g)) <= 100
    assert seo.hashtags(g)[-1] == "#Shorts" or len(seo.hashtags(g)) == 4
    d = seo.descripcion(g, serie, Tendencia(titulo="Noticia", url="https://n"), ["Video: Ana (Pexels)"])
    assert "Fuente: Serie sintética" in d and "no es asesoría financiera" in d and "Ana (Pexels)" in d
    assert sum(len(e) + 3 for e in seo.etiquetas(g, serie)) <= 503


def test_cuota_por_dia_del_pacifico(tmp_path):
    c = Cuota(tmp_path, limite=3200)
    # 07:30 UTC = 00:30 en Los Ángeles (PDT): ya es el día 26 allí.
    dia1 = datetime(2026, 10, 26, 6, 30, tzinfo=timezone.utc)
    c.reservar(1600, dia1)
    c.reservar(1600, dia1)
    with pytest.raises(ErrorCuota):
        c.reservar(1600, dia1)
    assert c.usadas(datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)) == 0  # nuevo día en el Pacífico


class _HttpError(Exception):
    pass


class _Peticion:
    def __init__(self, guion):
        self.guion = list(guion)

    def next_chunk(self):
        paso = self.guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        return paso


def _yt(guion, capturado):
    class Videos:
        def insert(self, part, body, media_body):
            capturado.update(part=part, body=body)
            return _Peticion(guion)

    return type("YT", (), {"videos": lambda self: Videos()})()


def _http_error(status, texto=""):
    from googleapiclient.errors import HttpError

    return HttpError(type("Resp", (), {"status": status, "reason": "x"})(), texto.encode())


@pytest.fixture
def video(tmp_path) -> Path:
    v = tmp_path / "v.mp4"
    v.write_bytes(b"\x00" * 1024)
    return v


def test_subida_reanudable_con_reintentos(video):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None, youtube_contenido_sintetico=True)
    capturado, esperas = {}, []
    meta = youtube.cuerpo(cfg, "Título #Shorts", "desc", ["a"], "private")
    yt = _yt([_http_error(503), ConnectionResetError("corte"), (None, {"id": "abc123", "status": {"privacyStatus": "private"}})], capturado)
    r = youtube.subir(cfg, video, meta, yt=yt, dormir=esperas.append)
    assert r.video_id == "abc123" and r.url.endswith("/shorts/abc123") and len(esperas) == 2
    estado = capturado["body"]["status"]
    assert estado["privacyStatus"] == "private" and estado["selfDeclaredMadeForKids"] is False
    assert estado["containsSyntheticMedia"] is True


@pytest.mark.parametrize("error, tipo", [
    (lambda: _http_error(403, '{"error": {"errors": [{"reason": "quotaExceeded"}]}}'), ErrorCuota),
    (lambda: _http_error(401), ErrorAutenticacion),
])
def test_subida_errores_definitivos(video, error, tipo):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None)
    with pytest.raises(tipo):
        youtube.subir(cfg, video, youtube.cuerpo(cfg, "t", "d", [], "private"), yt=_yt([error()], {}), dormir=lambda s: None)


def test_subida_agota_reintentos(video):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None)
    with pytest.raises(ErrorTransitorio):
        youtube.subir(cfg, video, youtube.cuerpo(cfg, "t", "d", [], "private"),
                      yt=_yt([_http_error(500)] * 3, {}), intentos=3, dormir=lambda s: None)


def test_refresh_token_revocado(monkeypatch):
    pytest.importorskip("google.oauth2")
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials

    from shortsfactory.publisher import auth

    def revocado(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr(Credentials, "refresh", revocado)
    secreto = json.dumps({"installed": {"client_id": "c", "client_secret": "s", "token_uri": "https://oauth2.googleapis.com/token"}})
    cfg = Settings(_env_file=None, youtube_client_secret=secreto, youtube_refresh_token="r")
    with pytest.raises(ErrorAutenticacion, match="shortsfactory auth"):
        auth.credenciales(cfg)
