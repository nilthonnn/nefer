"""Redaccion automatica: rotulos, leyendas de recuperacion y guias impresas."""

from __future__ import annotations

import re

LEYENDA_ESTADO = {
    "OK": "Funcional",
    "OBS": "Observado",
    "D": "Dañado",
}

# Consumibles que se controlan por familia de equipo movil.
CONTROL_BASE = {
    "plataforma_elevacion": [
        ("Nivel de carga de baterías", "%"),
        ("Aceite hidráulico", "%"),
        ("Electrolito de baterías", "OK/OBS"),
        ("Estado de llantas", "OK/OBS"),
    ],
    "maquinaria_amarilla": [
        ("Combustible diésel", "%"),
        ("Aceite de motor", "%"),
        ("Refrigerante", "%"),
        ("Aceite hidráulico", "%"),
        ("Filtros (aire / combustible)", "OK/OBS"),
        ("Tren de rodaje / llantas", "OK/OBS"),
    ],
    "torre_iluminacion": [
        ("Combustible diésel", "%"),
        ("Aceite de motor", "%"),
        ("Refrigerante", "%"),
        ("Focos operativos", "und"),
        ("Estado de baterías", "OK/OBS"),
    ],
    "grupo_electrogeno": [
        ("Combustible diésel", "%"),
        ("Aceite de motor", "%"),
        ("Refrigerante", "%"),
        ("Estado de baterías", "OK/OBS"),
    ],
    "compresor": [
        ("Combustible diésel", "%"),
        ("Aceite de motor", "%"),
        ("Aceite de compresor", "%"),
        ("Refrigerante", "%"),
        ("Filtros (aire / combustible)", "OK/OBS"),
        ("Estado de baterías", "OK/OBS"),
    ],
    "generico": [
        ("Combustible", "%"),
        ("Aceite de motor", "%"),
        ("Refrigerante", "%"),
    ],
}


def control_consumibles_vacio(categoria: str) -> list[dict]:
    """Tabla de consumibles en blanco para que el operador la llene en campo."""
    base = CONTROL_BASE.get(categoria, CONTROL_BASE["generico"])
    return [{"consumible": nombre, "unidad": unidad,
             "despacho": None, "recepcion": None, "consumo": None,
             "estado": "", "observacion": ""}
            for nombre, unidad in base]


SUFIJO_ESTADO = {"D": " DAÑADO(A)", "OBS": " OBSERVADO(A)"}


def reparto_consumible(cons: dict) -> tuple[int, int]:
    """Cuantas unidades volvieron y cuantas faltan.

    `cantidad_retorna` es opcional: un acta que no lo declara se lee como
    siempre —o vuelve todo, o no vuelve nada— y da el mismo resultado que
    antes de que existiera el campo.
    """
    cantidad = max(1, int(cons.get("cantidad", 1) or 1))
    if cons.get("cantidad_retorna") is None:
        retorna = 0 if cons.get("estado_recepcion") == "NO_RETORNA" else cantidad
    else:
        retorna = int(cons["cantidad_retorna"])
    retorna = max(0, min(cantidad, retorna))
    return retorna, cantidad - retorna


def texto_consumible(cons: dict, lado: str, tipo_documento: str = "RECEPCION") -> str:
    """Rotulo del bloque fotografico de un consumible/accesorio.

    En un acta de DESPACHO el lado de recepcion va en blanco: el equipo aun no
    ha vuelto, y afirmar lo contrario en un documento que el cliente firma
    seria declarar un hecho que no ocurrio.
    """
    cantidad = cons.get("cantidad", 1)
    descripcion = cons.get("descripcion", "").strip()
    if lado == "DESPACHO":
        return f"{cantidad:02d} {descripcion} DESPACHADO"
    if tipo_documento == "DESPACHO":
        return ""

    estado = cons.get("estado_recepcion")
    # Sin estado y sin retorno parcial declarado, nadie ha dicho todavia si el
    # equipo volvio con esto o sin esto. La celda va en blanco: la observacion
    # y su fotografia se imprimen igual, y el hecho lo declara quien firma.
    if estado is None and cons.get("cantidad_retorna") is None:
        return ""
    retorna, falta = reparto_consumible(cons)
    # Retorno parcial: la celda dice cuantas de cuantas volvieron. Decir solo
    # "retorno sin" o solo "retorno con" seria falso en los dos sentidos.
    if falta and retorna:
        return (f"EL EQUIPO RETORNÓ CON {retorna:02d} DE {cantidad:02d} "
                f"{descripcion}{SUFIJO_ESTADO.get(estado, '')}")
    if estado == "NO_RETORNA":
        return f"EL EQUIPO RETORNÓ SIN {cantidad:02d} {descripcion}"
    return (f"EL EQUIPO RETORNÓ CON {cantidad:02d} {descripcion}"
            f"{SUFIJO_ESTADO.get(estado, '')}")


