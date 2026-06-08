# Checklist — Nuevo cliente Valoz Digital

Usa esta lista cada vez que configures un agente para un cliente nuevo.
También puedes generarla automáticamente con `python3 scripts/create_client_template.py`.

---

## 1. Datos del negocio recopilados

- [ ] Nombre del negocio
- [ ] Tipo de negocio o giro
- [ ] Descripción del negocio (qué vende, a quién, cómo trabaja)
- [ ] Lista de servicios con precios o rangos
- [ ] Preguntas frecuentes (mínimo 5 preguntas reales de sus clientes)
- [ ] Horario de atención
- [ ] Nombre del agente IA (ej: "Ana", "Asistente", etc.)
- [ ] Tono de comunicación (formal, amigable, vendedor...)
- [ ] Nombre y WhatsApp del humano que recibe escalaciones
- [ ] Objetivo principal del agente (responder, cotizar, agendar, dar seguimiento...)

---

## 2. Archivos de configuración editados

- [ ] `config/client_config.yaml` — datos del negocio, servicios, FAQ
- [ ] `config/prompts.yaml` — system prompt del agente adaptado al negocio
- [ ] `knowledge/servicios.md` — descripción detallada de servicios
- [ ] `knowledge/precios.md` — rangos de precios por servicio
- [ ] `knowledge/faq.md` — preguntas frecuentes con respuestas
- [ ] `knowledge/politicas.md` — formas de pago, garantías, cancelaciones
- [ ] `knowledge/objeciones.md` — cómo responder objeciones comunes

---

## 3. Prueba local aprobada

- [ ] `python3 tests/test_local.py` ejecutado
- [ ] Agente conoce los servicios del negocio
- [ ] Agente responde con el tono correcto
- [ ] Agente maneja precios con rangos (no precios cerrados)
- [ ] Agente escala a humano cuando corresponde
- [ ] Agente captura datos del prospecto de forma natural

---

## 4. Google Sheets

- [ ] Google Sheet creado: `Leads — [Nombre del cliente]`
- [ ] ID del Sheet copiado de la URL
- [ ] Sheet compartido con la cuenta de servicio (permiso Editor)
- [ ] `GOOGLE_SHEET_ID` agregado a las variables de entorno
- [ ] Primer lead guardado correctamente
- [ ] Formato automático visible (encabezados azules, colores condicionales)
- [ ] Cliente tiene acceso al Sheet con permiso de solo lectura o editor

---

## 5. Google Calendar (opcional)

- [ ] Calendar creado o seleccionado para el cliente
- [ ] Calendar compartido con la cuenta de servicio (permiso: Hacer cambios)
- [ ] `GOOGLE_CALENDAR_ID` agregado a las variables de entorno
- [ ] Cita de prueba creada correctamente desde el agente

---

## 6. Meta Cloud API

- [ ] Número de WhatsApp del cliente registrado en Meta Business
- [ ] `META_PHONE_NUMBER_ID` copiado del dashboard de Meta
- [ ] Token de sistema creado (no el token temporal de prueba)
- [ ] `META_ACCESS_TOKEN` actualizado en Railway
- [ ] `META_VERIFY_TOKEN` definido (ej: `nombre-cliente-2026`)

---

## 7. Railway — Deploy

- [ ] Repositorio del cliente subido a GitHub
- [ ] Proyecto nuevo creado en Railway desde el repositorio
- [ ] Todas las variables de entorno configuradas en Railway:
  - [ ] `ANTHROPIC_API_KEY`
  - [ ] `META_ACCESS_TOKEN`
  - [ ] `META_PHONE_NUMBER_ID`
  - [ ] `META_VERIFY_TOKEN`
  - [ ] `GOOGLE_SHEET_ID`
  - [ ] `GOOGLE_SERVICE_ACCOUNT_EMAIL`
  - [ ] `GOOGLE_PRIVATE_KEY`
  - [ ] `GOOGLE_CALENDAR_ID` (si aplica)
  - [ ] `TIMEZONE=America/Mexico_City`
  - [ ] `ENVIRONMENT=production`
  - [ ] `PORT=8000`
- [ ] Deploy completado (estado verde en Railway)
- [ ] URL pública responde: `GET /` retorna `{"status": "ok"}`
- [ ] Logs de Railway muestran `Google Sheets: activo`

---

## 8. Webhook Meta

- [ ] URL del webhook configurada: `https://[app].up.railway.app/webhook`
- [ ] Verify Token coincide exactamente con `META_VERIFY_TOKEN`
- [ ] Webhook verificado exitosamente por Meta
- [ ] Suscripción al campo `messages` activada y guardada

---

## 9. Prueba final en WhatsApp real

- [ ] Mensaje de prueba enviado al número del cliente
- [ ] Agente respondió en menos de 10 segundos
- [ ] Respuesta tiene el tono correcto
- [ ] El agente conoce los servicios del cliente
- [ ] Lead aparece en Google Sheets con datos correctos
- [ ] Formato de Sheets aplicado correctamente
- [ ] Cita creada en Calendar (si aplica)

---

## 10. Entrega al cliente

- [ ] Cliente recibió el enlace a su Google Sheet
- [ ] Cliente sabe cuál es el número de WhatsApp del agente
- [ ] Cliente tiene el contacto de soporte de Valoz Digital
- [ ] Cliente aprobó el tono y las respuestas del agente
- [ ] Se agendó revisión de ajustes a los 7 días

---

**Tiempo estimado:** 15 a 30 minutos si todos los datos están listos.
