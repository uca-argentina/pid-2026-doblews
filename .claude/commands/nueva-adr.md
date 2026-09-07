---
description: Crear una nueva ADR a partir del template
---

Antes de escribir nada, leer todas las ADR existentes en `docs/adr/` para no duplicar ni contradecir una decisión ya aceptada.

Pasos:

1. Determinar el próximo número correlativo (`docs/adr/000N-*.md`).
2. Copiar la estructura de `docs/adr/template.md`.
3. Completar Contexto / Decisión / Consecuencias / Alternativas descartadas con la decisión sobre: $ARGUMENTS
4. Guardar como `docs/adr/000N-<slug-corto-en-ingles>.md`, estado inicial **Propuesta**.
5. Si esta decisión reemplaza o corrige una anterior, decirlo explícitamente en "Contexto" con un link a la ADR anterior. Las ADR se pueden editar: si el ajuste es chico, actualizá la que ya existe; si es un cambio de fondo, escribí una nueva y marcá la vieja como **Reemplazada por ADR-00N**.