def cierres_consumible(cons: dict, tipo_documento: str = "RECEPCION") -> list[dict]:
    """Franjas de cierre del bloque: una por cada hecho que hay que declarar.

    Un accesorio que vuelve entero cierra con una sola franja. Uno que vuelve
    en parte cierra con dos —lo que falta y lo que volvio— porque son dos
    hechos distintos: uno se cobra y el otro se da por conforme. Es el caso
    que en el formato llenado a mano acababa como dos lineas seguidas de
    RECUPERACION bajo el mismo bloque.
    """
    if tipo_documento == "DESPACHO":
        return []
    # Sin estado declarado no hay nada que cerrar: una franja CONFORME diria
    # que se da por bueno lo que nadie ha revisado, y una RECUPERACION cobraria
    # lo que nadie ha declarado perdido. Un texto escrito a mano si es una
    # declaracion, y entonces la franja va con lo que diga ese texto.
    if (cons.get("estado_recepcion") is None
            and cons.get("cantidad_retorna") is None
            and not any(t.strip() for t in _leyendas_manuales(cons))):
        return []
    retorna, falta = reparto_consumible(cons)
    danado = cons.get("estado_recepcion") in {"D", "OBS"}
    cierres = []
    if falta:
        cierres.append({"recupera": True, "cantidad": falta})
    if retorna:
        cierres.append({"recupera": danado, "cantidad": retorna})
    return cierres


def _leyendas_manuales(cons: dict) -> list[str]:
    manual = cons.get("recuperaciones")
    if manual is None and cons.get("recuperacion"):
        manual = [cons["recuperacion"]]
    return [str(x) for x in (manual or [])]


def texto_cierre(cons: dict, cierre: dict, numero: int, indice: int = 0) -> str:
    """Leyenda de una franja de cierre. La escrita a mano manda sobre la auto."""
    manual = _leyendas_manuales(cons)
    if indice < len(manual) and manual[indice].strip():
        return manual[indice]
    cantidad = cierre["cantidad"]
    descripcion = cons.get("descripcion", "").strip()
    # El numero es el ordinal dentro de su propia serie, no el del bloque: si
    # el primer accesorio vuelve conforme, el segundo que falte es la
    # RECUPERACION N° 1. Lo lleva quien llama.
    if cierre["recupera"]:
        return f"RECUPERACIÓN N° {numero} : {cantidad:02d} {descripcion}"
    return f"CONFORME N° {numero} : {cantidad:02d} {descripcion} — SIN RECUPERACIÓN"


def texto_recuperacion(cons: dict, numero: int,
                       tipo_documento: str = "RECEPCION") -> str:
    """Leyenda amarilla de la primera franja de cierre del bloque."""
    cierres = cierres_consumible(cons, tipo_documento)
    if not cierres:
        return ""
    return texto_cierre(cons, cierres[0], numero, 0)


def _enc(manifiesto: dict) -> dict:
    return manifiesto.get("encabezado", {})


