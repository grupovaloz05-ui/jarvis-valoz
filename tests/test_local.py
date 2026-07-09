# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial
from agent.promotions import manejar_mensaje_promocion
from agent.client_loader import get_admin_numbers
from agent.providers.base import MensajeEntrante

TELEFONO_TEST = "test-local-001"


class ProveedorLocalFalso:
    """
    Proveedor falso para probar comandos de promociones en terminal, sin WhatsApp real.
    Imprime en consola en vez de llamar a la Graph API. subir_media/descargar_media
    no están disponibles en este modo (no hay imágenes reales en la terminal).
    """

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        print(f"Jarvis: {mensaje}\n")
        return True

    async def enviar_imagen(self, telefono: str, media_id=None, image_url=None, caption=None) -> bool:
        print("[Jarvis enviaría aquí la imagen de la promoción guardada — no disponible en test local]")
        return True

    async def subir_media(self, ruta_local: str) -> str | None:
        return "media-id-fake-local"

    async def descargar_media(self, media_id: str):
        return None


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   Jarvis — Test Local | Valoz Digital")
    print("=" * 55)
    print()
    print("  Escribe mensajes como si fueras un cliente.")
    print("  Comandos especiales:")
    print("    'limpiar'      — borra el historial")
    print("    'salir'        — termina el test")
    print("    'ADMIN: texto' — simula el mensaje como si lo mandara un número")
    print("                     administrador (el primero en admin_numbers del")
    print("                     cliente activo). Ej: 'ADMIN: ACTUALIZAR PROMO")
    print("                     10 alitas + papas en $149'")

    admins = get_admin_numbers()
    if admins:
        print(f"  Admin de prueba disponible: {admins[0]}")
    else:
        print("  Este cliente no tiene admin_numbers configurados — 'ADMIN:' no autorizará nada.")
    print()
    print("-" * 55)
    print()

    proveedor_falso = ProveedorLocalFalso()

    while True:
        try:
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        es_admin_test = mensaje.upper().startswith("ADMIN:")
        if es_admin_test:
            mensaje = mensaje.split(":", 1)[1].strip()
            telefono = admins[0] if admins else "sin-admin-configurado"
        else:
            telefono = TELEFONO_TEST

        msg = MensajeEntrante(telefono=telefono, texto=mensaje, mensaje_id="local-test", es_propio=False)
        respuesta_promocion = await manejar_mensaje_promocion(proveedor_falso, msg)
        if respuesta_promocion is not None:
            await guardar_mensaje(telefono, "user", mensaje)
            await guardar_mensaje(telefono, "assistant", respuesta_promocion)
            continue

        historial = await obtener_historial(TELEFONO_TEST)

        print("\nJarvis: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial)
        print(respuesta)
        print()

        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
