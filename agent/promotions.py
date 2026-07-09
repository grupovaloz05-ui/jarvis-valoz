# agent/promotions.py — Promociones administrables por WhatsApp
#
# Permite que números autorizados (admin_numbers en client_config.yaml) actualicen
# la promoción actual del negocio mandando mensajes al número del bot. Los comandos
# administrativos se resuelven por keywords, SIN llamar al modelo de IA (más rápido
# y sin gastar tokens). Si un cliente no tiene promotion_settings configurado o
# promotion_settings.enabled es false, este módulo no hace nada — el bot sigue
# funcionando exactamente igual que antes.

import logging
import re
import unicodedata
from pathlib import Path

from agent.client_loader import get_admin_numbers, get_promotion_settings

logger = logging.getLogger("agentkit")

HELP_TEXT = (
    "Comandos disponibles:\n"
    "ACTUALIZAR PROMO: guarda una nueva promoción.\n"
    "VER PROMO ACTUAL: muestra la promoción guardada.\n"
    "BORRAR PROMO: elimina la promoción actual.\n"
    "PREPARAR STORY: genera texto listo para subir manualmente a estados."
)

NOT_AUTHORIZED_MESSAGE = (
    "No puedo actualizar promociones desde este número. Si eres parte del negocio, "
    "pide que agreguen tu número como administrador."
)

NO_PROMO_MESSAGE = (
    "Por ahora no tengo una promo cargada, pero puedo pasarte el menú o ayudarte con tu pedido."
)

UPDATED_MESSAGE = (
    "Listo, ya actualicé la promoción actual. Cuando un cliente pregunte por promos, "
    "le mostraré esta información."
)

DELETED_MESSAGE = "Listo, borré la promoción actual."

SAVE_ERROR_MESSAGE = (
    "Tuve un problema guardando la promoción. Intenta de nuevo en un momento, o avísale "
    "al equipo técnico si sigue fallando."
)

MISSING_CONTENT_MESSAGE = (
    'Manda el texto de la promoción, una imagen, o ambos después de "ACTUALIZAR PROMO".'
)

_COMANDOS: dict[str, str] = {
    "actualizar promo": "ACTUALIZAR_PROMO",
    "ver promo actual": "VER_PROMO_ACTUAL",
    "borrar promo": "BORRAR_PROMO",
    "ayuda admin": "AYUDA_ADMIN",
    "preparar story": "PREPARAR_STORY",
}

_CUSTOMER_PROMO_KEYWORDS = (
    "promos", "promociones", "promo de hoy", "promo del dia",
    "que promociones tienen", "que promocion tienen", "hay promo", "hay promos",
    "tienen promo", "tienen promos",
)

_STORY_MAX_CHARS = 200


