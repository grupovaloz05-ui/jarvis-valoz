import os
import json
import urllib.request
import urllib.error

API_BASE = os.getenv("LOYVERSE_API_BASE_URL", "https://api.loyverse.com/v1.0")
TOKEN = os.getenv("LOYVERSE_ACCESS_TOKEN")

def request_json(path):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"\nERROR en {path}: HTTP {e.code}")
        print(body[:800])
        return None
    except Exception as e:
        print(f"\nERROR en {path}: {e}")
        return None

def print_items(title, data, possible_keys):
    print(f"\n=== {title} ===")

    if not data:
        print("No se pudo obtener información.")
        return

    items = None
    for key in possible_keys:
        if isinstance(data, dict) and key in data:
            items = data[key]
            break

    if items is None:
        if isinstance(data, list):
            items = data
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
            return

    if not items:
        print("Sin resultados.")
        return

    for item in items[:30]:
        if not isinstance(item, dict):
            print(item)
            continue

        name = (
            item.get("name")
            or item.get("store_name")
            or item.get("employee_name")
            or item.get("device_name")
            or item.get("item_name")
            or "Sin nombre"
        )

        item_id = (
            item.get("id")
            or item.get("store_id")
            or item.get("employee_id")
            or item.get("pos_device_id")
        )

        print(f"- {name} | id: {item_id}")

def main():
    if not TOKEN:
        print("Falta LOYVERSE_ACCESS_TOKEN.")
        print('Primero ejecuta: export LOYVERSE_ACCESS_TOKEN="TU_TOKEN"')
        return

    print("Token detectado correctamente. No se imprimirá por seguridad.")
    print(f"API base: {API_BASE}")

    endpoints = [
        ("Stores / sucursales", "/stores", ["stores"]),
        ("POS devices", "/pos_devices", ["pos_devices"]),
        ("Employees / empleados", "/employees", ["employees"]),
        ("Items / productos", "/items?limit=20", ["items"]),
    ]

    for title, path, keys in endpoints:
        data = request_json(path)
        print_items(title, data, keys)

    print("\nIDs que después vas a poner en Railway:")
    print("LOYVERSE_STORE_ID=")
    print("LOYVERSE_POS_DEVICE_ID=")
    print("LOYVERSE_EMPLOYEE_ID=")

if __name__ == "__main__":
    main()
