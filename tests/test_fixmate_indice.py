"""El indice: que encuentre, que descarte y que sobreviva al viaje a disco.

La busqueda es hibrida a proposito, y las dos mitades se prueban por separado:
el BM25 tiene que encontrar un numero de parte exacto y el vector tiene que
encontrar una falla descrita con otras palabras. Si una de las dos deja de
aportar, estas pruebas lo dicen antes que el tecnico.
"""

import json

import pytest

from nefer.fixmate import embeddings
from nefer.fixmate.almacen_pg import literal_vector, sql_busqueda
from nefer.fixmate.indice import ErrorIndice, Fragmento, Indice


def _indice() -> Indice:
    indice = Indice()
    indice.agregar([
        Fragmento(id="a", texto="Filtro de aire colmatado por polvo de mina; humo "
                                "negro al tomar carga. Repuesto P533781.",
                  tipo="informe", fuente="historial.json",
                  metadatos={"codigo_ot": "OT-1", "codigos_dtc": ["P0300"],
                             "codigo_equipo": "GE074-01"}),
        Fragmento(id="b", texto="Fuga de aceite hidraulico en el cilindro del brazo "
                                "por sello de vastago cortado.",
                  tipo="informe", fuente="historial.json",
                  metadatos={"codigo_ot": "OT-2", "codigos_dtc": [],
                             "codigo_equipo": "EX336-03"}),
        Fragmento(id="c", texto="Electrolito de baterias por debajo de 1.220 de "
                                "densidad; bornes sulfatados.",
                  tipo="manual", fuente="manual.md",
                  metadatos={"seccion": "Sistema electrico"}),
    ])
    return indice


def test_encuentra_el_antecedente_por_la_descripcion_de_la_falla():
    resultados = _indice().buscar("humo negro al tomar carga", limite=1)
    assert resultados[0].fragmento.id == "a"


def test_el_numero_de_parte_exacto_lo_encuentra_el_lexico():
    resultados = _indice().buscar("P533781", limite=1)
    assert resultados[0].fragmento.id == "a"
    assert resultados[0].lexico > 0, "un numero de parte se encuentra por texto exacto"


def test_el_vector_empareja_lo_que_se_dice_distinto():
    # 'fugas hidraulicas' no comparte ninguna palabra exacta con el fragmento
    # ('fuga', 'hidraulico'), asi que aqui el que trabaja es el vector.
    resultados = _indice().buscar("fugas hidraulicas en cilindros", limite=1)
    assert resultados[0].fragmento.id == "b"
    assert resultados[0].similitud > 0


def test_el_filtro_por_codigo_de_falla_descarta_lo_demas():
    resultados = _indice().buscar("problema en el equipo", limite=5,
                                  filtros={"codigos_dtc": "P0300"})
    assert [r.fragmento.id for r in resultados] == ["a"]


def test_un_filtro_sin_coincidencias_no_devuelve_nada():
    assert _indice().buscar("humo negro", filtros={"codigos_dtc": "U1234"}) == []


def test_las_preferencias_empujan_pero_no_descartan():
    indice = _indice()
    sin = indice.buscar("revision general del equipo", limite=3)
    con = indice.buscar("revision general del equipo", limite=3,
                        preferencias={"codigo_equipo": "EX336-03"})
    assert {r.fragmento.id for r in sin} == {r.fragmento.id for r in con}
    assert con[0].fragmento.id == "b", "el equipo preferido tiene que subir"
    # El manual no declara equipo y aun asi sigue estando: descartarlo dejaria
    # al tecnico sin el procedimiento.
    assert "c" in {r.fragmento.id for r in con}


def test_el_umbral_deja_fuera_lo_que_no_se_parece():
    assert _indice().buscar("kilometraje del camion de rampa", umbral=0.9) == []


def test_mismo_indice_mismo_orden():
    uno = [r.fragmento.id for r in _indice().buscar("aceite", limite=3)]
    otro = [r.fragmento.id for r in _indice().buscar("aceite", limite=3)]
    assert uno == otro


