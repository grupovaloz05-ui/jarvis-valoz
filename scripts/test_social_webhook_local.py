# scripts/test_social_webhook_local.py — Prueba local del parser de Instagram/Facebook
#
# No llama a Meta ni a Claude, no requiere tokens ni credenciales: solo verifica que
# ProveedorInstagram/ProveedorFacebookMessenger extraen correctamente sender/texto de
# DMs y comentarios de ejemplo, y que la detección de keywords en comentarios funciona.
#
# Uso: python scripts/test_social_webhook_local.py

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.providers.instagram import ProveedorInstagram
from agent.providers.facebook_messenger import ProveedorFacebookMessenger
from agent.social_channels import detectar_keyword_comentario


class FakeRequest:
    """Sustituto mínimo de fastapi.Request — solo necesita .json()."""
    def __init__(self, payload: dict):
        self._payload = payload

    async def json(self):
        return self._payload


IG_DM_PAYLOAD = {
    "object": "instagram",
    "entry": [{
        "messaging": [{
            "sender": {"id": "1784140000000"},
            "recipient": {"id": "17841400000001"},
            "message": {"mid": "mid.123", "text": "Hola, quiero información de precios"},
        }]
    }],
}

IG_COMMENT_PAYLOAD = {
    "object": "instagram",
    "entry": [{
        "changes": [{
            "field": "comments",
            "value": {
                "id": "comment_ig_1",
                "text": "me interesa, cuánto cuesta",
                "from": {"id": "1784140000000"},
            },
        }]
    }],
}

FB_DM_PAYLOAD = {
    "object": "page",
    "entry": [{
        "messaging": [{
            "sender": {"id": "psid_de_prueba"},
            "recipient": {"id": "page_id"},
            "message": {"mid": "mid.456", "text": "Quiero un bot para mi negocio"},
        }]
    }],
}

FB_COMMENT_PAYLOAD = {
    "object": "page",
    "entry": [{
        "changes": [{
            "field": "feed",
            "value": {
                "item": "comment",
                "verb": "add",
                "comment_id": "comment_fb_1",
                "message": "quiero el bot para whatsapp",
                "from": {"id": "u1"},
            },
        }]
    }],
}


async def main():
    fallas = []

    ig = ProveedorInstagram()
    mensajes = await ig.parsear_webhook(FakeRequest(IG_DM_PAYLOAD))
    ok = (
        len(mensajes) == 1
        and mensajes[0].telefono == "1784140000000"
        and "precios" in mensajes[0].texto
        and mensajes[0].canal == "instagram"
    )
    print(f"[{'OK' if ok else 'FALLA'}] Instagram DM -> {mensajes}")
    if not ok:
        fallas.append("Instagram DM")

    comentarios = await ig.parsear_comentarios(FakeRequest(IG_COMMENT_PAYLOAD))
    ok = (
        len(comentarios) == 1
        and comentarios[0].comentario_id == "comment_ig_1"
        and comentarios[0].autor_id == "1784140000000"
    )
    print(f"[{'OK' if ok else 'FALLA'}] Instagram comentario -> {comentarios}")
    if not ok:
        fallas.append("Instagram comentario")

    fb = ProveedorFacebookMessenger()
    mensajes_fb = await fb.parsear_webhook(FakeRequest(FB_DM_PAYLOAD))
    ok = (
        len(mensajes_fb) == 1
        and mensajes_fb[0].telefono == "psid_de_prueba"
        and "bot" in mensajes_fb[0].texto
        and mensajes_fb[0].canal == "facebook"
    )
    print(f"[{'OK' if ok else 'FALLA'}] Facebook DM -> {mensajes_fb}")
    if not ok:
        fallas.append("Facebook DM")

    comentarios_fb = await fb.parsear_comentarios(FakeRequest(FB_COMMENT_PAYLOAD))
    ok = (
        len(comentarios_fb) == 1
        and comentarios_fb[0].comentario_id == "comment_fb_1"
        and comentarios_fb[0].autor_id == "u1"
    )
    print(f"[{'OK' if ok else 'FALLA'}] Facebook comentario -> {comentarios_fb}")
    if not ok:
        fallas.append("Facebook comentario")

    ok = detectar_keyword_comentario("Me interesa el PRECIO") and not detectar_keyword_comentario("qué bonito bebé")
    print(f"[{'OK' if ok else 'FALLA'}] Detección de keywords en comentarios")
    if not ok:
        fallas.append("Detección de keywords")

    print()
    if fallas:
        print(f"RESULTADO: {len(fallas)} prueba(s) fallaron: {', '.join(fallas)}")
        sys.exit(1)
    print("RESULTADO: todas las pruebas pasaron")


if __name__ == "__main__":
    asyncio.run(main())
