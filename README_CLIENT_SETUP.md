# Guía de setup para nuevos clientes — Valoz Digital

## Cómo crear un agente nuevo en 15 a 30 minutos

Sigue estos pasos en orden. Si tienes todos los datos del cliente listos,
el proceso completo toma entre 15 y 30 minutos.

También puedes usar el script automático:
```bash
python3 scripts/create_client_template.py
```

---

### Paso 1 — Copiar el proyecto base

```bash
git clone https://github.com/TU-USUARIO/whatsapp-agentkit.git agente-nombre-cliente
cd agente-nombre-cliente
pip3 install -r requirements.txt
```

O usa el script que crea la carpeta con todo prellenado:
```bash
python3 scripts/create_client_template.py
```

---

### Paso 2 — Crear nuevo repo en GitHub

1. Ve a **github.com → New repository**
2. Nombre: `agente-[nombre-cliente]`
3. Privado
4. Sin README (ya tienes uno)
5. Empuja el código:

```bash
git remote set-url origin https://github.com/TU-USUARIO/agente-nombre-cliente.git
git push -u origin main
```

---

### Paso 3 — Editar `config/client_config.yaml`

Cambia los campos con los datos reales del cliente:
- `BUSINESS_NAME`, `AGENT_NAME`, `TONE`, `BUSINESS_HOURS`
- `SERVICES` — lista de servicios con rangos de precio
- `FAQ` — 5 a 10 preguntas frecuentes reales
- `CONTACT_NAME`, `CONTACT_PHONE` — humano que recibe escalaciones

Usa uno de los ejemplos en `config/examples/` como punto de partida:
- `cafeteria.yaml` — negocios de alimentos y bebidas
- `restaurante.yaml` — restaurante con catering
- `comercializadora.yaml` — distribuidoras y mayoristas
- `clinica_dental.yaml` — clínicas y consultorios
- `inmobiliaria.yaml` — bienes raíces
- `estetica.yaml` — salones de belleza y spa
- `escuela.yaml` — academias y centros de capacitación
- `agencia_marketing.yaml` — agencias digitales

---

### Paso 4 — Editar `config/prompts.yaml`

Reemplaza el system prompt con el del nuevo negocio:
- Identidad y nombre del agente
- Cómo responde preguntas de precio (siempre rangos, nunca precio cerrado)
- Escenarios específicos del giro del negocio
- Datos a recopilar del prospecto

---

### Paso 5 — Llenar `knowledge/`

Edita los archivos de conocimiento del cliente:
- `knowledge/servicios.md` — descripción detallada de cada servicio
- `knowledge/precios.md` — rangos de precios por servicio
- `knowledge/faq.md` — preguntas frecuentes con respuestas reales
- `knowledge/politicas.md` — pagos, garantías, cancelaciones
- `knowledge/objeciones.md` — cómo manejar "está caro", "lo voy a pensar", etc.

El agente carga solo el archivo relevante según la intención del cliente, reduciendo el costo por mensaje.

---

### Paso 6 — Crear el Google Sheet

1. Ve a **sheets.google.com** → crear hoja nueva
2. Nómbrala: `Leads — [Nombre del cliente]`
3. Copia el ID de la URL:
   `docs.google.com/spreadsheets/d/[ESTE-ID]/edit`
4. Guárdalo para el Paso 10

---

### Paso 7 — Compartir el Sheet con la cuenta de servicio

1. En el Sheet → **Compartir**
2. Agrega el email de la cuenta de servicio (`GOOGLE_SERVICE_ACCOUNT_EMAIL`)
3. Dale permiso de **Editor**
4. El formato se aplica automáticamente en el primer lead

---

### Paso 8 — Obtener `GOOGLE_SHEET_ID`

El ID está en la URL del Sheet:
```
https://docs.google.com/spreadsheets/d/[AQUI_ESTA_EL_ID]/edit
```

---

### Paso 9 — Agregar o migrar el número en Meta Cloud API

1. Ve a **developers.facebook.com** → tu app → WhatsApp → API Setup
2. Agrega el número de WhatsApp del cliente
3. Copia el **Phone Number ID**
4. El token de sistema se obtiene en: Meta → Business Settings → System Users → Generate Token

---

### Paso 10 — Configurar variables en Railway

En Railway → tu proyecto → **Variables**, agrega o actualiza:

| Variable | Valor |
|----------|-------|
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic |
| `META_ACCESS_TOKEN` | Token de sistema de Meta |
| `META_PHONE_NUMBER_ID` | ID del número del cliente |
| `META_VERIFY_TOKEN` | Ej: `nombre-cliente-2026` |
| `GOOGLE_SHEET_ID` | ID del Sheet del cliente |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | Email de la cuenta de servicio |
| `GOOGLE_PRIVATE_KEY` | Private key del JSON (con `\n` literales) |
| `GOOGLE_CALENDAR_ID` | (Opcional) ID del Calendar del cliente |
| `TIMEZONE` | `America/Mexico_City` |
| `ENVIRONMENT` | `production` |
| `PORT` | `8000` |

