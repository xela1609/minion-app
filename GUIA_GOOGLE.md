# Conectar la app con Google Calendar (gratis, sin Google Cloud)

Se usa un pequeño script de **Google Apps Script** que vive en la cuenta de Google cuyo calendario quieres
usar. No hay que crear ningún proyecto en Google Cloud, ni activar facturación, ni dar tarjeta.
Son unos 5 minutos y se hace una sola vez.

## Qué calendario se va a usar
El script lee y escribe el calendario de la cuenta con la que lo crees. Elige una opción:
- **El tuyo:** haz los pasos con tu cuenta. La app mostrará tus eventos.
- **El de ella:** los pasos 1 a 5 los hace ella con su cuenta (en su ordenador, 5 minutos).
- **Un calendario compartido "Nosotros":** lo creas en tu cuenta (Google Calendar > Otros calendarios > Crear
  calendario nuevo), lo compartes con ella con permiso para **hacer cambios en los eventos**, y pones su ID en
  `ID_CALENDARIO` dentro del script (Ajustes del calendario > Integrar calendario > ID de calendario).
  Ella lo verá en su Google Calendar y le llegarán los avisos.

## Pasos
1. Entra en https://script.google.com con esa cuenta y pulsa **Nuevo proyecto**. Ponle de nombre "Mi Minion".
2. Borra el código de ejemplo y pega **todo** el contenido del fichero `google_script.gs`.
3. En la primera línea de configuración, cambia `CLAVE` por una clave larga que te inventes (20 letras y
   números o más). Guarda con el icono del disquete o Ctrl+S.
4. **Dar permiso (una sola vez):** arriba, en el selector de funciones elige `autorizar` y pulsa **Ejecutar**.
   Pulsa **Revisar permisos**, elige la cuenta y, cuando salga "Google no ha verificado esta aplicación", pulsa
   **Avanzado** y luego **Ir a Mi Minion (no seguro)** y **Permitir**. Es tu propio script y solo pide acceso al
   calendario.
5. **Publicarlo:** arriba a la derecha, **Implementar > Nueva implementación**. En la rueda dentada elige
   **Aplicación web**. Ejecutar como: **Yo**. Quién tiene acceso: **Cualquier persona**. Pulsa **Implementar** y
   copia la **URL de la aplicación web** (termina en `/exec`).
6. Abre `config.py` y rellena:
   ```python
   GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/xxxxxxxx/exec"
   GOOGLE_SCRIPT_CLAVE = "la-misma-clave-del-paso-3"
   ```
7. Lanza `python main.py` y ve a la pestaña **Fechas**. Se conecta sola: verás "Google Calendar conectado" y
   tus próximos eventos.

## Qué hace la app cuando está conectada
- Lee los próximos 60 días del calendario y los muestra en la pestaña Fechas.
- En el primer saludo del día, el Minion dice los eventos de hoy.
- Al añadir una fecha, hay una casilla para guardarla también en el calendario. Las fechas que ya existen
  tienen su botón para subirlas. Se crean de todo el día, repetidas cada año, con aviso el día antes a las 9:00
  (se cambia con `GOOGLE_RECORDATORIOS_MINUTOS` en `config.py`).
- Borrar una fecha de la app también la borra del calendario, pero **solo si la creó la app** (llevan
  "— Creado por Mi Minion" en la descripción). Los demás eventos nunca se tocan.

## Si algo falla
| Mensaje | Qué hacer |
|---|---|
| "Clave incorrecta" | La clave del script y la de `config.py` no coinciden (cuidado con espacios), o no guardaste el script. |
| "La respuesta no viene del script" | La URL no termina en `/exec` o el acceso no es "Cualquier persona". |
| "El script respondió 404 / 403" | La URL está mal copiada. Cópiala otra vez desde Implementar > Administrar implementaciones. |
| "No hay conexión con Google" | Sin internet, o el ordenador bloquea la conexión. |
| Cambié el script y no se nota | Implementar > **Administrar implementaciones** > lápiz > Versión: **Nueva versión** > Implementar. La URL no cambia. |
| Los eventos salen un día o una hora desplazados | Script > Configuración del proyecto > Zona horaria: pon la tuya (Europe/Madrid). |

## Seguridad
- La URL del script es pública, pero sin la **clave** no hace nada. Quien tenga la URL y la clave puede leer y
  crear eventos de ese calendario, así que no las compartas y mantén `config.py` en privado.
- La llamada la hace el programa de Python, no el móvil. Por eso funcionará igual cuando alojemos la app para
  su iPhone, sin direcciones de redirección que registrar.
- Con una cuenta de Google normal, Apps Script no pide tarjeta. Tiene límites diarios muy por encima de lo que
  usa esta app (por ejemplo, 5.000 eventos creados al día en cuentas personales).

## Actualizar el script (si ya lo tenías publicado)
Si cambia `google_script.gs`, pega el código nuevo en el editor, guarda y publica una versión nueva: **Implementar > Administrar implementaciones > lápiz (editar) > Versión: Nueva versión > Implementar**. La URL no cambia. Si no haces esto, el script sigue funcionando con el código viejo.

## Calendarios compartidos y colores (versión nueva del script)
1. **Actualiza el script**: pega el nuevo `google_script.gs` y publica una versión nueva (ver arriba). Si Google te pide permisos otra vez, ejecuta `autorizar` de nuevo y acepta.
2. **Calendarios**: en la pestaña Fechas aparece un cuadro «Calendarios» con una casilla por calendario (los tuyos y los que te han compartido). Marca o desmarca los que quieres ver; la app lo recuerda. La primera vez salen marcados los que tengas marcados en Google Calendar.
3. **Para ver el calendario de otra persona**: tiene que estar compartido contigo y añadido en TU Google Calendar (en calendar.google.com, a la izquierda, dentro de «Otros calendarios»). La cuenta es la misma con la que creaste el script.
4. **Crear en un calendario compartido** solo funciona si te dieron permiso de «Hacer cambios en eventos»; si no, la app te mostrará el error.
5. **Colores**: cada evento se pinta con su color de Google (si tiene uno propio) o con el color de su calendario. Al crear, eliges el color en el diálogo. Los colores de evento son los 11 de Google; pueden verse un poco distintos del tono exacto que ves en la web de Google.

## Tipos de evento al crear
- **Fecha especial**: se guarda en la app (lista de Fechas especiales), Bob la recuerda y te felicita ese día. En Google es un evento de todo el día que se repite cada año.
- **Evento normal**: solo va a tu Google Calendar (no sale en las fechas especiales). Puedes ponerle hora y elegir si se repite cada año. Se puede borrar desde el detalle del día en el calendario de la app.
