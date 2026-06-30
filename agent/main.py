# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.lead_parser import extraer_datos_lead
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor
from agent.tools import obtener_y_limpiar_confirmadas
from agent.client_loader import get_client_id, get_business_name
from agent.whatsapp_media import send_menu_image_if_requested
from integrations.google_sheets import guardar_lead, esta_configurado as sheets_activo
from integrations.google_calendar import crear_evento_cita, esta_configurado as calendar_activo

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
CLIENT_ID = get_client_id()

import re as _re
import json as _json

_PEDIDO_PREFIX = "[PEDIDO_RENZO:"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Cliente cargado: {get_business_name()}" if CLIENT_ID else "Cliente: Valoz Digital (default)")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    logger.info(f"Google Sheets: {'activo' if sheets_activo() else 'no configurado'}")
    logger.info(f"Google Calendar: {'activo' if calendar_activo() else 'no configurado'}")
    if CLIENT_ID == "renzosnacks":
        from integrations.loyverse import loyverse_is_enabled
        logger.info(f"Loyverse: {'activo' if loyverse_is_enabled() else 'inactivo'}")
    yield


app = FastAPI(
    title="Jarvis — Agente WhatsApp de Valoz Digital",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "agente": "Jarvis",
        "negocio": "Valoz Digital",
        "sheets": sheets_activo(),
        "calendar": calendar_activo(),
    }


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


async def _procesar_citas_confirmadas():
    """
    Procesa citas confirmadas durante este turno de conversación.
    Intenta crear evento en Calendar; si falla, guarda en Sheets como pendiente.
    """
    try:
        for cita in obtener_y_limpiar_confirmadas():
            resultado_calendar = await crear_evento_cita(cita)

            if resultado_calendar.get("ok"):
                estado = "Cita agendada en Calendar"
                proximo_paso = f"Confirmar con cliente: {cita.get('disponibilidad')}"
            else:
                estado = "Pendiente de agendar"
                proximo_paso = f"Agendar manualmente: {cita.get('disponibilidad')}"

            await guardar_lead({
                **cita,
                "estado": estado,
                "proximo_paso": proximo_paso,
                "resumen": f"Solicita cita para: {cita.get('servicio')}",
            })
            logger.info(f"Cita procesada para {cita.get('telefono')} — estado: {estado}")
    except Exception as e:
        logger.error(f"Error en _procesar_citas_confirmadas: {e}")


def _extraer_pedido_renzo(respuesta: str) -> tuple[dict | None, str]:
    """
    Si la respuesta contiene [PEDIDO_RENZO:{...}], extrae el JSON y retorna
    (pedido_dict, respuesta_limpia). Si no hay pedido, retorna (None, respuesta).
    Usa JSONDecoder para manejar objetos anidados correctamente.
    """
    if _PEDIDO_PREFIX not in respuesta:
        return None, respuesta

    try:
        prefix_idx = respuesta.index(_PEDIDO_PREFIX)
        json_start = prefix_idx + len(_PEDIDO_PREFIX)
        decoder = _json.JSONDecoder()
        pedido, json_end = decoder.raw_decode(respuesta, json_start)
        # Encuentra el ']' de cierre del bloque [PEDIDO_RENZO:...]
        close_idx = respuesta.index("]", json_end)
        bloque = respuesta[prefix_idx : close_idx + 1]
        respuesta_limpia = respuesta.replace(bloque, "").strip()
        return pedido, respuesta_limpia
    except Exception as e:
        logger.warning(f"No se pudo parsear PEDIDO_RENZO: {e}")
        return None, respuesta


async def _procesar_pedido_renzosnacks(telefono: str, pedido: dict):
    """Envía el pedido confirmado a Loyverse en background."""
    try:
        logger.info(f"Pedido confirmado — {telefono} | cliente: {pedido.get('nombre')}")
        from integrations.loyverse import procesar_pedido_confirmado
        await procesar_pedido_confirmado(telefono, pedido)
    except Exception as e:
        logger.error(f"Error procesando pedido Renzo Snacks [{telefono}]: {e}")


async def _registrar_contacto(telefono: str, historial_completo: list[dict]):
    """Extrae datos estructurados del lead y los guarda en Sheets (fire-and-forget)."""
    try:
        datos = await extraer_datos_lead(historial_completo, telefono)
        datos["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        await guardar_lead(datos)
    except Exception as e:
        logger.error(f"Error en _registrar_contacto: {e}")


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp, genera respuesta con Claude y la envía.
    Dispara integraciones con Google Sheets y Calendar en background.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)

            # Extraer pedido estructurado si el bot lo incluyó (solo Renzo Snacks)
            pedido_confirmado = None
            if CLIENT_ID == "renzosnacks":
                pedido_confirmado, respuesta = _extraer_pedido_renzo(respuesta)

            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar imagen del menú si el cliente la pidió (antes del texto)
            await send_menu_image_if_requested(proveedor, msg.telefono, msg.texto)

            await proveedor.enviar_mensaje(msg.telefono, respuesta)
            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

            # Historial completo incluyendo el turno actual para la extracción de lead
            historial_completo = historial + [
                {"role": "user", "content": msg.texto},
                {"role": "assistant", "content": respuesta},
            ]

            # Integraciones en background — no bloquean la respuesta a WhatsApp
            if pedido_confirmado:
                logger.info(f"Pedido iniciado — {msg.telefono}")
                asyncio.create_task(_procesar_pedido_renzosnacks(msg.telefono, pedido_confirmado))
            asyncio.create_task(_registrar_contacto(msg.telefono, historial_completo))
            asyncio.create_task(_procesar_citas_confirmadas())

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
