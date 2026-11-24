"""
Configuración personal del Minion.
Aquí cambias frases, fechas y la velocidad a la que se le baja la barra.
No hace falta tocar main.py para personalizar el regalo.
"""

# ------------------------------------------------------------------
# Datos básicos
# ------------------------------------------------------------------
NOMBRE_ELLA = "mi vida"          # TODO: cámbialo por como la llamas
NOMBRE_APP = "Mi Minion"
SALUDO = "¡Papoi!"

# ------------------------------------------------------------------
# Fechas especiales
#   dia, mes      -> obligatorios
#   anio          -> opcional; si lo pones, la app calcula "cumplís X años"
#   mensaje       -> opcional; sale en el bocadillo el propio día
# ------------------------------------------------------------------
FECHAS = [
    {
        "nombre": "Tu cumpleaños",
        "dia": 11,
        "mes": 1,
        "mensaje": "¡Feliz cumpleaños, {ella}! Te quiero muchísimo. ¡Papoi!",
    },
    # TODO: pon aquí vuestra fecha real (esta es solo un ejemplo)
    {
        "nombre": "Nuestro aniversario",
        "dia": 1,
        "mes": 1,
        "anio": 2024,
        "mensaje": "¡Feliz aniversario, {ella}! Gracias por todo.",
    },
]

# ------------------------------------------------------------------
# Ritmo del tamagotchi (puntos que baja cada barra por hora, de 0 a 100)
# ------------------------------------------------------------------
HAMBRE_POR_HORA = 4.0
CARINO_POR_HORA = 3.0
SUENO_HORAS = 8             # horas que duerme antes de despertarse solo (si no lo despiertas antes)
MAX_HORAS_AUSENTE = 48      # aunque pase más tiempo, no se le descuenta más

# ------------------------------------------------------------------
# Tiempo (se pide a Open-Meteo, gratis y sin clave)
# ------------------------------------------------------------------
CLIMA_ACTIVO = True
CIUDAD = "Alcalá de Henares"   # solo es un nombre
LATITUD = 40.4820       # Alcalá de Henares
LONGITUD = -3.3635      # Alcalá de Henares

# Para probar las animaciones sin esperar a que cambie el tiempo:
MODO_PRUEBA = False     # True: tocar el icono del tiempo recorre todos los climas
CLIMA_FORZADO = None    # por ejemplo "lluvia" (sin internet); None = tiempo real
# Climas posibles: despejado, parcial, nublado, niebla, lluvia, nieve, tormenta

# Frases del primer saludo del día. Puedes usar {ella}, {temp}, {tmax}, {tmin}, {prob}
FRASES_CLIMA = {
    "despejado": [
        "Hoy hace un día de sol precioso, {ella}. Máxima de {tmax}°.",
        "¡Sol, sol, solecito! Hoy llegamos a {tmax}°.",
    ],
    "parcial": [
        "Hoy habrá sol y algunas nubes, con {tmax}° de máxima.",
        "Hoy el cielo está medio nublado: {tmax}° de máxima.",
    ],
    "nublado": [
        "Hoy está nublado, {ella}. Máxima de {tmax}°.",
        "Cielo gris hoy, pero contigo no importa. {tmax}° de máxima.",
    ],
    "niebla": [
        "Hay niebla hoy, {ella}. ¡Ten mucho cuidado!",
        "¡Uuuh, qué niebla! Máxima de {tmax}°.",
    ],
    "lluvia": [
        "¡Hoy llueve, {ella}! Coge el paraguas. Máxima de {tmax}°.",
        "Hoy toca lluvia, así que más mimos en casa. {tmax}° de máxima.",
    ],
    "nieve": [
        "¡Hoy nieva! Abrígate mucho, {ella}. Mínima de {tmin}°.",
        "¡Nieve! ¡Quiero hacer un muñeco contigo!",
    ],
    "tormenta": [
        "¡Hay tormenta, {ella}! Yo me escondo contigo.",
        "Truenos y relámpagos hoy... ¡Quédate calentita!",
    ],
}
FRASE_MINIMA = " Y la mínima será de {tmin}°."   # se añade siempre (vacío "" para quitarla)
FRASE_CALOR = " ¡Mucho calor! Bebe agua."
FRASE_FRIO = " ¡Hace frío! Abrígate bien."
FRASE_PROBABLE_LLUVIA = " Ojo, hay un {prob}% de lluvia."
UMBRAL_CALOR = 30       # grados de máxima
UMBRAL_FRIO = 3         # grados de mínima

