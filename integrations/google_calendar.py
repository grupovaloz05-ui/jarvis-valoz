# integrations/google_calendar.py — Integración con Google Calendar para citas
# Generado por AgentKit

import asyncio
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("agentkit")

SCOPES_CALENDAR = ["https://www.googleapis.com/auth/calendar"]


def _crear_credenciales():
    """Construye credenciales de cuenta de servicio desde variables de entorno."""
    from google.oauth2 import service_account

    email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")

    if not email or "BEGIN" not in private_key:
        return None

    info = {
        "type": "service_account",
        "client_email": email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES_CALENDAR)


def esta_configurado() -> bool:
    """Retorna True si Google Calendar está configurado."""
    return bool(
        os.getenv("GOOGLE_CALENDAR_ID")
        and os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        and os.getenv("GOOGLE_PRIVATE_KEY")
    )


def _crear_evento_sync(datos: dict) -> dict:
    """Crea un evento en Google Calendar (sincrónico)."""
    from googleapiclient.discovery import build

    try:
        creds = _crear_credenciales()
        if not creds:
            return {"ok": False, "fallback": True}

        service = build("calendar", "v3", credentials=creds)
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        timezone = os.getenv("TIMEZONE", "America/Mexico_City")

        # Inicio: mañana a las 10am por defecto (en producción se usa el slot real)
        inicio = datetime.now() + timedelta(days=1)
        inicio = inicio.replace(hour=10, minute=0, second=0, microsecond=0)
        fin = inicio + timedelta(hours=1)

        nombre = datos.get("nombre", "Cliente")
        telefono = datos.get("telefono", "")
        negocio = datos.get("negocio", "")
        servicio = datos.get("servicio", "consulta")
        disponibilidad = datos.get("disponibilidad", "A confirmar")
        resumen = datos.get("resumen", "")

        evento = {
            "summary": f"Llamada de cotización — {nombre} ({negocio})",
            "description": (
                f"Cliente: {nombre}\n"
                f"WhatsApp: {telefono}\n"
                f"Negocio: {negocio}\n"
                f"Servicio de interés: {servicio}\n"
                f"Disponibilidad indicada: {disponibilidad}\n\n"
                f"Resumen:\n{resumen}"
            ),
            "start": {"dateTime": inicio.isoformat(), "timeZone": timezone},
            "end": {"dateTime": fin.isoformat(), "timeZone": timezone},
        }

        resultado = service.events().insert(calendarId=calendar_id, body=evento).execute()
        logger.info(f"Evento creado en Calendar: {resultado.get('htmlLink')}")
        return {"ok": True, "evento_id": resultado.get("id"), "link": resultado.get("htmlLink")}

    except Exception as e:
        logger.error(f"Error creando evento en Calendar: {e}")
        return {"ok": False, "fallback": True}


async def crear_evento_cita(datos: dict) -> dict:
    """
    Crea un evento en Google Calendar para una cita.
    Si Calendar no está configurado o falla, retorna {"ok": False, "fallback": True}
    para que el caller lo guarde en Sheets como "Pendiente de agendar".

    Args:
        datos: dict con nombre, telefono, negocio, servicio, disponibilidad, resumen
    """
    if not esta_configurado():
        logger.info("Google Calendar no configurado — usando fallback a Sheets")
        return {"ok": False, "fallback": True}
    return await asyncio.to_thread(_crear_evento_sync, datos)