def _normalizar(texto: str) -> str:
    """minúsculas, sin acentos, espacios colapsados — para comparar comandos/keywords."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_acentos.strip().lower())


def _normalizar_telefono(telefono: str) -> str:
    return re.sub(r"\D", "", telefono or "")


def es_admin(telefono: str) -> bool:
    admins = {_normalizar_telefono(n) for n in get_admin_numbers()}
    return bool(admins) and _normalizar_telefono(telefono) in admins


def es_pregunta_de_promo(texto: str) -> bool:
    msg = _normalizar(texto)
    return any(kw in msg for kw in _CUSTOMER_PROMO_KEYWORDS)


def detectar_comando_admin(texto: str) -> str | None:
    msg = _normalizar(texto)
    for prefijo, nombre in _COMANDOS.items():
        if msg.startswith(prefijo):
            return nombre
    return None


def _extraer_contenido(texto: str, comando: str) -> str:
    """Quita la primera aparición (case-insensitive) del comando y retorna el resto del texto."""
    patron = re.compile(re.escape(comando), re.IGNORECASE)
    resto = patron.sub("", texto or "", count=1)
    return resto.strip(" \n:-")


def _promotion_settings_activas() -> dict | None:
    settings = get_promotion_settings()
    if not settings or not settings.get("enabled"):
        return None
    return settings


def _texto_path(settings: dict) -> Path | None:
    ruta = settings.get("current_promo_text_path")
    return Path(ruta) if ruta else None


def _imagen_path(settings: dict) -> Path | None:
    ruta = settings.get("current_promo_image_path")
    return Path(ruta) if ruta else None


def obtener_promo_actual() -> tuple[str, Path | None]:
    """Retorna (texto_promo, ruta_imagen_o_None). texto_promo vacío si no hay."""
    settings = _promotion_settings_activas()
    if not settings:
        return "", None

    texto = ""
    ruta_texto = _texto_path(settings)
    if ruta_texto and ruta_texto.exists():
        try:
            texto = ruta_texto.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"No se pudo leer promoción actual ({ruta_texto}): {e}")

    ruta_imagen = _imagen_path(settings)
    imagen = ruta_imagen if (ruta_imagen and ruta_imagen.exists()) else None

    return texto, imagen


def guardar_promo_texto(texto: str) -> bool:
    settings = _promotion_settings_activas()
    if not settings or not settings.get("allow_text_promos", True):
        return False
    ruta = _texto_path(settings)
    if not ruta:
        return False
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto.strip() + "\n", encoding="utf-8")
        return True
    except Exception as e:
        logger.warning(f"No se pudo guardar promoción de texto ({ruta}): {e}")
        return False


def guardar_promo_imagen(contenido: bytes) -> bool:
    settings = _promotion_settings_activas()
    if not settings or not settings.get("allow_image_promos", True):
        return False
    ruta = _imagen_path(settings)
    if not ruta:
        return False
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        return True
    except Exception as e:
        logger.warning(f"No se pudo guardar imagen de promoción ({ruta}): {e}")
        return False


def borrar_promo() -> None:
    settings = _promotion_settings_activas()
    if not settings:
        return
    for ruta in (_texto_path(settings), _imagen_path(settings)):
        if ruta and ruta.exists():
            try:
                ruta.unlink()
            except Exception as e:
                logger.warning(f"No se pudo borrar {ruta}: {e}")


def _texto_corto_story(texto_promo: str, max_chars: int = _STORY_MAX_CHARS) -> str:
    if not texto_promo:
        return ""
    limpio = " ".join(texto_promo.split())
    if len(limpio) > max_chars:
        limpio = limpio[:max_chars].rstrip() + "…"
    return limpio


async def _enviar_imagen_promo(proveedor, telefono: str, ruta_imagen: Path) -> bool:
    """Sube y envía la imagen de promoción guardada. Nunca rompe el flujo si falla."""
    try:
        media_id = await proveedor.subir_media(str(ruta_imagen))
        if not media_id:
            logger.warning(f"No se pudo subir imagen de promoción para enviar a {telefono}")
            return False
        return await proveedor.enviar_imagen(telefono, media_id=media_id)
    except Exception as e:
        logger.warning(f"Excepción enviando imagen de promoción a {telefono}: {e}")
        return False


async def _actualizar_promo(proveedor, msg) -> str:
    texto_extra = _extraer_contenido(msg.texto or "", "ACTUALIZAR PROMO")
    intento_texto = bool(texto_extra)
    intento_imagen = msg.tipo == "image" and bool(msg.media_id)

    if not intento_texto and not intento_imagen:
        return MISSING_CONTENT_MESSAGE

    exito_imagen = True
    if intento_imagen:
        descarga = None
        try:
            descarga = await proveedor.descargar_media(msg.media_id)
        except Exception as e:
            logger.warning(f"No se pudo descargar imagen de promoción de {msg.telefono}: {e}")
        if descarga:
            contenido, _mime = descarga
            exito_imagen = guardar_promo_imagen(contenido)
        else:
            exito_imagen = False

    exito_texto = True
    if intento_texto:
        exito_texto = guardar_promo_texto(texto_extra)

    if not exito_texto or not exito_imagen:
        return SAVE_ERROR_MESSAGE

    return UPDATED_MESSAGE


async def _ver_promo_actual(proveedor, telefono: str, prefijo_admin: bool) -> str:
    texto, imagen = obtener_promo_actual()

    if not texto and not imagen:
        if prefijo_admin:
            return "Todavía no hay ninguna promoción guardada. Usa ACTUALIZAR PROMO para cargar una."
        return NO_PROMO_MESSAGE

    if imagen:
        await _enviar_imagen_promo(proveedor, telefono, imagen)

    if texto:
        return f"Promoción actual:\n\n{texto}" if prefijo_admin else texto

    return "Promoción actual guardada (solo imagen, sin texto)." if prefijo_admin else "Aquí tienes la promo de hoy."


async def _preparar_story(proveedor, telefono: str) -> str:
    texto, imagen = obtener_promo_actual()

    if not texto and not imagen:
        return "No tengo una promoción guardada para preparar el estado. Usa ACTUALIZAR PROMO primero."

    if imagen:
        await _enviar_imagen_promo(proveedor, telefono, imagen)

    corto = _texto_corto_story(texto)
    partes = []
    if corto:
        partes.append(f"Texto para tu estado:\n{corto}")
    partes.append("Puedes subir esto manualmente desde tu WhatsApp Business principal.")
    return "\n\n".join(partes)


async def _ejecutar_comando_admin(proveedor, msg, comando: str) -> str:
    try:
        if comando == "ACTUALIZAR_PROMO":
            return await _actualizar_promo(proveedor, msg)
        if comando == "VER_PROMO_ACTUAL":
            return await _ver_promo_actual(proveedor, msg.telefono, prefijo_admin=True)
        if comando == "BORRAR_PROMO":
            borrar_promo()
            return DELETED_MESSAGE
        if comando == "AYUDA_ADMIN":
            return HELP_TEXT
        if comando == "PREPARAR_STORY":
            return await _preparar_story(proveedor, msg.telefono)
    except Exception as e:
        logger.warning(f"Error ejecutando comando admin {comando} para {msg.telefono}: {e}")
        return SAVE_ERROR_MESSAGE
    return HELP_TEXT


async def manejar_mensaje_promocion(proveedor, msg) -> str | None:
    """
    Intercepta comandos de administración de promociones y consultas de clientes
    sobre promociones, sin llamar al modelo de IA.

    Retorna el texto de la respuesta ya enviada por WhatsApp si este módulo manejó
    el mensaje, o None si el mensaje debe seguir el flujo normal (IA).
    """
    settings = _promotion_settings_activas()
    if not settings:
        return None

    texto = msg.texto or ""
    comando = detectar_comando_admin(texto)

    if comando:
        if not es_admin(msg.telefono):
            respuesta = NOT_AUTHORIZED_MESSAGE
        else:
            respuesta = await _ejecutar_comando_admin(proveedor, msg, comando)
        await proveedor.enviar_mensaje(msg.telefono, respuesta)
        return respuesta

    if msg.tipo != "image" and es_pregunta_de_promo(texto):
        respuesta = await _ver_promo_actual(proveedor, msg.telefono, prefijo_admin=False)
        await proveedor.enviar_mensaje(msg.telefono, respuesta)
        return respuesta

    return None
