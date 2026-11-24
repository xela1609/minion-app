"""
Capa de animaciones del tiempo: sol, luna y estrellas, nubes, lluvia, nieve, niebla y tormenta.
Todo son formas de Flet colocadas por posición relativa (de -1 a 1), así que se adapta a cualquier pantalla.
Se mueve llamando a tick() unas 10 veces por segundo desde main.py.
"""
import math
import random

import flet as ft


def _capa(x, y, contenido):
    """Coloca algo en una posición relativa de la pantalla (x, y entre -1 y 1)."""
    return ft.Container(
        expand=True,
        alignment=ft.Alignment(x, y),
        content=contenido,
        ignore_interactions=True,
    )


def _nube(escala, color, opacidad=1.0):
    e = escala

    def parte(left, top, ancho, alto):
        return ft.Container(
            left=left, top=top, width=ancho, height=alto,
            bgcolor=color, border_radius=min(ancho, alto) / 2,
        )

    return ft.Container(
        width=140 * e, height=64 * e, opacity=opacidad,
        content=ft.Stack(
            [
                parte(0, 26 * e, 140 * e, 38 * e),
                parte(18 * e, 14 * e, 50 * e, 50 * e),
                parte(50 * e, 0, 62 * e, 62 * e),
            ],
            width=140 * e, height=64 * e,
        ),
    )


