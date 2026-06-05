# agent/tools.py — Herramientas del agente Jarvis para Valoz Digital
# Generado por AgentKit

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "No disponible"),
        "esta_abierto": True,
    }


def buscar_en_knowledge(consulta: str) -> str:
    """Busca información relevante en los archivos de /knowledge."""
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    return "\n---\n".join(resultados) if resultados else "No encontré información específica sobre eso."


# ────────────────────────────────────────────────────────────
# FAQ
# ────────────────────────────────────────────────────────────

def obtener_info_servicios() -> str:
    return buscar_en_knowledge("servicios")


def obtener_info_precios(servicio: str = "") -> str:
    return buscar_en_knowledge(servicio) if servicio else buscar_en_knowledge("precio")


# ────────────────────────────────────────────────────────────
# Agendamiento de citas
# ────────────────────────────────────────────────────────────

_citas_pendientes: dict[str, dict] = {}

# Cola de citas confirmadas para que main.py las procese con las integraciones
_citas_confirmadas: list[dict] = []


def iniciar_agendamiento(telefono: str) -> dict:
    """Inicia el flujo de agendamiento para un número de teléfono."""
    _citas_pendientes[telefono] = {
        "etapa": "nombre",
        "datos": {},
        "iniciado_en": datetime.utcnow().isoformat(),
    }
    return {"ok": True, "siguiente": "nombre"}


def guardar_dato_cita(telefono: str, campo: str, valor: str) -> dict:
    """Guarda un campo del formulario de agendamiento."""
    if telefono not in _citas_pendientes:
        iniciar_agendamiento(telefono)

    cita = _citas_pendientes[telefono]
    cita["datos"][campo] = valor

    campos_requeridos = ["nombre", "whatsapp", "servicio", "disponibilidad"]
    completados = [c for c in campos_requeridos if c in cita["datos"]]

    if len(completados) == len(campos_requeridos):
        cita["etapa"] = "confirmada"
        return {"ok": True, "completa": True, "datos": cita["datos"]}

    return {"ok": True, "completa": False, "completados": completados}


def obtener_cita_pendiente(telefono: str) -> dict:
    """Retorna los datos de la cita en progreso para un número."""
    return _citas_pendientes.get(telefono, {})


def confirmar_cita(telefono: str) -> str:
    """
    Genera el mensaje de confirmación y encola la cita para que main.py
    la procese con Google Sheets y Google Calendar.
    """
    cita = _citas_pendientes.pop(telefono, {})
    datos = cita.get("datos", {})
    nombre = datos.get("nombre", "cliente")
    servicio = datos.get("servicio", "consulta")
    disponibilidad = datos.get("disponibilidad", "horario acordado")

    # Encolar para procesamiento con integraciones en main.py
    _citas_confirmadas.append({
        "telefono": telefono,
        "nombre": nombre,
        "negocio": datos.get("negocio", ""),
        "servicio": servicio,
        "disponibilidad": disponibilidad,
        "whatsapp": datos.get("whatsapp", telefono),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    return (
        f"Listo, {nombre}. Tu solicitud de cita para {servicio} fue registrada. "
        f"Nuestro equipo te contactará en el horario: {disponibilidad}. "
        f"¡Gracias por confiar en Valoz Digital!"
    )


def obtener_y_limpiar_confirmadas() -> list[dict]:
    """Retorna las citas confirmadas y limpia la cola. Llamado desde main.py."""
    confirmadas = _citas_confirmadas.copy()
    _citas_confirmadas.clear()
    return confirmadas


# ────────────────────────────────────────────────────────────
# Escalación a humano
# ────────────────────────────────────────────────────────────

def escalar_a_humano(telefono: str, motivo: str = "") -> str:
    """Registra que este cliente debe ser atendido por un humano."""
    logger.info(f"[ESCALAR] {telefono} — motivo: {motivo}")
    return (
        "Entendido, voy a conectarte con un asesor de Valoz Digital "
        "para que pueda ayudarte de forma personalizada. "
        "En breve alguien de nuestro equipo se pondrá en contacto contigo."
    )
