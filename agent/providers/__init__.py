# agent/providers/__init__.py — Factory de proveedores
# Generado por AgentKit

import os
from agent.providers.base import ProveedorWhatsApp


def obtener_proveedor() -> ProveedorWhatsApp:
    """Retorna el proveedor de WhatsApp configurado en .env."""
    proveedor = os.getenv("WHATSAPP_PROVIDER", "").lower()

    if not proveedor:
        raise ValueError("WHATSAPP_PROVIDER no configurado en .env. Usa: meta o twilio")

    if proveedor == "meta":
        from agent.providers.meta import ProveedorMeta
        return ProveedorMeta()
    elif proveedor == "twilio":
        from agent.providers.twilio import ProveedorTwilio
        return ProveedorTwilio()
    else:
        raise ValueError(f"Proveedor no soportado: {proveedor}. Usa: meta o twilio")


def instagram_enabled() -> bool:
    """True si INSTAGRAM_ENABLED=true en .env. Por defecto false — no rompe nada si falta."""
    return os.getenv("INSTAGRAM_ENABLED", "false").strip().lower() == "true"


def facebook_messenger_enabled() -> bool:
    """True si FACEBOOK_MESSENGER_ENABLED=true en .env. Por defecto false — no rompe nada si falta."""
    return os.getenv("FACEBOOK_MESSENGER_ENABLED", "false").strip().lower() == "true"


def obtener_proveedor_instagram() -> ProveedorWhatsApp:
    from agent.providers.instagram import ProveedorInstagram
    return ProveedorInstagram()


def obtener_proveedor_facebook() -> ProveedorWhatsApp:
    from agent.providers.facebook_messenger import ProveedorFacebookMessenger
    return ProveedorFacebookMessenger()
