# agent/whatsapp_media.py — Envío de imágenes por WhatsApp Cloud API
# Soporta media_id, URL pública y upload de imagen local.
# No rompe el flujo de texto si el envío de imagen falla.

import os
import logging
import mimetypes
from pathlib import Path

import httpx

logger = logging.getLogger("agentkit")

# Keywords que indican que el cliente quiere ver el menú
_MENU_KEYWORDS = {
    "menú", "menu", "carta", "qué venden", "que venden", "qué tienen", "que tienen",
    "precios", "precio", "productos", "cuánto cuesta", "cuanto cuesta",
    "alitas", "boneless", "papas", "bebidas", "frappe", "combo", "combos",
    "postres", "complementos", "salsas", "waffles", "nachos", "chicken",
    "cuánto vale", "cuanto vale", "cuánto sale", "cuanto sale",
}


def _mensaje_pide_menu(mensaje: str) -> bool:
    """True si el mensaje contiene alguna keyword de menú."""
    lower = mensaje.lower()
    return any(kw in lower for kw in _MENU_KEYWORDS)


async def upload_whatsapp_media(
    ruta_local: str,
    access_token: str,
    phone_number_id: str,
    api_version: str = "v21.0",
) -> str | None:
    """
    Sube una imagen local a Meta Media API y retorna el media_id.
    Retorna None si falla.
    """
    ruta = Path(ruta_local)
    if not ruta.exists():
        logger.warning(f"Imagen no encontrada para subir: {ruta_local}")
        return None

    mime_type, _ = mimetypes.guess_type(str(ruta))
    mime_type = mime_type or "image/jpeg"

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(ruta, "rb") as f:
                files = {
                    "file": (ruta.name, f, mime_type),
                    "messaging_product": (None, "whatsapp"),
                    "type": (None, mime_type),
                }
                r = await client.post(url, headers=headers, files=files)

        if r.status_code == 200:
            media_id = r.json().get("id")
            logger.info(f"Imagen subida a Meta Media API — media_id: {media_id}")
            return media_id
        else:
            logger.error(f"Error subiendo imagen a Meta: {r.status_code} — {r.text}")
            return None
    except Exception as e:
        logger.error(f"Excepción subiendo imagen a Meta: {e}")
        return None


async def send_whatsapp_image(
    telefono: str,
    access_token: str,
    phone_number_id: str,
    media_id: str | None = None,
    image_url: str | None = None,
    caption: str | None = None,
    api_version: str = "v21.0",
) -> bool:
    """
    Envía una imagen por WhatsApp Cloud API.
    Prioridad: media_id > image_url.
    Retorna True si fue exitoso.
    """
    if not access_token or not phone_number_id:
        logger.warning("META_ACCESS_TOKEN o META_PHONE_NUMBER_ID no configurados — no se puede enviar imagen")
        return False

    if not media_id and not image_url:
        logger.warning("send_whatsapp_image: se requiere media_id o image_url")
        return False

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if media_id:
        image_payload: dict = {"id": media_id}
    else:
        image_payload = {"link": image_url}

    if caption:
        image_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "image",
        "image": image_payload,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload, headers=headers)

        if r.status_code == 200:
            logger.info(f"Imagen enviada correctamente a {telefono}")
            return True
        else:
            logger.error(f"Error enviando imagen a {telefono}: {r.status_code} — {r.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción enviando imagen a {telefono}: {e}")
        return False


async def get_or_upload_menu_media_id(
    image_path: str,
    access_token: str,
    phone_number_id: str,
    cached_media_id: str = "",
    api_version: str = "v21.0",
) -> str | None:
    """
    Retorna el media_id para el menú:
    - Si cached_media_id está definido, lo usa directamente.
    - Si no, sube la imagen local y retorna el nuevo media_id.
    """
    if cached_media_id:
        return cached_media_id

    return await upload_whatsapp_media(image_path, access_token, phone_number_id, api_version)


async def send_menu_image_if_requested(
    proveedor,
    telefono: str,
    mensaje: str,
) -> bool:
    """
    Envía la imagen del menú si el mensaje lo requiere.
    Solo actúa si CLIENT_ID está definido y el cliente tiene config de imagen.
    Nunca rompe el flujo de texto si falla.

    Retorna True si se envió la imagen.
    """
    from agent.client_loader import get_client_id, get_menu_image_config

    client_id = get_client_id()
    if not client_id:
        return False

    if not _mensaje_pide_menu(mensaje):
        return False

    logger.info(f"Menú solicitado por {telefono} — preparando imagen")

    img_config = get_menu_image_config()
    image_path = img_config.get("image_path", "")
    media_id = img_config.get("media_id", "")
    image_url = img_config.get("image_url", "")

    access_token = os.getenv("META_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "")

    # Estrategia 1: usar media_id ya conocido
    if media_id:
        logger.info(f"Enviando imagen de menú con media_id a {telefono}")
        ok = await send_whatsapp_image(telefono, access_token, phone_number_id, media_id=media_id)
        if ok:
            logger.info(f"Imagen de menú enviada correctamente a {telefono}")
            return True

    # Estrategia 2: usar URL pública
    if image_url:
        logger.info(f"Enviando imagen de menú por URL a {telefono}")
        ok = await send_whatsapp_image(telefono, access_token, phone_number_id, image_url=image_url)
        if ok:
            logger.info(f"Imagen de menú enviada correctamente a {telefono}")
            return True

    # Estrategia 3: subir imagen local y enviar
    if image_path:
        logger.info(f"Subiendo imagen de menú local a Meta API para {telefono}")
        new_media_id = await get_or_upload_menu_media_id(image_path, access_token, phone_number_id)
        if new_media_id:
            ok = await send_whatsapp_image(telefono, access_token, phone_number_id, media_id=new_media_id)
            if ok:
                logger.info(f"Imagen de menú enviada correctamente a {telefono} (media_id nuevo: {new_media_id})")
                logger.info(f"Tip: guarda RENZO_MENU_MEDIA_ID={new_media_id} en .env para evitar re-upload")
                return True

    logger.warning(f"No se pudo enviar imagen de menú a {telefono} — respondiendo solo con texto")
    return False
