# Loyverse — Renzo Snacks

## ¿Qué es Loyverse?

Loyverse es el sistema POS (punto de venta) que usa Renzo Snacks para registrar sus pedidos
y ventas. La integración permite que los pedidos tomados por WhatsApp lleguen directamente
al sistema del restaurante.

---

## Estado actual

**Integración: INACTIVA** — Las credenciales aún no están configuradas.

**Confirmado por el cliente:**
- Todos los productos están cargados en Loyverse con sus precios.
- Los pedidos deben aparecer en Loyverse cuando la integración esté activa.
- Se desea imprimir ticket doble si es posible (cocina + venta/caja).
- Alternativa: usar iPad como pantalla de cocina (Loyverse KDS) e imprimir un solo ticket.
- La impresora del restaurante es Bluetooth.

Cuando la integración esté activa:
- Los pedidos confirmados por WhatsApp se crean como receipts en Loyverse.
- El equipo los ve en el POS y los prepara.
- El bot informa al cliente que el pedido fue registrado.

Cuando la integración NO está activa (`LOYVERSE_ENABLED=false`):
- El bot toma el pedido y lo muestra como resumen.
- El pedido queda como "pendiente de confirmación humana".
- El bot informa al cliente que el equipo confirmará.
- El pedido NO se pierde: queda en el historial de conversación y en los logs.

---

## Variables de entorno requeridas

```
LOYVERSE_ENABLED=false          # Cambiar a true cuando esté listo
LOYVERSE_ACCESS_TOKEN=          # Token de acceso de Loyverse API
LOYVERSE_STORE_ID=              # ID de la tienda en Loyverse
LOYVERSE_POS_DEVICE_ID=         # ID del dispositivo POS (opcional)
LOYVERSE_EMPLOYEE_ID=           # ID del empleado asignado (opcional)
LOYVERSE_API_BASE_URL=https://api.loyverse.com/v1.0
```

---

## Cómo obtener las credenciales

1. Accede a tu cuenta de Loyverse en https://loyverse.com
2. Ve a Configuración → Integraciones → API
3. Crea un token de acceso con permisos de lectura y escritura de recibos
4. Copia el Store ID desde el dashboard de la tienda
5. El POS Device ID y Employee ID son opcionales; permiten asignar el pedido a un dispositivo específico

---

## Qué puede hacer la integración

- `loyverse_is_enabled()` — verifica si la integración está activa
- `loyverse_get_items()` — obtiene los productos del catálogo de Loyverse
- `loyverse_find_item_by_name(nombre)` — busca un producto por nombre aproximado
- `loyverse_format_order_payload(pedido)` — construye el payload para la API
- `loyverse_create_receipt(pedido)` — crea el recibo en Loyverse
- `loyverse_send_order(pedido)` — punto de entrada principal; maneja errores y logs

---

## Sobre impresión de tickets

- La API de Loyverse permite crear receipts (recibos), pero la impresión automática
  depende del dispositivo POS físico y su configuración.
- Si el POS está conectado a una impresora en el restaurante y el dispositivo está activo,
  el ticket puede imprimirse al crear el receipt.
- Si el dispositivo POS no está activo o no tiene impresora configurada, el receipt
  aparece en el sistema pero no se imprime automáticamente.
- Para confirmar la impresión automática, probar con el LOYVERSE_POS_DEVICE_ID configurado.

**Impresora Bluetooth:** Renzo Snacks usa impresora Bluetooth. La compatibilidad depende
del POS físico y la configuración del dispositivo. No prometer impresión automática hasta
probarlo con la cuenta real, POS real e impresora Bluetooth conectada.

### Opción A — Doble impresión (cocina + venta)

- Configurar dos impresoras en Loyverse POS: una para cocina y otra para caja/venta.
- Al crear el receipt, Loyverse puede disparar ambas impresoras si están configuradas.
- Esto se configura desde Loyverse POS → Ajustes → Impresoras, no desde el bot.
- No implementado desde el bot; el bot solo crea el receipt.

### Opción B — iPad como pantalla de cocina (Loyverse KDS)

- Usar un iPad o tablet en cocina mostrando Loyverse KDS (Kitchen Display System).
- Los pedidos llegan como tickets en pantalla; el equipo de cocina los ve sin imprimir.
- Solo se imprime un ticket si así lo prefieren (para el cliente o caja).
- El iPad y el POS deben estar en la misma red Wi-Fi.
- Se configura desde Loyverse POS; el bot no interactúa con KDS directamente.

---

## Mapeo de productos

Cuando se recibe un pedido, el sistema intenta buscar cada producto en el catálogo de Loyverse.

- Si encuentra una coincidencia exacta o cercana, usa el ID del producto.
- Si NO encuentra el producto, lo marca como "pendiente de revisión".
- Si hay productos sin mapear, el pedido se marca para revisión humana.
- El bot NO inventa precios ni IDs de Loyverse.

---

## Comportamiento cuando Loyverse falla

1. El pedido no se pierde: se guarda en los logs del servidor.
2. El bot informa al cliente que el pedido está pendiente de confirmación.
3. El equipo puede ver el pedido en los logs y procesarlo manualmente.
4. NO se dice al cliente que el pedido "ya quedó en el sistema" si Loyverse no respondió.
