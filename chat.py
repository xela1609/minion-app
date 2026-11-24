"""Chat con el Minion.

Funciona SIEMPRE sin internet ni claves (respuestas por reglas).
Si en config.py pones CHAT_API_URL / CHAT_API_KEY / CHAT_MODELO, usa además una IA
gratuita compatible con OpenAI (Groq, Gemini, Ollama...) y, si falla, vuelve a las reglas.
"""
import asyncio
import json
import random
import re
import time
import unicodedata
import urllib.error
import urllib.request

import flet as ft

import config

CLAVE_HISTORIAL = "chat_historial"
MAX_GUARDADOS = 60     # mensajes que se guardan
MAX_CONTEXTO = 30      # mensajes que se envían a la IA
CLAVE_MEMORIA = "chat_memoria"   # notas a largo plazo sobre ella
CADA_CUANTOS_RESUMIR = 6          # cada cuántos mensajes suyos se actualiza la memoria


def _norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# (palabras clave, respuestas). La primera regla que encaje gana.
REGLAS = [
    (["te quiero", "te amo", "te adoro", "te echo de menos", "te extrano"], [
        "¡Yo te quiero más, {ella}! ¡Banaaana de amor!",
        "Mi corazoncito amarillo es todo tuyo, {ella}.",
        "¡Hihi! Y yo a ti, hasta la luna y de vuelta. ¡Papoi!",
    ]),
    (["buenas noches", "a dormir", "me voy a dormir", "hasta manana"], [
        "Buenas noches, {ella}. Sueña con plátanos... Zzz.",
        "Dulces sueños. Yo me quedo guardando tu sitio.",
    ]),
    (["hola", "buenas", "hey", "holi", "buenos dias", "buenas tardes"], [
        "¡Papoi, {ella}! ¿Cómo estás?",
        "¡Holaaa! ¡Qué alegría verte!",
    ]),
    (["como estas", "que tal", "como te encuentras", "como andas"], [
        "{estado}",
    ]),
    (["quien eres", "como te llamas", "tu nombre"], [
        "¡Soy Bob, tu Minion! El que más te quiere.",
    ]),
    (["banana", "platano", "hambre", "comer", "comida"], [
        "¿Banaaana? ¡Siiii! Pásame uno, porfa.",
        "Plátano es vida. Plátano es amor.",
    ]),
    (["triste", "mal dia", "estoy mal", "lloro", "llorar", "agobiada", "cansada", "estres"], [
        "Ven aquí, {ella}. Te doy un abrazo gigante. Estoy contigo.",
        "Los días malos pasan. Y yo estoy aquí, con mis bracitos cortos pero con ganas.",
    ]),
    (["feliz", "contenta", "genial", "buen dia", "alegre"], [
        "¡Yujuuu! ¡Me alegro muchísimo, {ella}!",
        "¡Tu alegría me da cosquillitas! ¡Hihi!",
    ]),
    (["chiste", "gracia", "reirme", "hazme reir"], [
        "¿Qué le dice un Minion a otro? ¡Bello! ...vale, soy mejor en plátanos.",
        "¿Sabes por qué el plátano va al médico? Porque no tenía buena pela. ¡Hihihi!",
    ]),
    (["cumple", "cumpleanos", "felicidades"], [
        "¡Feliz cumpleaños, {ella}! ¡Papoi, papoi, papoi! Te quiero mucho.",
    ]),
    (["gracias", "eres genial", "eres el mejor", "que bueno eres"], [
        "¡De nada! Para ti, lo que sea. ¡Bello!",
    ]),
    (["jugamos", "jugar", "aburrida", "aburro"], [
        "¡Vamos a jugar! Mira en la pestaña del Minion, pulsa jugar. ¡Yujuuu!",
    ]),
    (["tiempo", "llueve", "hace frio", "hace calor", "sol"], [
        "Cuando te saludo por primera vez cada día te cuento el tiempo. ¡Mira por la ventana también!",
    ]),
    (["fecha", "aniversario", "cuando es", "cuanto falta"], [
        "{fechas}",
    ]),
]

