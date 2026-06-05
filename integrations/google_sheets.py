# integrations/google_sheets.py — Integración con Google Sheets para CRM de leads
# Generado por AgentKit

import asyncio
import os
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


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


def _get_gc():
    """
    Retorna un cliente gspread autenticado via cuenta de servicio.
    Usa service_account_from_dict() que maneja el ciclo de vida del token internamente.
    """
    import gspread

    email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
    # Soporta tanto \n literales (como se pegan en Railway) como saltos de línea reales
    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")

    info = {
        "type": "service_account",
        "project_id": "agentkit",
        "private_key_id": "key",
        "client_email": email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return gspread.service_account_from_dict(info)


def _guardar_lead_sync(datos: dict) -> bool:
    """Guarda o actualiza una fila de lead en Google Sheets (sincrónico)."""
    telefono = datos.get("telefono", "desconocido")
    estado = datos.get("estado", "Nuevo")
    servicio = datos.get("servicio", "")

    logger.info(f"Intentando guardar lead en Google Sheets: {telefono}")
    logger.info(
        f"Datos del lead preparados — telefono={telefono}, "
        f"estado={estado}, servicio={servicio or '(sin especificar)'}"
    )

    try:
        gc = _get_gc()
        ws = gc.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

        # Crear encabezados si la hoja está vacía
        if not ws.row_values(1):
            ws.append_row(ENCABEZADOS)

        fila = [
            datos.get("fecha", datetime.now().strftime("%Y-%m-%d %H:%M")),
            datos.get("nombre", ""),
            telefono,
            datos.get("negocio", ""),
            datos.get("tipo_negocio", ""),
            servicio,
            datos.get("presupuesto", ""),
            datos.get("urgencia", ""),
            datos.get("resumen", ""),
            estado,
            datos.get("proximo_paso", ""),
        ]

        # Actualizar fila si el teléfono ya existe, sino agregar nueva
        logger.info(f"Buscando teléfono en Sheets: {telefono}")
        celda = ws.find(telefono)

        if celda:
            logger.info(f"Teléfono encontrado, actualizando fila {celda.row}")
            col_fin = chr(64 + len(fila))
            ws.update(f"A{celda.row}:{col_fin}{celda.row}", [fila])
        else:
            logger.info("Teléfono no encontrado, creando nueva fila")
            ws.append_row(fila)

        logger.info(f"Lead guardado correctamente en Sheets: {telefono}")
        return True

    except Exception as e:
        logger.error(f"Error al guardar lead en Sheets: {e}")
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
