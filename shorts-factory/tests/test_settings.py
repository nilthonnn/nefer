import pytest
from pydantic import ValidationError

from shortsfactory.errors import ErrorConfiguracion
from shortsfactory.settings import Settings


def test_valores_por_defecto():
    s = Settings(_env_file=None)
    assert s.llm_proveedor == "anthropic" and s.llm_modelo == "claude-opus-5-5"
    assert s.youtube_privacidad == "private"  # nunca público por defecto
    assert s.duracion_max == 15.0 and s.fps == 30


def test_lee_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("SF_FPS", "60")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secreta")
    s = Settings(_env_file=None)
    assert s.fps == 60
    assert "sk-secreta" not in repr(s) and "sk-secreta" not in s.model_dump_json()


@pytest.mark.parametrize("cambios", [{"fps": 25}, {"youtube_privacidad": "publico"}, {"youtube_categoria": "ciencia"},
                                     {"duracion_max": 3}, {"llm_proveedor": "openai"}])
def test_rechaza_valores_invalidos(cambios):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **cambios)


def test_exigir_nombra_la_variable():
    with pytest.raises(ErrorConfiguracion, match="YOUTUBE_REFRESH_TOKEN"):
        Settings(_env_file=None).exigir("youtube_refresh_token")