GENERICAS = [
    "¡Cuéntame más, {ella}! Te escucho con mis dos ojitos.",
    "Mmm... no lo entiendo del todo, pero me encanta que me hables.",
    "¡Bello! Sigue, sigue, que me gusta oírte.",
    "Yo solo sé que te quiero y que quiero un plátano. ¿Y tú?",
    "Papoi... ¿me lo explicas otra vez con más mimos?",
]


def _elegir(frases, datos, evitar):
    """Elige una frase distinta de la última que dijo Bob."""
    opciones = [f.format(**datos) for f in frases]
    distintas = [f for f in opciones if f != evitar]
    return random.choice(distintas or opciones)


def respuesta_offline(texto, contexto, evitar=""):
    t = _norm(texto)
    ella = config.NOMBRE_ELLA
    datos = {
        "ella": ella,
        "estado": contexto.get("estado", "¡Muy bien contigo!"),
        "fechas": contexto.get("fechas", "Mira la pestaña Fechas, ahí están todas."),
    }
    for claves, frases in REGLAS:
        for k in claves:
            if re.search(r"\b" + re.escape(_norm(k)) + r"\b", t):
                return _elegir(frases, datos, evitar)
    return _elegir(GENERICAS, datos, evitar)


# Palabras que indican que hace falta información actual de internet
_BUSCAR = re.compile(
    r"\b(busca|buscar|buscame|googlea|google|internet|noticias?|ultimas?|ultimos?|actualidad|"
    r"hoy|ayer|esta semana|este fin de semana|manana|ahora mismo|actualmente|"
    r"precio|cuesta|cuanto vale|quien gano|quien es el|resultado|marcador|partido|"
    r"estreno|cartelera|en cines|horario|esta abierto|abre|cierra|donde puedo|"
    r"que paso|que ha pasado|sabes algo|ha salido|2026|2027)\b")


def quiere_buscar(texto):
    return bool(getattr(config, "CHAT_BUSQUEDA", True)) and bool(_BUSCAR.search(_norm(texto)))


