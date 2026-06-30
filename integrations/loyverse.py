# integrations/loyverse.py — Integración con Loyverse POS
# Cliente: Renzo Snacks
# Estado: INACTIVO por defecto (LOYVERSE_ENABLED=false)
# Activar cuando las credenciales estén configuradas en Railway.

import os
import json
import logging
import difflib
import httpx
from datetime import datetime

logger = logging.getLogger("agentkit")

LOYVERSE_API_BASE = os.getenv("LOYVERSE_API_BASE_URL", "https://api.loyverse.com/v1.0")


# ─── Estado de la integración ───────────────────────────────────

def loyverse_is_enabled() -> bool:
    """True si Loyverse está activo y tiene token configurado."""
    enabled = os.getenv("LOYVERSE_ENABLED", "false").lower() in ("true", "1", "yes")
    has_token = bool(os.getenv("LOYVERSE_ACCESS_TOKEN", "").strip())
    return enabled and has_token


def _get_headers() -> dict:
    token = os.getenv("LOYVERSE_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ─── Catálogo de productos ───────────────────────────────────────

async def loyverse_get_items() -> list[dict]:
    """Obtiene el catálogo de productos de Loyverse."""
    if not loyverse_is_enabled():
        logger.info("Loyverse inactivo — no se obtienen productos")
        return []

    store_id = os.getenv("LOYVERSE_STORE_ID", "")
    url = f"{LOYVERSE_API_BASE}/items"
    params = {"store_id": store_id} if store_id else {}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_get_headers(), params=params)

        if r.status_code == 200:
            return r.json().get("items", [])
        else:
            logger.error(f"Error obteniendo items de Loyverse: {r.status_code} — {r.text}")
            return []
    except Exception as e:
        logger.error(f"Excepción obteniendo items de Loyverse: {e}")
        return []


def loyverse_find_item_by_name(nombre: str, items: list[dict]) -> dict | None:
    """
    Busca un producto en el catálogo por nombre aproximado (fuzzy match).
    Retorna el item con mejor coincidencia, o None si no hay match aceptable.
    """
    if not items:
        return None

    nombres = [item.get("item_name", "") for item in items]
    matches = difflib.get_close_matches(nombre, nombres, n=1, cutoff=0.6)

    if matches:
        match_nombre = matches[0]
        for item in items:
            if item.get("item_name") == match_nombre:
                logger.info(f"Producto mapeado: '{nombre}' → '{match_nombre}'")
                return item

    logger.warning(f"Producto no encontrado en Loyverse: '{nombre}'")
    return None


# ─── Construcción del payload ────────────────────────────────────

