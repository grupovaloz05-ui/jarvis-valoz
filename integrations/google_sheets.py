# integrations/google_sheets.py — Integración con Google Sheets para CRM de leads
# Generado por AgentKit

import asyncio
import os
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


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
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def esta_configurado() -> bool:
    """Retorna True si todas las variables de Google Sheets están presentes."""
    return bool(
        os.getenv("GOOGLE_SHEET_ID")
        and os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        and os.getenv("GOOGLE_PRIVATE_KEY")
    )


ENCABEZADOS = [
    "Fecha y hora", "Nombre", "WhatsApp", "Negocio", "Tipo de negocio",
    "Servicio de interés", "Presupuesto", "Urgencia",
    "Resumen de conversación", "Estado", "Próximo paso",
]


def _guardar_lead_sync(datos: dict) -> bool:
    """Guarda o actualiza una fila de lead en Google Sheets (sincrónico)."""
    import gspread

    try:
        creds = _crear_credenciales()
        if not creds:
            logger.warning("Credenciales de Google no válidas")
            return False

        gc = gspread.Client(auth=creds)
        ws = gc.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

        # Crear encabezados si la hoja está vacía
        if not ws.row_values(1):
            ws.append_row(ENCABEZADOS)

        telefono = datos.get("telefono", "")
        fila = [
            datos.get("fecha", datetime.now().strftime("%Y-%m-%d %H:%M")),
            datos.get("nombre", ""),
            telefono,
            datos.get("negocio", ""),
            datos.get("tipo_negocio", ""),
            datos.get("servicio", ""),
            datos.get("presupuesto", ""),
            datos.get("urgencia", ""),
            datos.get("resumen", ""),
            datos.get("estado", "Nuevo"),
            datos.get("proximo_paso", ""),
        ]

        # Actualizar fila si el teléfono ya existe, sino agregar nueva
        try:
            celda = ws.find(telefono)
            col_fin = chr(64 + len(fila))
            ws.update(f"A{celda.row}:{col_fin}{celda.row}", [fila])
            logger.info(f"Lead actualizado en Sheets: {telefono}")
        except gspread.exceptions.CellNotFound:
            ws.append_row(fila)
            logger.info(f"Nuevo lead guardado en Sheets: {telefono}")

        return True

    except Exception as e:
        logger.error(f"Error en Google Sheets: {e}")
        return False


async def guardar_lead(datos: dict) -> bool:
    """
    Guarda o actualiza un lead en Google Sheets.
    Si Sheets no está configurado, retorna False sin lanzar error.

    Args:
        datos: dict con campos opcionales: telefono, nombre, negocio, tipo_negocio,
               servicio, presupuesto, urgencia, resumen, estado, proximo_paso
    """
    if not esta_configurado():
        logger.debug("Google Sheets no configurado — omitiendo guardado")
        return False
    return await asyncio.to_thread(_guardar_lead_sync, datos)
