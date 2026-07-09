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
| Servicios | Envío a domicilio (~$50), recoger en local, consumo en local |
| Envío | ~$50 aproximado, se confirma según ubicación |
| Preparación | 25 a 35 minutos (se prepara al momento) |

---

## Estructura de archivos

```
clientes/renzosnacks/
├── assets/
│   ├── menu_renzo_snacks.jpg          ← imagen del menú (YA EXISTE)
│   └── logo_renzo_snacks.png          ← PENDIENTE: cliente ya envió el logo, agregar aquí
├── config/
│   ├── client_config.yaml             ← configuración del negocio e intents
│   └── prompts.yaml                   ← system prompt del agente
├── knowledge/
│   ├── menu.md                        ← menú completo con precios (confirmado válido)
│   ├── faq.md                         ← preguntas frecuentes
│   ├── politicas.md                   ← políticas de pago y servicio
│   ├── loyverse.md                    ← documentación de Loyverse
│   └── promociones.md                 ← promos semanales (actualizar cada domingo)
└── README.md                          ← este archivo
```

---

## Variables de entorno requeridas

### Meta / WhatsApp

```env
CLIENT_ID=renzosnacks
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=
META_PHONE_NUMBER_ID=
META_VERIFY_TOKEN=
BUSINESS_WHATSAPP_NUMBER=9631000021
```

> **Decisión pendiente antes de activar el número 9631000021.**
> El número **9631000021 ya es conocido por los clientes de Renzo Snacks**, por lo que
> la migración completa a Cloud API **no debe asumirse como plan por defecto**. La opción
> recomendada es intentar **coexistencia** antes de considerar cambiar de número.
>
> Hasta que se pruebe y confirme un escenario, las variables `META_*` deben quedar vacías.
> Ver la sección **"Escenarios para el número de WhatsApp"** más abajo para el detalle completo.

---

## Escenarios para el número de WhatsApp

### ESCENARIO RECOMENDADO — Coexistencia

- Intentar **WhatsApp Business App + Cloud API en el mismo número** mediante la función de
  coexistencia de Meta.
- **Objetivo:** que Renzo conserve el número **9631000021** que sus clientes ya conocen.
- El negocio seguiría usando **WhatsApp Business App** para estados/historias, catálogo y
  manejo visual del chat, tal como lo hace hoy.
- El **bot usaría Cloud API** sobre ese mismo número para responder mensajes, mandar el menú
  y tomar pedidos.
- **Esto debe probarse antes de prometerse como seguro.** La coexistencia tiene requisitos y
  limitaciones de Meta (versión de la app, tipo de cuenta, disponibilidad por región) que no
  están confirmados para este número. No comunicar al cliente que "va a funcionar" hasta
  validarlo en la práctica.

### ESCENARIO DE RIESGO — Migración completa sin coexistencia

- Si el número 9631000021 se migra **completamente** a Cloud API sin activar coexistencia,
  Renzo Snacks **podría perder el uso normal de WhatsApp Business App** en ese número,
  incluyendo estados/historias.
- **No recomendar ni ejecutar una migración completa sin aprobación explícita del cliente**,
  informándole con claridad qué perdería (ver sección de Estados/Historias abajo).

### Opción C — Número nuevo dedicado al bot

- Sigue disponible como alternativa si la coexistencia no es viable, pero implica que los
  clientes deban aprender un número distinto al que ya conocen. Considerar solo si el
  escenario recomendado falla en las pruebas.

---

## Estados / Historias de WhatsApp

- Los **estados de WhatsApp se manejan desde WhatsApp Business App**, no desde la API del bot
  (Cloud API no tiene función de publicar estados).
- Si el cliente quiere compartir historias de Instagram a WhatsApp, eso es una **operación
  manual del negocio** hecha desde la app, **no es una función del bot**.
- **No prometer publicación automática de estados/historias desde Cloud API** bajo ninguna
  circunstancia — esa capacidad no existe en la API.

### Logo

```
clientes/renzosnacks/assets/logo_renzo_snacks.png
```

El cliente indicó que ya envió el logo. Si el archivo no existe aún, guardarlo en esa ruta.

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
4. Si todo falla, responde con texto y registra un warning en logs.

### Loyverse (integración pendiente)

```env
LOYVERSE_ENABLED=false
LOYVERSE_ACCESS_TOKEN=
LOYVERSE_STORE_ID=
LOYVERSE_POS_DEVICE_ID=
LOYVERSE_EMPLOYEE_ID=
LOYVERSE_API_BASE_URL=https://api.loyverse.com/v1.0
```

