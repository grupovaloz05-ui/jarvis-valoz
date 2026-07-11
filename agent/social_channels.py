# agent/social_channels.py — Flujo compartido para Instagram DM y Facebook Messenger
#
# Estrategia comercial: Instagram y Facebook son canales de CAPTACIÓN, no de venta.
# No usan a Claude — responden con lógica directa por palabras clave, clasifican el
# lead (caliente/medio/frío) y siempre invitan a continuar por WhatsApp, que es el
# único canal donde Jarvis vende/asesora completo (agent/brain.py + WhatsApp).
#
# En comentarios de Instagram/Facebook nunca se vende ni se da información larga:
# se responde público con un mensaje corto ("te mandé DM") y se intenta un private
# reply / DM con el link de WhatsApp. En DMs, la respuesta siempre redirige a
# WhatsApp salvo que el usuario diga explícitamente que no puede usar WhatsApp, que
# le urge, o que necesita respuesta ahí mismo — en ese caso se queda respondiendo
# breve en el mismo canal (sin llamar a Claude).
#
# Guarda el historial y el lead bajo un identificador prefijado por canal para no
# chocar con números de WhatsApp en agent/memory.py e integrations/google_sheets.py.

import asyncio
import logging
import os
import random
import re
import unicodedata
from datetime import datetime

from agent.memory import guardar_mensaje, obtener_historial
from integrations.google_sheets import guardar_lead

logger = logging.getLogger("agentkit")

VALOR_VACIO = "No especificado"

_CANAL_DM = {"instagram": "Instagram DM", "facebook": "Facebook Messenger"}
_CANAL_COMENTARIO = {"instagram": "Instagram comentario", "facebook": "Facebook comentario"}
_NOMBRE_CANAL = {"instagram": "Instagram", "facebook": "Facebook"}

# Variables de entorno requeridas para que cada canal pueda ENVIAR respuestas.
# Si faltan o vienen vacías/con espacios, el evento se sigue guardando (lead en
# Sheets) pero no se intenta enviar nada — y se loguea exactamente cuál falta.
_VARS_REQUERIDAS = {
    "instagram": ("META_PAGE_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID"),
    "facebook": ("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID"),
}


