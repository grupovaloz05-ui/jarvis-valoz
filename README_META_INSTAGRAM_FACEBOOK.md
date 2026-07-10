# Integración de Instagram DM y Facebook Messenger — Jarvis Valoz

Esta integración agrega Instagram Direct Messages y Facebook Messenger a Jarvis,
usando el mismo webhook `/webhook` que ya usa WhatsApp. **Solo aplica a Jarvis
Valoz Digital** — no se activa ni afecta a clientes con `CLIENT_ID` distinto
(ej. Renzo Snacks), y está deshabilitada por defecto.

WhatsApp sigue funcionando exactamente igual que antes: si el payload entrante
no trae `object: "instagram"` ni `object: "page"`, el webhook sigue el flujo
original de WhatsApp sin ningún cambio.

---

## 1. Variables de entorno necesarias

Agrega esto a tu `.env` (ya están en `.env.example` con valores vacíos/false):

```bash
INSTAGRAM_ENABLED=false
FACEBOOK_MESSENGER_ENABLED=false
META_PAGE_ACCESS_TOKEN=
META_PAGE_ID=
META_INSTAGRAM_ACCOUNT_ID=
VALOZ_WHATSAPP_LINK=https://wa.me/529615805721
```

| Variable | Para qué sirve |
|---|---|
| `INSTAGRAM_ENABLED` | Activa el canal de Instagram. Si es `false` (default), los eventos de Instagram se ignoran con un warning en logs, sin romper nada. |
| `FACEBOOK_MESSENGER_ENABLED` | Igual que arriba, para Facebook Messenger. |
| `META_PAGE_ACCESS_TOKEN` | Token de acceso de la Página de Facebook (se usa para enviar mensajes tanto de Instagram como de Messenger — la Instagram Messaging API usa el token de la Página vinculada). |
| `META_PAGE_ID` | ID numérico de la Página de Facebook (para Messenger). |
| `META_INSTAGRAM_ACCOUNT_ID` | ID de la cuenta profesional de Instagram vinculada a la Página. |
| `VALOZ_WHATSAPP_LINK` | Enlace de WhatsApp que se manda en DMs y en respuestas a comentarios. Ya viene con el de Valoz por defecto. |

Estas variables son independientes de `META_ACCESS_TOKEN` / `META_PHONE_NUMBER_ID`
(WhatsApp) — nunca se mezclan.

---

## 2. Permisos necesarios en Meta

En tu app de Meta (developers.facebook.com), en modo de desarrollo o ya
verificada, necesitas:

- `pages_show_list`
- `pages_manage_metadata`
- `pages_messaging` (Facebook Messenger)
- `instagram_basic`
- `instagram_manage_messages` (DMs de Instagram)
- `instagram_manage_comments` (para responder comentarios / private replies)
- `pages_manage_engagement` o equivalente para comentarios de Facebook

Meta requiere revisión de la app (App Review) para usar estos permisos en
producción con cuentas que no sean administradoras/testers de la app. En modo
desarrollo puedes probar con tu propia Página e Instagram sin revisión.

---

## 3. Cómo conectar tu cuenta de Instagram profesional

1. La cuenta de Instagram debe ser **profesional** (Business o Creator) y estar
   **vinculada a una Página de Facebook**.
2. En Meta for Developers → tu app → Instagram → agrega el producto "Instagram"
   (Messaging).
3. Vincula la cuenta de Instagram a través de la Página en la configuración de
   la app.
4. Obtén el `META_INSTAGRAM_ACCOUNT_ID`: puedes consultarlo con
   `GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token={page_access_token}`.
5. Genera un **Page Access Token de larga duración** (con los permisos de
   Instagram listados arriba) y ponlo en `META_PAGE_ACCESS_TOKEN`.

## 4. Cómo conectar tu página de Facebook

1. En Meta for Developers → tu app → agrega el producto "Messenger".
2. Selecciona la Página desde el panel de Messenger y genera el
   **Page Access Token** — este es el mismo token que usas para Instagram
   (`META_PAGE_ACCESS_TOKEN`), siempre que ambos productos estén en la misma app.
3. Copia el ID de la Página (`META_PAGE_ID`) desde la configuración de la
   Página o con `GET /me?access_token=...`.

## 5. Cómo configurar los webhooks

1. En Meta for Developers → tu app → Webhooks, usa la **misma URL** que ya
   usas para WhatsApp: `https://tu-dominio/webhook`, y el mismo
   `META_VERIFY_TOKEN` que ya tienes configurado (la verificación GET es a
   nivel de app, no cambia por producto).
