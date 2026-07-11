# integrations/google_sheets.py — Integración con Google Sheets para CRM de leads

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

ANCHOS_COLUMNAS = [160, 150, 120, 180, 150, 220, 110, 90, 340, 140, 220]


def esta_configurado() -> bool:
    return bool(
        os.getenv("GOOGLE_SHEET_ID")
        and os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        and os.getenv("GOOGLE_PRIVATE_KEY")
    )


def _get_gc():
    import gspread
    info = {
        "type": "service_account",
        "project_id": "agentkit",
        "private_key_id": "key",
        "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", ""),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return gspread.service_account_from_dict(info)


def _limpiar_reglas_condicionales(ws) -> None:
    """Elimina todas las reglas de formato condicional existentes para evitar acumulación."""
    sheet_id = ws.id
    while True:
        try:
            ws.spreadsheet.batch_update({"requests": [
                {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}}
            ]})
        except Exception:
            break


def aplicar_formato_sheet(ws) -> None:
    """
    Aplica formato profesional a la hoja. Se llama después de cada guardado de lead.
    Cada grupo falla de forma independiente — el guardado nunca se interrumpe por el formato.
    """
    logger.info("Aplicando formato a Google Sheets")
    sheet_id = ws.id
    num_cols = len(ENCABEZADOS)
    col_fin = chr(64 + num_cols)  # 'K' para 11 columnas

    # ── Grupo 1: Congelar fila + estilo de encabezados ──────────────────────
    try:
        ws.freeze(rows=1)
    except Exception as e:
        logger.warning(f"[Formato] No se pudo congelar fila 1: {e}")

    try:
        ws.format(f"A1:{col_fin}1", {
            "backgroundColor": {"red": 0.12, "green": 0.24, "blue": 0.49},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "fontSize": 10,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        })
    except Exception as e:
        logger.warning(f"[Formato] No se pudo aplicar estilo a encabezados: {e}")

    # ── Grupo 2: Ancho de columnas + ajuste de texto + bordes ───────────────
    try:
        estructural = []

        for i, ancho in enumerate(ANCHOS_COLUMNAS):
            estructural.append({
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                    "properties": {"pixelSize": ancho},
                    "fields": "pixelSize",
                }
            })

        # WRAP en Resumen (col I, idx 8) y Próximo paso (col K, idx 10)
        for col_idx in [8, 10]:
            estructural.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                    "fields": "userEnteredFormat.wrapStrategy",
                }
            })

        color_ext = {"red": 0.60, "green": 0.60, "blue": 0.60}
        color_int = {"red": 0.85, "green": 0.85, "blue": 0.85}
        estilo_ext = {"style": "SOLID", "width": 1, "color": color_ext}
        estilo_int = {"style": "SOLID", "width": 1, "color": color_int}
        estructural.append({
            "updateBorders": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": num_cols},
                "top": estilo_ext, "bottom": estilo_ext,
                "left": estilo_ext, "right": estilo_ext,
                "innerHorizontal": estilo_int, "innerVertical": estilo_int,
            }
        })

        ws.spreadsheet.batch_update({"requests": estructural})
    except Exception as e:
        logger.warning(f"[Formato] No se pudo aplicar formato estructural: {e}")

    # ── Grupo 3: Colores alternos + formato condicional ─────────────────────
    try:
        _limpiar_reglas_condicionales(ws)

        visual = []
        datos_range    = {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": num_cols}
        urgencia_range = {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 7, "endColumnIndex": 8}
        estado_range   = {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 9, "endColumnIndex": 10}

        # Filas alternas
        visual.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [datos_range],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=MOD(ROW(),2)=0"}]},
                        "format": {"backgroundColor": {"red": 0.95, "green": 0.97, "blue": 1.0}},
                    },
                },
                "index": 0,
            }
        })

        # Urgencia: Alta=rojo, Media=amarillo, Baja=verde
        for idx, (valor, color) in enumerate([
            ("Alta",  {"red": 1.00, "green": 0.80, "blue": 0.80}),
            ("Media", {"red": 1.00, "green": 0.95, "blue": 0.70}),
            ("Baja",  {"red": 0.80, "green": 0.95, "blue": 0.80}),
        ]):
            visual.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [urgencia_range],
                        "booleanRule": {
                            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": valor}]},
                            "format": {"backgroundColor": color},
                        },
                    },
                    "index": 1 + idx,
                }
            })

        # Estado: 7 valores con colores distintos
        estados_base = [
            ("Nuevo lead",           {"red": 0.80, "green": 0.95, "blue": 0.80}),
            ("En conversación",      {"red": 1.00, "green": 0.95, "blue": 0.70}),
            ("Interesado",           {"red": 0.90, "green": 0.85, "blue": 1.00}),
            ("Cita agendada",        {"red": 0.80, "green": 0.90, "blue": 1.00}),
            ("Cotización pendiente", {"red": 1.00, "green": 0.85, "blue": 0.65}),
            ("Cerrado",              {"red": 0.50, "green": 0.85, "blue": 0.50}),
            ("Perdido",              {"red": 1.00, "green": 0.75, "blue": 0.75}),
        ]
        # Calidad de lead (Instagram/Facebook) — reutiliza la columna "Estado" para no
        # romper el formato existente. Verde/amarillo/rojo según nivel de interés.
        estados_calidad_lead = [
            ("Lead caliente", {"red": 0.40, "green": 0.80, "blue": 0.40}),
            ("Lead medio",    {"red": 1.00, "green": 0.90, "blue": 0.55}),
            ("Lead frío",     {"red": 1.00, "green": 0.70, "blue": 0.70}),
        ]
        for idx, (valor, color) in enumerate(estados_base + estados_calidad_lead):
            visual.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [estado_range],
                        "booleanRule": {
                            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": valor}]},
                            "format": {"backgroundColor": color},
                        },
                    },
                    "index": 4 + idx,
                }
            })

        ws.spreadsheet.batch_update({"requests": visual})
    except Exception as e:
        logger.warning(f"[Formato] Error aplicando formato condicional: {e}")

    logger.info("Formato aplicado correctamente")


def _campo(datos: dict, clave: str) -> str:
    valor = datos.get(clave, "")
    return valor if valor and valor != VALOR_VACIO else VALOR_VACIO


def _guardar_lead_sync(datos: dict) -> bool:
    telefono = datos.get("telefono", "desconocido")
    estado   = datos.get("estado", VALOR_VACIO)
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

        # Crear encabezados si la hoja está vacía (sin aplicar formato aquí)
        primera_fila = ws.row_values(1)
        if not primera_fila:
            ws.append_row(ENCABEZADOS)

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

        # Aplicar formato después de cada guardado (independiente del resultado)
        try:
            aplicar_formato_sheet(ws)
        except Exception as e:
            logger.warning(f"Error aplicando formato: {e}")

        return True

    except Exception as e:
        logger.error(f"Error al guardar lead en Sheets: {e}")
        return False


async def guardar_lead(datos: dict) -> bool:
    if not esta_configurado():
        logger.debug("Google Sheets no configurado — omitiendo guardado")
        return False
    return await asyncio.to_thread(_guardar_lead_sync, datos)
