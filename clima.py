"""
Tiempo meteorológico con Open-Meteo (gratis, sin clave).
Se hace la petición en un hilo aparte para no bloquear la app.
"""
import asyncio
import json
import random
import urllib.parse
import urllib.request

import config

URL = "https://api.open-meteo.com/v1/forecast"

CATEGORIAS = ("despejado", "parcial", "nublado", "niebla", "lluvia", "nieve", "tormenta")


def categoria_desde_codigo(codigo):
    """Convierte el código meteorológico (WMO) en una de nuestras categorías."""
    if codigo == 0:
        return "despejado"
    if codigo in (1, 2):
        return "parcial"
    if codigo == 3:
        return "nublado"
    if codigo in (45, 48):
        return "niebla"
    if codigo in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "lluvia"
    if codigo in (71, 73, 75, 77, 85, 86):
        return "nieve"
    if codigo in (95, 96, 99):
        return "tormenta"
    return "nublado"


def _num(valor, defecto=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def interpretar(datos):
    """Del JSON de Open-Meteo saca lo que necesita la app."""
    actual = datos["current"]
    diario = datos["daily"]
    temp = _num(actual.get("temperature_2m"))
    return {
        "categoria": categoria_desde_codigo(int(_num(actual.get("weather_code"), 3))),
        "temp": temp,
        "tmax": _num(diario["temperature_2m_max"][0], temp),
        "tmin": _num(diario["temperature_2m_min"][0], temp),
        "prob": int(_num(diario["precipitation_probability_max"][0])),
        "es_dia": bool(actual.get("is_day", 1)),
    }


def _pedir(lat, lon):
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 1,
    }
    url = URL + "?" + urllib.parse.urlencode(parametros)
    peticion = urllib.request.Request(url, headers={"User-Agent": "MiMinion/1.0"})
    with urllib.request.urlopen(peticion, timeout=12) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


async def obtener_clima():
    """Devuelve el tiempo actual o None si algo falla (sin internet, etc.)."""
    if config.CLIMA_FORZADO:
        return datos_prueba(config.CLIMA_FORZADO)
    # A veces el servicio gratuito tarda o falla puntualmente: se reintenta unas veces.
    for intento in range(3):
        try:
            crudo = await asyncio.to_thread(_pedir, config.LATITUD, config.LONGITUD)
            return interpretar(crudo)
        except Exception:
            if intento < 2:
                await asyncio.sleep(2 * (intento + 1))
    return None


def datos_prueba(categoria):
    return {
        "categoria": categoria,
        "temp": 18.0,
        "tmax": 22.0,
        "tmin": 11.0,
        "prob": 60 if categoria in ("lluvia", "tormenta") else 10,
        "es_dia": True,
    }


def frase_tiempo(datos, ella):
    """Frase del Minion para el primer saludo del día."""
    plantillas = config.FRASES_CLIMA.get(datos["categoria"]) or config.FRASES_CLIMA["nublado"]
    valores = dict(
        ella=ella,
        temp=round(datos["temp"]),
        tmax=round(datos["tmax"]),
        tmin=round(datos["tmin"]),
        prob=datos["prob"],
    )
    plantilla = random.choice(plantillas)
    texto = plantilla.format(**valores)
    # Siempre dice también la mínima (si la frase elegida ya la nombra, no se repite)
    frase_minima = getattr(config, "FRASE_MINIMA", " Y la mínima será de {tmin}°.")
    if frase_minima and "{tmin}" not in plantilla:
        texto += frase_minima.format(**valores)
    if datos["tmax"] >= config.UMBRAL_CALOR:
        texto += config.FRASE_CALOR
    elif datos["tmin"] <= config.UMBRAL_FRIO and datos["categoria"] != "nieve":
        texto += config.FRASE_FRIO
    if datos["prob"] >= 50 and datos["categoria"] not in ("lluvia", "tormenta", "nieve"):
        texto += config.FRASE_PROBABLE_LLUVIA.format(**valores)
    return texto