---

### Paso 11 — Deploy

Railway detecta el push a GitHub y hace deploy automático.

```bash
git add config/ knowledge/ prompts.yaml
git commit -m "feat: agente para [nombre del cliente]"
git push origin main
```

Espera 2-3 minutos. Verifica en Railway que el deploy sea verde.

---

### Paso 12 — Configurar webhook en Meta (si cambió la URL)

Si es un proyecto nuevo en Railway, tendrás una nueva URL pública:

1. Ve a Meta → WhatsApp → Configuration → Webhook
2. Callback URL: `https://[tu-app].up.railway.app/webhook`
3. Verify Token: el valor de `META_VERIFY_TOKEN`
4. Haz clic en **Verify and Save**
5. Suscríbete al campo **messages**

---

### Paso 13 — Probar WhatsApp

Envía un mensaje al número del cliente y verifica:
- El agente responde en menos de 10 segundos
- Responde con el tono correcto
- Conoce los servicios y precios
- Logs de Railway muestran el mensaje recibido y enviado

---

### Paso 14 — Probar Google Sheets

1. Abre el Sheet del cliente
2. Envía un par de mensajes de prueba en WhatsApp
3. Confirma que aparece una fila con los datos del lead
4. Verifica que el formato se aplicó (encabezados azules, colores condicionales)

---

### Paso 15 — Entregar al cliente

- [ ] Comparte el Google Sheet con el cliente (permiso de solo lectura o editor)
- [ ] Envíale el número de WhatsApp del agente
- [ ] Explica cómo ver los leads en Sheets
- [ ] Agenda revisión de ajustes a los 7 días

---

## Qué datos pedirle al cliente antes de empezar

| Dato | Ejemplo |
|------|---------|
| Nombre del negocio | "Clínica Dental Sonrisa" |
| Tipo de negocio | Clínica dental |
| Descripción | Qué ofrece, a quién, cómo trabaja |
| Servicios y precios | Lista con rangos de precio |
| Nombre del agente | "Ana", "Soporte", "Asistente" |
| Tono | Formal / Amigable / Vendedor |
| Horario de atención | Lunes a Viernes 9am-6pm |
| Preguntas frecuentes | Las 5-10 más comunes de sus clientes |
| Contacto humano | Nombre y WhatsApp para escalaciones |
| Proveedor WhatsApp | Meta Cloud API (recomendado) |

---

## Comandos útiles

```bash
# Generar plantilla para cliente nuevo
python3 scripts/create_client_template.py

# Probar el agente sin WhatsApp
python3 tests/test_local.py

# Arrancar servidor local
uvicorn agent.main:app --reload --port 8000

# Verificar que el servidor responde
curl http://localhost:8000/

# Ver logs del agente en Railway
railway logs
```

---

## Estructura del repositorio

```
agente-cliente/
├── agent/
│   ├── main.py              # Servidor FastAPI + webhook
│   ├── brain.py             # Conexión con Claude API
│   ├── context_loader.py    # Carga selectiva de conocimiento
│   ├── memory.py            # Historial de conversación (SQLite)
│   ├── lead_parser.py       # Extrae datos del lead con Haiku
│   ├── tools.py             # Herramientas del agente
│   └── providers/
│       ├── base.py          # Interfaz abstracta de proveedor
│       └── meta.py          # Adaptador Meta Cloud API
├── config/
│   ├── client_config.yaml   # Datos del negocio ← EDITAR
│   ├── prompts.yaml         # System prompt del agente ← EDITAR
│   └── examples/            # Plantillas por tipo de negocio
├── integrations/
│   ├── google_sheets.py     # CRM de leads en Google Sheets
│   └── google_calendar.py   # Citas automáticas en Calendar
├── knowledge/
│   ├── servicios.md         # ← EDITAR con servicios del cliente
│   ├── precios.md           # ← EDITAR con precios del cliente
│   ├── faq.md               # ← EDITAR con FAQs del cliente
│   ├── politicas.md         # ← EDITAR con políticas del cliente
│   └── objeciones.md        # ← EDITAR con manejo de objeciones
├── scripts/
│   └── create_client_template.py  # Genera estructura para cliente nuevo
├── tests/
│   └── test_local.py        # Simulador de chat local
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── CHECKLIST_NUEVO_CLIENTE.md
└── README_CLIENT_SETUP.md
```
