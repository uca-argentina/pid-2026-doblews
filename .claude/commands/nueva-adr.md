---
description: Crear una nueva ADR a partir del template
---

Antes de escribir nada, leer todas las ADR existentes en `docs/adr/` para no duplicar ni contradecir una decisión ya aceptada.

Pasos:

1. Determinar el próximo número correlativo (`docs/adr/000N-*.md`).
2. Copiar la estructura de `docs/adr/template.md`.
3. Completar Contexto / Decisión / Consecuencias / Alternativas descartadas con la decisión sobre: $ARGUMENTS
4. Guardar como `docs/adr/000N-<slug-corto-en-ingles>.md`, estado inicial **Propuesta**.
5. Nunca editar una ADR con estado **Aceptado**: si esta decisión reemplaza una anterior, decirlo explícitamente en "Contexto" (link a la ADR anterior) y, si corresponde, actualizar el estado de la ADR vieja a **Superada por ADR-00N** (eso sí se puede editar: es metadato de estado, no la decisión en sí).
