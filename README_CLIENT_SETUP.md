# Guía de Setup para Nuevos Clientes — Valoz Digital

---

## Cómo crear un agente nuevo en menos de 24 horas

Sigue estos 9 pasos en orden para entregar un agente funcional en WhatsApp.

### 1. Copiar la plantilla

```bash
git clone https://github.com/TU-USUARIO/jarvis-valoz.git agente-nombre-cliente
cd agente-nombre-cliente
pip3 install -r requirements.txt
```

### 2. Cambiar `config/client_config.yaml`

Edita el archivo con los datos del cliente. Puedes partir de uno de los ejemplos en `config/examples/`:
- `cafeteria.yaml` — negocios de alimentos y bebidas
- `comercializadora.yaml` — distribuidoras y mayoristas
- `clinica_dental.yaml` — clínicas y consultorios
- `agencia_marketing.yaml` — agencias de servicios digitales

Campos clave a cambiar: `BUSINESS_NAME`, `AGENT_NAME`, `SERVICES`, `FAQ`, `TONE`, `BUSINESS_HOURS`.

También edita `config/prompts.yaml` con el system prompt personalizado para ese negocio.

### 3. Crear el Google Sheet

1. Ve a **sheets.google.com** y crea una hoja nueva
2. Nómbrala: `Leads - [Nombre del cliente]`
3. Copia el ID de la URL: `docs.google.com/spreadsheets/d/[ESTE-ID]/edit`
4. El formato se aplica automáticamente la primera vez que se guarda un lead

### 4. Compartir el Sheet con la cuenta de servicio

1. En el Sheet, haz clic en **Compartir**
2. Agrega el email de la cuenta de servicio (`GOOGLE_SERVICE_ACCOUNT_EMAIL`)
3. Dale permiso de **Editor**
4. Confirmar que el Sheet ID y el email están en las variables de entorno

### 5. Agregar el número en Meta

1. Ve a **developers.facebook.com** → tu app → WhatsApp → API Setup
2. Agrega o selecciona el número de WhatsApp del cliente
3. Copia el **Phone Number ID**
4. Actualiza `META_PHONE_NUMBER_ID` en Railway

### 6. Cambiar variables en Railway

En Railway → tu proyecto → **Variables**, actualiza:
- `META_PHONE_NUMBER_ID` (número del cliente)
- `META_VERIFY_TOKEN` (ej: `cliente-agente-2024`)
- `GOOGLE_SHEET_ID` (ID del Sheet del cliente)
- `ANTHROPIC_API_KEY` (puede ser la misma)

### 7. Deploy

```bash
git add .
git commit -m "feat: agente para [nombre del cliente]"
git push origin main
```

Railway detecta el push y hace deploy automático. Espera 2-3 minutos.

### 8. Probar WhatsApp

1. Configura el webhook en Meta con la URL de Railway + `/webhook`
2. Envía un mensaje de prueba al número del cliente
3. Verifica que el agente responde correctamente
4. Verifica que aparece una fila en el Google Sheet

### 9. Revisar Google Sheets

- Abre el Sheet del cliente
- Confirma que aparece la fila con los datos del lead
- Verifica que el formato (encabezados oscuros, columnas, colores) se aplicó
- Comparte el Sheet con el cliente para que vea sus leads en tiempo real

---

Cómo desplegar un agente de WhatsApp para un cliente nuevo en menos de 24 horas.

---

## Qué datos pedirle al cliente

Antes de empezar, recopila esta información:

| Dato | Ejemplo |
|------|---------|
| Nombre del negocio | "Clínica Dental Sonrisa" |
| Descripción del negocio | Qué vende, a quién, cómo trabaja |
| Servicios y precios | Lista completa con rangos de precio |
| Nombre del agente | "Ana", "Soporte", etc. |
| Tono de comunicación | Formal / Amigable / Vendedor |
| Horario de atención | Lunes-Viernes 9am-6pm |
| Preguntas frecuentes | Las 5-10 preguntas más comunes de sus clientes |
| WhatsApp del humano | Número para escalar conversaciones |
| Proveedor de WhatsApp | Meta Cloud API o Twilio |
| Credenciales del proveedor | Ver Sección 4 |

---

## Pasos para crear el agente

### 1. Clonar la plantilla

```bash
git clone https://github.com/TU-USUARIO/jarvis-valoz.git nombre-cliente-agente
cd nombre-cliente-agente
```

### 2. Instalar dependencias

```bash
pip3 install -r requirements.txt
```

### 3. Configurar el negocio

Edita estos dos archivos con los datos del cliente:

**`config/client_config.yaml`** — Datos del negocio, servicios, FAQ, horario.

**`config/prompts.yaml`** — System prompt del agente (personalidad, reglas, conocimiento).
Remplaza cada sección con la información específica del cliente.

**`knowledge/`** — Coloca aquí los archivos del cliente: menú, catálogo, precios en PDF/TXT/MD.

### 4. Configurar variables de entorno

Copia el template:
```bash
cp .env.example .env
```

Rellena `.env` con los datos del cliente:

