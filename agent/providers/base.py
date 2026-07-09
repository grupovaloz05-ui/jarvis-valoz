# agent/providers/base.py — Clase base para proveedores de WhatsApp
# Generado por AgentKit

from abc import ABC, abstractmethod
from dataclasses import dataclass
from fastapi import Request


@dataclass
class MensajeEntrante:
    """Mensaje normalizado — mismo formato sin importar el proveedor."""
    telefono: str       # Número del remitente
    texto: str          # Contenido del mensaje (o caption, si es imagen)
    mensaje_id: str     # ID único del mensaje
    es_propio: bool     # True si lo envió el agente (se ignora)
    tipo: str = "text"  # "text" | "image"
    media_id: str = ""  # ID de media del proveedor si tipo == "image"


class ProveedorWhatsApp(ABC):
    """Interfaz que cada proveedor de WhatsApp debe implementar."""

    @abstractmethod
    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Extrae y normaliza mensajes del payload del webhook."""
        ...

    @abstractmethod
    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía un mensaje de texto. Retorna True si fue exitoso."""
        ...

    async def enviar_imagen(
        self,
        telefono: str,
        media_id: str | None = None,
        image_url: str | None = None,
        caption: str | None = None,
    ) -> bool:
        """Envía una imagen. Implementación opcional; retorna False por defecto."""
        return False

    async def validar_webhook(self, request: Request) -> dict | int | None:
        """Verificación GET del webhook (solo Meta la requiere). Retorna respuesta o None."""
        return None

    async def subir_media(self, ruta_local: str) -> str | None:
        """Sube un archivo local y retorna su media_id. Implementación opcional; retorna None por defecto."""
        return None

    async def descargar_media(self, media_id: str) -> tuple[bytes, str] | None:
        """Descarga el contenido de un media entrante (ej. imagen recibida). Retorna (contenido, mime_type) o None."""
        return None
