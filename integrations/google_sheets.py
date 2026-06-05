# integrations/google_sheets.py — Integración con Google Sheets para CRM de leads
# Generado por AgentKit

import asyncio
import os
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")

VALOR_VACIO = "No especificado"

ENCABEZADOS = [
    "Fecha y hora", "Nombre", "WhatsApp", "Negocio", "Tipo de negocio",
    "Servicio de interés", "Presupuesto", "Urgencia",
    "Resumen de conversación", "Estado", "Próximo paso",
]

# Ancho de columnas en píxeles (mismo orden que ENCABEZADOS)
ANCHOS_COLUMNAS = [160, 150, 120, 180, 150, 220, 110, 90, 340, 140, 220]


def esta_configurado() -> bool:
    """Retorna True si todas las variables de Google Sheets están presentes."""
    return bool(
        os.getenv("GOOGLE_SHEET_ID")
        and os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        and os.getenv("GOOGLE_PRIVATE_KEY")
    )


def _get_gc():
    """Retorna cliente gspread autenticado via cuenta de servicio."""
    import gspread

    email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
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


def _aplicar_formato(ws) -> None:
    """
    Aplica formato profesional al Sheet: encabezados, colores alternos, columnas.
    Si falla algún paso, registra warning y continúa — nunca interrumpe el guardado.
    """
    try:
        # Fila 1 congelada
        ws.freeze(rows=1)
    except Exception as e:
        logger.warning(f"No se pudo congelar fila 1: {e}")

    try:
        # Fondo oscuro + texto blanco + negrita en encabezados
        ws.format(f"A1:{chr(64 + len(ENCABEZADOS))}1", {
            "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "fontSize": 10,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        })
    except Exception as e:
        logger.warning(f"No se pudo aplicar formato a encabezados: {e}")

    try:
        # Ancho de columnas via Sheets API batch
        sheet_id = ws.id
        requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": i,
                        "endIndex": i + 1,
                    },
                    "properties": {"pixelSize": ancho},
                    "fields": "pixelSize",
                }
            }
            for i, ancho in enumerate(ANCHOS_COLUMNAS)
        ]
        ws.spreadsheet.batch_update({"requests": requests})
    except Exception as e:
        logger.warning(f"No se pudo ajustar ancho de columnas: {e}")

    try:
        # Colores alternos en filas de datos (fila 2 en adelante)
        sheet_id = ws.id
        ws.spreadsheet.batch_update({
            "requests": [{
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000}],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": "=MOD(ROW(),2)=0"}],
                            },
                            "format": {
                                "backgroundColor": {"red": 0.93, "green": 0.96, "blue": 1.0}
                            },
                        },
                    },
                    "index": 0,
                }
            }]
        })
    except Exception as e:
        logger.warning(f"No se pudieron aplicar colores alternos: {e}")

    logger.info("Formato aplicado al Google Sheet")


def _campo(datos: dict, clave: str) -> str:
    """Retorna el valor del campo o 'No especificado' si está vacío."""
    valor = datos.get(clave, "")
    return valor if valor and valor != VALOR_VACIO else VALOR_VACIO


def _guardar_lead_sync(datos: dict) -> bool:
    """Guarda o actualiza una fila de lead en Google Sheets (sincrónico)."""
    telefono = datos.get("telefono", "desconocido")
    estado = datos.get("estado", VALOR_VACIO)
    servicio = datos.get("servicio", VALOR_VACIO)

    logger.info(f"Guardando lead en Google Sheets: {telefono}")
    logger.info(
        f"Lead estructurado antes de guardar — "
        f"nombre={datos.get('nombre', VALOR_VACIO)}, "
        f"negocio={datos.get('negocio', VALOR_VACIO)}, "
        f"servicio={servicio}, estado={estado}"
    )

    try:
        gc = _get_gc()
        ws = gc.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

        # Crear encabezados y aplicar formato si la hoja está vacía
        primera_fila = ws.row_values(1)
        if not primera_fila:
            ws.append_row(ENCABEZADOS)
            _aplicar_formato(ws)

        fila = [
            datos.get("fecha", datetime.now().strftime("%Y-%m-%d %H:%M")),
            _campo(datos, "nombre"),
            telefono,
            _campo(datos, "negocio"),
            _campo(datos, "tipo_negocio"),
            _campo(datos, "servicio"),
            _campo(datos, "presupuesto"),
            _campo(datos, "urgencia"),
            _campo(datos, "resumen"),
            _campo(datos, "estado"),
            _campo(datos, "proximo_paso"),
        ]

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
    """
    if not esta_configurado():
        logger.debug("Google Sheets no configurado — omitiendo guardado")
        return False
    return await asyncio.to_thread(_guardar_lead_sync, datos)