def test_indexar_dos_veces_lo_mismo_no_duplica_el_antecedente():
    indice = _indice()
    repetido = Fragmento(id="a", texto="Filtro de aire colmatado, version corregida.",
                         tipo="informe", metadatos={"codigo_ot": "OT-1"})
    agregados = indice.agregar([repetido])

    assert agregados == 0 and len(indice) == 3
    assert indice.buscar("filtro de aire", limite=2)[0].fragmento.texto.endswith(
        "version corregida.")


def test_ida_y_vuelta_a_disco(tmp_path):
    original = _indice()
    ruta = original.guardar(tmp_path / "indice.json")
    recuperado = Indice.cargar(ruta)

    assert len(recuperado) == len(original)
    esperado = [r.fragmento.id for r in original.buscar("humo negro", limite=3)]
    assert [r.fragmento.id for r in recuperado.buscar("humo negro", limite=3)] == esperado


def test_buscar_con_otro_embebedor_es_un_error_y_no_un_resultado_raro(tmp_path):
    ruta = _indice().guardar(tmp_path / "indice.json")
    otro = embeddings.EmbebedorLocal(dimension=64)
    with pytest.raises(ErrorIndice, match="se indexo con"):
        Indice.cargar(ruta, embebedor=otro)


def test_un_indice_de_otra_version_no_se_lee_a_medias(tmp_path):
    ruta = tmp_path / "viejo.json"
    ruta.write_text(json.dumps({"version": 0, "fragmentos": []}), encoding="utf-8")
    with pytest.raises(ErrorIndice, match="formato"):
        Indice.cargar(ruta)


def test_indice_inexistente_dice_como_construirlo(tmp_path):
    with pytest.raises(ErrorIndice, match="nefer fixmate indexar"):
        Indice.cargar(tmp_path / "no-esta.json")


# --------------------------------------------------------------- pgvector

def test_el_vector_va_a_postgres_con_la_sintaxis_de_pgvector():
    assert literal_vector([0.5, -0.25]) == "[0.500000,-0.250000]"


def test_los_filtros_viajan_como_parametros_y_no_pegados_al_sql():
    sql, parametros = sql_busqueda({"codigos_dtc": "P0300'; DROP TABLE x;--"})
    assert "DROP TABLE" not in sql
    assert "P0300'; DROP TABLE x;--" in parametros
    assert sql.count("%s") == len(parametros) + 3   # vector, vector y limite


def test_sin_filtros_no_hay_clausula_where():
    sql, parametros = sql_busqueda(None)
    assert "WHERE" not in sql and parametros == []


# ------------------------------------------- reindexar solo lo que cambio

def _carpeta(tmp_path):
    (tmp_path / "manual.md").write_text(
        "# Admision\n\nEl indicador de restriccion se lee sin carga.\n",
        encoding="utf-8")
    (tmp_path / "historial.json").write_text(json.dumps({"informes": [
        {"codigo_ot": "OT-1", "resumen_falla": "humo negro al tomar carga",
         "causa_raiz": "Filtro de aire colmatado",
         "solucion_aplicada": "Cambio de filtro"}]}), encoding="utf-8")
    return tmp_path


def test_la_firma_mira_el_contenido_y_no_la_fecha(tmp_path):
    from nefer.fixmate.indice import firma_de

    uno = tmp_path / "a.md"
    uno.write_text("mismo texto", encoding="utf-8")
    otro = tmp_path / "b.md"
    otro.write_text("mismo texto", encoding="utf-8")
    # Copiar la carpeta compartida cambia todas las fechas y ninguna coma.
    assert firma_de(uno) == firma_de(otro)

    uno.write_text("texto cambiado", encoding="utf-8")
    assert firma_de(uno) != firma_de(otro)


def test_lo_que_no_cambio_no_se_vuelve_a_leer(tmp_path):
    from nefer.fixmate import actualizar, indexar

    carpeta = _carpeta(tmp_path)
    indice = indexar([carpeta])
    antes = len(indice)

    parte = actualizar(indice, [carpeta])
    assert parte.iguales and not parte.hubo_cambios
    assert len(indice) == antes