def loyverse_map_order_items(pedido_productos: list[dict], catalogo: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Mapea los productos del pedido con el catálogo de Loyverse.

    Retorna:
        - line_items: lista con los items mapeados para el payload de Loyverse
        - sin_mapear: nombres de productos que no se encontraron
    """
    line_items = []
    sin_mapear = []

    for producto in pedido_productos:
        nombre = producto.get("item", "")
        cantidad = int(producto.get("cantidad", 1))
        item = loyverse_find_item_by_name(nombre, catalogo)

        if item:
            variant_id = None
            variants = item.get("variants", [])
            if variants:
                variant_id = variants[0].get("variant_id")

            line_items.append({
                "item_id": item.get("id"),
                "variant_id": variant_id,
                "quantity": cantidad,
                "price": item.get("price", 0),
                "note": producto.get("salsa", ""),
            })
        else:
            sin_mapear.append(nombre)

    return line_items, sin_mapear


def loyverse_format_order_payload(pedido: dict, line_items: list[dict]) -> dict:
    """
    Construye el payload para crear un receipt en Loyverse API.

    Args:
        pedido: dict con los datos del pedido (nombre, pago, tipo_servicio, etc.)
        line_items: items ya mapeados al catálogo

    Returns:
        payload listo para POST /receipts
    """
    store_id = os.getenv("LOYVERSE_STORE_ID", "")
    pos_device_id = os.getenv("LOYVERSE_POS_DEVICE_ID", "")
    employee_id = os.getenv("LOYVERSE_EMPLOYEE_ID", "")

    pago = pedido.get("pago", "efectivo").lower()
    payment_type_map = {
        "efectivo": "CASH",
        "tarjeta": "CARD",
        "transferencia": "TRANSFER",
    }
    payment_type = payment_type_map.get(pago, "CASH")

    note_parts = [
        f"Pedido WhatsApp — {pedido.get('nombre', '')}",
        f"Tipo: {pedido.get('tipo_servicio', '')}",
    ]
    if pedido.get("direccion"):
        note_parts.append(f"Dirección: {pedido['direccion']}")
    if pedido.get("comentarios"):
        note_parts.append(f"Comentarios: {pedido['comentarios']}")

    payload: dict = {
        "store_id": store_id,
        "receipt_number": f"WA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "note": " | ".join(note_parts),
        "line_items": line_items,
        "payments": [{"payment_type_id": payment_type}],
    }

    if pos_device_id:
        payload["pos_device_id"] = pos_device_id
    if employee_id:
        payload["employee_id"] = employee_id

    return payload


# ─── Crear receipt en Loyverse ───────────────────────────────────

async def loyverse_create_receipt(payload: dict) -> dict:
    """
    Envía el payload de receipt a la API de Loyverse.

    Retorna dict con:
        - ok: bool
        - receipt_id: str | None
        - error: str | None
    """
    url = f"{LOYVERSE_API_BASE}/receipts"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=_get_headers())

        if r.status_code in (200, 201):
            data = r.json()
            receipt_id = data.get("id") or data.get("receipt_number")
            logger.info(f"Pedido enviado a Loyverse — receipt_id: {receipt_id}")
            return {"ok": True, "receipt_id": receipt_id}
        else:
            logger.error(f"Error creando receipt en Loyverse: {r.status_code} — {r.text}")
            return {"ok": False, "error": f"{r.status_code}: {r.text}"}
    except Exception as e:
        logger.error(f"Excepción creando receipt en Loyverse: {e}")
        return {"ok": False, "error": str(e)}


# ─── Punto de entrada principal ──────────────────────────────────

async def loyverse_send_order(pedido: dict) -> dict:
    """
    Punto de entrada principal para enviar un pedido a Loyverse.

    Si Loyverse no está activo, retorna estado "pendiente".
    Si hay productos sin mapear, retorna estado "pendiente_revision".

    Args:
        pedido: dict con nombre, productos, pago, tipo_servicio, direccion, etc.

    Returns:
        dict con: ok, estado, receipt_id, sin_mapear, mensaje
    """
    if not loyverse_is_enabled():
        logger.info(f"Loyverse inactivo — pedido de {pedido.get('nombre')} queda pendiente")
        return {
            "ok": False,
            "estado": "pendiente_confirmacion_humana",
            "mensaje": "Loyverse no está activo. El pedido queda pendiente de confirmación manual.",
        }

    logger.info(f"Enviando pedido a Loyverse — cliente: {pedido.get('nombre')}")

    catalogo = await loyverse_get_items()
    productos = pedido.get("productos", [])
    line_items, sin_mapear = loyverse_map_order_items(productos, catalogo)

    if sin_mapear:
        logger.warning(f"Productos sin mapear en Loyverse: {sin_mapear}")
        return {
            "ok": False,
            "estado": "pendiente_revision",
            "sin_mapear": sin_mapear,
            "mensaje": f"Productos no encontrados en Loyverse: {', '.join(sin_mapear)}. Requiere revisión humana.",
        }

    if not line_items:
        return {
            "ok": False,
            "estado": "sin_productos",
            "mensaje": "No se pudo mapear ningún producto del pedido.",
        }

    payload = loyverse_format_order_payload(pedido, line_items)
    resultado = await loyverse_create_receipt(payload)

    if resultado.get("ok"):
        logger.info(f"Pedido enviado a Loyverse correctamente — {resultado.get('receipt_id')}")
        return {
            "ok": True,
            "estado": "enviado_a_loyverse",
            "receipt_id": resultado.get("receipt_id"),
            "mensaje": "Pedido registrado en Loyverse.",
        }
    else:
        logger.error(f"Error al enviar pedido a Loyverse: {resultado.get('error')}")
        return {
            "ok": False,
            "estado": "error_loyverse",
            "error": resultado.get("error"),
            "mensaje": "Error al conectar con Loyverse. Pedido pendiente de confirmación manual.",
        }


# ─── Procesamiento de pedido confirmado ──────────────────────────

async def procesar_pedido_confirmado(telefono: str, pedido_raw: dict) -> str:
    """
    Procesa un pedido confirmado: intenta enviarlo a Loyverse.
    Retorna el mensaje que el bot debe transmitir al cliente.
    """
    resultado = await loyverse_send_order(pedido_raw)
    estado = resultado.get("estado", "")

    log_prefix = f"[{telefono}] Pedido {pedido_raw.get('nombre', '')} —"

    if estado == "enviado_a_loyverse":
        logger.info(f"{log_prefix} enviado a Loyverse ({resultado.get('receipt_id')})")
        return "Listo, tu pedido fue registrado. En un momento el equipo lo confirma contigo."

    elif estado == "pendiente_revision":
        sin_mapear = resultado.get("sin_mapear", [])
        logger.warning(f"{log_prefix} pendiente revisión — productos sin mapear: {sin_mapear}")
        return "Listo, ya tengo los datos de tu pedido. Lo paso al equipo para que te confirmen."

    elif estado == "pendiente_confirmacion_humana":
        logger.info(f"{log_prefix} pendiente — Loyverse inactivo")
        return "Listo, ya tengo los datos de tu pedido. Lo paso al equipo para que te confirmen."

    else:
        logger.error(f"{log_prefix} error — {resultado.get('error', 'desconocido')}")
        return "Recibí tu pedido. El equipo te confirmará en un momento."
