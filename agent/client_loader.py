# agent/client_loader.py — Carga de configuración por cliente
# Permite servir múltiples clientes desde la carpeta clientes/
# Si CLIENT_ID no está definido, usa los paths de Valoz Digital (comportamiento original).

import os
import yaml
import logging
from pathlib import Path

logger = logging.getLogger("agentkit")

CLIENT_ID = os.getenv("CLIENT_ID", "").strip().lower()


def get_client_id() -> str:
    return CLIENT_ID


def get_knowledge_dir() -> Path:
    if CLIENT_ID:
        return Path(f"clientes/{CLIENT_ID}/knowledge")
    return Path("knowledge")


def get_config_path() -> str:
    if CLIENT_ID:
        return f"clientes/{CLIENT_ID}/config/client_config.yaml"
    return "config/client_config.yaml"


def get_prompts_path() -> str:
    if CLIENT_ID:
        return f"clientes/{CLIENT_ID}/config/prompts.yaml"
    return "config/prompts.yaml"


def cargar_client_config() -> dict:
    path = get_config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"client_config no encontrado: {path}")
        return {}
    except Exception as e:
        logger.error(f"Error cargando {path}: {e}")
        return {}


def get_client_intents() -> dict[str, list[str]] | None:
    """Retorna INTENTS del cliente si están definidos en su config YAML, o None."""
    config = cargar_client_config()
    intents = config.get("INTENTS")
    if isinstance(intents, dict):
        return intents
    return None


def get_client_intent_files() -> dict[str, str] | None:
    """Retorna INTENT_FILES del cliente si están definidos, o None."""
    config = cargar_client_config()
    files = config.get("INTENT_FILES")
    if isinstance(files, dict):
        return files
    return None


def get_client_fallback_files() -> list[str] | None:
    """Retorna FALLBACK_FILES del cliente si están definidos, o None."""
    config = cargar_client_config()
    fallback = config.get("FALLBACK_FILES")
    if isinstance(fallback, list):
        return fallback
    return None


def get_business_name() -> str:
    config = cargar_client_config()
    return config.get("BUSINESS_NAME", "negocio")


def get_admin_numbers() -> list[str]:
    """Retorna los números autorizados para administrar promociones por WhatsApp."""
    config = cargar_client_config()
    numeros = config.get("admin_numbers")
    if isinstance(numeros, list):
        return [str(n) for n in numeros]
    return []


def get_whatsapp_implementation_mode() -> str:
    """Retorna el modo de implementación de WhatsApp del cliente (ver README_WHATSAPP_IMPLEMENTATION_MODES.md)."""
    config = cargar_client_config()
    return config.get("whatsapp_implementation_mode", "") or ""


def get_promotion_settings() -> dict:
    """Retorna la config de promociones administrables del cliente, o {} si no aplica."""
    config = cargar_client_config()
    settings = config.get("promotion_settings")
    return settings if isinstance(settings, dict) else {}


def get_menu_image_config() -> dict:
    """Retorna config de imagen del menú para este cliente."""
    config = cargar_client_config()
    return {
        "image_path": config.get("MENU_IMAGE_PATH", ""),
        "media_id": os.getenv(f"{CLIENT_ID.upper()}_MENU_MEDIA_ID", "") or config.get("MENU_MEDIA_ID", ""),
        "image_url": os.getenv(f"{CLIENT_ID.upper()}_MENU_IMAGE_URL", "") or config.get("MENU_IMAGE_URL", ""),
    }
