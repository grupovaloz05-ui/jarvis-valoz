# agent/context_loader.py — Carga selectiva de contexto según intención del mensaje
# Evita enviar toda la base de conocimiento en cada turno. Carga solo lo relevante.
# Soporta múltiples clientes via CLIENT_ID (ver agent/client_loader.py).

import logging
from pathlib import Path

from agent.client_loader import (
    get_knowledge_dir,
    get_client_intents,
    get_client_intent_files,
    get_client_fallback_files,
)

logger = logging.getLogger("agentkit")

# ─── Defaults de Valoz Digital ───────────────────────────────────
_VALOZ_INTENTS: dict[str, list[str]] = {
    "objeciones": [
        "caro", "muy caro", "está caro", "mucho dinero", "no tengo presupuesto",
        "es mucho", "no me alcanza", "descuento", "rebaja", "precio menor",
        "más barato", "económico", "no puedo pagar",
    ],
    "precios": [
        "precio", "costo", "cuánto cuesta", "cuánto vale", "cuánto cobran",
        "tarifa", "cotización", "cotizar", "inversión", "pagar", "pago",
        "mensualidad", "cuánto es", "cuánto sale", "cuánto cobras",
    ],
    "servicios": [
        "agente", "bot", "página web", "landing", "contenido", "post",
        "carrusel", "reel", "redes sociales", "automatizar", "automatización",
        "instagram", "servicio", "ofrecen", "qué tienen", "qué hacen",
        "qué incluye", "qué es",
    ],
    "faq": [
        "cómo funciona", "cuánto tiempo", "cuándo", "proceso", "entrega",
        "garantía", "contrato", "incluye", "explica", "más información",
        "cuánto tarda", "en cuánto tiempo",
    ],
    "politicas": [
        "política", "devolución", "reembolso", "cancelar", "cancelación",
        "soporte", "ajustes", "cambios", "meses",
    ],
}

_VALOZ_ARCHIVO_POR_INTENT: dict[str, str] = {
    "precios":    "precios.md",
    "servicios":  "servicios.md",
    "faq":        "faq.md",
    "objeciones": "objeciones.md",
    "politicas":  "politicas.md",
}

_VALOZ_FALLBACK_FILES = ["valoz_servicios.md"]


def _normalizar_intents(raw: dict) -> dict[str, list[str]]:
    """Convierte intents del YAML (dict de str→list) al formato interno."""
    return {k: list(v) for k, v in raw.items() if isinstance(v, list)}


# Carga dinámica según CLIENT_ID (se evalúa al importar el módulo)
_client_intents = get_client_intents()
_client_files = get_client_intent_files()
_client_fallback = get_client_fallback_files()

KNOWLEDGE_DIR: Path = get_knowledge_dir()
INTENTS: dict[str, list[str]] = _normalizar_intents(_client_intents) if _client_intents else _VALOZ_INTENTS
ARCHIVO_POR_INTENT: dict[str, str] = _client_files if _client_files else _VALOZ_ARCHIVO_POR_INTENT
FALLBACK_FILES: list[str] = _client_fallback if _client_fallback is not None else _VALOZ_FALLBACK_FILES

FALLBACK_MAX_CHARS = 1200  # Limitar tokens en el fallback


def detectar_intento(mensaje: str) -> str:
    """Detecta la intención del mensaje. Retorna el intent o 'general'."""
    msg_lower = mensaje.lower()
    for intent, keywords in INTENTS.items():
        if any(kw in msg_lower for kw in keywords):
            return intent
    return "general"


def _leer_archivo(ruta: Path, max_chars: int = 0) -> str:
    try:
        content = ruta.read_text(encoding="utf-8").strip()
        if max_chars and len(content) > max_chars:
            content = content[:max_chars] + "\n[...]"
        return content
    except Exception as e:
        logger.warning(f"No se pudo cargar {ruta.name}: {e}")
        return ""


def cargar_conocimiento(intent: str) -> str:
    """Carga el archivo de conocimiento para el intent dado. Vacío si no aplica."""
    archivo = ARCHIVO_POR_INTENT.get(intent)
    if not archivo:
        return ""

    ruta = KNOWLEDGE_DIR / archivo
    if ruta.exists():
        content = _leer_archivo(ruta)
        if content:
            logger.info(f"Contexto usado: {intent} ({archivo})")
            return content

    # Fallback a archivos genéricos del negocio
    for fallback in FALLBACK_FILES:
        ruta_fb = KNOWLEDGE_DIR / fallback
        if ruta_fb.exists():
            content = _leer_archivo(ruta_fb, max_chars=FALLBACK_MAX_CHARS)
            if content:
                logger.info(f"Contexto usado: {intent} ({fallback} — fragmento)")
                return content

    return ""


def obtener_contexto(mensaje: str) -> tuple[str, str]:
    """
    Retorna (intent, contexto_adicional) para el mensaje dado.
    contexto_adicional está vacío si no hay archivo de conocimiento relevante.
    """
    intent = detectar_intento(mensaje)
    conocimiento = cargar_conocimiento(intent)

    if not conocimiento:
        logger.info(f"Contexto usado: {intent} (solo system prompt)")

    return intent, conocimiento