def _subtitulo(partes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Linea de identificacion del acta; se omite si no hay datos que mostrar."""
    llenas = [f"{etiqueta}: {valor}" for etiqueta, valor in partes if str(valor).strip()]
    return [("s", "   |   ".join(llenas))] if llenas else []


def _organizacion(enc: dict) -> str:
    """Como nombrar a la empresa dentro del texto de las guias."""
    return (enc.get("empresa") or "").strip() or "la empresa"


def _normalizar(lineas: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Evita el punto doble cuando la razon social ya termina en punto (S.A.C.)."""
    return [(nivel, re.sub(r"\.\.$", ".", texto)) for nivel, texto in lineas]


def guia_operador(manifiesto: dict) -> list[tuple[str, str]]:
    """Guia interna del operador para el acto de despacho/recepcion."""
    enc = _enc(manifiesto)
    tipo = enc.get("tipo_documento", "DESPACHO")
    org = _organizacion(enc)
    return _normalizar([
        ("t", "GUÍA DEL OPERADOR — DESPACHO Y RECEPCIÓN DE EQUIPOS"),
        *_subtitulo([("Documento", tipo if enc else ""),
                     ("Equipo", enc.get("codigo_equipo", "")),
                     ("Cliente", (enc.get("cliente") or "").strip())]),
        ("p", ""),
        ("s", "1. ANTES DE MOVILIZAR EL EQUIPO"),
        ("p", "1.1 Verificar que el N° de acta y el N° de guía de remisión coincidan con la "
              "orden de trabajo. Sin guía no sale el equipo del patio."),
        ("p", "1.2 Leer el horómetro con el equipo apagado y fotografiarlo de frente, sin "
              "reflejos. El valor de la foto es el que se transcribe al acta; si la lectura "
              "no es legible se escribe REVISIÓN MANUAL REQUERIDA y se levanta en patio."),
        ("p", "1.3 Registrar los consumibles y accesorios que salen con el equipo (extintor, "
              "conos, barra puesta a tierra, bandejas, tacos). Cada uno lleva su propia foto "
              "en la sección OBSERVACIONES."),
        ("p", "1.4 Llenar la hoja CONSUMIBLES con los niveles de despacho antes de subir el "
              "equipo a la plataforma."),
        ("p", ""),
        ("s", "2. REGISTRO FOTOGRÁFICO OBLIGATORIO"),
        ("p", "2.1 Las tomas mínimas son: frontal, posterior, lateral izquierda, lateral "
              "derecha, horómetro y panel de control. Según la familia del equipo se agregan "
              "motor, baterías, mástil y focos, cucharón o piso de plataforma."),
        ("p", "2.2 Una toma por bloque, en horizontal, con el equipo completo dentro del "
              "encuadre y luz suficiente para distinguir rayones y fugas."),
        ("p", "2.3 Todo daño preexistente se fotografía en el despacho. Un daño que no está "
              "en el acta de despacho no es reclamable en la recepción."),
        ("p", ""),
        ("s", "3. EN LA RECEPCIÓN"),
        ("p", "3.1 Repetir exactamente las mismas tomas del despacho para poder comparar."),
        ("p", "3.2 Contrastar cada consumible y anotar cuántas unidades retornan. Si "
              "retornan todas se marca conforme; si no retorna ninguna o retornan dañadas se "
              "genera la línea amarilla de RECUPERACIÓN, que es la que sustenta el cobro al "
              "cliente."),
        ("p", "3.3 Si de dos salieron y vuelve una, se anota 1 en la cantidad que retorna: el "
              "bloque cierra con dos líneas, la RECUPERACIÓN de lo que falta y el CONFORME de "
              "lo que volvió. Contarlo como si no hubiera vuelto nada cobra de más."),
        ("p", "3.4 Cerrar la hoja CONSUMIBLES con los niveles de retorno; el consumo se "
              "calcula solo."),
        ("p", ""),
        ("s", "4. CIERRE"),
        ("p", f"4.1 El acta se firma en sitio por el operador de {org} y por el responsable "
              "del cliente. Sin firma del cliente el acta no cierra."),
        ("p", "4.2 El PDF se archiva el mismo día con el nombre "
              "CODIGO_TIPO_FECHA.pdf y se envía al cliente y a la jefatura de operaciones."),
        ("p", "4.3 Toda discrepancia sobre el horómetro o sobre un daño se escala a la "
              "jefatura de operaciones antes de retirar el equipo del sitio."),
    ])


def guia_cliente(manifiesto: dict) -> list[tuple[str, str]]:
    """Guia que se entrega al cliente junto con el acta."""
    enc = _enc(manifiesto)
    org = _organizacion(enc)
    return _normalizar([
        ("t", "GUÍA PARA EL CLIENTE — RECEPCIÓN Y DEVOLUCIÓN DEL EQUIPO ALQUILADO"),
        *_subtitulo([("Equipo", (enc.get("modelo_equipo") or "").strip()),
                     ("Código", enc.get("codigo_equipo", ""))]),
        ("p", ""),
        ("s", "1. QUÉ ESTÁ RECIBIENDO"),
        ("p", "Este documento es el estado fotográfico del equipo al momento de la entrega. "
              "Las fotos y el horómetro que aparecen aquí son la referencia contra la que se "
              "comparará el equipo cuando lo devuelva."),
        ("p", ""),
        ("s", "2. REVISE ANTES DE FIRMAR"),
        ("p", "2.1 Que el código del equipo y el horómetro coincidan con el equipo físico."),
        ("p", "2.2 Que los accesorios y consumibles listados en OBSERVACIONES estén "
              "efectivamente en el equipo (extintor, conos, barra de puesta a tierra, tacos, "
              "bandejas, según corresponda)."),
        ("p", "2.3 Que cualquier daño que usted observe y no aparezca fotografiado quede "
              "registrado antes de firmar. Una vez firmada el acta, el estado documentado "
              "es el aceptado por ambas partes."),
        ("p", ""),
        ("s", "3. DURANTE EL ALQUILER"),
        ("p", "3.1 El equipo debe ser operado únicamente por personal capacitado y "
              "autorizado, con los EPP que exige la actividad."),
        ("p", "3.2 Mantener los niveles de combustible, aceite y refrigerante según la hoja "
              "CONSUMIBLES adjunta. Cualquier alarma en el panel de control debe reportarse "
              f"de inmediato a {org}."),
        ("p", "3.3 No retirar, prestar ni sustituir los accesorios entregados con el equipo."),
        ("p", f"3.4 El mantenimiento correctivo lo ejecuta {org}. No se autorizan "
              "intervenciones de terceros sobre el equipo."),
        ("p", ""),
        ("s", "4. AL DEVOLVER EL EQUIPO"),
        ("p", "4.1 El equipo se devuelve limpio, con todos sus accesorios y con los niveles "
              "de fluidos declarados en el despacho."),
        ("p", "4.2 Se levanta un acta de recepción con las mismas tomas fotográficas. Los "
              "faltantes o daños se listan como RECUPERACIÓN en la franja amarilla y se "
              "facturan según el tarifario vigente."),
        ("p", "4.3 Las horas facturables se calculan por diferencia de horómetro entre el "
              "acta de despacho y la de recepción."),
        ("p", ""),
        ("s", "5. CONTACTO"),
        ("p", f"Ante cualquier duda sobre este documento, comuníquese con la jefatura de "
              f"operaciones de {org} indicando el N° de acta y el código del equipo."),
    ])
