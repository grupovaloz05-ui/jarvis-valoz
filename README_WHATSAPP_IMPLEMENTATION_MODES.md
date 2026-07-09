# Modos de implementación de WhatsApp — guía para vender e implementar

Jarvis (este repositorio) es la **plantilla base** de Valoz Digital para agentes de
WhatsApp. No es el bot de un cliente único: cada cliente nuevo obtiene su propio
`CLIENT_ID`, su propia carpeta en `clientes/<cliente>/`, sus propias variables de
Meta y, opcionalmente, su propio servicio en Railway. Ver `README_CLIENT_SETUP.md`
para el proceso completo de alta de un cliente.

Este documento explica los **3 modelos de implementación** que se le pueden vender
a un negocio, sus riesgos, cuándo recomendar cada uno, y qué pedirle al cliente
antes de tocar su número de WhatsApp.

> **Nota sobre Valoz Digital:** el número de Valoz **ya no está conectado** a
> WhatsApp Cloud API (se quitó para recuperarlo en WhatsApp Business App). No
> asumas que hay un Phone Number ID activo para Valoz en ningún ejemplo, script o
> configuración de este repo.

---

## Los 3 modelos

### 1. NUMERO_PRINCIPAL_API — número principal directo a Cloud API

El número principal del negocio (el que ya usan sus clientes) se conecta
directamente a WhatsApp Cloud API. El bot responde desde ese mismo número.

- **Riesgo:** el negocio **puede perder WhatsApp Business App** en ese número,
  incluyendo **estados/historias**, catálogo y el manejo visual normal de la app.
  Cloud API y la app normal no siempre coexisten sin coexistencia oficial activada.
- **Cuándo recomendarlo:** el negocio no usa estados/historias, no le importa
  operar solo desde la API, o quiere la opción más rápida de implementar y ya
  entiende y acepta el riesgo.
- **Documentarlo como:** opción rápida, pero con riesgo. No es la opción por
  defecto para negocios que ya usan activamente WhatsApp Business App.

### 2. NUMERO_SECUNDARIO_API — número secundario dedicado al bot (recomendado por defecto)

El número principal del negocio se conserva tal cual en WhatsApp Business App
normal (con sus estados, catálogo, historial). El bot vive en un **número
secundario nuevo**, conectado a Cloud API.

- Es la opción **segura** para negocios que quieren seguir usando estados/historias
  en su número de siempre sin arriesgarlo.
- El número principal (o números autorizados) puede mandarle **comandos al bot**
  para actualizar promociones — ver `agent/promotions.py` y la sección de abajo.
- **Cuándo recomendarlo:** es el default razonable para la mayoría de negocios
  pequeños/medianos que ya tienen un número activo y no quieren arriesgarlo.
  El costo es que los clientes deben aprender/usar un número distinto para el bot
  (o el negocio redirige/anuncia el número nuevo).

### 3. COEXISTENCIA_OFICIAL — mismo número, app + API al mismo tiempo

El mismo número opera con WhatsApp Business App **y** con Cloud API/bot al mismo
tiempo, usando la función de coexistencia de Meta.

- **Requiere** un Tech Provider / BSP / proveedor oficial, y el flujo de
  **Embedded Signup aprobado por Meta** (ver `README_META_EMBEDDED_SIGNUP.md` y
  `/embedded-signup-test` en este repo para probar el flujo).
- Es la opción **premium**: el negocio conserva su número, sus estados y su app,
  y el bot responde por API sobre el mismo número.
- **Documentarla como:** futura o disponible solo cuando haya proveedor oficial
  aprobado. No prometerla como disponible de inmediato — depende de aprobación
  de Meta y de la disponibilidad de coexistencia para el tipo de cuenta/región
  del cliente. Debe **probarse** antes de prometerse como segura (ver el caso de
  Renzo Snacks en `clientes/renzosnacks/README.md` para un ejemplo de cómo
  documentar esto sin prometer de más).

---

## Cómo pedir consentimiento al cliente antes de migrar su número

Antes de tocar el número de WhatsApp que el negocio ya usa:

1. **Explica los 3 modelos** en términos simples: "directo con riesgo",
   "número nuevo seguro", "mismo número pero requiere aprobación de Meta".
