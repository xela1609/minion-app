"""
Mi Minion (Bob) - Fase 1.5
Tamagotchi + saludo "papoi" + bocadillo + reloj + tiempo + animaciones del clima + fechas.

Ejecutar en el navegador:   flet run --web main.py
Ejecutar en una ventana:    flet run main.py
"""
import asyncio
import calendar
import json
import re
import random
import time
import urllib.parse
from datetime import date, timedelta

import flet as ft

import clima
import config
import calendario
import chat
import google_calendar
from efectos_clima import EfectoClima
from juegos import JuegoMemoria, JuegoPlatanos, JuegoPPT, MenuJuegos

CLAVE_ESTADO = "minion_estado_v1"
CLAVE_FECHAS = "minion_fechas_v1"
CLAVE_GOOGLE_SUBIDAS = "minion_google_subidas_v1"
CLAVE_GOOGLE_CALENDARIOS = "minion_google_calendarios_v1"   # calendarios que ella quiere ver
MINIMO = 5.0  # las barras nunca bajan de aquí: el Minion no "muere"

AMARILLO = "#FFD83B"
AMARILLO_OSC = "#F2B705"
AZUL = "#3B78C4"
AZUL_OSC = "#235193"
GRIS = "#9AA0A6"
NEGRO = "#1E1E1E"
BOCA = "#7A1F1F"

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

ICONOS_CLIMA = {
    "despejado": ft.Icons.WB_SUNNY,
    "parcial": ft.Icons.WB_CLOUDY,
    "nublado": ft.Icons.CLOUD,
    "niebla": ft.Icons.FOGGY,
    "lluvia": ft.Icons.WATER_DROP,
    "nieve": ft.Icons.AC_UNIT,
    "tormenta": ft.Icons.THUNDERSTORM,
}


def limitar(valor, minimo=MINIMO, maximo=100.0):
    return max(minimo, min(maximo, valor))


def frase(texto):
    try:
        return texto.format(ella=config.NOMBRE_ELLA)
    except (KeyError, IndexError, ValueError):
        return texto  # por si el texto lleva llaves {} que no son de la plantilla


# =====================================================================
# Estado del tamagotchi (lógica pura, sin interfaz)
# =====================================================================
class Estado:
    def __init__(self):
        self.hambre = 80.0   # 100 = lleno
        self.carino = 80.0
        self.durmiendo = False
        self.sueno_horas = 0.0    # horas que lleva durmiendo
        self.ultimo = time.time()
        self.ultimo_saludo = ""   # fecha (AAAA-MM-DD) del último saludo con el tiempo

    def a_texto(self):
        return json.dumps(
            {
                "hambre": self.hambre,
                "carino": self.carino,
                "sueno_horas": self.sueno_horas,
                "durmiendo": self.durmiendo,
                "ultimo": self.ultimo,
                "ultimo_saludo": self.ultimo_saludo,
            }
        )

    @classmethod
    def desde_texto(cls, texto):
        estado = cls()
        try:
            datos = json.loads(texto)
            estado.hambre = limitar(float(datos["hambre"]))
            estado.carino = limitar(float(datos["carino"]))
            estado.sueno_horas = float(datos.get("sueno_horas", 0.0))
            estado.durmiendo = bool(datos["durmiendo"])
            estado.ultimo = float(datos["ultimo"])
            estado.ultimo_saludo = str(datos.get("ultimo_saludo", ""))
        except Exception:
            return cls()
        return estado

    def avanzar(self, ahora=None):
        """Aplica el paso del tiempo desde la última vez."""
        ahora = ahora or time.time()
        horas = max(ahora - self.ultimo, 0) / 3600
        horas = min(horas, config.MAX_HORAS_AUSENTE)
        self.ultimo = ahora
        if horas <= 0:
            return
        if self.durmiendo:
            self.hambre = limitar(self.hambre - config.HAMBRE_POR_HORA * 0.4 * horas)
            self.carino = limitar(self.carino - config.CARINO_POR_HORA * 0.3 * horas)
            self.sueno_horas += horas
            if self.sueno_horas >= config.SUENO_HORAS:   # se despierta solo tras dormir un rato
                self.durmiendo = False
                self.sueno_horas = 0.0
        else:
            self.hambre = limitar(self.hambre - config.HAMBRE_POR_HORA * horas)
            self.carino = limitar(self.carino - config.CARINO_POR_HORA * horas)

    @property
    def humor(self):
        if self.durmiendo:
            return "dormido"
        if self.hambre < 30:
            return "hambriento"
        if self.carino < 30:
            return "triste"
        return "feliz"


# =====================================================================
# Fechas especiales
# =====================================================================
def proxima_fecha(fecha, hoy):
    """Devuelve (fecha_objetivo, dias_que_faltan) para el próximo aniversario."""
    for anio in (hoy.year, hoy.year + 1):
        try:
            objetivo = date(anio, fecha["mes"], fecha["dia"])
        except ValueError:  # 29 de febrero en año no bisiesto
            objetivo = date(anio, 3, 1)
        if objetivo >= hoy:
            return objetivo, (objetivo - hoy).days
    return None, None


def fechas_de_hoy(hoy, lista):
    return [f for f in lista if f["dia"] == hoy.day and f["mes"] == hoy.month]


def texto_cuenta_atras(fecha, hoy):
    objetivo, dias = proxima_fecha(fecha, hoy)
    if dias == 0:
        extra = ""
        if fecha.get("anio"):
            extra = f" ({objetivo.year - fecha['anio']} años)"
        return f"¡Es hoy!{extra}"
    if dias == 1:
        return "¡Mañana!"
    extra = ""
    if fecha.get("anio"):
        extra = f" · cumplís {objetivo.year - fecha['anio']}"
    return f"Faltan {dias} días{extra}"


