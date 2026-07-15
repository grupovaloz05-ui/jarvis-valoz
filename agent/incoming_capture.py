# agent/incoming_capture.py — Detección de posibles códigos de verificación
# (Meta/Facebook/WhatsApp) en mensajes entrantes, antes de que el bot los procese.

import re

_PALABRAS_ORIGEN = [
    ("whatsapp", "WhatsApp"),
    ("facebook", "Facebook"),
    ("meta", "Meta"),
]

_PALABRAS_VERIFICACION = [
    "verification", "verify", "verified", "code",
    "código", "codigo", "verificación", "verificacion",
]

_PATRON_CODIGO = re.compile(r"\b(\d{4,8})\b")


def detectar_codigo(texto: str) -> dict:
    """
    Analiza un texto entrante y determina si parece un código de verificación.

    Retorna:
      es_codigo: bool
      codigo: str (dígitos encontrados, o "" si no aplica)
      origen: "WhatsApp" | "Facebook" | "Meta" | "Desconocido" (solo si es_codigo)
      notas: "POSIBLE_CODIGO_VERIFICACION" | ""
    """
    texto = texto or ""
    texto_lower = texto.lower()

    match = _PATRON_CODIGO.search(texto)
    if not match:
        return {"es_codigo": False, "codigo": "", "origen": "", "notas": ""}

    menciona_verificacion = any(p in texto_lower for p in _PALABRAS_VERIFICACION)

    origen = "Desconocido"
    for clave, nombre in _PALABRAS_ORIGEN:
        if clave in texto_lower:
            origen = nombre
            break

    # Mensaje que es únicamente el número (ej. "123456") o que menciona
    # verificación / Meta / Facebook / WhatsApp junto a un número de 4-8 dígitos.
    solo_digitos = texto.strip() == match.group(1)
    parece_codigo = solo_digitos or menciona_verificacion or origen != "Desconocido"

    if not parece_codigo:
        return {"es_codigo": False, "codigo": "", "origen": "", "notas": ""}

    return {
        "es_codigo": True,
        "codigo": match.group(1),
        "origen": origen,
        "notas": "POSIBLE_CODIGO_VERIFICACION",
    }