2. **Sé explícito sobre lo que se pierde** si elige `NUMERO_PRINCIPAL_API` sin
   coexistencia: estados/historias y el uso normal de WhatsApp Business App en
   ese número.
3. **No ejecutes una migración completa sin aprobación explícita por escrito**
   (o al menos por WhatsApp) del dueño del negocio o de quien administre el número.
4. Si el cliente elige `COEXISTENCIA_OFICIAL`, aclara que depende de aprobación de
   Meta y de tener proveedor oficial — no es instantáneo.
5. Registra la decisión final en el `README.md` del cliente (`clientes/<cliente>/README.md`),
   como se hizo para Renzo Snacks.

## Qué datos pedir antes de configurar

| Dato | Para qué |
|---|---|
| Número de WhatsApp actual del negocio | Decidir si aplica coexistencia o número nuevo |
| ¿Usa estados/historias activamente? | Determina si `NUMERO_PRINCIPAL_API` es aceptable |
| ¿Tiene catálogo de WhatsApp Business? | Mismo motivo — se pierde sin coexistencia |
| ¿Quién administra el número hoy? | Quién debe dar el consentimiento |
| Números que deben poder administrar promociones | Para `admin_numbers` en `client_config.yaml` |
| Modelo elegido (1, 2 o 3) | Se guarda en `whatsapp_implementation_mode` |

---

## Configuración por cliente

Cada cliente es independiente. En `clientes/<cliente>/config/client_config.yaml`:

```yaml
whatsapp_implementation_mode: "NUMERO_SECUNDARIO_API"   # o NUMERO_PRINCIPAL_API / COEXISTENCIA_OFICIAL

admin_numbers:
  - "521XXXXXXXXXX"
  - "521XXXXXXXXXX"

promotion_settings:
  enabled: true
  allow_text_promos: true
  allow_image_promos: true
  current_promo_text_path: "clientes/<cliente>/knowledge/promo_actual.md"
  current_promo_image_path: "clientes/<cliente>/assets/promos/current_promo.jpg"
```

Y en Railway (o `.env` local), variables propias del cliente — nunca compartidas
con otro cliente ni con Valoz:

```env
CLIENT_ID=<cliente>
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=...
META_VERIFY_TOKEN=...
```

Cada cliente puede tener su propio servicio de Railway (recomendado si necesita
aislar logs, dominio o base de datos), o compartir el mismo despliegue si
`CLIENT_ID` lo diferencia — depende del volumen y del presupuesto del cliente.

---

## Sistema de promociones administrables

Con `promotion_settings.enabled: true` y al menos un número en `admin_numbers`,
el negocio puede actualizar la promoción actual mandando mensajes al número del
bot, sin usar ningún panel ni tocar código. Ver `agent/promotions.py`.

**Comandos (solo para números en `admin_numbers`):**

| Comando | Acción |
|---|---|
| `ACTUALIZAR PROMO` | Guarda el texto y/o la imagen que siga al comando como la promoción actual. |
| `VER PROMO ACTUAL` | Muestra la promoción guardada. |
| `BORRAR PROMO` | Elimina la promoción actual. |
| `AYUDA ADMIN` | Lista los comandos disponibles. |
| `PREPARAR STORY` | Devuelve texto corto + imagen (si existe) para subir manualmente a estados de WhatsApp. |

**Reglas clave:**

- Solo los números en `admin_numbers` pueden usar estos comandos. Un número no
  autorizado recibe un mensaje explicando que no puede actualizar promociones.
- Los comandos administrativos **no llaman al modelo de IA** — se resuelven por
  keywords para no gastar tokens.
- Si un cliente normal pregunta "promos", "promociones", "promo de hoy", etc., el
  bot responde con la promoción actual (texto y/o imagen), o con un mensaje
  natural si no hay ninguna guardada.
- `PREPARAR STORY` **nunca sube nada automáticamente**: WhatsApp Cloud API no
  tiene función para publicar estados. El bot solo entrega el contenido listo
  para que alguien del negocio lo suba a mano desde su WhatsApp Business
  principal.
- Si un cliente no tiene `promotion_settings` en su config, o `enabled: false`,
  el bot funciona exactamente igual que antes — esta función es 100% opcional
  por cliente.
