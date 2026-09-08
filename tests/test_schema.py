from nefer import schema


def manifiesto_minimo(**cambios):
    base = {
        "encabezado": {
            "empresa": "Maquinarias del Sur S.A.C.",
            "tipo_documento": "DESPACHO",
            "cliente": "CLIENTE DEMO S.A.C.",
            "fecha": "2026-03-01",
            "horometro": 120.5,
            "codigo_equipo": "GE074-17",
            "modelo_equipo": "GRUPO ELECTRÓGENO 74 KW",
            "categoria": "grupo_electrogeno",
        },
        "registro_fotografico": [{"foto_id": 1, "descripcion": "VISTA FRONTAL"}],
        "resumen_ejecutivo": "Equipo operativo y completo, apto para despacho.",
    }
    base.update(cambios)
    return base


def test_manifiesto_minimo_valido():
    assert schema.validar(manifiesto_minimo()) == []


def test_tipo_de_documento_restringido():
    m = manifiesto_minimo()
    m["encabezado"]["tipo_documento"] = "ENTREGA"
    assert any("tipo_documento" in e for e in schema.validar(m))


def test_fecha_debe_ser_iso():
    m = manifiesto_minimo()
    m["encabezado"]["fecha"] = "01/03/2026"
    assert any("fecha" in e for e in schema.validar(m))


def test_horometro_ilegible_es_aceptable():
    m = manifiesto_minimo()
    m["encabezado"]["horometro"] = schema.REVISION_MANUAL
    assert schema.validar(m) == []


def test_horometro_texto_arbitrario_invalido():
    m = manifiesto_minimo()
    m["encabezado"]["horometro"] = "mas o menos 1200"
    assert any("horometro" in e for e in schema.validar(m))


def test_estado_observado_exige_observacion():
    m = manifiesto_minimo(inspeccion_componentes=[
        {"item": "Breaker principal", "estado": "OBS", "observacion": ""}])
    assert any("observacion" in e for e in schema.validar(m))


def test_resumen_limitado_a_veinte_palabras():
    m = manifiesto_minimo(resumen_ejecutivo=" ".join(["palabra"] * 21))
    assert any("resumen_ejecutivo" in e for e in schema.validar(m))


def test_foto_id_duplicado_detectado():
    m = manifiesto_minimo(registro_fotografico=[
        {"foto_id": 1, "descripcion": "VISTA FRONTAL"},
        {"foto_id": 1, "descripcion": "VISTA POSTERIOR"},
    ])
    assert any("duplicado" in e for e in schema.validar(m))


def test_celdas_destino_siguen_la_rejilla():
    m = manifiesto_minimo(registro_fotografico=[
        {"foto_id": 1, "descripcion": "VISTA FRONTAL"},
        {"foto_id": 2, "descripcion": "VISTA POSTERIOR"},
        {"foto_id": 3, "descripcion": "LATERAL IZQUIERDA"},
    ])
    assert schema.celdas_destino(m) == {1: "A11", 2: "M11", 3: "A26"}


def test_despacho_rechaza_datos_de_recepcion():
    """El equipo no ha vuelto: declarar su retorno es una contradicción."""
    m = manifiesto_minimo(consumibles=[
        {"descripcion": "EXTINTOR 6 KG", "estado_recepcion": "NO_RETORNA"}])
    m["encabezado"]["tipo_documento"] = "DESPACHO"
    errores = schema.validar(m)
    assert any("no puede declarar datos de recepcion" in e for e in errores)


def test_recepcion_acepta_los_mismos_datos():
    m = manifiesto_minimo(consumibles=[
        {"descripcion": "EXTINTOR 6 KG", "estado_recepcion": "NO_RETORNA"}])
    m["encabezado"]["tipo_documento"] = "RECEPCION"
    assert schema.validar(m) == []


def test_logo_inexistente_es_un_error(tmp_path):
    m = manifiesto_minimo()
    m["encabezado"]["logo"] = "marca/logo.png"
    assert any("logo" in e for e in schema.validar(m, tmp_path))
    # Sin raiz no se comprueba el disco: solo se valida el tipo.
    assert schema.validar(m) == []