### API de Claude

```env
ANTHROPIC_API_KEY=
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

## Flujo del bot para pedidos

El bot debe recopilar esta información antes de mostrar el resumen:

1. **Nombre** del cliente
2. **Pedido** (qué quiere)
3. **Cantidad**
4. **Salsa** (si aplica — alitas/boneless)
5. **Bebida** (si aplica)
6. **Complementos** (si aplica)
7. **Modalidad:** envío a domicilio / recoger en local / consumo en local
8. **Dirección** (solo si es envío — luego indicar costo ~$50 sujeto a ubicación)
9. **Forma de pago**
10. **Comentarios especiales**

Luego mostrar resumen y pedir confirmación. **Solo tras confirmar**, enviar a Loyverse.

### Ejemplo de resumen

```
Perfecto, te confirmo tu pedido:

10 boneless con salsa mango habanero
1 papas gajo
Modalidad: envío
Pago: transferencia
Tiempo aproximado: 25 a 35 minutos
Envío aproximado: $50, sujeto a ubicación

¿Así lo confirmo?
```

### Mensaje de envío al pedir dirección

> "El envío tiene un costo extra aproximado de $50, pero te confirmamos según tu ubicación. ¿Me pasas tu dirección?"

### Mensaje de tiempo de preparación

> "Normalmente tarda de 25 a 35 minutos, dependiendo de la cantidad del pedido."

---

## Promociones

Las promociones cambian por semana y pueden variar por día. Hay dos mecanismos,
independientes entre sí:

- **Manual vía Git (actual, siempre activo):** editar
  `clientes/renzosnacks/knowledge/promociones.md` cada domingo. Sirve como fallback/
  referencia que el agente de IA puede citar. Si está vacío, el bot responde:
  *"Las promociones pueden cambiar por día. Te puedo confirmar con el equipo o tomar tu
  pedido con el menú actual."*
- **Por comando de administrador vía WhatsApp (implementado, deshabilitado por defecto):**
  ver abajo. Cuando `promotion_settings.enabled: true`, las consultas de clientes sobre
  promos ("promos", "promociones"...) se responden directo con la promoción guardada por
  comando, sin pasar por el modelo de IA ni por `promociones.md`. Si no hay nada guardado,
  responde: *"Por ahora no tengo una promo cargada, pero puedo pasarte el menú o ayudarte
  con tu pedido."*
- El bot nunca inventa promociones, en ninguno de los dos mecanismos.

### Actualización de promociones por comandos de administrador (implementado)

> **Estado: implementado en el motor compartido** (`agent/promotions.py`), pero
> **DESHABILITADO para Renzo Snacks** (`promotion_settings.enabled: false` en
> `clientes/renzosnacks/config/client_config.yaml`) hasta que el negocio confirme
> qué números serán administradores. Mientras esté deshabilitado, el bot funciona
> exactamente igual que antes — sin esta función, usando solo `promociones.md`
> como fallback de referencia.

**Configuración (en `client_config.yaml`, no en `.env`):**

```yaml
admin_numbers:
  - "521XXXXXXXXXX"

promotion_settings:
  enabled: false  # cambiar a true cuando el negocio confirme los números admin
  allow_text_promos: true
  allow_image_promos: true
  current_promo_text_path: "clientes/renzosnacks/knowledge/promo_actual.md"
  current_promo_image_path: "clientes/renzosnacks/assets/promos/current_promo.jpg"
