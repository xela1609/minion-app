"""
Minijuegos para el botón "Jugar":
  - Memoria de parejas
  - Atrapa los plátanos
  - Piedra, papel o tijera
Cada juego es una clase con .control (lo que se muestra) y iniciar() / detener().
Al acabar llaman a al_terminar(texto_para_el_minion, puntos_de_cariño).
"""
import asyncio
import random

import flet as ft

TEXTO = "#2B2B2B"


def _titulo(texto):
    return ft.Text(texto, size=22, weight=ft.FontWeight.BOLD, color=TEXTO,
                   text_align=ft.TextAlign.CENTER)


def _boton_volver(al_volver):
    return ft.TextButton("Volver", icon=ft.Icons.ARROW_BACK, on_click=al_volver)


def _tarjeta(contenido, ancho=340):
    return ft.Container(
        content=contenido, bgcolor="#EFFFFFFF", border_radius=18, width=ancho,
        padding=ft.Padding.all(14),
        shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
    )


# =====================================================================
# Manos de Minion (guante negro y muñeca amarilla) para piedra, papel y tijera
# Se dibujan con formas; el lienzo base mide 100 x 110.
# =====================================================================
GUANTE = "#262626"
GUANTE_CLARO = "#454545"
MUNECA = "#FFD83B"


def formas_mano(gesto):
    """Lista de formas (x, y, ancho, alto, radio, color, giro, pivote) de cada gesto."""
    def f(x, y, w, h, r, c, giro=0.0, pivote="centro"):
        return dict(x=x, y=y, w=w, h=h, r=r, c=c, giro=giro, pivote=pivote)

    muneca = f(32, 88, 36, 22, 6, MUNECA)
    # Los Minions tienen 3 dedos en total (2 dedos + el pulgar)
    if gesto == "papel":
        return [
            muneca,
            f(56, 4, 20, 68, 10, GUANTE, 0.05, "abajo"),      # dedo 2
            f(34, 4, 20, 68, 10, GUANTE, -0.05, "abajo"),     # dedo 1
            f(30, 56, 16, 34, 8, GUANTE, -0.9, "abajo"),      # pulgar abierto
            f(20, 50, 64, 50, 24, GUANTE),                    # palma
            f(34, 60, 12, 24, 6, GUANTE_CLARO),               # brillo
        ]
    if gesto == "piedra":
        return [
            muneca,
            f(16, 40, 70, 58, 26, GUANTE),                    # puño
            f(18, 32, 33, 26, 12, GUANTE),                    # nudillos
            f(51, 32, 33, 26, 12, GUANTE),
            f(20, 50, 31, 28, 12, GUANTE_CLARO),              # dedos doblados
            f(53, 50, 31, 28, 12, GUANTE_CLARO),
            f(22, 68, 48, 17, 8.5, GUANTE, -0.1),             # pulgar cruzado
            f(30, 72, 28, 4, 2, GUANTE_CLARO, -0.1),          # brillo
        ]
    return [                                                   # tijera
        muneca,
        f(26, 2, 20, 66, 10, GUANTE, -0.22, "abajo"),         # dedo 1 estirado
        f(50, 2, 20, 66, 10, GUANTE, 0.22, "abajo"),          # dedo 2 estirado
        f(20, 52, 64, 48, 22, GUANTE),                        # palma
        f(24, 70, 40, 16, 8, GUANTE_CLARO, -0.15),            # pulgar doblado sobre la palma
    ]


def dibujo_mano(gesto, escala=1.0):
    """Control de Flet con la mano dibujada. gesto: 'piedra', 'papel' o 'tijera'."""
    e = escala
    piezas = []
    for p in formas_mano(gesto):
        giro = None
        if p["giro"]:
            punto = ft.Alignment.BOTTOM_CENTER if p["pivote"] == "abajo" else ft.Alignment.CENTER
            giro = ft.Rotate(angle=p["giro"], alignment=punto)
        piezas.append(ft.Container(
            left=p["x"] * e, top=p["y"] * e, width=p["w"] * e, height=p["h"] * e,
            bgcolor=p["c"], border_radius=p["r"] * e, rotate=giro,
        ))
    return ft.Stack(piezas, width=100 * e, height=110 * e)


