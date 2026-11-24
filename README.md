# Mi Minion (Bob) - Fase 1.5

Tamagotchi + saludo "papoi" + bocadillo + reloj + tiempo + animaciones del clima + fechas.
El Minion es provisional (formas de Flet) y está hecho como Bob; más adelante se cambia por las imágenes finales.

## Ficheros (todos en la misma carpeta, con estos nombres exactos)
- `main.py`             la app
- `config.py`           todo lo personal: nombre, frases, fechas, ciudad, datos del script de Google
- `clima.py`            consulta del tiempo (Open-Meteo, gratis y sin clave)
- `efectos_clima.py`    animaciones: sol, luna, nubes, lluvia, nieve, niebla, tormenta
- `juegos.py`           minijuegos: memoria, atrapa los plátanos, piedra-papel-tijera
- `calendario.py       -> calendario mensual con las fechas especiales marcadas (pestaña Fechas)
- `chat.py              -> chat con Bob (reglas offline + IA gratuita opcional, ver GUIA_CHAT.md)
- google_calendar.py`  conexión con Google Calendar (leer, escribir y borrar eventos)
- `google_script.gs`    script GRATIS de Google Apps Script que se pega en script.google.com
- `GUIA_GOOGLE.md`      cómo conectar el calendario, paso a paso (sin Google Cloud)
- `requirements.txt`

## Probarlo
```bash
pip install -r requirements.txt
python main.py            # se abre en el navegador (sirve si Windows bloquea flet.exe)
```

## Antes de regalarlo (en config.py)
- `NOMBRE_ELLA`
- `CIUDAD`, `LATITUD`, `LONGITUD`: ahora son los de Madrid de ejemplo; pon los de su ciudad
- La fecha de "Nuestro aniversario" (la actual es un ejemplo)

## Probar las animaciones del tiempo
En `config.py` pon `MODO_PRUEBA = True`: aparece un icono arriba a la derecha y cada toque cambia de clima
(despejado, parcial, nublado, niebla, lluvia, nieve, tormenta) y el Minion dice la frase correspondiente.
También puedes fijar uno con `CLIMA_FORZADO = "lluvia"`. Vuelve a poner `False` y `None` al acabar.

## Cómo funciona
- Al abrir, el Minion duerme. Al tocarlo se despierta, saluda con el brazo y dice "papoi".
- El primer saludo de cada día añade el tiempo de hoy. Los siguientes saludos del mismo día no lo repiten.
- El fondo y la animación cambian con la hora y el tiempo; el reloj marca la hora.
- Jugar: abre un menú con tres minijuegos. Ganar o terminar uno sube el cariño. Ya no hay barra de energía: jugar no tiene límite, y al dormir se despierta solo tras SUENO_HORAS.
- Pestaña Fechas: se pueden añadir fechas propias (se guardan en el dispositivo).
- Con Google Calendar conectado (ver GUIA_GOOGLE.md): se leen sus próximos eventos y aparecen en la pestaña Fechas,
  el Minion avisa de los eventos de hoy en el primer saludo, y las fechas nuevas (o las que ya hay, con su botón)
  se guardan en el calendario como evento anual con aviso. Borrar una fecha de la app también la borra del calendario.
- Sin conectar Google, el botón de cada fecha abre Google Calendar con el evento ya rellenado.

## Pendiente
Sonido, álbum de recuerdos semanal, servidor FastAPI, notificaciones push del propio Minion, voz,
alojar la app para usarla desde su iPhone y sustituir el Minion provisional por las animaciones finales.
