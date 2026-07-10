# agent/providers/facebook_messenger.py — Adaptador para Facebook Messenger (DMs y comentarios)

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante, ComentarioEntrante

logger = logging.getLogger("agentkit")


class ProveedorFacebookMessenger(ProveedorWhatsApp):
    """Proveedor de Facebook Messenger usando la Messenger Platform Send API de Meta."""

    def __init__(self):
        self.access_token = os.getenv("META_PAGE_ACCESS_TOKEN")
        self.page_id = os.getenv("META_PAGE_ID")
        self.api_version = "v21.0"
        if not self.access_token or not self.page_id:
            logger.warning(
                "META_PAGE_ACCESS_TOKEN o META_PAGE_ID no configurados — "
                "Facebook Messenger no podrá enviar mensajes (los eventos entrantes no se "
                "pierden, solo no se responden)"
            )

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea DMs entrantes del payload de Messenger Platform (object=page)."""
        body = await request.json()
        mensajes = []
        for entry in body.get("entry", []):
            for evento in entry.get("messaging", []):
                mensaje = evento.get("message", {})
                if mensaje.get("is_echo"):
                    continue
                sender_id = evento.get("sender", {}).get("id", "")
                if not sender_id:
                    continue
                mensajes.append(MensajeEntrante(
                    telefono=sender_id,
                    texto=mensaje.get("text", ""),
                    mensaje_id=mensaje.get("mid", ""),
                    es_propio=False,
                    tipo="text",
                    canal="facebook",
                ))
        return mensajes

    async def parsear_comentarios(self, request: Request) -> list[ComentarioEntrante]:
        """Parsea comentarios entrantes en publicaciones de la página (field=feed)."""
        body = await request.json()
        comentarios = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "feed":
                    continue
                value = change.get("value", {})
                if value.get("item") != "comment" or value.get("verb") not in (None, "add"):
                    continue
                comentarios.append(ComentarioEntrante(
                    comentario_id=value.get("comment_id", ""),
                    texto=value.get("message", ""),
                    autor_id=(value.get("from") or {}).get("id", ""),
                    canal="facebook",
                ))
        return comentarios

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía un DM de Messenger. `telefono` aquí es el Page-Scoped ID (PSID)."""
        if not self.access_token:
            logger.warning("META_PAGE_ACCESS_TOKEN no configurado")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/me/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": telefono},
            "message": {"text": mensaje},
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                logger.info(f"Mensaje de Facebook Messenger enviado correctamente a {telefono}")
                return True
            logger.error(
                f"Error al enviar mensaje de Facebook Messenger a {telefono}: "
                f"{r.status_code} — {r.text}"
            )
            return False

    async def responder_comentario_privado(self, comentario_id: str, mensaje: str) -> bool:
        """Envía una respuesta privada (DM) a partir de un comentario de la página."""
        if not self.access_token:
            logger.warning("META_PAGE_ACCESS_TOKEN no configurado")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/me/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"comment_id": comentario_id},
            "message": {"text": mensaje},
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                logger.info(f"Private reply de Facebook enviado para comentario {comentario_id}")
                return True
            logger.error(
                f"Error enviando private reply de Facebook ({comentario_id}): "
                f"{r.status_code} — {r.text}"
            )
            return False