```env
ANTHROPIC_API_KEY=sk-ant-...

WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=...
META_VERIFY_TOKEN=cliente-agente-2024

GOOGLE_SHEET_ID=...                 # Opcional
GOOGLE_SERVICE_ACCOUNT_EMAIL=...    # Opcional
GOOGLE_PRIVATE_KEY=...              # Opcional
GOOGLE_CALENDAR_ID=...              # Opcional
```

### 5. Probar el agente en local

```bash
python3 tests/test_local.py
```

Simula una conversación como si fueras el cliente. Verifica que:
- Responde correctamente las preguntas frecuentes
- Usa el tono correcto
- Conoce los servicios y precios
- Escala a humano cuando corresponde

Si algo no está bien, ajusta `config/prompts.yaml` y repite.

---

## Configurar Google Sheets (CRM de leads)

### Crear la cuenta de servicio

1. Ve a **console.cloud.google.com**
2. Crea un proyecto nuevo (ej: "jarvis-cliente")
3. Ve a **APIs & Services → Enable APIs** y activa:
   - Google Sheets API
   - Google Drive API
4. Ve a **APIs & Services → Credentials → Create Credentials → Service Account**
5. Ponle un nombre (ej: "jarvis-sheets")
6. Descarga el archivo JSON de la cuenta de servicio

### Extraer credenciales del JSON

Del archivo JSON descargado, copia:
- `client_email` → `GOOGLE_SERVICE_ACCOUNT_EMAIL`
- `private_key` → `GOOGLE_PRIVATE_KEY` (reemplaza los saltos de línea reales por `\n` literal)

Para convertir el private_key en una sola línea (en Mac/Linux):
```bash
cat tu-archivo.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['private_key'].replace('\n','\\\\n'))"
```

### Compartir el Google Sheet

1. Crea un nuevo Google Sheet para el cliente
2. Copia el ID del Sheet desde la URL:
   `https://docs.google.com/spreadsheets/d/[ESTE-ES-EL-ID]/edit`
3. Comparte el Sheet con el email de la cuenta de servicio (`client_email` del JSON)
4. Dale permiso de **Editor**

### Configurar en .env

```env
GOOGLE_SHEET_ID=1BxiMV...tu-sheet-id
GOOGLE_SERVICE_ACCOUNT_EMAIL=jarvis-sheets@proyecto.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n
```

---

## Configurar Google Calendar (citas automáticas)

### Activar Calendar API

1. En el mismo proyecto de Google Cloud, activa la **Google Calendar API**
2. La misma cuenta de servicio sirve para ambas integraciones

### Compartir el Calendar

1. Abre Google Calendar y ve a **Configuración → [Tu calendario] → Compartir**
2. Agrega el email de la cuenta de servicio con permiso de **Hacer cambios en eventos**
3. Copia el **ID del calendario** (aparece en Configuración del calendario)
   Ejemplo: `cliente@gmail.com` o `c_abc123...@group.calendar.google.com`

### Configurar en .env

```env
GOOGLE_CALENDAR_ID=tu-calendario@gmail.com
TIMEZONE=America/Mexico_City
```

---

## Deploy en Railway

### 1. Subir a GitHub

```bash
git add .
git commit -m "feat: agente para [nombre del cliente]"
git remote add origin https://github.com/TU-USUARIO/nombre-cliente-agente.git
git push -u origin main
```

### 2. Crear proyecto en Railway

1. Ve a **railway.app** → New Project → Deploy from GitHub
2. Selecciona el repositorio del cliente
3. Railway detecta el `Dockerfile` automáticamente

### 3. Variables de entorno en Railway

En Railway → tu proyecto → **Variables**, agrega todas las del `.env` del cliente.

> Para `GOOGLE_PRIVATE_KEY` en Railway: pega el valor con los `\n` literales.
> Railway los maneja correctamente.

### 4. Configurar webhook en Meta

Una vez que Railway asigne la URL pública:

1. Ve a **developers.facebook.com** → tu app → WhatsApp → Configuration
2. Callback URL: `https://tu-app.up.railway.app/webhook`
3. Verify Token: el valor de `META_VERIFY_TOKEN` en `.env`
4. Suscríbete al campo **"messages"** → Guardar

---

## Checklist de entrega al cliente

Antes de entregar el agente, verifica:

- [ ] El agente responde correctamente en `python3 tests/test_local.py`
- [ ] Conoce todos los servicios y precios del cliente
- [ ] Responde en el tono correcto
- [ ] Las preguntas frecuentes están bien cubiertas
- [ ] Escala a humano cuando el cliente quiere cotización o llamada
- [ ] El agente está desplegado en Railway y el servidor responde
- [ ] El webhook de Meta/Twilio está configurado y verificado
- [ ] Se recibió al menos un mensaje de prueba real en WhatsApp
- [ ] Google Sheets está guardando leads (si está configurado)
- [ ] Google Calendar está creando eventos (si está configurado)
- [ ] El cliente tiene acceso al Google Sheet para ver sus leads

---

## Comandos útiles

```bash
# Probar sin WhatsApp
python3 tests/test_local.py

# Arrancar servidor local
uvicorn agent.main:app --reload --port 8000

# Ver estado del agente
curl http://localhost:8000/

# Build Docker
docker compose up --build
```