2. Suscribe los campos:
   - **Messenger** (`object: page`): `messages`, `messaging_postbacks`, `feed`
     (para comentarios).
   - **Instagram** (`object: instagram`): `messages`, `comments`.
3. Suscribe tu Página específica (y su Instagram vinculado) en la pestaña de
   suscripciones del producto correspondiente — no basta con configurar el
   webhook a nivel de app, cada Página debe suscribirse explícitamente.

No se necesita ni se toca ningún otro webhook: el endpoint `GET /webhook`
(verificación) y el manejo de `whatsapp_business_account` en `POST /webhook`
quedan exactamente igual que antes.

---

## 6. Cómo probar DMs localmente

Con el servidor corriendo localmente (`uvicorn agent.main:app --reload`) y
`INSTAGRAM_ENABLED=true` / `FACEBOOK_MESSENGER_ENABLED=true`:

```bash
# Simula un DM de Instagram
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "messaging": [{
        "sender": {"id": "1784140000000"},
        "recipient": {"id": "PAGE_ID"},
        "message": {"mid": "m1", "text": "Hola, quiero info de precios"}
      }]
    }]
  }'

# Simula un DM de Facebook Messenger
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "page",
    "entry": [{
      "messaging": [{
        "sender": {"id": "PSID_DE_PRUEBA"},
        "recipient": {"id": "PAGE_ID"},
        "message": {"mid": "m1", "text": "Quiero un bot para mi negocio"}
      }]
    }]
  }'
```

Si no configuraste `META_PAGE_ACCESS_TOKEN`, Jarvis genera la respuesta pero
falla al enviarla (verás un warning en logs) — no rompe el servidor.

Para probar en local **sin exponer tu servidor a internet**, puedes usar una
herramienta de túnel (ej. ngrok) apuntando a tu puerto local y usar esa URL
como Callback URL en Meta.

## 7. Cómo probar comentario → DM

```bash
# Simula un comentario con palabra clave en Instagram
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "changes": [{
        "field": "comments",
        "value": {
          "id": "comment_123",
          "text": "me interesa, cuánto cuesta",
          "from": {"id": "1784140000000"}
        }
      }]
    }]
  }'

# Simula un comentario con palabra clave en Facebook
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "page",
    "entry": [{
      "changes": [{
        "field": "feed",
        "value": {
          "item": "comment",
          "verb": "add",
          "comment_id": "comment_456",
          "message": "quiero el bot para whatsapp",
          "from": {"id": "u1"}
        }
      }]
    }]
  }'
```

Si el comentario contiene alguna de estas palabras clave (sin importar
mayúsculas/acentos): `info, precio, precios, whatsapp, me interesa, paquetes,
bot, página, web, tarjeta, reseñas, calificaciones` — Jarvis intenta enviar un
private reply con el mensaje breve y el link de WhatsApp, y guarda el lead en
Sheets con `Canal: Comentario Instagram` o `Canal: Comentario Facebook` en la
columna "Próximo paso". Comentarios sin esas palabras se ignoran por completo
(no hay respuesta pública ni DM frío).

---

## 8. Límites importantes

- **App Review de Meta**: sin revisión de la app, solo podrás probar con
  cuentas admin/tester de la app (tu propia Página e Instagram). Para
  producción con clientes reales necesitas pasar App Review para los permisos
  listados en la sección 2.
- **Ventana de 24 horas**: Meta solo permite mensajes de texto libre dentro de
  las 24 horas después del último mensaje del usuario (igual que Messenger
  Platform estándar). Pasada esa ventana, se requieren plantillas o tags
  especiales — esto no está implementado aquí.
- **Private replies**: Meta limita cuántas veces puedes responder
  privadamente a un mismo comentario y por cuánto tiempo sigue siendo válido
  el `comment_id` para ese fin (generalmente unas horas). No sirve para
  reabrir conversaciones viejas.
- **Un token, dos canales**: Instagram Messaging y Messenger comparten el
  mismo `META_PAGE_ACCESS_TOKEN` porque el IG debe estar vinculado a la
  Página — si revocas o rotas ese token, ambos canales dejan de enviar hasta
  que lo actualices.
- **No hay envío proactivo**: esta integración solo responde a mensajes o
  comentarios entrantes. No manda mensajes fríos ni republica en redes.
- **Historial separado por canal**: las conversaciones de Instagram/Facebook
  se guardan con el identificador prefijado (`instagram:<IGSID>` o
  `facebook:<PSID>`), nunca se mezclan con números de WhatsApp ni entre sí.