def test_un_archivo_editado_se_reindexa_entero_y_solo_el(tmp_path):
    from nefer.fixmate import actualizar, indexar

    carpeta = _carpeta(tmp_path)
    indice = indexar([carpeta])
    (carpeta / "manual.md").write_text(
        "# Admision\n\nEl indicador se lee sin carga.\n\n"
        "# Inyeccion\n\nPrisionero a 30 N·m.\n", encoding="utf-8")

    parte = actualizar(indice, [carpeta])
    assert parte.cambiados == [str(carpeta / "manual.md")]
    assert len(parte.iguales) == 1
    secciones = {f.metadatos.get("seccion") for f in indice.fragmentos}
    assert "Inyeccion" in secciones


def test_un_manual_retirado_deja_de_responder(tmp_path):
    from nefer.fixmate import actualizar, indexar

    carpeta = _carpeta(tmp_path)
    indice = indexar([carpeta])
    (carpeta / "manual.md").unlink()

    parte = actualizar(indice, [carpeta])
    assert parte.eliminados == [str(carpeta / "manual.md")]
    assert all(f.tipo != "manual" for f in indice.fragmentos)


def test_indexar_una_carpeta_no_borra_lo_que_esta_fuera_de_ella(tmp_path):
    from nefer.fixmate import actualizar, indexar

    carpeta = tmp_path / "taller"
    carpeta.mkdir()
    _carpeta(carpeta)
    aparte = tmp_path / "otra"
    aparte.mkdir()
    (aparte / "otro.md").write_text("# Otro\n\nTexto del otro manual.\n",
                                    encoding="utf-8")
    indice = indexar([carpeta, aparte])
    (aparte / "otro.md").unlink()

    # Se reindexa solo la primera carpeta: lo de la otra sigue en pie.
    parte = actualizar(indice, [carpeta])
    assert parte.eliminados == []
    assert any(f.metadatos.get("seccion") == "Otro" for f in indice.fragmentos)


def test_las_fuentes_viajan_con_el_indice_a_disco(tmp_path):
    from nefer.fixmate import actualizar, indexar

    carpeta = _carpeta(tmp_path)
    indice = indexar([carpeta])
    ruta = indice.guardar(tmp_path / "indice.json")

    recuperado = Indice.cargar(ruta)
    assert recuperado.fuentes == indice.fuentes
    # Y por eso, recien cargado, no vuelve a leer nada.
    assert not actualizar(recuperado, [carpeta]).hubo_cambios


def test_el_indice_no_se_indexa_a_si_mismo(tmp_path):
    # El indice se guarda casi siempre dentro de la carpeta que indexa.
    from nefer.fixmate import actualizar, indexar

    carpeta = _carpeta(tmp_path)
    indice = indexar([carpeta])
    indice.guardar(carpeta / "indice.json")

    parte = actualizar(indice, [carpeta])
    assert not parte.hubo_cambios
    assert all("indice.json" not in o for o in indice.fuentes)


def test_apuntar_al_indice_en_vez_de_a_los_documentos_lo_dice(tmp_path):
    from nefer.fixmate import indexar
    from nefer.fixmate.ingesta import ErrorIngesta

    indice = indexar([_carpeta(tmp_path)])
    ruta = indice.guardar(tmp_path / "guardado" / "indice.json")
    with pytest.raises(ErrorIngesta, match="es un indice de FixMate"):
        indexar([ruta])


def test_se_puede_filtrar_con_una_regla_escrita_en_python():
    indice = _indice()
    solo_manual = indice.buscar("aceite", limite=5,
                                acepta=lambda f: f.tipo == "manual")
    assert [c.fragmento.id for c in solo_manual] == ["c"]


# ----------------------- el mismo vector, en Python y en el telefono

