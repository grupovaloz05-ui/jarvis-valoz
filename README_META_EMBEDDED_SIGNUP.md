# Verificacion de Embedded Signup de Meta (WhatsApp)

Este repo tiene dos piezas para probar el flujo de **Embedded Signup** de
Meta sin depender de business.facebook.com:

1. La pagina `/embedded-signup-test` (seccion siguiente), que lanza el popup
   de login desde tu propio dominio.
2. El script `scripts/check_meta_embedded_signup.py` (mas abajo), que verifica
   por la Graph API que el numero quedo conectado despues de ese login.

Nada de esto hace deploy, toca produccion, toca el cliente Renzo ni Railway,
ni guarda tokens en archivos.

## Pagina de prueba: `/embedded-signup-test`

Ruta agregada en `agent/main.py` (`GET /embedded-signup-test`). Sirve una
pagina HTML simple, servida desde tu propio dominio, que:

- Carga el SDK de Facebook para JavaScript (`connect.facebook.net/.../sdk.js`).
- Inicializa `FB.init` con tu `META_APP_ID`.
- Al hacer clic en el boton, llama `FB.login` con `config_id` =
  `META_EMBEDDED_SIGNUP_CONFIG_ID` y pide los scopes:
  - `business_management`
  - `whatsapp_business_management`
  - `whatsapp_business_messaging`
- Muestra en pantalla el resultado crudo del callback de `FB.login`
  (`code`, `business_id`, `waba_id`, `phone_number_id`, `error`) y tambien
  los eventos `WA_EMBEDDED_SIGNUP` que Meta manda por `postMessage` durante
  el flujo.
- Nunca imprime el App Secret (la pagina ni siquiera lo lee).
- No guarda ningun token ni codigo en el servidor: todo vive solo en el
  navegador, en esa pestaña, mientras la pruebas.

### Variables de entorno necesarias

```bash
META_APP_ID=tu_app_id
META_EMBEDDED_SIGNUP_CONFIG_ID=tu_config_id_de_embedded_signup
```

Ninguna de las dos es secreta (el App ID y el Config ID viajan igual al
navegador con el flujo normal de `FB.login`), pero **nunca** pongas
`META_APP_SECRET` en esta pagina ni la expongas al frontend.

### Como probarla

1. Configura `META_APP_ID` y `META_EMBEDDED_SIGNUP_CONFIG_ID` en tu `.env`
   (ver `.env.example`) y corre el servidor localmente o en tu entorno de
   staging (no hay deploy automatico — tu decides cuando desplegar).
2. Abre la pagina **desde un dominio autorizado** en la configuracion de tu
   app de Meta (Meta for Developers → tu app → Facebook Login → Configuracion
   → "Dominios de la app" / "URI de redireccionamiento de OAuth valida").
   Por ejemplo:
   ```
   https://valoz-digital-web-production.up.railway.app/embedded-signup-test
   ```
   **No** uses la URL alojada de `business.facebook.com` como `redirect_uri`:
   ese dominio es el que usa Meta para su propio flujo alojado, y no coincide
   con el dominio desde el que estas sirviendo esta pagina. Si el
   `redirect_uri` no coincide caracter por caracter con el dominio real desde
   el que se abrio el popup, Meta puede rechazar el intercambio de codigo
   (ver la seccion `META_REDIRECT_URI` mas abajo).
3. Haz clic en "Probar Embedded Signup" e inicia sesion con la cuenta de
   Facebook que administra el WhatsApp Business App que quieres conectar.
4. Revisa el bloque de resultado en pantalla: si aparece `code`, copialo de
   inmediato (expira en minutos) y usalo con
   `scripts/check_meta_embedded_signup.py` para confirmar por la Graph API
   que el WABA y el numero quedaron conectados.

### Seguridad de la pagina

- No imprime el App Secret (no lo lee del entorno).
- No guarda tokens: el `code` que entrega Meta solo se muestra en pantalla,
  no se envia a ningun backend propio ni se persiste.
- No toca el cliente Renzo Snacks ni ninguna configuracion de produccion.
- No dispara ningun deploy: correrla localmente o en un entorno ya
  desplegado es responsabilidad tuya.

---

## Script de verificacion: `check_meta_embedded_signup.py`

Este script sirve para revisar, de forma segura y solo de lectura, que quedo
conectado despues de correr el flujo de **Embedded Signup** de Meta (el popup
de "Iniciar sesion con Facebook" que entrega un codigo de autorizacion).