# =====================================================================
# Menú
# =====================================================================
class MenuJuegos:
    def __init__(self, al_elegir, al_volver):
        def opcion(icono, nombre, descripcion, clave):
            async def pulsar(e):
                await al_elegir(clave)

            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icono, size=34, color="#C2185B"),
                        ft.Column(
                            [ft.Text(nombre, size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
                             ft.Text(descripcion, size=13, color="#6A6A6A")],
                            spacing=1, expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                ),
                bgcolor="#EFFFFFFF", border_radius=18, width=340, ink=True, on_click=pulsar,
                padding=ft.Padding.all(16),
                shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
            )

        self.control = ft.Column(
            [
                ft.Container(height=14),
                _titulo("¿A qué jugamos?"),
                opcion(ft.Icons.GRID_VIEW, "Memoria", "Encuentra las parejas", "memoria"),
                opcion(ft.Icons.SPORTS_BASEBALL, "Atrapa los plátanos",
                       "Toca los plátanos y esquiva las bombas", "platanos"),
                opcion(ft.Icons.CONTENT_CUT, "Piedra, papel o tijera",
                       "El primero en ganar 3 rondas", "ppt"),
                _boton_volver(al_volver),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=12,
        )


# =====================================================================
# 1) Memoria de parejas
# =====================================================================
class JuegoMemoria:
    ICONOS = [ft.Icons.FAVORITE, ft.Icons.STAR, ft.Icons.CAKE,
              ft.Icons.MUSIC_NOTE, ft.Icons.PETS, ft.Icons.WB_SUNNY]

    def __init__(self, actualizar, al_terminar, al_volver):
        self.actualizar = actualizar
        self.al_terminar = al_terminar
        self.al_volver = al_volver
        self.activo = False
        self.control = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    async def iniciar(self):
        self.activo = True
        self.cartas = self.ICONOS * 2
        random.shuffle(self.cartas)
        self.visibles = []
        self.resueltas = set()
        self.bloqueado = False
        self.intentos = 0
        self.info = ft.Text("Intentos: 0", size=16, color=TEXTO, weight=ft.FontWeight.W_600)
        self.casillas = []
        filas = []
        for fila in range(4):
            fila_ctrl = []
            for col in range(3):
                i = fila * 3 + col
                casilla = ft.Container(
                    width=88, height=88, border_radius=16, ink=True,
                    alignment=ft.Alignment.CENTER,
                    on_click=self._crear_click(i),
                )
                self.casillas.append(casilla)
                fila_ctrl.append(casilla)
                self._dibujar(i)
            filas.append(ft.Row(fila_ctrl, alignment=ft.MainAxisAlignment.CENTER, spacing=10))
        self.control.controls = [
            ft.Container(height=10), _titulo("Memoria"), self.info, *filas,
            _boton_volver(self.al_volver),
        ]
        self.actualizar()

    def detener(self):
        self.activo = False

    def _crear_click(self, i):
        async def pulsar(e):
            await self._voltear(i)
        return pulsar

    def _dibujar(self, i):
        casilla = self.casillas[i]
        if i in self.resueltas or i in self.visibles:
            casilla.bgcolor = "#FFF3B0" if i in self.resueltas else "white"
            casilla.content = ft.Icon(self.cartas[i], size=40, color="#C2185B")
        else:
            casilla.bgcolor = "#F2B705"
            casilla.content = ft.Icon(ft.Icons.HELP_OUTLINE, size=36, color="white")

    async def _voltear(self, i):
        if (not self.activo or self.bloqueado
                or i in self.resueltas or i in self.visibles):
            return
        self.visibles.append(i)
        self._dibujar(i)
        self.actualizar()
        if len(self.visibles) < 2:
            return
        self.intentos += 1
        self.info.value = f"Intentos: {self.intentos}"
        a, b = self.visibles
        if self.cartas[a] == self.cartas[b]:
            self.resueltas.update((a, b))
            self.visibles = []
            self._dibujar(a)
            self._dibujar(b)
            self.actualizar()
            if len(self.resueltas) == len(self.cartas):
                self.activo = False
                puntos = 14 if self.intentos <= 9 else 9
                await self.al_terminar(
                    f"¡Las encontraste todas en {self.intentos} intentos! ¡Qué lista!", puntos)
        else:
            self.bloqueado = True
            self.actualizar()
            await asyncio.sleep(0.8)
            self.visibles = []
            self._dibujar(a)
            self._dibujar(b)
            self.bloqueado = False
            self.actualizar()


# =====================================================================
# 2) Atrapa los plátanos
# =====================================================================
class JuegoPlatanos:
    ANCHO = 320
    ALTO = 380
    DURACION = 25      # segundos
    PASO = 0.08        # segundos entre fotogramas

    def __init__(self, actualizar, al_terminar, al_volver):
        self.actualizar = actualizar
        self.al_terminar = al_terminar
        self.al_volver = al_volver
        self.activo = False
        self.control = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def detener(self):
        self.activo = False

    def _dibujo(self, bomba):
        if bomba:
            return ft.Container(
                width=36, height=36, border_radius=18, bgcolor="#222222",
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.CLOSE, size=20, color="#FF5252"),
            )
        return ft.Container(
            width=22, height=50, border_radius=14, bgcolor="#FFD83B",
            border=ft.Border.all(2, "#C99A00"), rotate=0.5,
        )

    async def iniciar(self):
        self.activo = True
        self.puntos = 0
        self.items = []
        self.restante = float(self.DURACION)
        self.marcador = ft.Text("Plátanos: 0", size=18, weight=ft.FontWeight.BOLD, color=TEXTO)
        self.reloj = ft.Text(f"{self.DURACION} s", size=18, color="#C2185B",
                             weight=ft.FontWeight.BOLD)
        self.area = ft.Stack(width=self.ANCHO, height=self.ALTO)
        campo = ft.Container(
            content=self.area, width=self.ANCHO, height=self.ALTO, border_radius=18,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                colors=["#BFE6FF", "#FFF4C2"]),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        self.control.controls = [
            ft.Container(height=8), _titulo("Atrapa los plátanos"),
            ft.Row([self.marcador, self.reloj], alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                   width=self.ANCHO),
            campo, _boton_volver(self.al_volver),
        ]
        self.actualizar()
        await self._bucle()

    def _crear_toque(self, item):
        async def tocar(e):
            if not self.activo or item not in self.items:
                return
            self.items.remove(item)
            self.area.controls.remove(item["ctrl"])
            self.puntos = max(0, self.puntos - 2) if item["bomba"] else self.puntos + 1
            self.marcador.value = f"Plátanos: {self.puntos}"
            self.actualizar()
        return tocar

    def _nuevo(self):
        bomba = random.random() < 0.18
        item = {"bomba": bomba, "y": -60.0, "vy": random.uniform(7, 12)}
        x = random.uniform(0, self.ANCHO - 56)
        item["ctrl"] = ft.Container(
            left=x, top=item["y"], width=56, height=56, alignment=ft.Alignment.CENTER,
            content=self._dibujo(bomba), on_click=self._crear_toque(item),
        )
        self.items.append(item)
        self.area.controls.append(item["ctrl"])

    async def _bucle(self):
        siguiente = 0.0
        while self.activo and self.restante > 0:
            await asyncio.sleep(self.PASO)
            if not self.activo:
                return
            self.restante -= self.PASO
            siguiente -= self.PASO
            if siguiente <= 0:
                self._nuevo()
                siguiente = random.uniform(0.45, 0.8)
            for item in list(self.items):
                item["y"] += item["vy"]
                item["ctrl"].top = item["y"]
                if item["y"] > self.ALTO:
                    self.items.remove(item)
                    self.area.controls.remove(item["ctrl"])
            self.reloj.value = f"{max(0, int(self.restante) + 1)} s"
            self.actualizar()
        if self.activo:
            self.activo = False
            puntos = 14 if self.puntos >= 15 else (10 if self.puntos >= 8 else 6)
            await self.al_terminar(
                f"¡Atrapaste {self.puntos} plátanos! ¡Banaaana!", puntos)


