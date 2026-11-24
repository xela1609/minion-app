# Chat con Bob

## Sin configurar nada
La pestaña **Chat** ya funciona: Bob contesta con frases por reglas (te quiero, hola, buenas noches, tristeza, chistes, fechas, etc.). No usa internet, no tiene límites y no cuesta nada.

## Con IA (opcional, para que converse de verdad)
Sirve cualquier servicio compatible con OpenAI que tenga plan gratuito. Ejemplo con Groq:

1. Crea una cuenta en https://console.groq.com y genera una API key (plan gratuito: unas 30 peticiones/minuto y 1.000/día en gpt-oss, de sobra para vosotros; los límites pueden cambiar, míralos en su web).
2. En `config.py` rellena:
   ```
   CHAT_API_URL = "https://api.groq.com/openai/v1"
   CHAT_API_KEY = "tu_clave"
   CHAT_MODELO = "openai/gpt-oss-20b"   # o "openai/gpt-oss-120b" (más listo, mismo límite gratuito)
   CHAT_PERSONALIDAD_EXTRA = "Le encanta el chocolate. Nos conocimos en ..."
   ```
3. Reinicia la app. Si la IA falla (sin internet, límite alcanzado, clave mala), Bob sigue contestando con las reglas.

## Ojo
- **Privacidad**: con IA, lo que ella escriba viaja al proveedor. Díselo y que no cuente datos sensibles.
- **La clave va dentro de la app**: si la sirves por internet, cualquiera que mire el código la vería. Para el regalo final lo correcto es guardarla en tu servidor FastAPI (siguiente fase) y que la app llame a tu servidor.
- El historial se guarda en el dispositivo (últimos 60 mensajes).

## Cómo saber si la IA está activa
Debajo del título "Chat con Bob" aparece un indicador:
- `● IA conectada`: está contestando la IA.
- `○ Modo sencillo (...)`: contesta con reglas, y entre paréntesis dice por qué (IA sin configurar, clave incorrecta, límite gratuito alcanzado, sin conexión...).

Si ves "IA sin configurar", faltan `CHAT_API_URL`, `CHAT_API_KEY` o `CHAT_MODELO` en `config.py`. Las respuestas repetidas son típicas del modo sencillo: solo con IA conversa de verdad.

## Memoria
Con IA, Bob recuerda los últimos 30 mensajes y además va guardando notas sobre ella (gustos, planes, cosas que cuenta) que actualiza solo cada 6 mensajes. Cuanto más rellenes `CHAT_PERSONALIDAD_EXTRA` (cómo os conocisteis, apodos, gustos, bromas internas), mejor conversa.

## Búsquedas en internet
Si ella pregunta por algo actual (noticias, precios, resultados, horarios, "busca...", "qué ha pasado hoy"), Bob busca en internet con la herramienta de búsqueda que Groq incluye en los modelos `openai/gpt-oss-20b` y `openai/gpt-oss-120b` (mientras busca pone "Bob está buscando en internet..."). Si la búsqueda falla (límite gratuito, modelo sin soporte...), contesta sin buscar. Búsquedas gastan más cuota que un mensaje normal. Se apaga con `CHAT_BUSQUEDA = False` en `config.py`. Bob también sabe la fecha, la hora y el tiempo que hace.
