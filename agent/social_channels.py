# agent/social_channels.py — Flujo compartido para Instagram DM y Facebook Messenger
#
# Estrategia comercial: Instagram y Facebook son canales de CAPTACIÓN, no de venta.
# No usan a Claude — responden con lógica directa por palabras clave, clasifican el
# lead (caliente/medio/frío) y siempre invitan a continuar por WhatsApp, que es el
# único canal donde Jarvis vende/asesora completo (agent/brain.py + WhatsApp).
#
# Guarda el historial y el lead bajo un identificador prefijado por canal para no
# chocar con números de WhatsApp en agent/memory.py e integrations/google_sheets.py.

import asyncio
import logging
import os
import re
import unicodedata
from datetime import datetime

from agent.memory import guardar_mensaje, obtener_historial
from integrations.google_sheets import guardar_lead

logger = logging.getLogger("agentkit")

VALOR_VACIO = "No especificado"

_CANAL_DM = {"instagram": "Instagram DM", "facebook": "Facebook Messenger"}
_CANAL_COMENTARIO = {"instagram": "Comentario Instagram", "facebook": "Comentario Facebook"}
_NOMBRE_CANAL = {"instagram": "Instagram", "facebook": "Facebook"}


def _normalizar(texto: str) -> str:
    """minúsculas, sin acentos — para comparar keywords de DMs y comentarios."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.strip().lower()


def _link_whatsapp() -> str:
    return os.getenv("VALOZ_WHATSAPP_LINK", "https://wa.me/529615805721")


# ─────────────────────────────────────────────────────────────────────────────
# Respuestas cortas de redirección a WhatsApp — lógica directa, sin llamar a Claude.
# ─────────────────────────────────────────────────────────────────────────────

_KW_PRECIO = ("precio", "precios", "cuanto cuesta", "costo", "cotizacion", "cotizame")
_KW_BOT = ("bot", "agente ia", "agente virtual", "chatbot", "automatizacion", "automatizar")
_KW_PAGINA_WEB = ("pagina", "sitio web", "landing", "web")
_KW_FRIO = ("no gracias", "no me interesa", "no, gracias", "jaja", "jajaja", "spam")
_SALUDOS = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "ola")


def _es_mensaje_frio(normalizado: str) -> bool:
    if not normalizado:
        return True
    if any(kw in normalizado for kw in _KW_FRIO):
        return True
    return normalizado in _SALUDOS


def _respuesta_corta_dm(texto: str) -> str:
    """
    Respuesta breve y natural para Instagram DM / Facebook Messenger. Nunca da
    asesoría larga ni vende ahí — solo detecta intención básica por keywords y
    manda al cliente a WhatsApp, que es el canal de atención completa.
    """
    normalizado = _normalizar(texto)
    link = _link_whatsapp()

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
    "quiero contratar", "me interesa", "quiero el bot", "quiero un bot",
    "quiero pagina", "quiero mi pagina", "pasame precios", "quiero paquete",
    "como le hacemos", "quiero empezar", "cotizame", "cotizeme", "agenda",
    "quiero automatizar", "quiero mas informacion de precios", "tengo un negocio",
)

_KW_LEAD_MEDIO = (
    "info", "precio", "precios", "cuanto cuesta", "que manejan", "paquetes",
    "quiero saber", "mandame informacion", "tal vez me interesa", "bot",
    "pagina", "web", "tarjeta", "resena", "resenas",
)

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
    como caliente solo porque contiene la frase "me interesa".
    """
    normalizado = _normalizar(texto)

    if _es_mensaje_frio(normalizado):
        return "frio"
    if any(kw in normalizado for kw in _KW_LEAD_CALIENTE):
        return "caliente"
    if any(kw in normalizado for kw in _KW_LEAD_MEDIO):
        return "medio"
    return "frio"


# ─────────────────────────────────────────────────────────────────────────────
# Palabras clave que disparan un mensaje privado cuando alguien comenta en una
# publicación de Instagram o Facebook (sin acentos, en minúsculas).
# ─────────────────────────────────────────────────────────────────────────────
_COMMENT_KEYWORDS = (
    "info", "precio", "precios", "whatsapp", "me interesa", "paquetes",
    "bot", "pagina", "web", "tarjeta", "resenas", "resena", "calificaciones",
)
# Palabras cortas que solo cuentan con límite de palabra completa, para evitar
# falsos positivos por substring (ej. "ia" dentro de "todavia" o "envia").
_COMMENT_KEYWORDS_PALABRA = ("ia",)


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


