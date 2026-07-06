"""
Verifica el resultado de un flujo de Embedded Signup de Meta para WhatsApp.

Toma el "codigo de respuesta de registro" (authorization code) que entrega el
SDK de Facebook Login tras el flujo de Embedded Signup, lo intercambia por un
access token, y usa ese token para averiguar que activos (negocio, WABA,
numero de telefono) quedaron conectados.

No modifica nada en Meta ni en este proyecto: solo hace llamadas GET de
lectura contra la Graph API.

Uso:
    export META_APP_ID=...
    export META_APP_SECRET=...
    export META_EMBEDDED_SIGNUP_CODE=...
    # Opcional, solo si tu flujo de OAuth uso un redirect_uri explicito:
    export META_REDIRECT_URI=...
    python3 scripts/check_meta_embedded_signup.py

Ver README_META_EMBEDDED_SIGNUP.md para instrucciones detalladas.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
TIMEOUT = 20


def mask_secret(_value):
    """El app secret nunca se imprime, ni siquiera parcialmente."""
    return "(configurado, oculto)"


def mask_partial(value, visible=4):
    """Muestra solo los primeros/ultimos caracteres para poder confirmar
    que se cargo la variable correcta, sin exponer el valor completo."""
    if not value:
        return "(vacio)"
    if len(value) <= visible * 2:
        return f"{'*' * len(value)} (len={len(value)})"
    return f"{value[:visible]}...{value[-visible:]} (len={len(value)})"


def get_required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        print(f"ERROR: falta la variable de entorno {name}.")
        print("Exportala antes de correr el script (ver README_META_EMBEDDED_SIGNUP.md).")
        sys.exit(1)
    return value


def http_get_json(url):
    """GET contra la Graph API. Devuelve (status_code, json_body)."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"error": {"message": raw[:500]}}
        return e.code, body
    except urllib.error.URLError as e:
        return None, {"error": {"message": f"No se pudo conectar a Meta: {e}"}}


def describe_meta_error(body):
    err = (body or {}).get("error", {})
    msg = err.get("message", "Error desconocido de Meta")
    err_type = err.get("type", "")
    code = err.get("code", "")
    subcode = err.get("error_subcode", "")
    trace = err.get("fbtrace_id", "")
    parts = [f"mensaje='{msg}'"]
    if err_type:
        parts.append(f"type={err_type}")
    if code != "":
        parts.append(f"code={code}")
    if subcode != "":
        parts.append(f"subcode={subcode}")
    if trace:
        parts.append(f"fbtrace_id={trace}")
    return ", ".join(parts)


def is_permission_error(body):
    err = (body or {}).get("error", {})
    err_type = str(err.get("type", ""))
    code = err.get("code")
    subcode = err.get("error_subcode")
    if err_type == "OAuthException" and code in (10, 200, 3):
        return True
    if subcode in (33, 458, 459, 460):
        return True
    return False


def exchange_code_for_token(app_id, app_secret, code, redirect_uri=None):
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "code": code,
    }
    if redirect_uri:
        params["redirect_uri"] = redirect_uri
    url = f"{GRAPH_BASE}/oauth/access_token?{urllib.parse.urlencode(params)}"
    status, body = http_get_json(url)
    return status, body


def debug_token(app_id, app_secret, access_token):
    params = {
        "input_token": access_token,
        "access_token": f"{app_id}|{app_secret}",
    }
    url = f"{GRAPH_BASE}/debug_token?{urllib.parse.urlencode(params)}"
    return http_get_json(url)


def get_object_fields(object_id, fields, access_token):
    params = {"fields": ",".join(fields), "access_token": access_token}
    url = f"{GRAPH_BASE}/{object_id}?{urllib.parse.urlencode(params)}"
    return http_get_json(url)


def get_phone_numbers(waba_id, access_token):
    fields = [
        "id",
        "display_phone_number",
        "verified_name",
        "quality_rating",
        "platform_type",
        "code_verification_status",
    ]
    params = {"fields": ",".join(fields), "access_token": access_token}
    url = f"{GRAPH_BASE}/{waba_id}/phone_numbers?{urllib.parse.urlencode(params)}"
    return http_get_json(url)


