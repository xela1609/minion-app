"""
Google Calendar SIN Google Cloud.

La app habla con un pequeño script de Google Apps Script (gratis, vive en tu propia cuenta de Google;
el código está en google_script.gs y los pasos en GUIA_GOOGLE.md).

- Leer:     eventos de uno o varios calendarios (propios o compartidos), con sus colores.
- Escribir: fechas especiales (todo el día, cada año) y eventos normales, con el color y el
            calendario que elijas.
- Borrar:   solo los eventos que creó la propia app.
"""
import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request

from datetime import date

import config


class ErrorCalendario(Exception):
    pass


# Colores de evento de Google Calendar: id -> (nombre, color). El id "" es el del calendario.
COLORES_EVENTO = {
    "":   ("Del calendario", None),
    "1":  ("Lavanda", "#a4bdfc"),
    "2":  ("Salvia", "#7ae7bf"),
    "3":  ("Uva", "#dbadff"),
    "4":  ("Flamenco", "#ff887c"),
    "5":  ("Plátano", "#fbd75b"),
    "6":  ("Mandarina", "#ffb878"),
    "7":  ("Pavo real", "#46d6db"),
    "8":  ("Grafito", "#e1e1e1"),
    "9":  ("Arándano", "#5484ed"),
    "10": ("Albahaca", "#51b749"),
    "11": ("Tomate", "#dc2127"),
}
COLOR_POR_DEFECTO = "#1E88E5"


def configurado():
    return bool(config.GOOGLE_SCRIPT_URL.strip() and config.GOOGLE_SCRIPT_CLAVE.strip())


# ---------------------------------------------------------------------
# Utilidades (sin red, fáciles de probar)
# ---------------------------------------------------------------------
def clave_fecha(fecha):
    """Identifica una fecha de la app para saber si ya está subida al calendario."""
    return f"{fecha['nombre']}|{fecha['dia']}|{fecha['mes']}"


def parametros_crear(datos, mensaje=""):
    """Parámetros que se envían al script para crear un evento.

    datos: dict con nombre, dia, mes y, si se quiere, anio, tipo ("especial"/"normal"),
           repetir (bool), hora ("HH:MM"), color ("1".."11") y calendario (id).
    Si no se indica nada más, es una fecha especial de todo el día que se repite cada año.
    """
    normal = datos.get("tipo") == "normal"
    parametros = {
        "accion": "crear",
        "nombre": datos["nombre"],
        "dia": datos["dia"],
        "mes": datos["mes"],
        "mensaje": (mensaje or "")[:400],   # la petición va en la dirección, mejor corta
        "tipo": "normal" if normal else "especial",
        "repetir": "1" if datos.get("repetir", not normal) else "0",
    }
    if datos.get("anio"):
        parametros["anio"] = datos["anio"]
    if normal and datos.get("hora"):
        parametros["hora"] = datos["hora"]
    if datos.get("color"):
        parametros["color"] = str(datos["color"])
    if datos.get("calendario"):
        parametros["calendario"] = datos["calendario"]
    minutos = list(getattr(config, "GOOGLE_RECORDATORIOS_MINUTOS", []))
    if minutos:
        parametros["recordatorio"] = int(minutos[0])
    return parametros


def evento_desde_script(item):
    """Convierte un evento del script en un diccionario sencillo (o None si no sirve)."""
    try:
        fecha = date.fromisoformat(str(item.get("fecha", "")))
    except ValueError:
        return None
    hora = item.get("hora") or None
    de_la_app = bool(item.get("deLaApp"))
    return {
        "id": item.get("id", ""),
        "titulo": item.get("titulo") or "(sin título)",
        "fecha": fecha,
        "hora": hora,
        "todo_el_dia": bool(item.get("todoDia")) or hora is None,
        "de_la_app": de_la_app,
        # un script antiguo no dice si es especial: se supone que lo es si lo creó la app
        "especial": bool(item["especial"]) if "especial" in item else de_la_app,
        "color": item.get("color") or COLOR_POR_DEFECTO,
        "calendario_id": item.get("calendarioId", ""),
        "calendario": item.get("calendario", ""),
    }