class EfectoClima:
    def __init__(self):
        self.control = ft.Stack(expand=True)
        self.categoria = None
        self.noche = False
        self.anima = False
        self._t = 0
        self._limpiar()

    def _limpiar(self):
        self._nubes = []
        self._gotas = []
        self._copos = []
        self._bandas = []
        self._estrellas = []
        self._sol = None
        self._flash = None
        self._flash_activo = False

    # ------------------------------------------------------------------
    def poner(self, categoria, noche):
        """Monta la escena. Devuelve True si ha cambiado algo."""
        if (categoria, noche) == (self.categoria, self.noche):
            return False
        self.categoria, self.noche = categoria, noche
        self._limpiar()
        capas = []

        # --- astros ---
        if categoria in ("despejado", "parcial"):
            if noche:
                capas.extend(self._estrellas_y_luna(14 if categoria == "despejado" else 6))
            else:
                self._sol = ft.Container(
                    width=92, height=92, border_radius=46, bgcolor="#FFD54F",
                    scale=1.0, animate_scale=ft.Animation(1500, ft.AnimationCurve.EASE_IN_OUT),
                    shadow=ft.BoxShadow(blur_radius=70, spread_radius=22, color="#99FFC107"),
                )
                capas.append(_capa(0.72, -0.82, self._sol))

        # --- nubes ---
        color_nube, cantidad = self._config_nubes(categoria, noche)
        for i in range(cantidad):
            escala = random.uniform(0.8, 1.5)
            x = -1.4 + i * (2.8 / max(cantidad, 1)) + random.uniform(-0.2, 0.2)
            y = random.uniform(-0.95, -0.35)
            nube = _capa(x, y, _nube(escala, color_nube, 0.92))
            self._nubes.append({"ctrl": nube, "x": x, "y": y, "vx": random.uniform(0.003, 0.008)})
            capas.append(nube)

        # --- niebla ---
        if categoria == "niebla":
            for i in range(4):
                y = -0.6 + i * 0.4
                x = random.uniform(-0.3, 0.3)
                banda = _capa(
                    x, y,
                    ft.Container(width=520, height=70, border_radius=35,
                                 bgcolor="#66FFFFFF" if not noche else "#33FFFFFF"),
                )
                self._bandas.append({"ctrl": banda, "x": x, "y": y,
                                     "vx": random.choice((-1, 1)) * random.uniform(0.002, 0.004)})
                capas.append(banda)

        # --- lluvia / tormenta ---
        if categoria in ("lluvia", "tormenta"):
            for _ in range(26 if categoria == "tormenta" else 18):
                gota = ft.Container(width=2, height=16, bgcolor="#D6EAFF", opacity=0.75,
                                    border_radius=1, rotate=0.2)
                x, y = random.uniform(-1.1, 1.1), random.uniform(-1.1, 1.1)
                capa = _capa(x, y, gota)
                self._gotas.append({"ctrl": capa, "x": x, "y": y,
                                    "vy": random.uniform(0.07, 0.11), "vx": -0.012})
                capas.append(capa)

        # --- nieve ---
        if categoria == "nieve":
            for _ in range(24):
                tam = random.uniform(5, 10)
                copo = ft.Container(width=tam, height=tam, border_radius=tam / 2,
                                    bgcolor="white", opacity=0.9)
                x, y = random.uniform(-1, 1), random.uniform(-1.1, 1.1)
                capa = _capa(x, y, copo)
                self._copos.append({"ctrl": capa, "x": x, "y": y,
                                    "vy": random.uniform(0.012, 0.026),
                                    "fase": random.uniform(0, 6.28)})
                capas.append(capa)

        # --- relámpago ---
        if categoria == "tormenta":
            self._flash = ft.Container(
                expand=True, bgcolor="white", opacity=0,
                animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
                ignore_interactions=True,
            )
            capas.append(self._flash)

        self.control.controls = capas
        self.anima = True
        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _config_nubes(categoria, noche):
        if categoria == "parcial":
            return ("#7C88AD" if noche else "#FFFFFF"), 2
        if categoria == "nublado":
            return ("#7C88AD" if noche else "#DDE3EA"), 4
        if categoria == "niebla":
            return ("#7C88AD" if noche else "#E6EBF0"), 2
        if categoria == "lluvia":
            return ("#68748F" if noche else "#8793A6"), 3
        if categoria == "tormenta":
            return ("#434B60" if noche else "#4F586B"), 4
        if categoria == "nieve":
            return ("#7C88AD" if noche else "#E8EEF4"), 3
        return "#FFFFFF", 0

    def _estrellas_y_luna(self, cuantas):
        capas = []
        luna = ft.Container(
            width=62, height=62, border_radius=31, bgcolor="#F4F1DE",
            shadow=ft.BoxShadow(blur_radius=40, spread_radius=8, color="#66F4F1DE"),
            content=ft.Stack([
                ft.Container(left=14, top=14, width=12, height=12, border_radius=6, bgcolor="#E3DFC4"),
                ft.Container(left=36, top=30, width=9, height=9, border_radius=5, bgcolor="#E3DFC4"),
            ]),
        )
        capas.append(_capa(0.72, -0.8, luna))
        for _ in range(cuantas):
            tam = random.uniform(2, 4)
            estrella = ft.Container(
                width=tam, height=tam, border_radius=tam / 2, bgcolor="white",
                opacity=random.uniform(0.4, 1.0), animate_opacity=600,
            )
            capa = _capa(random.uniform(-0.95, 0.5), random.uniform(-0.95, -0.2), estrella)
            self._estrellas.append(estrella)
            capas.append(capa)
        return capas

    # ------------------------------------------------------------------
    def tick(self):
        """Avanza un fotograma (llamar unas 10 veces por segundo)."""
        self._t += 1

        for n in self._nubes:
            n["x"] += n["vx"]
            if n["x"] > 1.5:
                n["x"] = -1.5
            n["ctrl"].alignment = ft.Alignment(n["x"], n["y"])

        for g in self._gotas:
            g["y"] += g["vy"]
            g["x"] += g["vx"]
            if g["y"] > 1.1:
                g["y"] = -1.1
                g["x"] = random.uniform(-1.0, 1.2)
            g["ctrl"].alignment = ft.Alignment(g["x"], g["y"])

        for c in self._copos:
            c["y"] += c["vy"]
            c["x"] += math.sin(self._t * 0.1 + c["fase"]) * 0.006
            if c["y"] > 1.1:
                c["y"] = -1.1
                c["x"] = random.uniform(-1, 1)
            c["ctrl"].alignment = ft.Alignment(c["x"], c["y"])

        for b in self._bandas:
            b["x"] += b["vx"]
            if abs(b["x"]) > 0.35:
                b["vx"] = -b["vx"]
            b["ctrl"].alignment = ft.Alignment(b["x"], b["y"])

        if self._sol is not None and self._t % 15 == 0:
            self._sol.scale = 1.08 if self._sol.scale == 1.0 else 1.0

        if self._estrellas and self._t % 4 == 0:
            e = random.choice(self._estrellas)
            e.opacity = random.uniform(0.25, 1.0)

        if self._flash is not None:
            if self._flash_activo:
                self._flash.opacity = 0
                self._flash_activo = False
            elif random.random() < 0.015:
                self._flash.opacity = 0.6
                self._flash_activo = True