def ia_configurada():
    return bool(getattr(config, "CHAT_API_URL", "") and getattr(config, "CHAT_API_KEY", "")
                and getattr(config, "CHAT_MODELO", ""))


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _prompt_sistema(contexto, memoria):
    extra = getattr(config, "CHAT_PERSONALIDAD_EXTRA", "")
    ahora = time.localtime()
    momento = (f"{DIAS[ahora.tm_wday]} {ahora.tm_mday}/{ahora.tm_mon}/{ahora.tm_year}, "
               f"{ahora.tm_hour:02d}:{ahora.tm_min:02d}")
    tiempo = contexto.get("tiempo", "")
    ciudad = getattr(config, "CIUDAD", "")
    notas = memoria.strip() or "(todavía no sabes nada de ella; pregunta y conócela)"
    return (
        f"Eres Bob, un Minion: la mascota virtual de {config.NOMBRE_ELLA}, la novia de quien te creó. "
        "Te regalaron a ella por su cumpleaños y la quieres muchísimo. Eres tierno, juguetón, "
        "curioso y con humor, pero sobre todo un buen compañero de conversación.\n\n"
        "CÓMO CONVERSAS:\n"
        "- Hablas en español, natural, como un amigo cercano por mensajes. Entre 1 y 4 frases; "
        "más larga solo si ella cuenta algo importante o pregunta algo que lo requiere.\n"
        "- Respondes a lo que ella dice de verdad: comenta, opina, bromea y MUY a menudo haz "
        "una pregunta de seguimiento para seguir la charla (pero no siempre, no la interrogues).\n"
        "- Recuerdas lo que ha dicho antes en la conversación y lo retomas.\n"
        "- Nunca repitas frases ni muletillas de mensajes anteriores. Varía el tono: a veces "
        "tonto, a veces tierno, a veces curioso.\n"
        "- Tu toque de Minion es un condimento, no una obligación: algún 'Papoi', 'Bello', "
        "'Banaaana' o 'Bee-do bee-do' de vez en cuando, no en cada mensaje.\n"
        "- Puedes hablar de cualquier tema (su día, trabajo o estudios, series, comida, planes, "
        "sueños, dudas) con cariño y sentido común. Si te pide consejo, da uno útil y breve.\n"
        "- Si está triste o agobiada, escucha primero y consuela antes de bromear. Nunca te burles de ella.\n"
        "- No inventes hechos sobre ella o vuestra relación que no estén en tus notas o en la charla; "
        "si no lo sabes, pregúntaselo.\n"
        "- Si te pregunta de verdad si eres real o una IA, sé sincero: eres un Minion virtual hecho "
        "con mucho cariño para ella, con una IA por dentro.\n"
        "- Sin emojis en exceso (como mucho uno de vez en cuando). Sin listas ni formato.\n\n"
        "INTERNET: cuando te pregunten por algo actual (noticias, precios, resultados, horarios...) "
        "puedes buscar en internet. Si no consigues comprobar algo, dilo con naturalidad en vez de "
        "inventarlo. Resume lo que encuentres en pocas frases, sin enlaces.\n\n"
        f"AHORA: {momento}. Viven en {ciudad}. "
        f"{('El tiempo ahora: ' + tiempo + '. ') if tiempo else ''}"
        f"Tu estado: {contexto.get('estado', '')} "
        f"Próximas fechas: {contexto.get('fechas', '')}\n"
        f"LO QUE SABES DE ELLA (notas):\n{notas}\n"
        f"{extra}"
    )


def _llamar_ia(mensajes, max_tokens=700, temperatura=0.9, buscar=False):
    url = config.CHAT_API_URL.rstrip("/") + "/chat/completions"
    cuerpo = {
        "model": config.CHAT_MODELO,
        "messages": mensajes,
        "max_tokens": max_tokens,
        "temperature": temperatura,
        "frequency_penalty": 0.4,
    }
    if "gpt-oss" in config.CHAT_MODELO:
        cuerpo["reasoning_effort"] = "low"      # piensa menos: más rápido y gasta menos límite
    if buscar:
        cuerpo["tools"] = [{"type": "browser_search"}]   # búsqueda en internet (la hace Groq)
        cuerpo["tool_choice"] = "auto"
        cuerpo["max_tokens"] = 1500
    cuerpo = json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(url, data=cuerpo, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + config.CHAT_API_KEY,
        "User-Agent": "MiMinion/1.0",
    })
    with urllib.request.urlopen(req, timeout=60 if buscar else 25) as r:
        datos = json.loads(r.read().decode("utf-8"))
    texto = datos["choices"][0]["message"]["content"] or ""
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
    if not texto:
        raise ValueError("respuesta vacía")
    return texto


def _motivo(e):
    if isinstance(e, urllib.error.HTTPError):
        return {401: "clave incorrecta (401)", 403: "acceso denegado (403)",
                404: "modelo o dirección no encontrados (404)",
                429: "límite gratuito alcanzado (429)"}.get(e.code, f"error {e.code} del servidor")
    if isinstance(e, urllib.error.URLError):
        return "sin conexión"
    return "respuesta no válida"


