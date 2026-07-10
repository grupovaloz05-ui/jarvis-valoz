# agent/providers/instagram.py — Adaptador para Instagram Messaging (DMs y comentarios)

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante, ComentarioEntrante

logger = logging.getLogger("agentkit")


class ProveedorInstagram(ProveedorWhatsApp):
    """Proveedor de Instagram Direct Messages usando la Instagram Messaging API de Meta."""

    def __init__(self):
        self.access_token = os.getenv("META_PAGE_ACCESS_TOKEN")
        self.ig_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
        self.api_version = "v21.0"
        if not self.access_token or not self.ig_account_id:
            logger.warning(
                "META_PAGE_ACCESS_TOKEN o META_INSTAGRAM_ACCOUNT_ID no configurados — "
                "Instagram no podrá enviar mensajes (los eventos entrantes no se pierden, "
                "solo no se responden)"
            )

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea DMs entrantes del payload de Instagram Messaging (object=instagram)."""
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
                    canal="instagram",
                ))
        return mensajes

    async def parsear_comentarios(self, request: Request) -> list[ComentarioEntrante]:
        """Parsea comentarios entrantes en publicaciones de Instagram (field=comments)."""
        body = await request.json()
        comentarios = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "comments":
                    continue
                value = change.get("value", {})
                comentarios.append(ComentarioEntrante(
                    comentario_id=value.get("id", ""),
                    texto=value.get("text", ""),
                    autor_id=(value.get("from") or {}).get("id", ""),
                    canal="instagram",
                ))
        return comentarios

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía un DM de Instagram. `telefono` aquí es el Instagram-Scoped ID (IGSID)."""
        if not self.access_token or not self.ig_account_id:
            logger.warning("META_PAGE_ACCESS_TOKEN o META_INSTAGRAM_ACCOUNT_ID no configurados")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/{self.ig_account_id}/messages"
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
                logger.info(f"Mensaje de Instagram enviado correctamente a {telefono}")
                return True
            logger.error(f"Error al enviar mensaje de Instagram a {telefono}: {r.status_code} — {r.text}")
            return False

    async def responder_comentario_privado(self, comentario_id: str, mensaje: str) -> bool:
        """Envía una respuesta privada (DM) a partir de un comentario de Instagram."""
        if not self.access_token or not self.ig_account_id:
            logger.warning("META_PAGE_ACCESS_TOKEN o META_INSTAGRAM_ACCOUNT_ID no configurados")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/{self.ig_account_id}/messages"
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
                logger.info(f"Private reply de Instagram enviado para comentario {comentario_id}")
                return True
            logger.error(
                f"Error enviando private reply de Instagram ({comentario_id}): "
                f"{r.status_code} — {r.text}"
            )
            return False
