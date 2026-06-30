# Renzo Snacks — Agente WhatsApp

Agente de WhatsApp para **Renzo Snacks**, restaurante de alitas, boneless y papas preparadas.

---

## Datos del negocio

| Campo | Valor |
|---|---|
| Nombre | Renzo Snacks |
| Giro | Restaurante / snacks |
| Dirección | Primera Avenida Oriente Sur No. 74, Barrio San Sebastián |
| Horario | Lunes a sábado, 7:00 p.m. a 10:30 p.m. |
| WhatsApp pedidos | 9631000021 |
| Instagram | @renzo_snacks |
| Facebook | @renzosnacks |
| Métodos de pago | Efectivo, Transferencia, Tarjeta |
| Servicios | Envío a domicilio (con costo extra), recoger en local, consumo en local |

---

## Estructura de archivos

```
clientes/renzosnacks/
├── assets/
│   └── menu_renzo_snacks.jpg     ← imagen del menú (YA EXISTE)
├── config/
│   ├── client_config.yaml        ← configuración del negocio e intents
│   └── prompts.yaml              ← system prompt del agente
├── knowledge/
│   ├── menu.md                   ← menú completo con precios
│   ├── faq.md                    ← preguntas frecuentes
│   ├── politicas.md              ← políticas de pago y servicio
│   └── loyverse.md               ← documentación de Loyverse
└── README.md                     ← este archivo
```

---

## Variables de entorno requeridas

### Meta / WhatsApp (placeholder — número no conectado aún)

```env
CLIENT_ID=renzosnacks
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=            # Token de Meta Business (pendiente)
META_PHONE_NUMBER_ID=         # ID del número en Meta (pendiente)
META_VERIFY_TOKEN=            # Token de verificación del webhook (pendiente)
BUSINESS_WHATSAPP_NUMBER=9631000021
```

### Imagen del menú

```env
RENZO_MENU_IMAGE_PATH=clientes/renzosnacks/assets/menu_renzo_snacks.jpg
RENZO_MENU_MEDIA_ID=          # Rellenar tras subir la imagen a Meta Media API
RENZO_MENU_IMAGE_URL=         # O URL pública si se hospeda externamente
```

El bot intenta enviar la imagen con esta prioridad:
1. Usar `RENZO_MENU_MEDIA_ID` si está definido.
2. Usar `RENZO_MENU_IMAGE_URL` si está definido.
3. Subir el archivo local a Meta Media API y usar el media_id resultante.
4. Si todo falla, responde solo con texto y registra un warning en logs.

### Loyverse (integración pendiente)

```env
LOYVERSE_ENABLED=false          # Cambiar a true cuando esté listo
LOYVERSE_ACCESS_TOKEN=          # Token de API de Loyverse
LOYVERSE_STORE_ID=              # ID de la tienda
LOYVERSE_POS_DEVICE_ID=         # ID del dispositivo POS (opcional)
LOYVERSE_EMPLOYEE_ID=           # ID del empleado asignado (opcional)
LOYVERSE_API_BASE_URL=https://api.loyverse.com/v1.0
```

### API de Claude

```env
ANTHROPIC_API_KEY=              # Requerido
```

### Servidor

```env
PORT=8000
ENVIRONMENT=production
TIMEZONE=America/Mexico_City
DATABASE_URL=sqlite+aiosqlite:///./agentkit.db
```

---

## Google Sheets

**Este cliente NO usa Google Sheets.** Los pedidos van a Loyverse.
Las variables `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_EMAIL` y `GOOGLE_PRIVATE_KEY`
no deben configurarse para Renzo Snacks.

---

## Cómo activar el cliente

1. Configura todas las variables de entorno en Railway.
2. Establece `CLIENT_ID=renzosnacks`.
3. El agente usará automáticamente:
   - `clientes/renzosnacks/config/client_config.yaml`
   - `clientes/renzosnacks/config/prompts.yaml`
   - `clientes/renzosnacks/knowledge/`

---

## Cómo probar el flujo de menú

```
Cliente: ¿Tienen menú?
Bot: [envía imagen del menú] + "Te comparto el menú. Si ves algo que te llame la atención, con gusto te ayudo con tu pedido."

Cliente: ¿Cuánto cuestan las alitas?
Bot: [carga menu.md] + responde con precios de alitas/boneless
```

Para probar localmente sin número real, ejecuta `python3 tests/test_local.py`.

---

## Cómo probar un pedido

```
Cliente: Quiero 10 boneless
Bot: Las 10 piezas están en $170 e incluyen ranch y varitas. ¿Qué salsa te gustaría?

Cliente: Mango habanero
Bot: ¿Lo quieres para envío a domicilio, recoger o consumo en local?

Cliente: Domicilio, pago transferencia
Bot: [pide nombre y dirección]

Cliente: [confirma]
Bot: Muestra resumen → "¿Así lo confirmo?"

Cliente: Sí confirmo
Bot: [si Loyverse activo] "Listo, tu pedido fue registrado."
     [si Loyverse inactivo] "Listo, ya tengo los datos. Lo paso al equipo para confirmar."
```

---

## Estados del pedido

| Estado | Significado |
|---|---|
| `enviado_a_loyverse` | Pedido registrado en el POS |
| `pendiente_revision` | Hay productos que no se encontraron en Loyverse |
| `pendiente_confirmacion_humana` | Loyverse inactivo; requiere acción manual |
| `error_loyverse` | Error de API; pedido en logs del servidor |

---

## Qué falta para activar Loyverse

- [ ] Obtener token de acceso de Loyverse (Configuración → Integraciones → API)
- [ ] Copiar Store ID desde el dashboard
- [ ] Configurar `LOYVERSE_ENABLED=true` y `LOYVERSE_ACCESS_TOKEN=...` en Railway
- [ ] (Opcional) Agregar `LOYVERSE_POS_DEVICE_ID` para asignar pedidos al dispositivo físico
- [ ] Probar con un pedido real y verificar que aparece en el POS

---

## Qué falta para conectar el número real

- [ ] Registrar el número 9631000021 en Meta Business Manager
- [ ] Crear la app de WhatsApp Cloud API en Meta Developers
- [ ] Obtener `META_PHONE_NUMBER_ID` y `META_ACCESS_TOKEN` (token de sistema)
- [ ] Definir `META_VERIFY_TOKEN` (ej. `renzosnacks-2026`)
- [ ] Configurar el webhook en Meta: `https://[tu-app].up.railway.app/webhook`
- [ ] Activar la suscripción al campo `messages`

---

## Limitaciones de impresión de tickets en Loyverse

- La API de Loyverse permite crear receipts (recibos de venta).
- La impresión automática depende del dispositivo POS físico y su configuración.
- Si el POS está conectado a una impresora y el dispositivo está activo, el ticket
  puede imprimirse al crear el receipt desde la API.
- Sin `LOYVERSE_POS_DEVICE_ID` configurado, el receipt aparece en el sistema pero
  puede no disparar la impresora automáticamente.
- Verificar con el equipo de Renzo Snacks si tienen el POS conectado a impresora.

---

## Logs esperados al iniciar

```
Cliente cargado: Renzo Snacks
Proveedor de WhatsApp: ProveedorMeta
Google Sheets: no configurado
Google Calendar: no configurado
Loyverse: inactivo
```

## Logs esperados en operación

```
Menú solicitado por 9631000021
Enviando imagen de menú con media_id a 9631000021
Imagen de menú enviada correctamente a 9631000021

Pedido iniciado — 9631000021
Pedido confirmado — 9631000021 | cliente: José
Loyverse inactivo — pedido de José queda pendiente
```
