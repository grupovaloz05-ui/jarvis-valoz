# agent/social_channels.py — Flujo compartido para Instagram DM y Facebook Messenger
#
# Reutiliza el mismo cerebro (Claude) y la misma lógica de leads que ya usa WhatsApp
# (agent/brain.py, agent/lead_parser.py, integrations/google_sheets.py), pero separa
# el historial y los identificadores por canal para no mezclar IDs de página/Instagram
# con números de WhatsApp.

import asyncio
import logging
import os
import unicodedata
from datetime import datetime

from agent.brain import generar_respuesta
from agent.lead_parser import extraer_datos_lead
from agent.memory import guardar_mensaje, obtener_historial
from integrations.google_sheets import guardar_lead

logger = logging.getLogger("agentkit")

VALOR_VACIO = "No especificado"

_CANAL_DM = {"instagram": "Instagram DM", "facebook": "Facebook Messenger"}
_CANAL_COMENTARIO = {"instagram": "Comentario Instagram", "facebook": "Comentario Facebook"}
_NOMBRE_CANAL = {"instagram": "Instagram", "facebook": "Facebook"}

# Palabras clave que disparan un mensaje privado cuando alguien comenta en una
# publicación de Instagram o Facebook (sin acentos, en minúsculas — ver _normalizar).
_COMMENT_KEYWORDS = (
    "info", "precio", "precios", "whatsapp", "me interesa", "paquetes",
    "bot", "pagina", "web", "tarjeta", "resenas", "calificaciones",
)


def _normalizar(texto: str) -> str:
    """minúsculas, sin acentos — para comparar keywords de comentarios."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.strip().lower()


def detectar_keyword_comentario(texto: str) -> bool:
    normalizado = _normalizar(texto)
    return any(kw in normalizado for kw in _COMMENT_KEYWORDS)


def _mensaje_privado_comentario() -> str:
    link = os.getenv("VALOZ_WHATSAPP_LINK", "https://wa.me/529615805721")
    return (
        "¡Claro! Te paso info por aquí. En Valoz manejamos paquetes para automatizar "
        "WhatsApp, páginas web, contenido y tarjetas digitales para reseñas. También "
        f"puedes escribirnos directo a WhatsApp: {link}"
    )


async def _registrar_contacto_social(canal: str, identificador: str, historial_completo: list[dict]):
    """Extrae datos estructurados del lead y los guarda en Sheets, marcando el canal de origen."""
    try:
        datos = await extraer_datos_lead(historial_completo, identificador)
        datos["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        etiqueta = _CANAL_DM.get(canal, canal)
        proximo_paso = datos.get("proximo_paso", VALOR_VACIO)
        datos["proximo_paso"] = f"Canal: {etiqueta} | {proximo_paso}"
        await guardar_lead(datos)
    except Exception as e:
        logger.error(f"Error en _registrar_contacto_social ({canal}): {e}")


async def procesar_mensaje_social(proveedor, canal: str, sender_id: str, texto: str):
    """
    Genera y envía una respuesta de Jarvis para un DM de Instagram o Facebook Messenger.
    Usa el mismo system prompt y tono comercial que WhatsApp (agent/brain.py), guardando
    el historial bajo un identificador prefijado por canal para no chocar con teléfonos.
    """
    nombre_canal = _NOMBRE_CANAL.get(canal, canal)

    if not texto or not texto.strip():
        logger.info(f"[{canal}] Mensaje sin texto útil de {sender_id} — no se llama a Claude")
        return

    identificador = f"{canal}:{sender_id}"
    historial = await obtener_historial(identificador)
    respuesta = await generar_respuesta(texto, historial, canal=canal)

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
        logger.info(f"Respuesta {nombre_canal} enviada OK")
    else:
        logger.warning(
            f"Error enviando {nombre_canal}: el proveedor no pudo enviar el mensaje "
            f"(revisa META_PAGE_ACCESS_TOKEN, META_PAGE_ID/META_INSTAGRAM_ACCOUNT_ID y permisos)"
        )

    historial_completo = historial + [
        {"role": "user", "content": texto},
        {"role": "assistant", "content": respuesta},
    ]
    asyncio.create_task(_registrar_contacto_social(canal, identificador, historial_completo))


async def procesar_comentario_social(proveedor, canal: str, comentario_id: str, texto: str, autor_id: str):
    """
    Si el comentario contiene una palabra clave de interés, envía un mensaje privado
    breve (private reply) y guarda el lead en Sheets. Nunca responde públicamente ni
    manda mensajes a quien no comentó.
    """
    if not detectar_keyword_comentario(texto):
        logger.info(f"[{canal}] Comentario {comentario_id} sin palabra clave de interés — se ignora")
        return

    nombre_canal = _NOMBRE_CANAL.get(canal, canal)

    if not os.getenv("META_PAGE_ACCESS_TOKEN"):
        logger.warning("No se puede responder: falta META_PAGE_ACCESS_TOKEN")

    mensaje = _mensaje_privado_comentario()
    logger.info(f"Enviando private reply {nombre_canal}...")
    try:
        enviado = await proveedor.responder_comentario_privado(comentario_id, mensaje)
    except Exception as e:
        logger.error(f"Error enviando {nombre_canal}: {e}")
        enviado = False

    if enviado:
        logger.info(f"Private reply {nombre_canal} enviado OK")
    else:
        logger.warning(
            f"No se pudo enviar private reply de {nombre_canal} para comentario {comentario_id} "
            f"(revisa META_PAGE_ACCESS_TOKEN, permisos instagram_manage_comments/pages_manage_engagement, "
            f"o si el comment_id ya expiró para private reply)"
        )

    etiqueta = _CANAL_COMENTARIO.get(canal, canal)
    asyncio.create_task(guardar_lead({
        "telefono": f"{canal}-comment:{autor_id or comentario_id}",
        "resumen": f"Comentó: {texto[:200]}",
        "estado": "Nuevo lead",
        "proximo_paso": f"Canal: {etiqueta} | Dar seguimiento si responde al mensaje privado",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }))