# =====================================================================
# 3) Piedra, papel o tijera
# =====================================================================
class JuegoPPT:
    OPCIONES = {
        "piedra": ("Piedra", ft.Icons.CIRCLE),
        "papel": ("Papel", ft.Icons.DESCRIPTION),
        "tijera": ("Tijera", ft.Icons.CONTENT_CUT),
    }
    GANA_A = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}
    META = 3

    def __init__(self, actualizar, al_terminar, al_volver):
        self.actualizar = actualizar
        self.al_terminar = al_terminar
        self.al_volver = al_volver
        self.activo = False
        self.control = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 scroll=ft.ScrollMode.AUTO, expand=True, spacing=12)

    def detener(self):
        self.activo = False

    async def iniciar(self):
        self.activo = True
        self.tu, self.minion = 0, 0
        self.resultado = ft.Text("¡Elige!", size=18, color=TEXTO, weight=ft.FontWeight.W_600,
                                 text_align=ft.TextAlign.CENTER)
        self.marcador = ft.Text("Tú 0 - 0 Minion", size=20, weight=ft.FontWeight.BOLD,
                                color="#C2185B")
        self.mano_tu = ft.Container(width=100, height=110, alignment=ft.Alignment.CENTER,
                                    content=ft.Text("?", size=40, color="#9A9A9A"))
        self.mano_rival = ft.Container(width=100, height=110, alignment=ft.Alignment.CENTER,
                                       content=ft.Text("?", size=40, color="#9A9A9A"))
        mesa = ft.Row(
            [
                ft.Column([self.mano_tu, ft.Text("Tú", size=14, color=TEXTO,
                                                 weight=ft.FontWeight.W_600)],
                          spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text("vs", size=18, color="#9A9A9A"),
                ft.Column([self.mano_rival, ft.Text("Minion", size=14, color=TEXTO,
                                                    weight=ft.FontWeight.W_600)],
                          spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            alignment=ft.MainAxisAlignment.CENTER, spacing=22,
        )

        def boton(clave):
            nombre, icono = self.OPCIONES[clave]

            async def jugar(e):
                await self._ronda(clave)

            return ft.Container(
                content=ft.Column([dibujo_mano(clave, 0.62),
                                   ft.Text(nombre, size=13, color=TEXTO)],
                                  spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=96, padding=ft.Padding.symmetric(vertical=12), bgcolor="#EFFFFFFF",
                border_radius=18, ink=True, on_click=jugar,
                shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
            )

        self.control.controls = [
            ft.Container(height=14), _titulo("Piedra, papel o tijera"),
            self.marcador,
            _tarjeta(ft.Column([mesa, self.resultado], spacing=6,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER), 320),
            ft.Row([boton(c) for c in self.OPCIONES], alignment=ft.MainAxisAlignment.CENTER,
                   spacing=10),
            _boton_volver(self.al_volver),
        ]
        self.actualizar()

    async def _ronda(self, eleccion):
        if not self.activo:
            return
        rival = random.choice(list(self.OPCIONES))
        nombre_tu = self.OPCIONES[eleccion][0]
        nombre_rival = self.OPCIONES[rival][0]
        self.mano_tu.content = dibujo_mano(eleccion, 0.9)
        self.mano_rival.content = dibujo_mano(rival, 0.9)
        if eleccion == rival:
            self.resultado.value = f"Tú: {nombre_tu}. Yo: {nombre_rival}. ¡Empate!"
        elif self.GANA_A[eleccion] == rival:
            self.tu += 1
            self.resultado.value = f"Tú: {nombre_tu}. Yo: {nombre_rival}. ¡Punto para ti!"
        else:
            self.minion += 1
            self.resultado.value = f"Tú: {nombre_tu}. Yo: {nombre_rival}. ¡Punto para mí! Hihi"
        self.marcador.value = f"Tú {self.tu} - {self.minion} Minion"
        self.actualizar()
        if self.tu >= self.META or self.minion >= self.META:
            self.activo = False
            if self.tu > self.minion:
                await self.al_terminar("¡Me ganaste! Eres la mejor jugadora.", 12)
            else:
                await self.al_terminar("¡Te gané! Hihi... pero la revancha es tuya.", 8)