def calendario_desde_script(item):
    """Convierte un calendario del script en un diccionario sencillo."""
    return {
        "id": item.get("id", ""),
        "nombre": item.get("nombre") or item.get("id", ""),
        "color": item.get("color") or COLOR_POR_DEFECTO,
        "propio": bool(item.get("propio")),
        "seleccionado": bool(item.get("seleccionado")),
        "principal": bool(item.get("principal")),
    }


# ---------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------
def _llamar(parametros):
    base = config.GOOGLE_SCRIPT_URL.strip()
    datos = dict(parametros)
    datos["clave"] = config.GOOGLE_SCRIPT_CLAVE.strip()
    url = base + ("&" if "?" in base else "?") + urllib.parse.urlencode(datos)
    try:
        with urllib.request.urlopen(url, timeout=30) as respuesta:
            texto = respuesta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise ErrorCalendario(
            f"El script respondió {e.code}. Revisa la dirección y que esté desplegado "
            "con acceso «Cualquier persona».") from e
    except urllib.error.URLError as e:
        raise ErrorCalendario("No hay conexión con Google.") from e
    try:
        respuesta_json = json.loads(texto)
    except ValueError as e:
        raise ErrorCalendario(
            "La respuesta no viene del script. Revisa que la dirección termine en /exec y que el "
            "acceso sea «Cualquier persona».") from e
    if not respuesta_json.get("ok"):
        raise ErrorCalendario(respuesta_json.get("error") or "El script devolvió un error.")
    return respuesta_json


async def probar_conexion():
    await asyncio.to_thread(_llamar, {"accion": "ping"})


def _ordenar(respuesta):
    eventos = [evento_desde_script(i) for i in respuesta.get("eventos", [])]
    eventos = [e for e in eventos if e]
    eventos.sort(key=lambda e: (e["fecha"], e["hora"] or ""))
    return eventos


def _con_calendarios(parametros, calendarios):
    if calendarios:
        parametros["cals"] = ",".join(calendarios)
    return parametros


async def listar_calendarios():
    """Calendarios de la cuenta (propios y compartidos). Con un script antiguo da error."""
    respuesta = await asyncio.to_thread(_llamar, {"accion": "calendarios"})
    return [calendario_desde_script(i) for i in respuesta.get("calendarios", [])]


async def listar_eventos(dias, calendarios=None, maximo=60):
    """Próximos eventos de los calendarios indicados (vacío = el principal), por fecha y hora."""
    respuesta = await asyncio.to_thread(
        _llamar, _con_calendarios({"accion": "listar", "dias": int(dias)}, calendarios))
    return _ordenar(respuesta)[:maximo]


async def listar_rango(desde, hasta, calendarios=None):
    """Eventos entre dos fechas (incluidas), por ejemplo un mes entero. Admite el pasado."""
    respuesta = await asyncio.to_thread(
        _llamar, _con_calendarios(
            {"accion": "listar", "desde": desde.isoformat(), "hasta": hasta.isoformat()},
            calendarios))
    return _ordenar(respuesta)


async def crear_evento(datos, texto_mensaje=""):
    """Crea un evento (ver parametros_crear). Devuelve el id del evento."""
    respuesta = await asyncio.to_thread(_llamar, parametros_crear(datos, texto_mensaje))
    return respuesta.get("id", "")


async def crear_evento_anual(fecha, texto_mensaje=""):
    """Crea la fecha como evento anual de todo el día. Devuelve el id del evento."""
    return await crear_evento(fecha, texto_mensaje)


async def borrar_evento(id_evento, calendario=""):
    parametros = {"accion": "borrar", "id": id_evento}
    if calendario:
        parametros["calendario"] = calendario
    await asyncio.to_thread(_llamar, parametros)