def _lead_dm_directo(canal: str, identificador: str, texto: str, calidad: str) -> dict:
    """Construye el registro de lead para un DM sin llamar a Claude — lógica directa."""
    etiqueta = _CANAL_DM.get(canal, canal)
    extracto = texto.strip()[:200]
    resumen = (
        f"Canal: {etiqueta}. Usuario escribió: \"{extracto}\". "
        f"Se le envió link de WhatsApp."
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
        "proximo_paso": f"Canal: {etiqueta} | {_PROXIMO_PASO_CALIDAD[calidad]}",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


async def procesar_mensaje_social(proveedor, canal: str, sender_id: str, texto: str):
    """
    Responde un DM de Instagram o Facebook Messenger con un mensaje corto que
    redirige a WhatsApp (canal de atención completa). No llama a Claude — usa
    lógica directa por keywords para ahorrar tokens, clasifica el lead y lo
    guarda en Sheets.
    """
    nombre_canal = _NOMBRE_CANAL.get(canal, canal)

    if not texto or not texto.strip():
        logger.info(f"[{canal}] Mensaje sin texto útil de {sender_id} — no se procesa")
        return

    identificador = f"{canal}:{sender_id}"
    calidad = clasificar_calidad_lead(texto)
    respuesta = _respuesta_corta_dm(texto)

    logger.info(f"[{canal}] Clasificación de lead={_ESTADO_CALIDAD[calidad]} — sender={sender_id}")

    await guardar_mensaje(identificador, "user", texto)
    await guardar_mensaje(identificador, "assistant", respuesta)

    if not os.getenv("META_PAGE_ACCESS_TOKEN"):
        logger.warning("No se puede responder: falta META_PAGE_ACCESS_TOKEN")

    logger.info(f"Enviando respuesta {nombre_canal}...")
    try:
        enviado = await proveedor.enviar_mensaje(sender_id, respuesta)
    except Exception as e:
        logger.error(f"Error enviando {nombre_canal}: {e}")
        enviado = False

    if enviado:
        logger.info(f"[{canal}] Respuesta enviada OK — sender={sender_id} — texto={respuesta!r}")
    else:
        logger.warning(
            f"[{canal}] Error enviando respuesta a {sender_id}: el proveedor no pudo enviar el mensaje "
            f"(revisa META_PAGE_ACCESS_TOKEN, META_PAGE_ID/META_INSTAGRAM_ACCOUNT_ID y permisos)"
        )

    datos_lead = _lead_dm_directo(canal, identificador, texto, calidad)
    asyncio.create_task(_guardar_lead_social(datos_lead, contexto=f"{canal} DM"))


async def procesar_comentario_social(proveedor, canal: str, comentario_id: str, texto: str, autor_id: str):
    """
    Si el comentario contiene una palabra clave de interés, envía un mensaje privado
    breve (private reply) redirigiendo a WhatsApp y guarda el lead clasificado en
    Sheets. Nunca responde públicamente de forma larga ni manda mensajes a quien no
    comentó.
    """
    if not detectar_keyword_comentario(texto):
        logger.info(f"[{canal}] Comentario {comentario_id} sin palabra clave de interés — se ignora")
        return

    nombre_canal = _NOMBRE_CANAL.get(canal, canal)
    calidad = clasificar_calidad_lead(texto)
    mensaje = _respuesta_corta_dm(texto)

    logger.info(f"[{canal}] Clasificación de lead={_ESTADO_CALIDAD[calidad]} — comentario={comentario_id}")

    if not os.getenv("META_PAGE_ACCESS_TOKEN"):
        logger.warning("No se puede responder: falta META_PAGE_ACCESS_TOKEN")

    logger.info(f"Enviando private reply {nombre_canal}...")
    try:
        enviado = await proveedor.responder_comentario_privado(comentario_id, mensaje)
    except Exception as e:
        logger.error(f"Error enviando {nombre_canal}: {e}")
        enviado = False

    if enviado:
        logger.info(f"[{canal}] Private reply enviado OK — comentario={comentario_id} — texto={mensaje!r}")
    else:
        logger.warning(
            f"[{canal}] No se pudo enviar private reply para comentario {comentario_id} "
            f"(revisa META_PAGE_ACCESS_TOKEN, permisos instagram_manage_comments/pages_manage_engagement, "
            f"o si el comment_id ya expiró para private reply)"
        )

    etiqueta = _CANAL_COMENTARIO.get(canal, canal)
    extracto = texto.strip()[:200]
    datos_lead = {
        "telefono": f"{canal}-comment:{autor_id or comentario_id}",
        "urgencia": _URGENCIA_CALIDAD[calidad],
        "resumen": f"Comentó: \"{extracto}\". Se le envió link de WhatsApp por mensaje privado.",
        "estado": _ESTADO_CALIDAD[calidad],
        "proximo_paso": f"Canal: {etiqueta} | {_PROXIMO_PASO_CALIDAD[calidad]}",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    asyncio.create_task(_guardar_lead_social(datos_lead, contexto=f"{canal} comentario"))
