#!/usr/bin/env python3
"""
scripts/create_client_template.py — Genera la estructura base para un nuevo cliente.

Uso:
    python3 scripts/create_client_template.py

Crea una carpeta con:
- client_config.yaml prellenado
- knowledge/ con archivos template
- .env.example con campos vacíos
- CHECKLIST.md específico del cliente
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent


def preguntar(campo: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    resp = input(f"  {campo}{hint}: ").strip()
    return resp or default


def main():
    print("\n" + "=" * 55)
    print("  Valoz Digital — Crear nuevo agente para cliente")
    print("=" * 55 + "\n")

    print("Datos del cliente:")
    business_name  = preguntar("Nombre del negocio")
    agent_name     = preguntar("Nombre del agente IA", "Asistente")
    business_type  = preguntar("Tipo de negocio (ej: cafetería, clínica...)")
    contact_name   = preguntar("Nombre del contacto humano")
    contact_phone  = preguntar("WhatsApp del contacto humano (+52...)")
    business_hours = preguntar("Horario de atención", "Lunes a Viernes 9:00 AM a 6:00 PM")
    tone           = preguntar("Tono del agente", "Amigable, profesional y orientado a ventas")

    # Carpeta destino
    slug = business_name.lower().replace(" ", "_").replace("/", "_")
    destino = REPO_ROOT.parent / f"agente-{slug}"
    if destino.exists():
        sobreescribir = input(f"\n  La carpeta {destino.name} ya existe. ¿Sobreescribir? (s/n): ")
        if sobreescribir.lower() != "s":
            print("  Cancelado.")
            return

    print(f"\n  Creando estructura en: {destino}/")

    # Copiar repositorio completo (sin .git, .env, agentkit.db)
    ignorar = shutil.ignore_patterns(
        ".git", ".env", "agentkit.db", "__pycache__", "*.pyc", ".DS_Store",
        "node_modules",
    )
    shutil.copytree(REPO_ROOT, destino, ignore=ignorar)

    # Generar client_config.yaml prellenado
    config_content = f"""# config/client_config.yaml — {business_name}
# Generado por create_client_template.py el {datetime.now().strftime("%Y-%m-%d")}

CLIENT_NAME: "{business_name}"
CONTACT_NAME: "{contact_name}"
CONTACT_PHONE: "{contact_phone}"

BUSINESS_NAME: "{business_name}"
BUSINESS_TYPE: "{business_type}"
BUSINESS_DESCRIPTION: >
  [Describe aquí qué hace {business_name}, a quién atiende y cuál es su propuesta de valor.]

AGENT_NAME: "{agent_name}"
TONE: "{tone}"

BUSINESS_HOURS: "{business_hours}"

SERVICES:
  - nombre: "[Servicio 1]"
    precio: "$X,XXX – $X,XXX MXN"
  - nombre: "[Servicio 2]"
    precio: "$X,XXX – $X,XXX MXN"

FAQ:
  - pregunta: "[Pregunta frecuente 1]"
    respuesta: "[Respuesta 1]"
  - pregunta: "[Pregunta frecuente 2]"
    respuesta: "[Respuesta 2]"

QUALIFICATION_QUESTIONS:
  - "[¿Pregunta para calificar al prospecto?]"
  - "[¿Qué objetivo tiene?]"
  - "[¿Cuál es su presupuesto?]"

LEAD_FIELDS:
  - nombre
  - negocio
  - servicio_interes
  - presupuesto
  - urgencia
  - whatsapp

OBJETIVO_LEAD: "[Agendar llamada / enviar cotización / confirmar cita]"
PROXIMO_PASO_IDEAL: "[Paso 1] → [Paso 2] → [Cierre]"

WHATSAPP_PROVIDER: "meta"
"""
    (destino / "config" / "client_config.yaml").write_text(config_content, encoding="utf-8")

    # Limpiar knowledge/ del cliente (dejar solo templates vacíos)
    knowledge_dir = destino / "knowledge"
    for f in knowledge_dir.glob("*.md"):
        f.unlink()

    # Crear knowledge/ con encabezados listos para editar
    knowledge_files = {
        "servicios.md":  f"# Servicios — {business_name}\n\n[Detalla aquí cada servicio: qué incluye, tiempo de entrega, para quién es ideal.]\n",
        "precios.md":    f"# Precios — {business_name}\n\n[Agrega rangos de precios por servicio. Recuerda: el agente nunca da precio final cerrado.]\n",
        "faq.md":        f"# Preguntas frecuentes — {business_name}\n\n[Agrega las 5 a 10 preguntas más comunes de tus clientes con respuestas claras.]\n",
        "politicas.md":  f"# Políticas — {business_name}\n\n[Formas de pago, garantías, tiempos de entrega, política de cancelaciones.]\n",
        "objeciones.md": f"# Manejo de objeciones — {business_name}\n\n[¿Cómo responde el agente cuando dicen que es caro, que lo van a pensar, etc.?]\n",
    }
    for nombre, contenido in knowledge_files.items():
        (knowledge_dir / nombre).write_text(contenido, encoding="utf-8")

    # Crear .env específico del cliente
    env_content = f"""# .env — {business_name}