def enlace_google_calendar(fecha, hoy):
    """
    Enlace que abre Google Calendar con el evento ya rellenado (todo el día, repetido cada año).
    Al guardarlo, Google Calendar le avisa con sus propias notificaciones.
    """
    objetivo, _ = proxima_fecha(fecha, hoy)
    inicio = objetivo.strftime("%Y%m%d")
    fin = (objetivo + timedelta(days=1)).strftime("%Y%m%d")
    parametros = {
        "action": "TEMPLATE",
        "text": fecha["nombre"],
        "dates": f"{inicio}/{fin}",
        "details": frase(fecha.get("mensaje") or ""),
        "recur": "RRULE:FREQ=YEARLY",
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(parametros)


# =====================================================================
# Minion provisional (formas de Flet)
# =====================================================================
class MinionVista:
    ANCHO = 220
    ALTO = 236

    def __init__(self, al_tocar, actualizar):
        self.actualizar = actualizar
        suave = ft.Animation(150, ft.AnimationCurve.EASE_OUT)

        # --- ojos (cada ojo tiene un párpado amarillo que baja) ---
        self.parpados = []
        ojos = []
        for color_iris in ("#4C9A2A", "#6B4226"):   # Bob: un ojo verde y otro marrón
            parpado = ft.Container(
                left=0, top=0, width=44, height=0, bgcolor=AMARILLO, animate_size=120
            )
            pupila = ft.Container(
                left=13, top=13, width=18, height=18,
                bgcolor=color_iris, border_radius=9,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(width=8, height=8, bgcolor=NEGRO, border_radius=4),
            )
            self.parpados.append(parpado)
            ojos.append(
                ft.Container(
                    width=44, height=44, bgcolor="white", border_radius=22,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Stack([pupila, parpado], width=44, height=44),
                )
            )
        gafas = ft.Container(
            left=44, top=52, width=132, height=66,
            border=ft.Border.all(7, GRIS), border_radius=33, bgcolor="#EDEDED",
            alignment=ft.Alignment.CENTER,
            content=ft.Row(ojos, alignment=ft.MainAxisAlignment.CENTER, spacing=6),
        )
        correa = ft.Container(left=31, top=76, width=158, height=16, bgcolor="#2B2B2B")

        # --- boca ---
        self.boca = ft.Container(
            width=56, height=28, bgcolor=BOCA,
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            animate_size=150,
        )
        boca_caja = ft.Container(
            left=25, top=128, width=170, alignment=ft.Alignment.CENTER, content=self.boca
        )

        # --- cuerpo ---
        cuerpo = ft.Container(
            left=25, top=28, width=170, height=176, border_radius=85,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[AMARILLO_OSC, AMARILLO, "#FFF08A", AMARILLO, AMARILLO_OSC],
            ),
            shadow=ft.BoxShadow(blur_radius=14, color="#33000000", offset=ft.Offset(0, 6)),
        )
        peto = ft.Container(
            left=25, top=150, width=170, height=54,
            border_radius=ft.BorderRadius.only(bottom_left=85, bottom_right=85),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[AZUL_OSC, AZUL, "#5C97DC", AZUL, AZUL_OSC],
            ),
        )
        bolsillo = ft.Container(
            left=85, top=164, width=50, height=30, bgcolor=AZUL_OSC, border_radius=8
        )

        # --- brazos (detrás del cuerpo) ---
        def brazo(izquierda, angulo):
            return ft.Container(
                left=4 if izquierda else 190, top=106, width=26, height=70,
                bgcolor=AMARILLO, border_radius=13,
                alignment=ft.Alignment.BOTTOM_CENTER,
                content=ft.Container(width=26, height=26, bgcolor=NEGRO, border_radius=13),
                rotate=ft.Rotate(angle=angulo, alignment=ft.Alignment.TOP_CENTER),
                animate_rotation=ft.Animation(220, ft.AnimationCurve.EASE_IN_OUT),
            )

        self.brazo_izq = brazo(True, 0.25)
        self.brazo_der = brazo(False, -0.25)

        # --- pies (Bob no tiene pelo) ---
        pies = [
            ft.Container(left=x, top=198, width=48, height=22, bgcolor=NEGRO, border_radius=14)
            for x in (50, 122)
        ]
        sombra = ft.Container(
            left=35, top=214, width=150, height=18, border_radius=75,
            bgcolor="#26000000",
        )

        figura = ft.Stack(
            [sombra, self.brazo_izq, self.brazo_der, cuerpo, peto, bolsillo,
             correa, gafas, boca_caja, *pies],
            width=self.ANCHO, height=self.ALTO,
        )

        # Capas de animación: rebote (desplazamiento) y respiración (escala)
        self.respira = ft.Container(
            content=figura, scale=1.0,
            animate_scale=ft.Animation(1300, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.rebote = ft.Container(
            content=self.respira, offset=ft.Offset(0, 0),
            animate_offset=ft.Animation(170, ft.AnimationCurve.EASE_OUT),
            on_click=al_tocar,
        )
        self.control = self.rebote
        self.dormido = False
        self.parpadeo_base = 0

    # ---- expresiones ----
    def poner_humor(self, humor, riendo=False):
        o = self.boca
        if riendo:
            o.width, o.height = 62, 40
            o.border_radius = ft.BorderRadius.only(bottom_left=31, bottom_right=31)
        elif humor == "feliz":
            o.width, o.height = 56, 28
            o.border_radius = ft.BorderRadius.only(bottom_left=28, bottom_right=28)
        elif humor == "hambriento":
            o.width, o.height = 30, 30
            o.border_radius = 15
        elif humor == "triste":
            o.width, o.height = 42, 14
            o.border_radius = ft.BorderRadius.only(top_left=14, top_right=14)
        else:  # dormido
            o.width, o.height = 30, 6
            o.border_radius = 3
        self.dormido = humor == "dormido"
        self.parpadeo_base = 44 if humor == "dormido" else 0
        for p in self.parpados:
            p.height = self.parpadeo_base
        self.actualizar()

    # ---- animaciones ----
    async def parpadear(self):
        if self.dormido:
            return
        for p in self.parpados:
            p.height = 44
        self.actualizar()
        await asyncio.sleep(0.13)
        for p in self.parpados:
            p.height = self.parpadeo_base
        self.actualizar()

    async def rebotar(self, veces=1):
        for _ in range(veces):
            self.rebote.offset = ft.Offset(0, -0.06)
            self.actualizar()
            await asyncio.sleep(0.18)
            self.rebote.offset = ft.Offset(0, 0)
            self.actualizar()
            await asyncio.sleep(0.18)

    async def saludar(self):
        for i in range(6):
            self.brazo_der.rotate = ft.Rotate(
                angle=-2.35 if i % 2 == 0 else -2.9, alignment=ft.Alignment.TOP_CENTER
            )
            self.actualizar()
            await asyncio.sleep(0.24)
        self.brazo_der.rotate = ft.Rotate(angle=-0.25, alignment=ft.Alignment.TOP_CENTER)
        self.actualizar()

    def respirar(self, dentro):
        self.respira.scale = 1.03 if dentro else 1.0
        self.actualizar()


# =====================================================================
# Bocadillo de texto
# =====================================================================
class Bocadillo:
    def __init__(self, actualizar):
        self.actualizar = actualizar
        self._id = 0
        self.texto = ft.Text(
            "", size=19, weight=ft.FontWeight.BOLD, color="#2B2B2B",
            text_align=ft.TextAlign.CENTER,
        )
        globo = ft.Container(
            content=self.texto, bgcolor="white", border_radius=22,
            padding=ft.Padding.symmetric(vertical=12, horizontal=18),
            width=290,
            shadow=ft.BoxShadow(blur_radius=10, color="#22000000", offset=ft.Offset(0, 3)),
        )
        cola = ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=40, color="white")
        self.control = ft.Container(
            content=ft.Column([globo, cola], spacing=0,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            opacity=0, animate_opacity=250,
        )

    async def decir(self, mensaje, mantener=4.5):
        """Escribe el mensaje letra a letra y lo deja visible un rato."""
        self._id += 1
        mi_id = self._id
        self.texto.value = ""
        self.control.opacity = 1
        self.actualizar()
        for i in range(1, len(mensaje) + 1):
            if mi_id != self._id:
                return  # otro mensaje ha tomado el relevo
            self.texto.value = mensaje[:i]
            self.actualizar()
            await asyncio.sleep(0.03)
        if mantener is None:
            return
        await asyncio.sleep(mantener)
        if mi_id == self._id:
            self.control.opacity = 0
            self.actualizar()


# =====================================================================
# Fondo y colores según la hora y el tiempo
# =====================================================================
def es_noche(durmiendo):
    hora = time.localtime().tm_hour
    return durmiendo or hora >= 21 or hora < 7


def tema(durmiendo, categoria):
    """Devuelve (degradado, color_de_texto) según la hora, el sueño y el clima."""
    hora = time.localtime().tm_hour
    if es_noche(durmiendo):
        colores, texto = ["#1F2A52", "#3B4A86"], "white"
    elif categoria in ("lluvia", "tormenta"):
        colores, texto = ["#5F6F86", "#9DB0C6"], "white"
    elif categoria in ("nublado", "niebla"):
        colores, texto = ["#AEBBC9", "#E3E9EF"], "#2B2B2B"
    elif categoria == "nieve":
        colores, texto = ["#C9DDF0", "#F6FAFF"], "#2B2B2B"
    elif hora < 10:
        colores, texto = ["#FFE9B8", "#FFC48A"], "#2B2B2B"
    elif hora < 19:
        colores, texto = ["#BFE6FF", "#FFF4C2"], "#2B2B2B"
    else:
        colores, texto = ["#FFB88C", "#C97BB5"], "white"
    degradado = ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER, colors=colores
    )
    return degradado, texto


# =====================================================================
# App
# =====================================================================
async def main(page: ft.Page):
    page.title = config.NOMBRE_APP
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- persistencia (en web se guarda en el navegador) ---
    prefs = ft.SharedPreferences()
    lanzador = ft.UrlLauncher()
    try:
        page.services.append(prefs)
        page.services.append(lanzador)
    except Exception:
        pass

    async def cargar():
        try:
            texto = await prefs.get(CLAVE_ESTADO)
            if texto:
                return Estado.desde_texto(texto)
        except Exception:
            pass
        return Estado()

    async def cargar_fechas_usuario():
        try:
            texto = await prefs.get(CLAVE_FECHAS)
            if texto:
                lista = json.loads(texto)
                return [f for f in lista if isinstance(f, dict) and "nombre" in f]
        except Exception:
            pass
        return []

    async def guardar():
        try:
            await prefs.set(CLAVE_ESTADO, estado.a_texto())
        except Exception:
            pass

    async def guardar_fechas():
        try:
            await prefs.set(CLAVE_FECHAS, json.dumps(fechas_usuario))
        except Exception:
            pass

    async def leer_texto(clave):
        try:
            return await prefs.get(clave) or ""
        except Exception:
            return ""

    async def guardar_texto(clave, valor):
        try:
            await prefs.set(clave, valor)
        except Exception:
            pass

    estado = await cargar()
    estado.avanzar()
    fechas_usuario = await cargar_fechas_usuario()
    try:
        subidas = json.loads(await leer_texto(CLAVE_GOOGLE_SUBIDAS) or "{}")
    except Exception:
        subidas = {}   # fecha -> id del evento creado en Google Calendar

    try:
        _elegidos = json.loads(await leer_texto(CLAVE_GOOGLE_CALENDARIOS) or "null")
    except Exception:
        _elegidos = None   # None = los que tenga marcados en su Google Calendar

    async def guardar_subidas():
        await guardar_texto(CLAVE_GOOGLE_SUBIDAS, json.dumps(subidas))

    def todas_las_fechas():
        return list(config.FECHAS) + fechas_usuario

    sesion = {
        "intro": True,         # hasta que ella toque, el Minion "duerme"
        "clima": None,         # último tiempo conocido
        "clima_hora": 0.0,     # cuándo se pidió
        "prueba_idx": -1,      # para el modo prueba
        "pantalla": 0,
        "reloj": "",
    }

    def actualizar():
        page.update()

    # --- piezas ---
    bocadillo = Bocadillo(actualizar)
    efectos = EfectoClima()

    barras = {}
    iconos_barra = []

    def crear_barra(clave, icono, color):
        barra = ft.ProgressBar(value=0.5, color=color, bgcolor="#33808080",
                               bar_height=10, border_radius=5, width=86)
        barras[clave] = barra
        icono_ctrl = ft.Icon(icono, color="white", size=22)
        iconos_barra.append(icono_ctrl)
        return ft.Column(
            [icono_ctrl, barra],
            spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    panel_barras = ft.Row(
        [
            crear_barra("hambre", ft.Icons.RESTAURANT, "#FFD83B"),
            crear_barra("carino", ft.Icons.FAVORITE, "#FF6B8B"),
        ],
        alignment=ft.MainAxisAlignment.CENTER, spacing=22,
    )

    # --- reloj y tiempo ---
    reloj = ft.Text("--:--", size=46, weight=ft.FontWeight.W_300, color="white")
    fecha_txt = ft.Text("", size=14, color="white")
    chip_icono = ft.Icon(ft.Icons.CLOUD, size=22, color="white")
    chip_texto = ft.Text("", size=18, weight=ft.FontWeight.W_600, color="white")

    async def al_tocar_chip(e):
        if not config.MODO_PRUEBA:
            return
        sesion["prueba_idx"] = (sesion["prueba_idx"] + 1) % len(clima.CATEGORIAS)
        datos = clima.datos_prueba(clima.CATEGORIAS[sesion["prueba_idx"]])
        sesion["clima"] = datos
        sesion["clima_hora"] = time.time()
        refrescar_tema()
        await bocadillo.decir(clima.frase_tiempo(datos, config.NOMBRE_ELLA), mantener=4)

    chip_clima = ft.Container(
        content=ft.Row([chip_icono, chip_texto], spacing=6),
        visible=False, on_click=al_tocar_chip,
        padding=ft.Padding.symmetric(vertical=6, horizontal=10),
        border_radius=16, bgcolor="#22808080",
    )

    cabecera = ft.Container(
        content=ft.Row(
            [ft.Column([reloj, fecha_txt], spacing=0), chip_clima],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.Padding.symmetric(horizontal=20),
    )

    fondo = ft.Container(expand=True)

    def actualizar_reloj():
        ahora = time.localtime()
        hora = f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}"
        if hora != sesion["reloj"]:
            sesion["reloj"] = hora
            reloj.value = hora
            fecha_txt.value = (
                f"{DIAS_SEMANA[ahora.tm_wday].capitalize()}, "
                f"{ahora.tm_mday} de {MESES[ahora.tm_mon - 1]}"
            )
            return True
        return False

    def refrescar_tema():
        """Recalcula fondo, colores de texto, icono del tiempo y animación del clima."""
        datos = sesion["clima"]
        categoria = datos["categoria"] if datos else None
        degradado, color_texto = tema(estado.durmiendo, categoria)
        fondo.gradient = degradado
        reloj.color = color_texto
        fecha_txt.color = color_texto
        chip_icono.color = color_texto
        chip_texto.color = color_texto
        for ic in iconos_barra:
            ic.color = color_texto
        if datos:
            chip_icono.name = ICONOS_CLIMA.get(categoria, ft.Icons.CLOUD)
            chip_texto.value = f"{round(datos['temp'])}°"
            chip_clima.visible = True
            efectos.poner(categoria, es_noche(estado.durmiendo))
        else:
            chip_clima.visible = config.MODO_PRUEBA
            if config.MODO_PRUEBA:
                chip_icono.name = ft.Icons.WB_SUNNY
                chip_texto.value = "test"
            efectos.poner(None, es_noche(estado.durmiendo))

    def refrescar_barras():
        barras["hambre"].value = estado.hambre / 100
        barras["carino"].value = estado.carino / 100
        refrescar_tema()

    # --- tiempo meteorológico ---
    async def asegurar_clima(forzar=False):
        """Devuelve el tiempo actual; lo pide de nuevo si tiene más de 30 minutos."""
        if not config.CLIMA_ACTIVO:
            return None
        vigente = sesion["clima"] and (time.time() - sesion["clima_hora"] < 1800)
        if vigente and not forzar:
            return sesion["clima"]
        datos = await clima.obtener_clima()
        if datos:
            sesion["clima"] = datos
            sesion["clima_hora"] = time.time()
            refrescar_tema()
            actualizar()
        return sesion["clima"]

    # --- Google Calendar (por un script de Apps Script, sin Google Cloud) ---
    google = {
        "estado": "desconectado" if google_calendar.configurado() else "no_configurado",
        "mensaje": "",      # errores
        "aviso": "",        # avisos buenos
        "eventos": [],      # próximos días (lista de abajo en la pestaña Fechas)
        "meses": {},        # eventos por mes visto en el calendario: (año, mes) -> lista
        "calendarios": [],  # calendarios de la cuenta (propios y compartidos) con su color
        "activos": set(_elegidos) if isinstance(_elegidos, list) else None,  # ids que se muestran
        "antiguo": False,   # True si el script de Google es de una versión sin calendarios
        "ultima": 0.0,      # último intento de lectura
    }

    def conectado():
        return google["estado"] == "conectado"

    def refrescar_fechas_si_visible():
        if sesion["pantalla"] == 1:
            cuerpo.content = construir_fechas()
        page.update()

    def ids_para_mostrar():
        """Ids de los calendarios que se leen. Lista vacía = el principal (script antiguo)."""
        cals = google["calendarios"]
        if not cals:
            return []
        existentes = {c["id"] for c in cals}
        if google["activos"] is not None:
            return [i for i in google["activos"] if i in existentes]
        elegidos = [c["id"] for c in cals if c["seleccionado"]]
        return elegidos or [c["id"] for c in cals if c["principal"]]

    def sin_calendarios_activos():
        return bool(google["calendarios"]) and not ids_para_mostrar()

    async def leer_calendarios():
        try:
            google["calendarios"] = await google_calendar.listar_calendarios()
            google["antiguo"] = False
        except google_calendar.ErrorCalendario as ex:
            if "desconocida" not in str(ex).lower():
                raise
            google["calendarios"] = []       # script sin la versión nueva: solo el principal
            google["antiguo"] = True

    async def sincronizar_google(forzar=False):
        """Lee los próximos eventos del calendario (como mucho cada 2 minutos).
        La primera lectura que sale bien deja la app conectada."""
        if google["estado"] == "no_configurado":
            return
        if not forzar and time.time() - google["ultima"] < 120:
            return
        google["ultima"] = time.time()
        try:
            if (forzar or not google["calendarios"]) and not google["antiguo"]:
                await leer_calendarios()
            if sin_calendarios_activos():
                google["eventos"] = []
            else:
                google["eventos"] = await google_calendar.listar_eventos(
                    config.GOOGLE_DIAS_ADELANTE, ids_para_mostrar())
            google["estado"] = "conectado"
            google["mensaje"] = ""
            google["meses"].clear()      # se vuelven a pedir para ver los cambios recientes
            await cargar_mes(vista_cal.anio, vista_cal.mes)
        except Exception as ex:
            if not conectado():
                google["estado"] = "desconectado"
            google["mensaje"] = f"No pude leer tu calendario: {ex}"
        refrescar_fechas_si_visible()

    async def cargar_mes(anio, mes):
        """Pide al calendario de Google los eventos de un mes entero (también meses pasados)."""
        if not conectado():
            return
        try:
            desde = date(anio, mes, 1)
            hasta = date(anio, mes, calendar.monthrange(anio, mes)[1])
            if sin_calendarios_activos():
                google["meses"][(anio, mes)] = []
            else:
                google["meses"][(anio, mes)] = await google_calendar.listar_rango(
                    desde, hasta, ids_para_mostrar())
        except Exception as ex:
            google["mensaje"] = f"No pude leer ese mes de tu calendario: {ex}"
        refrescar_fechas_si_visible()

    def pedir_mes(anio, mes):
        if conectado() and (anio, mes) not in google["meses"]:
            page.run_task(cargar_mes, anio, mes)

    def eventos_para_calendario():
        return google["eventos"] + [e for lista in google["meses"].values() for e in lista]

    async def conectar_google(e=None):
        """Botón «Conectar»: prueba la conexión con el script y lee el calendario."""
        if google["estado"] == "no_configurado":
            return
        google["estado"] = "conectando"
        google["mensaje"] = google["aviso"] = ""
        refrescar_fechas_si_visible()
        await sincronizar_google(forzar=True)
        if conectado():
            google["aviso"] = "Conectado con Google Calendar."
            refrescar_fechas_si_visible()

    async def conectar_google_inicial():
        """Al abrir la app se conecta sola si ya está configurada."""
        if google["estado"] != "no_configurado":
            await sincronizar_google(forzar=True)

    async def subir_a_google(fecha):
        """Guarda la fecha en Google Calendar como evento anual. Devuelve True si fue bien."""
        clave = google_calendar.clave_fecha(fecha)
        if clave in subidas:
            return True
        try:
            id_evento = await google_calendar.crear_evento_anual(
                fecha, frase(fecha.get("mensaje") or ""))
        except Exception as ex:
            google["mensaje"] = f"No pude guardar en tu calendario: {ex}"
            refrescar_fechas_si_visible()
            return False
        subidas[clave] = id_evento
        await guardar_subidas()
        google["mensaje"] = ""
        google["aviso"] = f"«{fecha['nombre']}» guardada en tu Google Calendar."
        await sincronizar_google(forzar=True)
        return True

    # --- interacción con el Minion ---
    async def al_tocar_minion(e):
        if sesion["intro"]:
            sesion["intro"] = False
            await despertar_con_saludo()
            return
        if estado.durmiendo:
            estado.durmiendo = False
            minion.poner_humor(estado.humor)
            refrescar_barras()
            await guardar()
            await minion.rebotar()
            await bocadillo.decir(frase(config.FRASE_DESPERTAR))
            return
        estado.carino = limitar(estado.carino + 2)
        humor = estado.humor
        minion.poner_humor(humor, riendo=(humor == "feliz"))
        refrescar_barras()
        page.run_task(minion.rebotar)
        await bocadillo.decir(frase(random.choice(config.FRASES_TOCAR[humor])), mantener=3)
        minion.poner_humor(estado.humor)
        await guardar()

    minion = MinionVista(al_tocar_minion, actualizar)

    async def despertar_con_saludo():
        hoy = date.today()
        primera_del_dia = estado.ultimo_saludo != hoy.isoformat()
        estado.durmiendo = False
        minion.poner_humor(estado.humor, riendo=(estado.humor == "feliz"))
        refrescar_barras()
        await guardar()
        page.run_task(minion.saludar)
        await bocadillo.decir(config.SALUDO, mantener=1.6)

        # Primer saludo del día: el tiempo
        if primera_del_dia and config.CLIMA_ACTIVO:
            datos = await asegurar_clima()
            if datos:
                estado.ultimo_saludo = hoy.isoformat()
                await guardar()
                await bocadillo.decir(clima.frase_tiempo(datos, config.NOMBRE_ELLA), mantener=7)

        # Eventos de hoy de su Google Calendar
        if conectado():
            await sincronizar_google()
            de_hoy = [ev for ev in google["eventos"]
                      if ev["fecha"] == hoy and not ev["especial"]]
            if de_hoy:
                lista = ", ".join(
                    f"{ev['titulo']} ({ev['hora']})" if ev["hora"] else ev["titulo"]
                    for ev in de_hoy[:3])
                await bocadillo.decir(config.FRASE_EVENTOS_HOY.format(lista=lista), mantener=7)

        # Si hoy es una fecha especial, su mensaje
        especiales = fechas_de_hoy(hoy, todas_las_fechas())
        if especiales:
            f = especiales[0]
            mensaje = f.get("mensaje") or f"¡Hoy es {f['nombre']}!"
            await bocadillo.decir(frase(mensaje), mantener=8)
        minion.poner_humor(estado.humor)

    # --- acciones ---
    async def accion_platano(e):
        if sesion["intro"] or estado.durmiendo:
            return
        if estado.hambre > 95:
            await bocadillo.decir(frase(config.FRASE_LLENO), mantener=3)
            return
        estado.hambre = limitar(estado.hambre + 25)
        estado.carino = limitar(estado.carino + 2)
        minion.poner_humor("feliz", riendo=True)
        refrescar_barras()
        page.run_task(minion.rebotar, 2)
        await bocadillo.decir(frase(random.choice(config.FRASES_PLATANO)), mantener=3)
        minion.poner_humor(estado.humor)
        await guardar()

    async def accion_mimos(e):
        if sesion["intro"] or estado.durmiendo:
            return
        estado.carino = limitar(estado.carino + 20)
        minion.poner_humor("feliz", riendo=True)
        refrescar_barras()
        page.run_task(minion.rebotar)
        await bocadillo.decir(frase(random.choice(config.FRASES_MIMOS)), mantener=3)
        minion.poner_humor(estado.humor)
        await guardar()

    async def accion_tiempo(e):
        """Botón «Tiempo»: Bob dice el tiempo de ahora, las veces que ella quiera."""
        if sesion["intro"]:
            return
        if estado.durmiendo:
            await bocadillo.decir("Zzz... despiértame primero, porfa.", mantener=3)
            return
        if not config.CLIMA_ACTIVO:
            await bocadillo.decir("El tiempo está desactivado en mis ajustes.", mantener=3)
            return
        await bocadillo.decir("Déjame mirar por la ventana...", mantener=1.5)
        # refresca si el dato tiene más de 5 minutos (así no se pide a cada toque)
        datos = await asegurar_clima(forzar=time.time() - sesion["clima_hora"] > 300)
        if not datos:
            datos = sesion["clima"]     # el último que se pudo leer, si lo hay
        if not datos:
            await bocadillo.decir("Uy, hoy no consigo ver el cielo. Prueba otra vez en un rato.",
                                  mantener=4)
            return
        page.run_task(minion.rebotar)
        await bocadillo.decir(clima.frase_tiempo(datos, config.NOMBRE_ELLA), mantener=7)

    async def accion_jugar(e):
        if sesion["intro"] or estado.durmiendo:
            return
        sesion["pantalla"] = 2
        cuerpo.content = menu_juegos.control
        page.update()

    async def accion_dormir(e):
        if sesion["intro"]:
            return
        if estado.durmiendo:
            estado.durmiendo = False
            minion.poner_humor(estado.humor)
            refrescar_barras()
            await guardar()
            await bocadillo.decir(frase(config.FRASE_DESPERTAR), mantener=3)
            return
        estado.durmiendo = True
        estado.sueno_horas = 0.0
        minion.poner_humor("dormido")
        refrescar_barras()
        await guardar()
        await bocadillo.decir(frase(config.FRASE_DORMIR), mantener=4)

    def boton_accion(icono, etiqueta, al_pulsar):
        return ft.Container(
            content=ft.Column(
                [ft.Icon(icono, color="#3A3A3A", size=26),
                 ft.Text(etiqueta, size=12, color="#3A3A3A", weight=ft.FontWeight.W_600)],
                spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=64, padding=ft.Padding.symmetric(vertical=10, horizontal=2),
            bgcolor="#E6FFFFFF", border_radius=18, ink=True, on_click=al_pulsar,
            shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
        )

    botones = ft.Row(
        [
            boton_accion(ft.Icons.LUNCH_DINING, "Plátano", accion_platano),
            boton_accion(ft.Icons.FAVORITE, "Mimos", accion_mimos),
            boton_accion(ft.Icons.WB_SUNNY, "Tiempo", accion_tiempo),
            boton_accion(ft.Icons.SPORTS_ESPORTS, "Jugar", accion_jugar),
            boton_accion(ft.Icons.BEDTIME, "Dormir", accion_dormir),
        ],
        alignment=ft.MainAxisAlignment.CENTER, spacing=6,
    )

    # --- pantalla 1: Minion ---
    pantalla_minion = ft.Column(
        [
            ft.Container(height=6),
            cabecera,
            # Zona de Bob: el Minion va abajo y el bocadillo FLOTA justo encima de su cabeza, creciendo
            # solo hacia arriba (si es larguísimo puede tapar el reloj un momento). Así ningún mensaje
            # empuja a Bob ni a los botones, ni queda cortado.
            ft.Stack(
                [
                    ft.Container(content=ft.Row([minion.control], alignment=ft.MainAxisAlignment.CENTER),
                                 left=0, right=0, bottom=0),
                    ft.Container(content=ft.Row([bocadillo.control],
                                                alignment=ft.MainAxisAlignment.CENTER),
                                 left=0, right=0, bottom=MinionVista.ALTO),
                ],
                expand=True, clip_behavior=ft.ClipBehavior.NONE,
            ),
            # Las barras van debajo de Bob, junto a los botones: el bocadillo nunca las tapa
            ft.Container(height=8),
            panel_barras,
            ft.Container(height=12),
            botones,
            ft.Container(height=14),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    # --- pantalla 2: fechas ---
    async def abrir_enlace_calendario(fecha):
        url = enlace_google_calendar(fecha, date.today())
        try:
            await lanzador.launch_url(url)
        except Exception:
            pass

    async def accion_calendario(fecha):
        google["mensaje"] = google["aviso"] = ""
        if conectado():
            if google_calendar.clave_fecha(fecha) in subidas:
                google["aviso"] = "Esa fecha ya está en tu Google Calendar."
                refrescar_fechas_si_visible()
            else:
                await subir_a_google(fecha)
        else:
            await abrir_enlace_calendario(fecha)

    async def borrar_fecha(fecha):
        google["mensaje"] = google["aviso"] = ""
        if fecha in fechas_usuario:
            fechas_usuario.remove(fecha)
            await guardar_fechas()
        id_evento = subidas.pop(google_calendar.clave_fecha(fecha), None)
        if id_evento:
            await guardar_subidas()
            if conectado():
                try:
                    await google_calendar.borrar_evento(id_evento, fecha.get("calendario", ""))
                    await sincronizar_google(forzar=True)
                except Exception as ex:
                    google["mensaje"] = f"Se borró de la app, pero no de tu calendario: {ex}"
        mostrar_fechas()

    def tarjeta_fecha(f, hoy, es_propia, ancho=340, al_tocar=None):
        def al_calendario(e):
            page.run_task(accion_calendario, f)

        def al_borrar(e):
            page.run_task(borrar_fecha, f)

        color_fecha = google_calendar.COLORES_EVENTO.get(str(f.get("color", "")), ("", None))[1]
        ya_subida = google_calendar.clave_fecha(f) in subidas
        if conectado() and ya_subida:
            boton_cal = ft.IconButton(ft.Icons.EVENT_AVAILABLE, icon_color="#2E7D32",
                                      tooltip="Ya está en tu Google Calendar",
                                      on_click=al_calendario)
        elif conectado():
            boton_cal = ft.IconButton(ft.Icons.EVENT_NOTE, icon_color="#C2185B",
                                      tooltip="Guardar en Google Calendar",
                                      on_click=al_calendario)
        else:
            boton_cal = ft.IconButton(ft.Icons.EVENT, icon_color="#C2185B",
                                      tooltip="Abrir en Google Calendar", on_click=al_calendario)
        acciones = [boton_cal]
        if es_propia:
            acciones.append(
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#8A8A8A",
                              tooltip="Borrar", on_click=al_borrar)
            )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row([
                                *([ft.Container(width=12, height=12, border_radius=6,
                                                bgcolor=color_fecha)] if color_fecha else []),
                                ft.Text(f["nombre"], size=20, weight=ft.FontWeight.BOLD,
                                        color="#2B2B2B", expand=True),
                            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Text(f"{f['dia']:02d}/{f['mes']:02d}", size=14, color="#6A6A6A"),
                            ft.Text(texto_cuenta_atras(f, hoy), size=16,
                                    weight=ft.FontWeight.W_600, color="#C2185B"),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Row(acciones, spacing=0),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#EFFFFFFF", border_radius=18,
            padding=ft.Padding.all(16), width=ancho,
            on_click=al_tocar, ink=al_tocar is not None,
            shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
        )

    def bloque_google():
        filas = []
        situacion = google["estado"]
        if situacion == "no_configurado":
            filas.append(ft.Text(
                "Google Calendar sin configurar (mira GUIA_GOOGLE.md). Mientras tanto, el botón "
                "del calendario abre Google con la fecha ya rellenada.",
                size=12, color=reloj.color, text_align=ft.TextAlign.CENTER, width=320))
        elif situacion == "desconectado":
            filas.append(ft.Button(
                "Reintentar conexión" if google["mensaje"] else "Conectar con Google Calendar",
                icon=ft.Icons.EVENT, on_click=conectar_google))
        elif situacion == "conectando":
            filas.append(ft.Text(
                "Conectando con tu calendario...",
                size=13, color=reloj.color, text_align=ft.TextAlign.CENTER, width=320))
        else:
            filas.append(ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="#2E7D32", size=20),
                    ft.Text(f"Google Calendar conectado · {len(google['eventos'])} próximos",
                            size=14, color=reloj.color),
                    ft.IconButton(ft.Icons.REFRESH, tooltip="Actualizar",
                                  icon_color=reloj.color,
                                  on_click=lambda e: page.run_task(sincronizar_google, True)),
                ],
                alignment=ft.MainAxisAlignment.CENTER, spacing=4,
            ))
        if google["mensaje"]:
            filas.append(ft.Text(google["mensaje"], size=12, color="#C62828",
                                 text_align=ft.TextAlign.CENTER, width=320))
        if google["aviso"]:
            filas.append(ft.Text(google["aviso"], size=12, color="#2E7D32",
                                 text_align=ft.TextAlign.CENTER, width=320))
        return ft.Column(filas, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

    async def cambiar_calendarios_activos():
        await guardar_texto(CLAVE_GOOGLE_CALENDARIOS, json.dumps(sorted(google["activos"])))
        google["meses"].clear()
        await sincronizar_google(forzar=True)

    def bloque_calendarios():
        """Casillas para elegir qué calendarios (propios o compartidos) se ven, con su color."""
        if not conectado():
            return None
        if google["antiguo"]:
            return ft.Text(
                "Para ver calendarios compartidos y los colores, actualiza el script de Google "
                "(mira GUIA_GOOGLE.md).", size=12, color=reloj.color,
                text_align=ft.TextAlign.CENTER, width=320)
        cals = google["calendarios"]
        if len(cals) < 2:
            return None
        activos = set(ids_para_mostrar())

        def alternar(id_cal):
            def al_cambiar(e):
                nuevos = set(ids_para_mostrar())
                if e.control.value:
                    nuevos.add(id_cal)
                else:
                    nuevos.discard(id_cal)
                google["activos"] = nuevos
                page.run_task(cambiar_calendarios_activos)
            return al_cambiar

        casillas = [
            ft.Checkbox(label=c["nombre"] + ("" if c["propio"] else " (compartido)"),
                        value=c["id"] in activos, active_color=c["color"],
                        on_change=alternar(c["id"]))
            for c in cals
        ]
        return ft.Container(
            content=ft.Column(
                [ft.Text("Calendarios", size=16, weight=ft.FontWeight.BOLD, color="#2B2B2B"),
                 *casillas], spacing=0),
            bgcolor="#EFFFFFFF", border_radius=14, padding=ft.Padding.all(12), width=340)

    def pedir_borrar_evento(ev):
        async def confirmar(e):
            page.pop_dialog()
            google["mensaje"] = google["aviso"] = ""
            try:
                await google_calendar.borrar_evento(ev["id"], ev.get("calendario_id", ""))
                google["aviso"] = f"«{ev['titulo']}» borrado de tu calendario."
            except Exception as ex:
                google["mensaje"] = f"No pude borrarlo: {ex}"
            google["meses"].clear()
            await sincronizar_google(forzar=True)

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("¿Borrar este evento?"),
            content=ft.Text(f"{ev['titulo']}\nSi se repite cada año, se borrarán todas las "
                            "repeticiones."),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                     ft.TextButton("Borrar", on_click=confirmar)],
        ))

    def lista_eventos_google():
        if not conectado():
            return []
        propios = [ev for ev in google["eventos"] if not ev["especial"]]
        filas = [ft.Text("En tu Google Calendar", size=20, weight=ft.FontWeight.BOLD,
                         color=reloj.color)]
        if not propios:
            filas.append(ft.Text("No hay eventos en los próximos días.", size=13,
                                 color=reloj.color))
        for ev in propios[:15]:
            dia = DIAS_SEMANA[ev["fecha"].weekday()][:3].capitalize()
            cuando = f"{dia} {ev['fecha'].day} {MESES[ev['fecha'].month - 1][:3]}"
            if ev["hora"]:
                cuando += f" · {ev['hora']}"
            if ev.get("calendario") and len(google["calendarios"]) > 1:
                cuando += f" · {ev['calendario']}"
            filas.append(ft.Container(
                content=ft.Row([
                    ft.Container(width=6, height=38, border_radius=3, bgcolor=ev["color"]),
                    ft.Column(
                        [ft.Text(ev["titulo"], size=16, weight=ft.FontWeight.W_600, color="#2B2B2B"),
                         ft.Text(cuando, size=13, color="#6A6A6A")],
                        spacing=1, expand=True),
                ], spacing=10),
                bgcolor="#EFFFFFFF", border_radius=14, padding=ft.Padding.all(12), width=340))
        return filas

    def abrir_dialogo_fecha(e=None):
        hay_google = conectado()
        nombre = ft.TextField(label="¿Qué es?", autofocus=True)
        dia = ft.TextField(label="Día", width=90, max_length=2,
                           keyboard_type=ft.KeyboardType.NUMBER)
        mes = ft.TextField(label="Mes", width=90, max_length=2,
                           keyboard_type=ft.KeyboardType.NUMBER)
        anio = ft.TextField(label="Año (opcional)", width=140, max_length=4,
                            keyboard_type=ft.KeyboardType.NUMBER)
        tipo = ft.Dropdown(
            label="Tipo", value="especial", width=320,
            options=[
                ft.DropdownOption(key="especial",
                                  text="Fecha especial (Bob la recuerda y la felicita)"),
                ft.DropdownOption(key="normal", text="Evento normal (solo en tu calendario)"),
            ])
        hora = ft.TextField(label="Hora (opcional, por ejemplo 18:30)", max_length=5, visible=False)
        repetir = ft.Switch(label="Repetir cada año", value=False, visible=False)
        mensaje = ft.TextField(label="Mensaje del Minion (opcional)",
                               multiline=True, min_lines=2, max_lines=3)
        a_google = ft.Checkbox(label="Añadir también a Google Calendar", value=True,
                               visible=hay_google)
        error = ft.Text("", color="#C62828", size=12)

        # calendario donde guardarlo (solo si hay más de uno)
        escribibles = google["calendarios"]
        principal = next((c["id"] for c in escribibles if c["principal"]),
                         escribibles[0]["id"] if escribibles else "")
        calendario_destino = ft.Dropdown(
            label="Guardar en el calendario", value=principal, width=320,
            visible=hay_google and len(escribibles) > 1,
            options=[ft.DropdownOption(key=c["id"], text=c["nombre"]) for c in escribibles])

        # color con el que se guarda en Google Calendar
        color_elegido = {"id": ""}
        selector_color = ft.Row(wrap=True, spacing=8, run_spacing=8)
        titulo_color = ft.Text("Color en Google Calendar", size=12, color="#6A6A6A")

        def pintar_colores():
            selector_color.controls.clear()
            for id_color, (nombre_color, hexa) in google_calendar.COLORES_EVENTO.items():
                elegido = color_elegido["id"] == id_color
                if hexa is None:   # "del calendario": círculo con una raya
                    contenido = ft.Icon(ft.Icons.CLOSE, size=14, color="#6A6A6A")
                    fondo = "#F2F2F2"
                else:
                    contenido, fondo = None, hexa
                selector_color.controls.append(ft.Container(
                    content=contenido, width=30, height=30, border_radius=15, bgcolor=fondo,
                    alignment=ft.Alignment.CENTER, tooltip=nombre_color,
                    border=ft.Border.all(3, "#2B2B2B") if elegido else ft.Border.all(1, "#CCCCCC"),
                    on_click=lambda ev, i=id_color: elegir_color(i)))

        def elegir_color(id_color):
            color_elegido["id"] = id_color
            pintar_colores()
            page.update()

        pintar_colores()

        def ajustar(ev=None):
            normal = tipo.value == "normal"
            hora.visible = normal and hay_google
            repetir.visible = normal and hay_google
            mensaje.visible = not normal
            a_google.visible = hay_google and not normal
            guarda_en_google = hay_google and (normal or a_google.value)
            selector_color.visible = guarda_en_google
            titulo_color.visible = guarda_en_google
            page.update()

        tipo.on_select = ajustar
        a_google.on_change = ajustar
        ajustar()

        async def guardar_nueva(ev):
            normal = tipo.value == "normal"
            try:
                d, m = int(dia.value), int(mes.value)
                a = int(anio.value) if (anio.value or "").strip() else None
            except (TypeError, ValueError):
                error.value = "Día, mes y año tienen que ser números."
                page.update()
                return
            texto_hora = (hora.value or "").strip()
            if not (nombre.value or "").strip():
                error.value = "Ponle un nombre."
            elif not (1 <= m <= 12) or not (
                    1 <= d <= calendar.monthrange(a if a else 2024, m)[1]):
                error.value = "Esa fecha no existe."
            elif a is not None and not (1900 <= a <= 2100):
                error.value = "Revisa el año."
            elif normal and not hay_google:
                error.value = "Para crear eventos normales conecta primero Google Calendar."
            elif normal and texto_hora and not re.fullmatch(
                    r"([01]?\d|2[0-3]):[0-5]\d", texto_hora):
                error.value = "La hora tiene que ser como 18:30."
            else:
                destino = calendario_destino.value if calendario_destino.visible else ""
                if normal:
                    datos = {"nombre": nombre.value.strip(), "dia": d, "mes": m,
                             "tipo": "normal", "repetir": bool(repetir.value)}
                    if a is not None:
                        datos["anio"] = a
                    if texto_hora:
                        datos["hora"] = texto_hora
                    if color_elegido["id"]:
                        datos["color"] = color_elegido["id"]
                    if destino:
                        datos["calendario"] = destino
                    page.pop_dialog()
                    google["mensaje"] = google["aviso"] = ""
                    try:
                        await google_calendar.crear_evento(datos)
                        google["aviso"] = f"«{datos['nombre']}» guardado en tu Google Calendar."
                    except Exception as ex:
                        google["mensaje"] = f"No pude guardar en tu calendario: {ex}"
                    google["meses"].clear()
                    await sincronizar_google(forzar=True)
                    try:
                        cuando = date(a, m, d) if a else proxima_fecha(datos, date.today())[0]
                        if cuando:
                            vista_cal.ir_a(cuando)
                    except ValueError:
                        pass
                    mostrar_fechas()
                    return
                nueva = {"nombre": nombre.value.strip(), "dia": d, "mes": m}
                if a is not None:
                    nueva["anio"] = a
                if (mensaje.value or "").strip():
                    nueva["mensaje"] = mensaje.value.strip()
                if hay_google and a_google.value:
                    if color_elegido["id"]:
                        nueva["color"] = color_elegido["id"]
                    if destino:
                        nueva["calendario"] = destino
                fechas_usuario.append(nueva)
                await guardar_fechas()
                page.pop_dialog()
                google["mensaje"] = google["aviso"] = ""
                if conectado() and a_google.value:
                    await subir_a_google(nueva)
                mostrar_fechas()
                return
            page.update()

        def cancelar(ev):
            page.pop_dialog()

        dialogo = ft.AlertDialog(
            modal=True, scrollable=True,
            title=ft.Text("Nueva fecha o evento"),
            content=ft.Column(
                [tipo, nombre, ft.Row([dia, mes, anio], spacing=8), hora, repetir, mensaje,
                 a_google, calendario_destino, titulo_color, selector_color, error],
                tight=True, width=320, spacing=10,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=cancelar),
                ft.TextButton("Guardar", on_click=guardar_nueva),
            ],
        )
        page.show_dialog(dialogo)

    vista_cal = calendario.VistaCalendario(
        actualizar, todas_las_fechas, eventos_para_calendario, al_cambiar_mes=pedir_mes,
        al_borrar_evento=pedir_borrar_evento)

    def construir_fechas():
        hoy = date.today()
        orden = sorted(todas_las_fechas(), key=lambda x: proxima_fecha(x, hoy)[1])

        def tocar(f):
            objetivo = proxima_fecha(f, hoy)[0]
            return lambda e: vista_cal.ir_a(objetivo)

        filas = [tarjeta_fecha(f, hoy, f in fechas_usuario, ancho=None, al_tocar=tocar(f))
                 for f in orden]
        vista_cal.pintar()
        # En pantallas anchas (ordenador, iPad) las fechas van al lado; en el móvil, debajo.
        panel_calendario = ft.Container(vista_cal.control, col={"xs": 12, "md": 7})
        panel_fechas = ft.Container(
            ft.Column(
                [ft.Text("Fechas especiales", size=20, weight=ft.FontWeight.BOLD,
                         color=reloj.color), *filas],
                spacing=10),
            col={"xs": 12, "md": 5},
        )
        return ft.Column(
            [
                ft.Container(height=18),
                ft.Text("Nuestras fechas", size=26, weight=ft.FontWeight.BOLD,
                        color=reloj.color),
                bloque_google(),
                *([bloque_calendarios()] if bloque_calendarios() is not None else []),
                ft.Button("Añadir fecha o evento", icon=ft.Icons.ADD, on_click=abrir_dialogo_fecha),
                ft.Container(
                    ft.ResponsiveRow([panel_calendario, panel_fechas], spacing=14, run_spacing=14),
                    width=max(300, min((page.width or 400) - 24, 1000)),
                ),
                ft.Container(height=6),
                *lista_eventos_google(),
                ft.Container(height=16),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=12,
        )

    cuerpo = ft.Container(content=pantalla_minion, expand=True)

    # --- chat ---
    def contexto_chat():
        hoy = date.today()
        frases_estado = {
            "dormido": "Tengo sueñecito, pero contigo siempre despierto.",
            "hambriento": "¡Tengo hambre! Un platanito sería perfecto.",
            "triste": "Estoy un poquito triste, necesito mimos.",
            "feliz": "¡Feliz como una perdiz! Contigo siempre.",
        }
        proximas = sorted(todas_las_fechas(), key=lambda f: proxima_fecha(f, hoy)[1])[:3]
        fechas = " ".join(f"{f['nombre']}: {texto_cuenta_atras(f, hoy)}." for f in proximas)
        tiempo = ""
        d = sesion["clima"]
        if d:
            tiempo = (f"{round(d['temp'])}°, {d['categoria']} (máx {round(d['tmax'])}°, "
                      f"mín {round(d['tmin'])}°, prob. de lluvia {d['prob']}%)")
        return {"estado": frases_estado[estado.humor], "fechas": fechas, "tiempo": tiempo}

    async def bob_dice_del_chat(texto):
        page.run_task(minion.rebotar, 1)

    pantalla_chat = chat.PantallaChat(
        actualizar, leer_texto, guardar_texto, contexto_chat, reloj.color,
        al_hablar=bob_dice_del_chat,
    )
    await pantalla_chat.cargar()

    def mostrar_fechas():
        sesion["pantalla"] = 1
        cuerpo.content = construir_fechas()
        page.update()

    juego_actual = {"obj": None}

    def detener_juego():
        if juego_actual["obj"] is not None:
            juego_actual["obj"].detener()
            juego_actual["obj"] = None

    def al_cambiar_tamano(e=None):
        # recoloca el calendario y las fechas (al lado o debajo) cuando cambia el tamaño
        if sesion["pantalla"] == 1:
            cuerpo.content = construir_fechas()
            page.update()

    page.on_resize = al_cambiar_tamano

    def cambiar_pantalla(e):
        detener_juego()
        if e.control.selected_index == 0:
            sesion["pantalla"] = 0
            cuerpo.content = pantalla_minion
            page.update()
        elif e.control.selected_index == 1:
            mostrar_fechas()
            if conectado():
                page.run_task(sincronizar_google)
        else:
            sesion["pantalla"] = 3
            cuerpo.content = pantalla_chat.control
            page.update()

    navegacion = ft.NavigationBar(
        selected_index=0,
        on_change=cambiar_pantalla,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.PETS, label="Minion"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="Fechas"),
            ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE, label="Chat"),
        ],
    )

    # --- juegos ---
    def volver_a_minion():
        detener_juego()
        sesion["pantalla"] = 0
        navegacion.selected_index = 0
        cuerpo.content = pantalla_minion
        page.update()

    def volver_al_menu(e=None):
        detener_juego()
        sesion["pantalla"] = 2
        cuerpo.content = menu_juegos.control
        page.update()

    async def terminar_juego(texto, puntos):
        estado.carino = limitar(estado.carino + puntos)
        estado.hambre = limitar(estado.hambre - 3)
        refrescar_barras()
        await guardar()
        volver_a_minion()
        minion.poner_humor("feliz", riendo=True)
        page.run_task(minion.rebotar, 3)
        await bocadillo.decir(texto, mantener=5)
        minion.poner_humor(estado.humor)

    async def elegir_juego(clave):
        detener_juego()
        clases = {"memoria": JuegoMemoria, "platanos": JuegoPlatanos, "ppt": JuegoPPT}
        juego = clases[clave](actualizar, terminar_juego, volver_al_menu)
        juego_actual["obj"] = juego
        sesion["pantalla"] = 2
        cuerpo.content = juego.control
        page.update()
        page.run_task(juego.iniciar)

    menu_juegos = MenuJuegos(elegir_juego, volver_a_minion)

    page.add(
        ft.Column(
            [
                ft.Stack(
                    [fondo, efectos.control, ft.SafeArea(content=cuerpo, expand=True)],
                    expand=True,
                ),
                navegacion,
            ],
            spacing=0, expand=True,
        )
    )

    # --- estado inicial: dormido hasta el primer toque ---
    actualizar_reloj()
    refrescar_barras()
    minion.poner_humor("dormido")
    await bocadillo.decir(config.FRASE_INTRO, mantener=None)

    # --- bucles de vida ---
    async def bucle_respiracion():
        dentro = False
        while True:
            await asyncio.sleep(1.4)
            dentro = not dentro
            minion.respirar(dentro)

    async def bucle_parpadeo():
        while True:
            await asyncio.sleep(random.uniform(2.5, 5.5))
            await minion.parpadear()

    async def bucle_tiempo():
        while True:
            await asyncio.sleep(30)
            humor_antes = estado.humor
            estado.avanzar()
            refrescar_barras()
            if estado.humor != humor_antes and not sesion["intro"]:
                minion.poner_humor(estado.humor)
            await guardar()
            if config.CLIMA_ACTIVO and not config.MODO_PRUEBA:
                await asegurar_clima()
            await sincronizar_google()
            actualizar()

    async def bucle_reloj():
        while True:
            await asyncio.sleep(1)
            if actualizar_reloj():
                actualizar()

    async def bucle_efectos():
        while True:
            await asyncio.sleep(0.1)
            if efectos.anima and efectos.categoria:
                efectos.tick()
                actualizar()

    async def carga_inicial_clima():
        if config.CLIMA_ACTIVO:
            await asegurar_clima()

    page.run_task(bucle_respiracion)
    page.run_task(bucle_parpadeo)
    page.run_task(bucle_tiempo)
    page.run_task(bucle_reloj)
    page.run_task(bucle_efectos)
    page.run_task(carga_inicial_clima)
    page.run_task(conectar_google_inicial)


if __name__ == "__main__":
    # "python main.py"            -> se abre en el navegador (no usa flet.exe)
    # "python main.py --ventana"  -> ventana de escritorio
    # En un servidor (Render, etc.) la plataforma define la variable PORT: se arranca sin abrir
    # navegador y escuchando hacia fuera.
    import os
    import sys

    if os.environ.get("PORT"):
        ft.run(main, view=None, host="0.0.0.0", port=int(os.environ["PORT"]))
    else:
        vista = ft.AppView.FLET_APP if "--ventana" in sys.argv else ft.AppView.WEB_BROWSER
        ft.run(main, view=vista, port=8550)
