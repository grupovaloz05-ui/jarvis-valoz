# agent/brain.py — Cerebro del agente: conexión con Claude API

import os
import yaml
import logging
import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from agent.context_loader import obtener_contexto

load_dotenv()
logger = logging.getLogger("agentkit")

client = AsyncAnthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=httpx.Timeout(60.0, connect=10.0),
    max_retries=2,
)

# Máximo de mensajes del historial enviados a Claude por turno
MAX_HISTORIAL = 10


def _cargar_nombre_negocio() -> str:
    try:
        with open("config/client_config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
            return cfg.get("BUSINESS_NAME", "negocio")
    except Exception:
        return "negocio"


_NOMBRE_NEGOCIO = _cargar_nombre_negocio()
logger.info(f"Configuración cargada para: {_NOMBRE_NEGOCIO}")


def cargar_config_prompts() -> dict:
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres un asistente útil. Responde en español.")


def obtener_mensaje_error() -> str:
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo.")


def obtener_mensaje_fallback() -> str:
    config = cargar_config_prompts()
    return config.get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Podrías reformularlo?")


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    system_prompt = cargar_system_prompt()

    # Carga contextual selectiva según intención del mensaje
    intent, conocimiento = obtener_contexto(mensaje)
    if conocimiento:
        system_prompt = (
            system_prompt
            + "\n\n---\n## Contexto adicional para este turno\n\n"
            + conocimiento
        )

    # Limitar historial para reducir tokens por turno
    mensajes = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in historial[-MAX_HISTORIAL:]
    ]
    mensajes.append({"role": "user", "content": mensaje})

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=system_prompt,
            messages=mensajes,
        )

        respuesta = response.content[0].text
        logger.info(
            f"Respuesta generada — intent={intent} | "
            f"{response.usage.input_tokens} in / {response.usage.output_tokens} out tokens"
        )
        return respuesta

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error()
