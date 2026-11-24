"""Personaliza la página web que sirve Flet: nombre, icono de la pantalla de inicio y manifest.
Se ejecuta una vez al construir el servidor (ver Dockerfile). En tu PC no hace falta."""
import importlib.util
import os
import shutil

import config

origen = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_overrides")
paquete = importlib.util.find_spec("flet_web")
if paquete is None or not paquete.origin:
    raise SystemExit("No encuentro flet_web: instala los requisitos primero.")
destino = os.path.join(os.path.dirname(paquete.origin), "web")

# 1) iconos y manifest propios
for carpeta, _, archivos in os.walk(origen):
    for archivo in archivos:
        desde = os.path.join(carpeta, archivo)
        hacia = os.path.join(destino, os.path.relpath(desde, origen))
        os.makedirs(os.path.dirname(hacia), exist_ok=True)
        shutil.copyfile(desde, hacia)

# 2) nombre de la app en index.html (lo que ve ella al "Añadir a pantalla de inicio")
ruta = os.path.join(destino, "index.html")
html = open(ruta, encoding="utf-8").read()
cambios = [
    ('<meta name="description" content="Flet application.">',
     f'<meta name="description" content="{config.NOMBRE_APP}">'),
    ('<meta name="apple-mobile-web-app-title" content="Flet">',
     f'<meta name="apple-mobile-web-app-title" content="{config.NOMBRE_APP}">'),
    ("<title>Flet</title>", f"<title>{config.NOMBRE_APP}</title>"),
]
for viejo, nuevo in cambios:
    if viejo not in html:
        print("AVISO: no encontré esto en index.html (¿otra versión de Flet?):", viejo)
    html = html.replace(viejo, nuevo)
open(ruta, "w", encoding="utf-8").write(html)
print("Página web personalizada en", destino)