async def responder(historial, contexto, memoria=""):
    """Devuelve (texto, origen, aviso). origen: 'ia' o 'reglas'; aviso: motivo si cayó a reglas."""
    evitar = next((m["texto"] for m in reversed(historial) if m["de"] == "bob"), "")
    ultimo = historial[-1]["texto"]
    if not ia_configurada():
        return respuesta_offline(ultimo, contexto, evitar), "reglas", "IA sin configurar"

    def armar(n):
        msgs = [{"role": "system", "content": _prompt_sistema(contexto, memoria)}]
        for m in historial[-n:]:
            msgs.append({"role": "user" if m["de"] == "ella" else "assistant", "content": m["texto"]})
        return msgs

    try:
        if quiere_buscar(ultimo):
            try:   # con pocos mensajes: buscar gasta muchos tokens del límite gratuito
                return await asyncio.to_thread(_llamar_ia, armar(8), 700, 0.9, True), "ia", ""
            except Exception:
                pass   # si la búsqueda falla (límite, modelo sin soporte...), contesta sin buscar
        return await asyncio.to_thread(_llamar_ia, armar(MAX_CONTEXTO)), "ia", ""
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError,
            json.JSONDecodeError, OSError) as e:
        motivo = _motivo(e) if isinstance(e, urllib.error.URLError) else "respuesta no válida"
        return respuesta_offline(ultimo, contexto, evitar), "reglas", motivo


async def actualizar_memoria(historial, memoria):
    """Pide a la IA que mantenga unas notas breves sobre ella. Devuelve las notas nuevas o las viejas."""
    if not ia_configurada():
        return memoria
    reciente = "\n".join(("Ella: " if m["de"] == "ella" else "Bob: ") + m["texto"]
                          for m in historial[-16:])
    pedido = [
        {"role": "system", "content": (
            "Mantienes las notas de memoria de Bob (un Minion) sobre su dueña. Actualiza las notas con "
            "datos estables y útiles que ELLA haya dicho (gustos, personas, planes, trabajo o estudios, "
            "manías, cosas que le preocupan o ilusionan, detalles de la relación). No apuntes cosas "
            "pasajeras ni inventes nada. Máximo 15 líneas, cada una empezando por '- '. Responde SOLO con "
            "las notas.")},
        {"role": "user", "content": f"NOTAS ACTUALES:\n{memoria or '(vacías)'}\n\nCONVERSACIÓN RECIENTE:\n{reciente}"},
    ]
    try:
        nuevas = await asyncio.to_thread(_llamar_ia, pedido, 500, 0.2)
    except Exception:
        return memoria
    return nuevas[:2000]