```

- `admin_numbers` es la lista de números autorizados. Vacía por defecto — nadie puede
  actualizar promociones hasta que se agreguen números aquí.
- `promo_actual.md` es un archivo **separado** de `promociones.md`: `promociones.md` sigue
  siendo el contenido curado/versionado que se edita a mano cada domingo; `promo_actual.md`
  es lo que el comando `ACTUALIZAR PROMO` sobrescribe. Así un comando de WhatsApp nunca borra
  el archivo curado de referencia.

**Comandos reservados a administradores (ver `README_WHATSAPP_IMPLEMENTATION_MODES.md` para el detalle general):**

| Comando | Acción |
|---|---|
| `ACTUALIZAR PROMO` | Guarda el texto y/o imagen que sigue al comando como la promoción actual. |
| `VER PROMO ACTUAL` | Muestra la promoción guardada. |
| `BORRAR PROMO` | Elimina la promoción actual. |
| `AYUDA ADMIN` | Lista los comandos disponibles. |
| `PREPARAR STORY` | Devuelve texto corto + imagen (si existe) para subir manualmente a estados. |

**Reglas:**

- Solo los números en `admin_numbers` pueden usar estos comandos. Un número no autorizado que
  intente `ACTUALIZAR PROMO` (o cualquier otro comando admin) recibe un mensaje explicando que
  no puede administrar promociones.
- Los comandos administrativos se resuelven por keywords, **sin llamar al modelo de IA**.
- Las promociones actualizadas por comando se guardan como archivos (`current_promo_text_path`
  / `current_promo_image_path`), no en la base de datos sqlite ni en `promociones.md`.
- Si el cliente pregunta "promos", "promociones" o similar, el bot responde con la promoción
  actual (texto y/o imagen) sin usar IA; si no hay ninguna guardada, responde el mensaje
  natural de siempre: *"Por ahora no tengo una promo cargada, pero puedo pasarte el menú o
  ayudarte con tu pedido."*

---

## Impresión de tickets y KDS

Renzo Snacks desea que los pedidos lleguen a Loyverse y se impriman. La impresora del restaurante es **Bluetooth**.

> No prometer impresión automática hasta probar con la cuenta real, POS real e impresora Bluetooth.

### Opción A — Doble impresión (cocina + venta)

- Configurar dos impresoras en Loyverse POS: una para cocina y otra para caja/venta.
- Al crear el receipt desde la API, Loyverse puede disparar ambas impresoras si están configuradas.
- Se configura en Loyverse POS → Ajustes → Impresoras. El bot no controla esto.

### Opción B — iPad como pantalla de cocina (Loyverse KDS)

- Instalar Loyverse KDS en un iPad o tablet en cocina.
- El iPad muestra los pedidos en pantalla; el equipo de cocina los ve sin necesidad de impresión.
- POS y KDS deben estar en la misma red Wi-Fi.
- Solo se imprime un ticket si lo prefieren (para el cliente o caja).
- Se configura desde Loyverse POS/KDS. El bot no interactúa con KDS directamente.

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

Cliente: Domicilio
Bot: El envío tiene un costo extra aproximado de $50, pero te confirmamos según tu ubicación. ¿Me pasas tu dirección?

Cliente: [da dirección], pago transferencia
Bot: [muestra resumen] "¿Así lo confirmo?"

Cliente: Sí confirmo
Bot: [si Loyverse activo] "Listo, tu pedido fue registrado."
     [si Loyverse inactivo] "Listo, ya tengo los datos. Lo paso al equipo para confirmar."
```

---

## Qué falta para activar Loyverse

- [ ] Decidir opción de número WhatsApp (ver sección Variables de entorno)
- [ ] Obtener token de acceso de Loyverse (Configuración → Integraciones → API)
- [ ] Copiar Store ID desde el dashboard
- [ ] Configurar `LOYVERSE_ENABLED=true` y `LOYVERSE_ACCESS_TOKEN=...` en Railway
- [ ] (Opcional) Agregar `LOYVERSE_POS_DEVICE_ID` para asignar pedidos al dispositivo físico
- [ ] Probar con un pedido real y verificar que aparece en el POS
- [ ] Probar impresión con impresora Bluetooth y decidir entre Opción A o Opción B
- [ ] Guardar logo en `assets/logo_renzo_snacks.png`

---

## Qué falta para conectar el número real

- [ ] Probar el **escenario recomendado de coexistencia** (WhatsApp Business App + Cloud API
      en 9631000021) antes de prometer nada al cliente — ver "Escenarios para el número de
      WhatsApp"
- [ ] Si la coexistencia no es viable, obtener aprobación explícita del cliente antes de
      considerar migración completa o número nuevo
- [ ] Registrar el número en Meta Business Manager
- [ ] Crear la app de WhatsApp Cloud API en Meta Developers
- [ ] Obtener `META_PHONE_NUMBER_ID` y `META_ACCESS_TOKEN` (token de sistema)
- [ ] Definir `META_VERIFY_TOKEN` (ej. `renzosnacks-2026`)
- [ ] Configurar el webhook en Meta: `https://[tu-app].up.railway.app/webhook`
- [ ] Activar la suscripción al campo `messages`

---

## Estados del pedido

| Estado | Significado |
|---|---|
| `enviado_a_loyverse` | Pedido registrado en el POS |
| `pendiente_revision` | Hay productos que no se encontraron en Loyverse |
| `pendiente_confirmacion_humana` | Loyverse inactivo; requiere acción manual |
| `error_loyverse` | Error de API; pedido en logs del servidor |

---

## Logs esperados al iniciar

```
Cliente cargado: Renzo Snacks
Modo de implementación WhatsApp: no definido
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