def test_el_hash_es_el_mismo_numero_en_cualquier_lenguaje():
    """Valores fijos de FNV-1a: el puerto a JavaScript tiene que dar esto.

    No es una prueba de regresion cualquiera. El indice se calcula aquí y la
    consulta se escribe en el telefono: si el navegador saca otro numero, el
    vector de la consulta no casa con ninguno y la busqueda devuelve ruido
    sin avisar. Estos valores son el contrato entre las dos mitades.

    En JavaScript:
        let h = 0xcbf29ce484222325n;
        for (const b of new TextEncoder().encode(s))
            h = BigInt.asUintN(64, (h ^ BigInt(b)) * 0x100000001b3n);
    """
    from nefer.fixmate.embeddings import fnv1a

    assert fnv1a(b"") == 0xCBF29CE484222325
    assert fnv1a(b"a") == 0xAF63DC4C8601EC8C          # vector de prueba de FNV
    assert fnv1a(b"foobar") == 0x85944171F73967E8     # idem
    assert fnv1a(b"fixmate:motor") == 0xC7063C56A41F90C2
    # Con tildes: los bytes son UTF-8, no latin-1. El navegador codifica
    # igual con TextEncoder, y de eso depende que 'hidráulico' case.
    assert fnv1a("fixmate:hidráulico".encode("utf-8")) == 0x25825C47648B5F22


def test_donde_cae_cada_rasgo_del_vector_esta_fijado():
    embebedor = embeddings.EmbebedorLocal()
    assert embebedor._posicion("motor") == (194, 1.0)
    assert embebedor._posicion("^inye") == (124, -1.0)


def test_el_vector_de_una_frase_conocida_no_se_mueve():
    # Si esto cambia, todos los indices del mundo quedan invalidados: la
    # prueba esta para que el cambio sea una decision y no un descuido.
    vector = embeddings.EmbebedorLocal().embeber(["humo negro al tomar carga"])[0]
    assert len(vector) == 256
    assert round(sum(vector), 6) == 0.725322
    assert round(max(vector), 6) == 0.455432
    assert round(min(vector), 6) == -0.455432


def test_un_indice_del_embebedor_viejo_pide_reindexar(tmp_path):
    # Antes de FNV-1a el embebedor se llamaba 'local-hash-256'. Un indice de
    # entonces trae vectores de otra cuenta: buscarlos con los de ahora no
    # falla, devuelve ruido. Por eso se rechaza.
    ruta = tmp_path / "viejo.json"
    ruta.write_text(json.dumps({
        "version": 1, "embebedor": "local-hash-256", "dimension": 256,
        "fragmentos": [{"id": "a", "texto": "humo negro", "vector": [0.1] * 256}],
    }), encoding="utf-8")
    with pytest.raises(ErrorIndice, match="Vuelva a indexar|vuelva a reindexar|se indexo con"):
        Indice.cargar(ruta)


def test_buscar_mientras_se_reindexa_no_revienta():
    """La API atiende una búsqueda y un cierre a la vez.

    Con las cuentas del BM25 cambiándose una lista a la vez, la búsqueda leía
    una nueva contra otra vieja y saltaba con IndexError: un 500 en la cara
    del técnico por haber preguntado en el momento equivocado.
    """
    import threading

    indice = _indice()
    fallos = []
    parar = threading.Event()

    def buscando():
        while not parar.is_set():
            try:
                indice.buscar("aceite hidraulico en el cilindro", limite=3)
            except Exception as exc:          # noqa: BLE001 - es lo que se mide
                fallos.append(exc)
                return

    hilo = threading.Thread(target=buscando)
    hilo.start()
    try:
        for n in range(60):
            indice.agregar([Fragmento(
                id=f"nuevo-{n}", texto=f"informe {n} de fuga de aceite",
                tipo="informe", metadatos={"codigo_ot": f"OT-{n}"})])
    finally:
        parar.set()
        hilo.join(timeout=10)

    assert not fallos, f"la búsqueda se rompió al reindexar: {fallos[0]!r}"