# ------------------------------------------------------------------
# Google Calendar SIN Google Cloud: usa un script gratuito de Google Apps Script
# (pasos en GUIA_GOOGLE.md; el código del script está en google_script.gs)
# Si los dejas vacíos, la app funciona igual y el botón del calendario abre Google con la fecha rellenada.
# ------------------------------------------------------------------
GOOGLE_SCRIPT_URL = ""   # privado: va en config_local.py (o en variable de entorno)
GOOGLE_SCRIPT_CLAVE = ""   # privado: va en config_local.py (o en variable de entorno)
GOOGLE_DIAS_ADELANTE = 60    # cuántos días hacia delante se leen del calendario
GOOGLE_RECORDATORIOS_MINUTOS = [900]  # 900 = el día antes a las 9:00 (eventos de todo el día)
FRASE_EVENTOS_HOY = "Hoy tienes en el calendario: {lista}."

# ------------------------------------------------------------------
# Chat con el Minion. Sin configurar, responde con reglas (sin internet).
# Con IA gratuita (ver GUIA_CHAT.md): rellena estas tres líneas. NO compartas este archivo con la clave.
# ------------------------------------------------------------------
CHAT_API_URL = ""   # privado: va en config_local.py (o en variable de entorno)
CHAT_API_KEY = ""   # privado: va en config_local.py (o en variable de entorno)
CHAT_MODELO = ""   # privado: va en config_local.py (o en variable de entorno)
CHAT_BUSQUEDA = True   # si pregunta por algo actual (noticias, precios...), Bob busca en internet
CHAT_PERSONALIDAD_EXTRA = ""   # privado: va en config_local.py (o en variable de entorno)

# ------------------------------------------------------------------
# Frases (usa {ella} para poner su nombre)
# ------------------------------------------------------------------
FRASES_TOCAR = {
    "feliz": [
        "¡Hihi! ¡Cosquillas!",
        "¡Te quiero mucho, {ella}!",
        "¡Banaaana! ...bueno, también tú.",
        "¡Papoi, {ella}!",
        "¡Bello día para estar contigo!",
    ],
    "hambriento": [
        "¡Tengo hambre! ¡Banaaana, por favor!",
        "Mi barriguita hace ruido...",
        "¿Un platanito? ¿Siiii?",
    ],
    "triste": [
        "Estoy un poquito triste... ¿me das un abrazo?",
        "Te echaba de menos, {ella}.",
        "Necesito mimos...",
    ],
    "dormido": [
        "Zzz... Zzz...",
    ],
}

FRASES_PLATANO = [
    "¡Banaaana! ¡Qué rico!",
    "¡Ñam ñam ñam! ¡El mejor plátano!",
    "¡Gracias, {ella}! ¡Me encanta!",
]
FRASES_MIMOS = [
    "Mmm... qué calentito. Te quiero.",
    "¡Qué bien me cuidas, {ella}!",
    "¡Hihihi! ¡Más mimos!",
]
FRASES_JUGAR = [
    "¡Jugamos! ¡Yujuuu!",
    "¡Corre, corre, corre!",
    "¡Qué divertido es contigo!",
]
FRASE_LLENO = "¡Estoy llenísimo! Luego otro platanito."
FRASE_DORMIR = "Buenas noches, {ella}... Zzz..."
FRASE_DESPERTAR = "¡Buenos días! ¡Papoi!"
FRASE_INTRO = "Zzz... (tócame para despertarme)"

# ------------------------------------------------------------------
# Datos privados: se leen de config_local.py (en tu PC) o de variables de entorno (en el servidor).
# Orden de prioridad: variables de entorno > config_local.py > lo que ponga arriba.
# ------------------------------------------------------------------
import os as _os

try:
    from config_local import *   # noqa: F401,F403
except ImportError:
    pass

for _nombre in ("GOOGLE_SCRIPT_URL", "GOOGLE_SCRIPT_CLAVE", "CHAT_API_URL", "CHAT_API_KEY",
                "CHAT_MODELO", "CHAT_PERSONALIDAD_EXTRA", "NOMBRE_ELLA", "CIUDAD"):
    if _os.environ.get(_nombre):
        globals()[_nombre] = _os.environ[_nombre]
for _nombre in ("LATITUD", "LONGITUD"):
    if _os.environ.get(_nombre):
        globals()[_nombre] = float(_os.environ[_nombre])