# Generado el {datetime.now().strftime("%Y-%m-%d")}
# NUNCA subas este archivo a GitHub.

ANTHROPIC_API_KEY=

WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=
META_PHONE_NUMBER_ID=
META_VERIFY_TOKEN={slug}-jarvis-2026

GOOGLE_SHEET_ID=
GOOGLE_SERVICE_ACCOUNT_EMAIL=
GOOGLE_PRIVATE_KEY=
GOOGLE_CALENDAR_ID=

TIMEZONE=America/Mexico_City
ENVIRONMENT=production
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./agentkit.db
"""
    (destino / ".env").write_text(env_content, encoding="utf-8")
    (destino / ".env.example").write_text(env_content.replace(
        "# NUNCA subas este archivo a GitHub.",
        "# Copia este archivo como .env y llena tus datos.",
    ), encoding="utf-8")

    # Eliminar .env del .gitignore si está hardcodeado (ya debería estar)
    gitignore = destino / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(".env\nagentkit.db\n__pycache__/\n*.pyc\n.DS_Store\n")

    # Checklist del cliente
    checklist = f"""# Checklist — {business_name}
# Generado por create_client_template.py el {datetime.now().strftime("%Y-%m-%d")}

## Datos del negocio
- [ ] Nombre del negocio: {business_name}
- [ ] Tipo de negocio: {business_type}
- [ ] Descripción del negocio
- [ ] Servicios y precios actualizados
- [ ] Preguntas frecuentes (mínimo 5)
- [ ] Horario de atención: {business_hours}
- [ ] Nombre y WhatsApp del contacto humano: {contact_name} / {contact_phone}

## Archivos de configuración
- [ ] `config/client_config.yaml` — editado con datos reales
- [ ] `config/prompts.yaml` — system prompt adaptado al negocio
- [ ] `knowledge/servicios.md` — descripción detallada de servicios
- [ ] `knowledge/precios.md` — rangos de precios
- [ ] `knowledge/faq.md` — preguntas frecuentes
- [ ] `knowledge/politicas.md` — políticas del negocio
- [ ] `knowledge/objeciones.md` — manejo de objeciones

## Google Sheets
- [ ] Google Sheet creado: "Leads — {business_name}"
- [ ] Sheet compartido con la cuenta de servicio (permiso Editor)
- [ ] `GOOGLE_SHEET_ID` copiado
- [ ] Primer lead de prueba guardado correctamente
- [ ] Formato automático aplicado (encabezados, colores, condicionales)

## Google Calendar (opcional)
- [ ] Calendar compartido con la cuenta de servicio
- [ ] `GOOGLE_CALENDAR_ID` configurado
- [ ] Cita de prueba creada correctamente

## Meta Cloud API
- [ ] Número de WhatsApp agregado en Meta Business
- [ ] `META_PHONE_NUMBER_ID` copiado
- [ ] `META_ACCESS_TOKEN` (token de sistema, no de prueba)
- [ ] `META_VERIFY_TOKEN` definido: `{slug}-jarvis-2026`

## Railway
- [ ] Proyecto creado en Railway desde GitHub
- [ ] Variables de entorno configuradas
- [ ] Deploy exitoso (verde en Railway)
- [ ] URL pública funcionando (`/` retorna status ok)

## Webhook Meta
- [ ] Callback URL configurada: `https://[tu-app].up.railway.app/webhook`
- [ ] Verify Token coincide con `META_VERIFY_TOKEN`
- [ ] Suscripción a campo `messages` activa

## Pruebas
- [ ] Mensaje de prueba enviado por WhatsApp
- [ ] Agente respondió correctamente
- [ ] Lead guardado en Google Sheets
- [ ] Formato de Sheets aplicado
- [ ] Tono del agente aprobado por el cliente

## Entrega
- [ ] Cliente tiene acceso al Google Sheet
- [ ] Cliente sabe el número de WhatsApp del agente
- [ ] Contacto humano de escalación confirmado
- [ ] Instrucciones básicas entregadas al cliente
"""
    (destino / "CHECKLIST_CLIENTE.md").write_text(checklist, encoding="utf-8")

    print(f"\n  ✓ Estructura creada en: {destino}/")
    print("\n  Próximos pasos:")
    print(f"  1. cd {destino}")
    print(f"  2. Edita config/client_config.yaml")
    print(f"  3. Edita config/prompts.yaml con el system prompt del negocio")
    print(f"  4. Llena los archivos en knowledge/")
    print(f"  5. Llena .env con las credenciales del cliente")
    print(f"  6. python3 tests/test_local.py")
    print(f"  7. Sube a GitHub → Railway hace deploy automático")
    print(f"  8. Configura el webhook en Meta")
    print(f"  9. Revisa CHECKLIST_CLIENTE.md\n")


if __name__ == "__main__":
    main()
