# Promociones — Renzo Snacks

> **IMPORTANTE PARA EL BOT:** Si este archivo está vacío o sin promociones cargadas,
> NO inventar promociones. Responder: "Las promociones pueden cambiar por día.
> Te puedo confirmar con el equipo o tomar tu pedido con el menú actual."

---

## Actualización semanal

Las promociones de Renzo Snacks cambian por semana y pueden variar por día.
El equipo debe actualizar este archivo **cada domingo** con las promociones de la semana.

**Responsable:** Equipo Renzo Snacks / Administrador del bot.
**Frecuencia:** Cada domingo antes de abrir.

Este archivo es el **contenido versionado (Git)** que sirve de referencia/fallback. Existe
además una especificación (no implementada aún) para que administradores autorizados
actualicen promociones por comando de WhatsApp (`ACTUALIZAR PROMOS`, `VER PROMOS`,
`BORRAR PROMOS`); esas actualizaciones se guardarían en runtime/base de datos, **nunca en
Git**. Ver `README.md` → "Actualización de promociones por comandos de administrador (spec)".

---

## Comportamiento del bot cuando no hay promociones

Si la sección "Promociones de la semana" está vacía o indica "Sin promociones cargadas":

- **NO** inventar ni suponer promociones.
- Responder: *"Las promociones pueden cambiar por día. Te puedo confirmar con el equipo o tomar tu pedido con el menú actual."*
- Si el cliente insiste, ofrecer escalada a humano.

---

## Promociones de la semana

> Actualizar cada domingo. Si no hay promos esta semana, dejar vacío o escribir "Sin promociones esta semana."

Sin promociones cargadas esta semana.

---

## Historial de promociones

<!-- Registrar aquí promos pasadas para referencia interna -->
