# agent/lead_parser.py — Extractor de datos estructurados de lead desde conversación
# Usa Claude Haiku para parsear la conversación y rellenar todos los campos del CRM.

import json
import logging
import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

VALOR_VACIO = "No especificado"
CAMPOS = ["nombre", "negocio", "tipo_negocio", "servicio",
          "presupuesto", "urgencia", "resumen", "estado", "proximo_paso"]


async def extraer_datos_lead(historial: list[dict], telefono: str) -> dict:
    """
    Parsea el historial de conversación con Claude Haiku y retorna un dict
    con todos los campos del lead. Los campos no encontrados llevan "No especificado".
    """
    base = {campo: VALOR_VACIO for campo in CAMPOS}
    base["telefono"] = telefono

    if not historial:
        return base

    # Usar los últimos 14 mensajes para no exceder tokens
    conversacion = "\n".join(
        f"{'CLIENTE' if m['role'] == 'user' else 'AGENTE'}: {m['content']}"
        for m in historial[-14:]
    )

    prompt = f"""Analiza esta conversación de WhatsApp entre un agente de ventas y un cliente.
Extrae los datos del cliente. Si un dato no se mencionó, escribe exactamente: "No especificado".

CONVERSACIÓN:
{conversacion}

Responde ÚNICAMENTE con JSON válido, sin texto extra ni bloques de código:
{{
  "nombre": "nombre completo del cliente o No especificado",
  "negocio": "nombre del negocio o No especificado",
  "tipo_negocio": "giro del negocio o No especificado",
  "servicio": "servicio de interés o No especificado",
  "presupuesto": "presupuesto mencionado o No especificado",
  "urgencia": "Alta | Media | Baja | No especificado",
  "resumen": "resumen de la conversación en 1-2 oraciones",
  "estado": "Nuevo lead | En conversación | Interesado | Cita agendada | Cotización pendiente | Cerrado | Perdido",
  "proximo_paso": "acción recomendada o No especificado"
}}"""

    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Limpiar bloques markdown si el modelo los agrega
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        datos = json.loads(raw)

        # Garantizar que todos los campos existen y no están vacíos
        for campo in CAMPOS:
            valor = datos.get(campo, "").strip()
            datos[campo] = valor if valor else VALOR_VACIO

        datos["telefono"] = telefono
        logger.info(
            f"Lead estructurado — nombre={datos['nombre']}, "
            f"negocio={datos['negocio']}, servicio={datos['servicio']}, "
            f"estado={datos['estado']}"
        )
        return datos

    except Exception as e:
        logger.error(f"Error extrayendo datos del lead: {e}")
        return base