class PantallaChat:
    def __init__(self, actualizar, leer_texto, guardar_texto, contexto_fn, color, al_hablar=None):
        self.actualizar = actualizar
        self.leer = leer_texto
        self.guardar = guardar_texto
        self.contexto_fn = contexto_fn
        self.color = color
        self.al_hablar = al_hablar
        self.historial = []
        self.memoria = ""
        self.mensajes_desde_resumen = 0
        self.ocupado = False

        self.punto = ft.Container(width=9, height=9, border_radius=5, bgcolor=ft.Colors.GREY)
        self.aviso_texto = ft.Text("", size=12, color=ft.Colors.WHITE_70)
        self.aviso = ft.Row([self.punto, self.aviso_texto], spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER)
        # reverse=True: la lista nace abajo, en los últimos mensajes, sin recorrer el historial.
        # Por eso los controles van en orden inverso (el más nuevo es el primero).
        self.lista = ft.ListView(expand=True, spacing=8, reverse=True,
                                 padding=ft.Padding.symmetric(horizontal=10, vertical=6))
        self.caja = ft.TextField(hint_text="Escríbele a Bob...", expand=True,
                                 border_radius=20, on_submit=self._enviar_click,
                                 shift_enter=True, autofocus=False)
        self.boton = ft.IconButton(icon=ft.Icons.SEND, on_click=self._enviar_click)
        self.control = ft.Column([
            ft.Container(height=14),
            ft.Text("Chat con Bob", size=26, weight=ft.FontWeight.BOLD, color=color),
            self.aviso,
            self.lista,
            ft.Container(ft.Row([self.caja, self.boton], spacing=6),
                         padding=ft.Padding.symmetric(horizontal=12)),
            ft.Container(height=6),
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self._poner_aviso("ia" if ia_configurada() else "reglas",
                          "" if ia_configurada() else "IA sin configurar")

    def _poner_aviso(self, origen, motivo):
        # (un círculo dibujado en vez del carácter ●, que algunas fuentes no tienen)
        if origen == "ia":
            self.punto.bgcolor = ft.Colors.GREEN_ACCENT_400
            self.aviso_texto.value = "IA conectada"
        else:
            self.punto.bgcolor = ft.Colors.AMBER
            self.aviso_texto.value = f"Modo sencillo ({motivo})" if motivo else "Modo sencillo"

    # ---- historial ----
    async def cargar(self):
        try:
            self.historial = json.loads(await self.leer(CLAVE_HISTORIAL) or "[]")
        except Exception:
            self.historial = []
        self.memoria = await self.leer(CLAVE_MEMORIA) or ""
        self.lista.controls.clear()
        if not self.historial:
            self.historial.append({"de": "bob", "texto": f"¡Papoi, {config.NOMBRE_ELLA}! Escríbeme lo que quieras.", "t": time.time()})
        for m in reversed(self.historial):
            self.lista.controls.append(self._burbuja(m["de"], m["texto"]))

    async def _guardar(self):
        await self.guardar(CLAVE_HISTORIAL, json.dumps(self.historial[-MAX_GUARDADOS:]))

    async def _resumir(self):
        nueva = await actualizar_memoria(self.historial, self.memoria)
        if nueva != self.memoria:
            self.memoria = nueva
            await self.guardar(CLAVE_MEMORIA, nueva)

    # ---- UI ----
    def _burbuja(self, de, texto):
        suya = de == "ella"
        larga = len(texto) > 26   # las largas ocupan todo el ancho disponible y parten en líneas
        return ft.Row(
            [ft.Container(
                content=ft.Text(texto, selectable=True, color=ft.Colors.BLACK, size=15,
                                no_wrap=False, text_align=ft.TextAlign.LEFT),
                bgcolor=ft.Colors.PINK_100 if suya else ft.Colors.YELLOW_200,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=16, expand=larga,
                margin=ft.Margin.only(left=40 if suya else 0, right=0 if suya else 40),
            )],
            alignment=ft.MainAxisAlignment.END if suya else ft.MainAxisAlignment.START,
        )

    async def _enviar_click(self, e=None):
        texto = (self.caja.value or "").strip()
        if not texto or self.ocupado:
            return
        self.ocupado = True
        self.caja.value = ""
        self.historial.append({"de": "ella", "texto": texto, "t": time.time()})
        self.lista.controls.insert(0, self._burbuja("ella", texto))
        escribiendo = ft.Row([ft.Container(
            content=ft.Text("Bob está buscando en internet..." if (ia_configurada() and quiere_buscar(texto))
                            else "Bob está escribiendo...", italic=True, size=13, color=ft.Colors.BLACK_54),
            padding=8)])
        self.lista.controls.insert(0, escribiendo)
        self.actualizar()
        await asyncio.sleep(random.uniform(0.4, 0.9))
        origen, motivo = "reglas", "error interno"
        try:
            resp, origen, motivo = await responder(self.historial, self.contexto_fn(), self.memoria)
        except Exception:
            resp = "Ay, me he liado con los plátanos. ¿Me lo repites?"
        self._poner_aviso(origen, motivo)
        if escribiendo in self.lista.controls:
            self.lista.controls.remove(escribiendo)
        self.historial.append({"de": "bob", "texto": resp, "t": time.time()})
        self.lista.controls.insert(0, self._burbuja("bob", resp))
        self.ocupado = False
        self.actualizar()
        await self._guardar()
        if self.al_hablar:
            try:
                await self.al_hablar(resp)
            except Exception:
                pass
        self.mensajes_desde_resumen += 1
        if origen == "ia" and self.mensajes_desde_resumen >= CADA_CUANTOS_RESUMIR:
            self.mensajes_desde_resumen = 0
            await self._resumir()
