# agent/providers/meta.py — Adaptador para Meta WhatsApp Cloud API
# Generado por AgentKit

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante
from agent.whatsapp_media import send_whatsapp_image, upload_whatsapp_media, download_whatsapp_media

logger = logging.getLogger("agentkit")


class ProveedorMeta(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando la API oficial de Meta (Cloud API)."""

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "agentkit-verify")
        self.api_version = "v21.0"

    async def validar_webhook(self, request: Request) -> dict | int | None:
        """Meta requiere verificación GET con hub.verify_token."""
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        if mode == "subscribe" and token == self.verify_token:
            return int(challenge)
        return None

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload anidado de Meta Cloud API."""
        body = await request.json()
        mensajes = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        mensajes.append(MensajeEntrante(
                            telefono=msg.get("from", ""),
                            texto=msg.get("text", {}).get("body", ""),
                            mensaje_id=msg.get("id", ""),
                            es_propio=False,
                            tipo="text",
                        ))
                    elif msg.get("type") == "image":
                        imagen = msg.get("image", {})
                        mensajes.append(MensajeEntrante(
                            telefono=msg.get("from", ""),
                            texto=imagen.get("caption", ""),
                            mensaje_id=msg.get("id", ""),
                            es_propio=False,
                            tipo="image",
                            media_id=imagen.get("id", ""),
                        ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Meta WhatsApp Cloud API."""
        if not self.access_token or not self.phone_number_id:
            logger.warning("META_ACCESS_TOKEN o META_PHONE_NUMBER_ID no configurados")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": mensaje},
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                logger.info(f"Mensaje enviado por WhatsApp correctamente a {telefono}")
                return True
            else:
                logger.error(f"Error al enviar mensaje a {telefono}: {r.status_code} — {r.text}")
                return False

    async def enviar_imagen(
        self,
        telefono: str,
        media_id: str | None = None,
        image_url: str | None = None,
        caption: str | None = None,
    ) -> bool:
        """Envía una imagen por Meta WhatsApp Cloud API."""
        return await send_whatsapp_image(
            telefono=telefono,
            access_token=self.access_token or "",
            phone_number_id=self.phone_number_id or "",
            media_id=media_id,
            image_url=image_url,
            caption=caption,
            api_version=self.api_version,
        )

    async def subir_media(self, ruta_local: str) -> str | None:
        """Sube una imagen local a Meta Media API y retorna el media_id."""
        return await upload_whatsapp_media(
            ruta_local=ruta_local,
            access_token=self.access_token or "",
            phone_number_id=self.phone_number_id or "",
            api_version=self.api_version,
        )

    async def descargar_media(self, media_id: str) -> tuple[bytes, str] | None:
        """Descarga el contenido de un media entrante (ej. imagen de promoción)."""
        return await download_whatsapp_media(
            media_id=media_id,
            access_token=self.access_token or "",
            api_version=self.api_version,
        )
