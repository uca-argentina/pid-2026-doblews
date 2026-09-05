# frontend/CLAUDE.md

React + TypeScript + Vite + Mantine (sin Next.js). Ver [../docs/adr/0001-stack.md](../docs/adr/0001-stack.md) para el porqué.

## Convenciones

- Formularios con `@mantine/form`; componentes de UI con Mantine (`DatePicker`, `Modal`, `Notifications`, `Table`) en vez de reimplementar.
- Cualquier campo "unidad" es un `<select>` alimentado por `GET /unidades-medida`, nunca texto libre.
- Mobile-first: verificar responsive a 375px en toda historia que toque UI (listados como tarjetas, no tablas horizontales, en mobile).
- `eslint` + `prettier` antes de cada commit.

## Comandos

```bash
npm run dev
npm run lint
npm run build
```