def main():
    print("=== Verificacion de Embedded Signup de Meta (solo lectura) ===")
    print(f"Graph API version: {GRAPH_API_VERSION}")

    app_id = get_required_env("META_APP_ID")
    app_secret = get_required_env("META_APP_SECRET")
    code = get_required_env("META_EMBEDDED_SIGNUP_CODE")
    redirect_uri = os.getenv("META_REDIRECT_URI", "").strip() or None

    print(f"META_APP_ID: {app_id}")
    print(f"META_APP_SECRET: {mask_secret(app_secret)}")
    print(f"META_EMBEDDED_SIGNUP_CODE: {mask_partial(code)}")
    if redirect_uri:
        print(f"META_REDIRECT_URI: {redirect_uri} (se enviara en el intercambio de codigo)")
    else:
        print("META_REDIRECT_URI: (no configurado, se intentara sin redirect_uri)")

    # 1. Intercambiar el codigo por un access token
    print("\n--- Paso 1: intercambio de codigo por access token ---")
    status, body = exchange_code_for_token(app_id, app_secret, code, redirect_uri)

    if status is None or "error" in body:
        print(f"ERROR al intercambiar el codigo (HTTP {status}).")
        print(describe_meta_error(body))
        err = (body or {}).get("error", {})
        if err.get("code") == 100 and err.get("error_subcode") == 36008:
            print(
                "\nDiagnostico: REDIRECT_URI INCORRECTO. Meta exige que el "
                "redirect_uri de este intercambio sea identico (caracter por "
                "caracter) al que se uso en el dialogo de OAuth original."
            )
            if redirect_uri:
                print(
                    f"Se envio META_REDIRECT_URI='{redirect_uri}'. Verifica que "
                    "sea exactamente el mismo que se uso al iniciar el flujo de "
                    "login (incluyendo esquema, mayusculas/minusculas, barra "
                    "final y query params, si los hubiera)."
                )
            else:
                print(
                    "No se configuro META_REDIRECT_URI. Si tu flujo de OAuth "
                    "uso un redirect_uri explicito (por ejemplo, en un login "
                    "manual en vez del Embedded Signup alojado por Meta), "
                    "exporta META_REDIRECT_URI con ese mismo valor exacto y "
                    "volve a correr el script."
                )
            print(
                "\nNota sobre Embedded Signup alojado por Meta: si tu flujo "
                "muestra una 'pagina de destino del registro insertado "
                "alojada por Meta', el redirect_uri debe ser esa URL exacta "
                "si aplica a tu configuracion."
            )
            sys.exit(1)
        print("\nDiagnostico: FLUJO INCOMPLETO o codigo invalido/expirado.")
        print(
            "El codigo de Embedded Signup normalmente expira en minutos y "
            "solo puede usarse una vez. Repeti el flujo de 'Iniciar sesion "
            "con Facebook' para generar un codigo nuevo y corre este script "
            "de inmediato."
        )
        sys.exit(1)

    access_token = body.get("access_token")
    if not access_token:
        print("ERROR: Meta respondio sin access_token.")
        print(json.dumps(body, indent=2, ensure_ascii=False)[:800])
        sys.exit(1)

    print(f"Access token obtenido: {mask_partial(access_token)}")
    token_type = body.get("token_type", "desconocido")
    print(f"Tipo de token: {token_type}")

    # 2. Inspeccionar el token para ver que permisos/activos quedaron autorizados
    print("\n--- Paso 2: inspeccion del token (debug_token) ---")
    dbg_status, dbg_body = debug_token(app_id, app_secret, access_token)

    if dbg_status is None or "error" in dbg_body:
        print(f"ERROR al inspeccionar el token (HTTP {dbg_status}).")
        print(describe_meta_error(dbg_body))
        sys.exit(1)

    data = dbg_body.get("data", {})
    if not data.get("is_valid", False):
        print("El token no es valido segun Meta.")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:800])
        print("\nDiagnostico: FLUJO INCOMPLETO.")
        sys.exit(1)

    scopes = data.get("scopes", [])
    granular_scopes = data.get("granular_scopes", [])
    print(f"Scopes otorgados: {scopes if scopes else '(ninguno)'}")

    waba_candidate_ids = set()
    business_candidate_ids = set()

    for g in granular_scopes:
        scope = g.get("scope", "")
        target_ids = g.get("target_ids", []) or []
        if scope in ("whatsapp_business_management", "whatsapp_business_messaging"):
            waba_candidate_ids.update(target_ids)
        elif scope == "business_management":
            business_candidate_ids.update(target_ids)

    if not scopes and not granular_scopes:
        print(
            "\nDiagnostico: FLUJO INCOMPLETO. El token no tiene scopes "
            "asociados: probablemente el usuario cerro el popup de "
            "Facebook antes de terminar el flujo, o no selecciono un "
            "negocio/numero durante el Embedded Signup."
        )
        sys.exit(0)

    if not waba_candidate_ids:
        print(
            "\nDiagnostico: FALTA DE PERMISOS o FLUJO INCOMPLETO. El token "
            "es valido pero no tiene scopes de WhatsApp Business "
            "(whatsapp_business_management / whatsapp_business_messaging). "
            "Revisa que el config_id usado en el Embedded Signup incluya "
            "esos permisos y que el usuario haya aprobado el acceso al "
            "WhatsApp Business Account durante el popup."
        )
        sys.exit(0)

    # 3. Resolver nombre(s) de negocio
    print("\n--- Paso 3: negocio(s) autorizado(s) ---")
    business_names = {}
    if business_candidate_ids:
        for biz_id in business_candidate_ids:
            b_status, b_body = get_object_fields(biz_id, ["id", "name"], access_token)
            if b_status == 200 and "error" not in b_body:
                business_names[biz_id] = b_body.get("name", "(sin nombre)")
                print(f"business_id={biz_id}  nombre='{business_names[biz_id]}'")
            else:
                print(f"business_id={biz_id}  (no se pudo leer: {describe_meta_error(b_body)})")
    else:
        print("No se recibieron IDs de negocio (business_management) en el token.")

    # 4. Resolver WABA(s) y numero(s) conectado(s)
    print("\n--- Paso 4: WhatsApp Business Account(s) y numero(s) ---")
    connection_found = False
    permission_issue_found = False
    waba_found_but_no_phone = False

    for waba_id in waba_candidate_ids:
        fields = ["id", "name", "currency", "timezone_id", "on_behalf_of_business_info"]
        w_status, w_body = get_object_fields(waba_id, fields, access_token)

        if w_status != 200 or "error" in w_body:
            if is_permission_error(w_body):
                permission_issue_found = True
            print(f"\nwaba_id candidato: {waba_id}")
            print(f"  No se pudo leer como WABA: {describe_meta_error(w_body)}")
            print("  (puede ser un ID de negocio, no de WABA, o falta de permisos)")
            continue

        print(f"\nwhatsapp_business_account_id: {waba_id}")
        print(f"  nombre del WABA: {w_body.get('name', '(sin nombre)')}")
        obo = w_body.get("on_behalf_of_business_info")
        if obo:
            print(f"  negocio asociado (on_behalf_of_business_info): {obo}")

        ph_status, ph_body = get_phone_numbers(waba_id, access_token)
        if ph_status != 200 or "error" in ph_body:
            if is_permission_error(ph_body):
                permission_issue_found = True
            print(f"  No se pudieron leer los numeros: {describe_meta_error(ph_body)}")
            continue

        phones = ph_body.get("data", [])
        if not phones:
            waba_found_but_no_phone = True
            print("  Numero conectado: NINGUNO (el WABA existe pero no tiene numeros).")
            continue

        for p in phones:
            connection_found = True
            print("  --- numero ---")
            print(f"  phone_number_id: {p.get('id')}")
            print(f"  numero: {p.get('display_phone_number', '(no disponible)')}")
            print(f"  nombre verificado: {p.get('verified_name', '(no disponible)')}")
            print(f"  calidad: {p.get('quality_rating', '(no disponible)')}")
            print(f"  platform_type (dato crudo de Meta): {p.get('platform_type', '(no disponible)')}")
            print(f"  code_verification_status: {p.get('code_verification_status', '(no disponible)')}")

    # 5. Diagnostico final
    print("\n=== Diagnostico final ===")
    if connection_found:
        print("CONEXION CORRECTA: se encontro al menos un WhatsApp Business")
        print("Account con un numero de telefono conectado (ver detalle arriba).")
        print(
            "\nNota: 'platform_type' es el dato crudo que devuelve Meta para "
            "ese numero. No asumas que se trata de 'coexistencia' (numero "
            "ya usado en la app de WhatsApp Business) solo por este script: "
            "confirma el estado real en Meta Business Suite / WhatsApp "
            "Manager antes de tomar decisiones."
        )
    elif waba_found_but_no_phone:
        print("NUMERO NO CONECTADO: se encontro un WhatsApp Business Account")
        print("valido, pero no tiene ningun numero de telefono asociado.")
        print("El usuario probablemente no completo la seleccion/verificacion")
        print("del numero durante el Embedded Signup.")
    elif permission_issue_found:
        print("FALTA DE PERMISOS: Meta devolvio errores de permisos al leer")
        print("el WABA o los numeros. Revisa los scopes del config_id de")
        print("Embedded Signup y los permisos del usuario/sistema que aprobo")
        print("el flujo.")
    else:
        print("FLUJO INCOMPLETO: no se pudo confirmar un WABA con numero")
        print("conectado. Revisa los mensajes anteriores para mas detalle.")

    print("\nRecordatorio: este script solo hizo lecturas (GET). No se")
    print("modifico nada en Meta, no se hizo deploy, y no se guardo ningun")
    print("token en disco.")


if __name__ == "__main__":
    main()
