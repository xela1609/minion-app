"""Calendario mensual de verdad, con vuestras fechas especiales marcadas.

- Cuadrícula Lunes-Domingo, flechas para cambiar de mes, botón «Hoy».
- Día de hoy con círculo; fechas especiales en rosa con corazón; eventos de Google con un punto
  del mismo color que tienen en Google Calendar (el suyo o el de su calendario).
- Al tocar un día se ve debajo qué hay ese día.
"""
import calendar as cal
from datetime import date

import flet as ft

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["L", "M", "X", "J", "V", "S", "D"]

ROSA = "#C2185B"
ROSA_CLARO = "#F8BBD0"
TEXTO = "#2B2B2B"
GRIS = "#6A6A6A"
AZUL = "#1E88E5"


class VistaCalendario:
    def __init__(self, actualizar, fechas_fn, eventos_fn, al_cambiar_mes=None,
                 al_borrar_evento=None):
        """
        actualizar: función que refresca la pantalla (page.update)
        fechas_fn:  devuelve la lista de fechas especiales [{"nombre","dia","mes",...}]
        eventos_fn: devuelve los eventos de Google
                    [{"fecha": date, "titulo", "hora", "especial", "de_la_app", "color", "calendario"}]
        al_borrar_evento: función(evento) para borrar un evento normal creado por la app
        """
        self.actualizar = actualizar
        self.fechas_fn = fechas_fn
        self.eventos_fn = eventos_fn
        self.al_cambiar_mes = al_cambiar_mes   # se llama con (año, mes) al mostrar un mes
        self.al_borrar_evento = al_borrar_evento
        hoy = date.today()
        self.anio, self.mes = hoy.year, hoy.month
        self.sel = hoy
        self.control = ft.Container(
            bgcolor="#EFFFFFFF", border_radius=18, padding=ft.Padding.all(12),
            shadow=ft.BoxShadow(blur_radius=8, color="#22000000", offset=ft.Offset(0, 3)),
        )
        self.pintar()

    # ---------- datos ----------
    def _especiales_de(self, d):
        return [f for f in self.fechas_fn() if f["dia"] == d.day and f["mes"] == d.month]

    def _eventos_de(self, d):
        # las fechas especiales ya se muestran aparte (corazón): no se repiten como evento
        vistos, salida = set(), []
        for e in self.eventos_fn():
            if e["fecha"] != d or e.get("especial"):
                continue
            clave = (e.get("id"), e["fecha"], e["titulo"])
            if clave not in vistos:
                vistos.add(clave)
                salida.append(e)
        return salida

    # ---------- navegación ----------
    def cambiar_mes(self, delta):
        m = self.mes - 1 + delta
        self.anio += m // 12
        self.mes = m % 12 + 1
        self.pintar()
        self.actualizar()
        self._avisar_mes()

    def ir_a_hoy(self, e=None):
        self.ir_a(date.today())

    def ir_a(self, d):
        """Salta al mes de una fecha y la selecciona."""
        self.anio, self.mes, self.sel = d.year, d.month, d
        self.pintar()
        self.actualizar()
        self._avisar_mes()

    def _avisar_mes(self):
        if self.al_cambiar_mes:
            self.al_cambiar_mes(self.anio, self.mes)

    def _seleccionar(self, d):
        self.sel = d
        self.pintar()
        self.actualizar()

    # ---------- dibujo ----------
    def _celda(self, d, hoy):
        especiales = self._especiales_de(d)
        eventos = self._eventos_de(d)
        es_hoy = d == hoy
        es_sel = d == self.sel

        detalles = []
        if especiales:
            detalles.append(ft.Icon(ft.Icons.FAVORITE, size=10, color=ROSA))
        colores = []
        for ev in eventos:
            c = ev.get("color") or AZUL
            if c not in colores:
                colores.append(c)
        for c in colores[:3]:   # como mucho 3 puntos, cada uno del color de su evento
            detalles.append(ft.Container(width=6, height=6, border_radius=3, bgcolor=c))

        color_num = "white" if es_hoy else TEXTO
        numero = ft.Container(
            content=ft.Text(str(d.day), size=14, color=color_num,
                            weight=ft.FontWeight.BOLD if (es_hoy or especiales) else None),
            width=26, height=26, border_radius=13,
            bgcolor=ROSA if es_hoy else None, alignment=ft.Alignment.CENTER,
        )
        return ft.Container(
            content=ft.Column(
                [numero, ft.Row(detalles, spacing=2, alignment=ft.MainAxisAlignment.CENTER,
                                height=10)],
                spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=1, height=48, border_radius=10,
            bgcolor=ROSA_CLARO if especiales else None,
            border=ft.Border.all(2, ROSA) if es_sel else None,
            on_click=lambda e, d=d: self._seleccionar(d),
            ink=True,
        )

    def _detalle(self):
        d = self.sel
        titulo = f"{d.day} de {MESES[d.month - 1]} de {d.year}"
        filas = [ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD, color=TEXTO)]
        especiales = self._especiales_de(d)
        eventos = self._eventos_de(d)
        for f in especiales:
            extra = ""
            if f.get("anio") and d.year > f["anio"]:
                extra = f" · {d.year - f['anio']} años"
            filas.append(ft.Row([ft.Icon(ft.Icons.FAVORITE, size=16, color=ROSA),
                                 ft.Text(f"{f['nombre']}{extra}", size=14, color=TEXTO, expand=True)],
                                spacing=6))
        for ev in eventos:
            hora = f" · {ev['hora']}" if ev.get("hora") else ""
            textos = [ft.Text(f"{ev['titulo']}{hora}", size=14, color=TEXTO)]
            if ev.get("calendario"):
                textos.append(ft.Text(ev["calendario"], size=11, color=GRIS))
            fila = [ft.Container(width=10, height=10, border_radius=5,
                                 bgcolor=ev.get("color") or AZUL),
                    ft.Column(textos, spacing=0, expand=True)]
            if self.al_borrar_evento and ev.get("de_la_app"):
                fila.append(ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, icon_color=GRIS, icon_size=18,
                    tooltip="Borrar este evento",
                    on_click=lambda e, ev=ev: self.al_borrar_evento(ev)))
            filas.append(ft.Row(fila, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER))
        if not especiales and not eventos:
            filas.append(ft.Text("Nada este día.", size=13, color=GRIS))
        return ft.Column(filas, spacing=4)

    def pintar(self):
        hoy = date.today()
        cabecera = ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=ROSA, tooltip="Mes anterior",
                              on_click=lambda e: self.cambiar_mes(-1)),
                ft.Text(f"{MESES[self.mes - 1].capitalize()} {self.anio}", size=20,
                        weight=ft.FontWeight.BOLD, color=TEXTO, expand=True,
                        text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.TODAY, icon_color=ROSA, tooltip="Ir a hoy",
                              on_click=self.ir_a_hoy),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ROSA, tooltip="Mes siguiente",
                              on_click=lambda e: self.cambiar_mes(1)),
            ],
            spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        nombres = ft.Row(
            [ft.Container(ft.Text(n, size=12, color=GRIS, weight=ft.FontWeight.W_600),
                          expand=1, alignment=ft.Alignment.CENTER) for n in DIAS],
            spacing=0,
        )
        semanas = []
        for semana in cal.Calendar(firstweekday=0).monthdatescalendar(self.anio, self.mes):
            celdas = []
            for d in semana:
                if d.month == self.mes:
                    celdas.append(self._celda(d, hoy))
                else:  # días de los meses vecinos, vacíos
                    celdas.append(ft.Container(expand=1, height=48))
            semanas.append(ft.Row(celdas, spacing=2))
        self.control.content = ft.Column(
            [cabecera, nombres, *semanas, ft.Divider(height=8), self._detalle()],
            spacing=2,
        )
