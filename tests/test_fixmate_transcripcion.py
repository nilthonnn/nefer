"""La consulta dictada. Lo que se prueba es lo que pasa antes y despues.

Antes: que al servicio se le pasen los codigos de la propia flota, porque sin
eso «ge cero setenta y cuatro» se transcribe como suene. Despues: que lo
transcrito se devuelva para que el tecnico lea que entendio la maquina.

La transcripcion en si la hace un servicio; aqui se inyecta uno falso. No se
prueba que OpenAI transcriba: se prueba que nefer le pregunte bien y se crea
lo justo de la respuesta.
"""

import pytest

from nefer.fixmate import transcripcion
from nefer.fixmate.indice import Fragmento, Indice


class ClienteFalso:
    """Imita `cliente.audio.transcriptions.create`."""

    def __init__(self, texto="humo negro y pierde fuerza", error=None):
        self.texto, self.error, self.visto = texto, error, {}
        self.audio = self

    @property
    def transcriptions(self):
        return self

    def create(self, **kw):
        self.visto.update(kw)
        if self.error:
            raise self.error
        return type("R", (), {"text": self.texto})()


def _indice() -> Indice:
    indice = Indice()
    indice.agregar([Fragmento(
        id="ot:1", tipo="informe", fuente="h.json", texto="humo negro",
        metadatos={"codigo_equipo": "GE074-01", "codigos_dtc": ["P0300"],
                   "modelo_equipo": "GRUPO ELECTROGENO 74 KW"})])
    return indice


def test_se_le_pasan_los_codigos_de_la_flota_al_transcriptor(tmp_path):
    cliente = ClienteFalso()
    audio = tmp_path / "nota.m4a"
    audio.write_bytes(b"audio de mentira")

    texto = transcripcion.TranscriptorOpenAI(cliente=cliente)(
        audio, pistas=transcripcion.pistas_de_indice(_indice()))

    assert texto == "humo negro y pierde fuerza"
    assert "GE074-01" in cliente.visto["prompt"]
    assert "P0300" in cliente.visto["prompt"]
    assert cliente.visto["language"] == "es"


def test_las_pistas_salen_del_propio_indice():
    pistas = transcripcion.pistas_de_indice(_indice())
    assert "GE074-01" in pistas and "GRUPO ELECTROGENO 74 KW" in pistas


def test_un_formato_que_no_es_audio_se_rechaza_antes_de_subirlo(tmp_path):
    ruta = tmp_path / "foto.jpg"
    ruta.write_bytes(b"no soy audio")
    with pytest.raises(transcripcion.ErrorTranscripcion, match="formato"):
        transcripcion.TranscriptorOpenAI(cliente=ClienteFalso())(ruta)


def test_un_audio_enorme_se_rechaza_antes_de_subirlo():
    grande = ("larga.m4a", b"0" * (transcripcion.TAMANO_MAXIMO + 1))
    with pytest.raises(transcripcion.ErrorTranscripcion, match="limite"):
        transcripcion.TranscriptorOpenAI(cliente=ClienteFalso())(grande)


def test_un_audio_vacio_no_se_manda():
    with pytest.raises(transcripcion.ErrorTranscripcion, match="vacio"):
        transcripcion.TranscriptorOpenAI(cliente=ClienteFalso())(("n.m4a", b""))


def test_una_transcripcion_vacia_no_se_convierte_en_consulta():
    # Buscar con una cadena vacia devolveria cualquier cosa como si fuera la
    # respuesta a lo que el tecnico dijo.
    cliente = ClienteFalso(texto="   ")
    with pytest.raises(transcripcion.ErrorTranscripcion, match="vacia"):
        transcripcion.TranscriptorOpenAI(cliente=cliente)(("n.m4a", b"x"))


def test_si_el_servicio_falla_se_dice_lo_que_paso():
    cliente = ClienteFalso(error=RuntimeError("503 desde el servicio"))
    with pytest.raises(transcripcion.ErrorTranscripcion, match="503"):
        transcripcion.TranscriptorOpenAI(cliente=cliente)(("n.m4a", b"x"))


def test_sin_clave_se_explica_el_camino_que_no_necesita_servicio(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(transcripcion.ErrorTranscripcion, match="dictado del teclado"):
        transcripcion.TranscriptorOpenAI()(("n.m4a", b"x"))


def test_un_transcriptor_que_no_existe_es_un_error():
    with pytest.raises(ValueError, match="desconocido"):
        transcripcion.obtener("magia")