def _normalizar(texto: str) -> str:
    """minúsculas, sin acentos — para comparar keywords de DMs y comentarios."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.strip().lower()


def _link_whatsapp() -> str:
    return os.getenv("VALOZ_WHATSAPP_LINK", "https://wa.me/529615805721")


def _variables_faltantes(canal: str) -> list[str]:
    """Nombres exactos de variables de entorno faltantes o vacías/con espacios para `canal`."""
    return [v for v in _VARS_REQUERIDAS.get(canal, ()) if not (os.getenv(v) or "").strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Respuestas cortas de redirección a WhatsApp — lógica directa, sin llamar a Claude.
# ─────────────────────────────────────────────────────────────────────────────

_KW_PRECIO = ("precio", "precios", "cuanto cuesta", "costo", "costos", "cotizacion", "cotizame")
_KW_BOT = ("bot", "agente ia", "agente virtual", "chatbot", "automatizacion", "automatizar", "agente", "agentes")
_KW_PAGINA_WEB = ("pagina", "sitio web", "landing", "web")
_KW_FRIO = ("no gracias", "no me interesa", "no, gracias", "jaja", "jajaja", "spam")
_SALUDOS = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "ola")

# Frases que indican que el usuario no puede/no quiere usar WhatsApp — en ese caso
# NO se le redirige, se le atiende breve en el mismo canal.
_KW_NO_PUEDE_WHATSAPP = (
    "no puedo por whatsapp", "no puedo usar whatsapp", "no tengo whatsapp",
    "no uso whatsapp", "sin whatsapp", "no manejo whatsapp", "no puedo whatsapp",
)
# Frases de urgencia o que piden explícitamente respuesta en el mismo chat.
_KW_URGENTE = (
    "me urge", "es urgente", "urgente", "necesito ya", "responde aqui",
    "respondeme aqui", "aqui mismo", "ahi mismo", "en este chat",
    "necesito respuesta aqui", "atencion aqui", "aqui mismo por favor",
)


def _es_mensaje_frio(normalizado: str) -> bool:
    if not normalizado:
        return True
    if any(kw in normalizado for kw in _KW_FRIO):
        return True
    return normalizado in _SALUDOS


def _requiere_atencion_directa(normalizado: str) -> bool:
    """True si el usuario pidió explícitamente quedarse en el canal (no redirigir a WhatsApp)."""
    return any(kw in normalizado for kw in _KW_NO_PUEDE_WHATSAPP + _KW_URGENTE)


def _respuesta_corta_dm(texto: str) -> str:
    """
    Respuesta breve y natural para Instagram DM / Facebook Messenger. Nunca da
    asesoría larga ni vende ahí — solo detecta intención básica por keywords y
    manda al cliente a WhatsApp, que es el canal de atención completa.

    Excepción: si el usuario dice que no puede usar WhatsApp, que le urge, o pide
    respuesta ahí mismo, se queda respondiendo breve en el propio canal — sin
    llamar a Claude, con una respuesta corta fija.
    """
    normalizado = _normalizar(texto)
    link = _link_whatsapp()

    if any(kw in normalizado for kw in _KW_NO_PUEDE_WHATSAPP):
        return "Sin problema, también puedo ayudarte por aquí. Cuéntame qué tipo de negocio tienes y qué quieres automatizar o mejorar."

    if any(kw in normalizado for kw in _KW_URGENTE):
        return "Claro, te apoyo por aquí. Para orientarte rápido: ¿buscas agente para WhatsApp, página web, contenido o tarjetas digitales?"

    if any(kw in normalizado for kw in _KW_PRECIO):
        return f"Claro. Te paso precios y paquetes por WhatsApp para atenderte mejor según tu negocio: {link}"

    if any(kw in normalizado for kw in _KW_BOT):
        return f"Sí, hacemos agentes IA para negocios. Para explicarte bien opciones y precios, escríbenos por WhatsApp: {link}"

    if any(kw in normalizado for kw in _KW_PAGINA_WEB):
        return f"Sí manejamos páginas web y paquetes digitales. Te atendemos mejor por WhatsApp aquí: {link}"

    if _es_mensaje_frio(normalizado):
        return f"Gracias por escribirnos. Si después necesitas automatización, web o marketing, puedes contactarnos por WhatsApp: {link}"

    return f"¡Claro! Te paso la info por WhatsApp para atenderte mejor: {link}"


# ─────────────────────────────────────────────────────────────────────────────
# Clasificación de calidad del lead — caliente / medio / frío, por keywords.
# ─────────────────────────────────────────────────────────────────────────────

_KW_LEAD_CALIENTE = (
    "quiero contratar", "quiero el bot", "quiero un bot", "quiero un agente",
    "quiero agente", "quiero pagina", "quiero mi pagina", "pasame precios",
    "quiero paquete", "como le hacemos", "quiero empezar", "necesito eso",
    "cotizame", "cotizeme", "cotizacion", "agenda", "quiero automatizar",
    "quiero mas informacion de precios", "tengo un negocio", "me urge",
    "agente", "agentes", "bot", "automatizacion", "automatizar",
)

_KW_LEAD_MEDIO = (
    "info", "precio", "precios", "cuanto cuesta", "cuanto", "que manejan",
    "paquete", "paquetes", "quiero saber", "mandame informacion",
    "tal vez me interesa", "me interesa", "pagina", "web", "tarjeta", "resena",
    "resenas", "calificaciones", "informes", "costos",
)
# Palabras cortas que solo cuentan con límite de palabra completa, para evitar
# falsos positivos por substring (ej. "ia" dentro de "todavia" o "envia").
_KW_LEAD_MEDIO_PALABRA = ("ia",)

_ESTADO_CALIDAD = {
    "caliente": "Lead caliente",
    "medio": "Lead medio",
    "frio": "Lead frío",
}

_PROXIMO_PASO_CALIDAD = {
    "caliente": "Contactar cuanto antes por WhatsApp",
    "medio": "Esperar mensaje por WhatsApp. Si escribe, dar seguimiento prioritario",
    "frio": "No priorizar / Sin seguimiento inmediato",
}

_URGENCIA_CALIDAD = {"caliente": "Alta", "medio": "Media", "frio": "Baja"}


def clasificar_calidad_lead(texto: str) -> str:
    """
    Clasifica el lead como 'caliente' | 'medio' | 'frio' por palabras clave (sin IA).
    Revisa primero las señales de rechazo/saludo — "no me interesa" no debe clasificar
    como caliente solo porque contenga alguna palabra positiva.
    """
    normalizado = _normalizar(texto)

    if _es_mensaje_frio(normalizado):
        return "frio"
    if any(kw in normalizado for kw in _KW_LEAD_CALIENTE):
        return "caliente"
    if any(kw in normalizado for kw in _KW_LEAD_MEDIO):
        return "medio"
    if any(re.search(rf"\b{kw}\b", normalizado) for kw in _KW_LEAD_MEDIO_PALABRA):
        return "medio"
    return "frio"


# ─────────────────────────────────────────────────────────────────────────────
# Palabras clave que disparan un mensaje privado cuando alguien comenta en una
# publicación de Instagram o Facebook (sin acentos, en minúsculas).
# ─────────────────────────────────────────────────────────────────────────────
_COMMENT_KEYWORDS = (
    "info", "precio", "precios", "paquete", "paquetes", "bot", "bots", "agente",
    "automatizacion", "automatizar", "web", "pagina", "sitio", "redes", "contenido",
    "tarjeta", "resena", "resenas", "calificaciones", "whatsapp", "quiero",
    "me interesa", "informes", "costos", "cuanto", "cotizacion",
    "inteligencia artificial",
)
# Palabras cortas que solo cuentan con límite de palabra completa, para evitar
# falsos positivos por substring (ej. "ia" dentro de "todavia" o "envia").
_COMMENT_KEYWORDS_PALABRA = ("ia",)

# Variaciones cortas de respuesta pública al comentario — nunca se vende en público,
# solo se avisa que se mandó DM. Se elige una al azar para sonar natural.
_RESPUESTAS_PUBLICAS_COMENTARIO = (
    "Te mandé DM 🙌",
    "Claro, revisa tus mensajes.",
    "Te pasé la info por DM.",
)


def detectar_keyword_comentario(texto: str) -> bool:
    normalizado = _normalizar(texto)
    if any(kw in normalizado for kw in _COMMENT_KEYWORDS):
        return True
    return any(re.search(rf"\b{kw}\b", normalizado) for kw in _COMMENT_KEYWORDS_PALABRA)


async def _guardar_lead_social(datos: dict, contexto: str) -> None:
    """Guarda el lead en Sheets y loguea el resultado (nunca lanza excepción hacia arriba)."""
    try:
        ok = await guardar_lead(datos)
        if ok:
            logger.info(f"[{contexto}] Guardado en Sheets OK — telefono={datos.get('telefono')}")
        else:
            logger.warning(f"[{contexto}] Guardado en Sheets omitido (no configurado) — telefono={datos.get('telefono')}")
    except Exception as e:
        logger.error(f"[{contexto}] Error guardando en Sheets: {e}")


def _lead_dm_directo(canal: str, identificador: str, texto: str, calidad: str, atencion_directa: bool) -> dict:
    """Construye el registro de lead para un DM sin llamar a Claude — lógica directa."""
    etiqueta = _CANAL_DM.get(canal, canal)
    extracto = texto.strip()[:200]
    accion = (
        f"atención directa en {_NOMBRE_CANAL.get(canal, canal)} (usuario pidió no usar WhatsApp o urgencia)"
        if atencion_directa
        else "enviado a WhatsApp"
    )
    resumen = (
        f"Canal: {etiqueta}. Usuario escribió: \"{extracto}\". "
        f"Acción: {accion}."
    )
    return {
        "telefono": identificador,
        "nombre": VALOR_VACIO,
        "negocio": VALOR_VACIO,
        "tipo_negocio": VALOR_VACIO,
        "servicio": VALOR_VACIO,
        "presupuesto": VALOR_VACIO,
        "urgencia": _URGENCIA_CALIDAD[calidad],
        "resumen": resumen,
        "estado": _ESTADO_CALIDAD[calidad],
        "proximo_paso": f"Canal: {etiqueta} | Acción: {accion} | {_PROXIMO_PASO_CALIDAD[calidad]}",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


async def procesar_mensaje_social(proveedor, canal: str, sender_id: str, texto: str):
    """
    Responde un DM de Instagram o Facebook Messenger. Por defecto redirige a
    WhatsApp (canal de atención completa) con un mensaje corto. Solo si el usuario
    dice que no puede usar WhatsApp, que le urge, o pide respuesta ahí mismo, se
    queda respondiendo breve en el mismo canal. Nunca llama a Claude — usa lógica
    directa por keywords, clasifica el lead y lo guarda en Sheets.
    """
    tag = f"[{canal} DM]"

    if not texto or not texto.strip():
        logger.info(f"{tag} Mensaje sin texto útil de {sender_id} — no se procesa")
        return

    identificador = f"{canal}:{sender_id}"
    normalizado = _normalizar(texto)
    calidad = clasificar_calidad_lead(texto)
    atencion_directa = _requiere_atencion_directa(normalizado)
    respuesta = _respuesta_corta_dm(texto)

    logger.info(f"{tag} Clasificación de lead={_ESTADO_CALIDAD[calidad]} — sender={sender_id}")
    if atencion_directa:
        logger.info(f"{tag} Usuario pidió atención directa aquí (no redirigir a WhatsApp) — sender={sender_id}")
    else:
        logger.info(f"{tag} redirigiendo a WhatsApp — sender={sender_id}")

    await guardar_mensaje(identificador, "user", texto)
    await guardar_mensaje(identificador, "assistant", respuesta)

    faltantes = _variables_faltantes(canal)
    if faltantes:
        logger.warning(
            f"{tag} No se puede responder — variable(s) de entorno faltante(s) o vacía(s): "
            f"{', '.join(faltantes)} (el lead se guarda igual)"
        )

    try:
        enviado = await proveedor.enviar_mensaje(sender_id, respuesta)
    except Exception as e:
        logger.error(f"{tag} Error enviando respuesta: {e}")
        enviado = False

    if enviado:
        logger.info(f"{tag} respuesta_enviada OK — sender={sender_id} — texto={respuesta!r}")
    else:
        logger.warning(
            f"{tag} respuesta_enviada error — sender={sender_id} "
            f"(revisa META_PAGE_ACCESS_TOKEN, META_PAGE_ID/META_INSTAGRAM_ACCOUNT_ID y permisos)"
        )

    datos_lead = _lead_dm_directo(canal, identificador, texto, calidad, atencion_directa)
    asyncio.create_task(_guardar_lead_social(datos_lead, contexto=f"{canal} DM"))


async def procesar_comentario_social(proveedor, canal: str, comentario_id: str, texto: str, autor_id: str):
    """
    Si el comentario contiene una palabra clave de interés:
      1. Responde públicamente algo corto (ej. "Te mandé DM 🙌") — nunca vende en público.
      2. Intenta un private reply / DM con el link de WhatsApp.
      3. Guarda el lead clasificado en Sheets.
    Si no hay palabra clave: no responde, no guarda lead, solo loguea que se ignoró.
    """
    tag = f"[{canal} comment]"
    keyword_detectada = detectar_keyword_comentario(texto)
    logger.info(f"{tag} keyword_detectada={str(keyword_detectada).lower()} — comentario={comentario_id}")

    if not keyword_detectada:
        logger.info(f"{tag} comentario sin palabra clave, ignorado — comentario={comentario_id}")
        return

    calidad = clasificar_calidad_lead(texto)
    mensaje_publico = random.choice(_RESPUESTAS_PUBLICAS_COMENTARIO)
    mensaje_privado = f"¡Claro! Te paso la info por WhatsApp para atenderte mejor: {_link_whatsapp()}"

    logger.info(f"{tag} Clasificación de lead={_ESTADO_CALIDAD[calidad]} — comentario={comentario_id}")

    faltantes = _variables_faltantes(canal)
    if faltantes:
        logger.warning(
            f"{tag} No se puede responder — variable(s) de entorno faltante(s) o vacía(s): "
            f"{', '.join(faltantes)} (el lead se guarda igual)"
        )

    try:
        publico_enviado = await proveedor.responder_comentario_publico(comentario_id, mensaje_publico)
    except Exception as e:
        logger.error(f"{tag} Error enviando respuesta pública: {e}")
        publico_enviado = False
    logger.info(f"{tag} respuesta_publica_enviada {'OK' if publico_enviado else 'error'} — comentario={comentario_id}")

    try:
        privado_enviado = await proveedor.responder_comentario_privado(comentario_id, mensaje_privado)
    except Exception as e:
        logger.error(f"{tag} Error enviando private reply: {e}")
        privado_enviado = False
    logger.info(f"{tag} private_reply_enviado {'OK' if privado_enviado else 'error'} — comentario={comentario_id}")

    etiqueta = _CANAL_COMENTARIO.get(canal, canal)
    extracto = texto.strip()[:200]
    resumen = (
        f"Canal: {etiqueta}. Comentó: \"{extracto}\". Acción: enviado a WhatsApp. "
        f"Se respondió comentario y se envió DM si Meta lo permitió."
    )
    datos_lead = {
        "telefono": f"{canal}-comment:{autor_id or comentario_id}",
        "urgencia": _URGENCIA_CALIDAD[calidad],
        "resumen": resumen,
        "estado": _ESTADO_CALIDAD[calidad],
        "proximo_paso": f"Canal: {etiqueta} | Acción: enviado a WhatsApp | {_PROXIMO_PASO_CALIDAD[calidad]}",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    asyncio.create_task(_guardar_lead_social(datos_lead, contexto=f"{canal} comentario"))