No hace deploy, no toca produccion, no toca el cliente Renzo ni Railway, y no
guarda ningun token en archivos.

## Que necesitas antes de correr el script

1. **App ID** y **App Secret** de tu app de Meta (Meta for Developers > tu
   app > Configuracion basica).
2. El **codigo de respuesta de registro** ("response code") que te entrego el
   flujo de Embedded Signup justo despues de hacer clic en "Iniciar sesion
   con Facebook". Este codigo **expira en pocos minutos y se usa una sola
   vez**, asi que conviene correr el script apenas lo obtengas.

## Como correrlo

Todo se pasa por variables de entorno en tu propia terminal, nunca dentro de
un archivo del repo:

```bash
export META_APP_ID="tu_app_id"
export META_APP_SECRET="tu_app_secret"
export META_EMBEDDED_SIGNUP_CODE="el_codigo_que_te_dio_el_popup"

python3 scripts/check_meta_embedded_signup.py
```

Opcional: si necesitas forzar otra version de la Graph API (por defecto usa
`v21.0`):

```bash
export META_GRAPH_API_VERSION="v20.0"
```

### META_REDIRECT_URI (opcional)

Si al correr el script Meta responde con un error como este:

```
Error validating verification code. Please make sure your redirect_uri is
identical to the one you used in the OAuth dialog request.
code=100, subcode=36008
```

significa que tu flujo de OAuth uso un `redirect_uri` explicito al iniciar el
login, y ese mismo valor se debe repetir, caracter por caracter, al
intercambiar el codigo por un access token. Para eso, exporta:

```bash
export META_REDIRECT_URI="https://tu-dominio.com/tu/ruta/exacta"

python3 scripts/check_meta_embedded_signup.py
```

El script:
- Si `META_REDIRECT_URI` esta configurado, lo incluye tal cual en la llamada
  a `/oauth/access_token`.
- Si no esta configurado, intenta el intercambio sin `redirect_uri` (como
  antes) y, si Meta devuelve el error `code=100, subcode=36008`, explica que
  probablemente falte configurar esta variable.
- Siempre muestra en pantalla que `redirect_uri` esta usando (o si no esta
  configurado ninguno), pero nunca imprime tokens completos ni secretos.

**Nota sobre Embedded Signup alojado por Meta:** si tu flujo muestra una
"pagina de destino del registro insertado alojada por Meta" (Meta-hosted
Embedded Signup landing page), el `redirect_uri` debe ser esa URL exacta, si
aplica a tu configuracion. El requisito general de Meta es que el
`redirect_uri` usado al intercambiar el codigo sea identico, caracter por
caracter, al usado en el dialogo de login original.

## Que hace el script

1. Lee el codigo, el App ID y el App Secret desde variables de entorno.
2. Intercambia el codigo por un access token contra la Graph API de Meta.
3. Usa `debug_token` sobre ese access token para ver que scopes y que IDs
   (negocio, WhatsApp Business Account) quedaron autorizados.
4. Para cada WABA candidato, consulta su nombre y sus numeros de telefono
   conectados (`/{waba_id}/phone_numbers`).
5. Imprime un diagnostico final en una de estas categorias:
   - **Conexion correcta**: hay un WABA con al menos un numero conectado.
   - **Numero no conectado**: el WABA existe pero no tiene numero asociado.
   - **Falta de permisos**: Meta devolvio errores de permisos al leer los
     activos.
   - **Flujo incompleto**: el token no tiene scopes de WhatsApp Business, o
     el intercambio de codigo fallo (codigo vencido o invalido).

## Sobre "coexistencia"

El script imprime el campo crudo `platform_type` que devuelve Meta para cada
numero, pero **no asume** que el resultado es un caso de "coexistencia"
(numero ya usado en la app de WhatsApp Business conectado ahora via API).
Esa interpretacion hay que confirmarla revisando el detalle en Meta Business
Suite / WhatsApp Manager, no solo con la salida de este script.

## Seguridad

- El script nunca imprime el App Secret (ni siquiera parcialmente).
- El codigo de Embedded Signup y el access token se muestran enmascarados
  (solo primeros/ultimos caracteres) para poder confirmar que se cargo la
  variable correcta, sin exponer el valor completo en la terminal.
- Ningun token ni secreto se escribe en disco. Todo vive solo en la sesion de
  tu terminal mientras el script corre.
- Solo se hacen llamadas `GET` de lectura a la Graph API. No se crea, edita
  ni borra nada en Meta.
