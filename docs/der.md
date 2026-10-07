# Diagrama entidad-relación

> **Archivo generado: no editar a mano.** Sale de los modelos de SQLAlchemy
> (`backend/app/models/`). Al cambiar un modelo se regenera con:
>
> ```bash
> cd backend && uv run python -m scripts.generate_erd
> ```
>
> El CI falla si este archivo no coincide con los modelos.

Es el estado **actual** del esquema: 17 tablas. Lo que todavía se está
diseñando no aparece acá sino en la ADR que lo propone. El porqué de cada tabla está en
las ADR que cita cada área, y las convenciones en
[modelo-datos-sprint-1.md](modelo-datos-sprint-1.md).

## Cómo leerlo

- `PK`, `FK`, `UK`: clave primaria, clave foránea, columna única por sí sola.
- `"NULL"`: la columna admite nulos. Sin esa marca es `NOT NULL`.
- `numeric "14,2"`: precisión y escala (Mermaid no admite la coma dentro del tipo).
- Cada línea es una clave foránea, etiquetada con las columnas que la forman en la
  tabla hija. Una clave foránea compuesta es una sola línea.
- `||--o{` uno a muchos · `|o--o{` la clave foránea admite nulos · `||--o|` uno a uno.
- Las tablas de reglas listan lo que el esquema garantiza y el dibujo no muestra:
  `CHECK`, unicidad compuesta o parcial, claves foráneas compuestas y `ON DELETE`.

## Modelo completo

```mermaid
erDiagram
    account {
        bigint id PK
        varchar(120) name
        varchar(255) email UK
        varchar(255) password_hash
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    budget_version {
        bigint id PK
        bigint project_id FK
        bigint firm_id FK
        integer version_number
        varchar(150) note "NULL"
        numeric total "14,2"
        varchar(3) currency
        timestamptz prices_as_of
        bigint created_by FK
        timestamptz created_at
    }
    budget_version_item {
        bigint id PK
        bigint budget_version_id FK
        bigint resource_id
        varchar(150) resource_name
        varchar(20) resource_type
        varchar(10) unit_abbreviation
        numeric quantity "14,3"
        numeric unit_price "14,2"
        varchar(3) currency
        numeric subtotal "14,2"
    }
    budget_version_line {
        bigint id PK
        bigint budget_version_id FK
        bigint recipe_id FK
        numeric quantity "14,3"
        varchar(150) note "NULL"
    }
    firm {
        bigint id PK
        varchar(120) name
        varchar(255) contact_email
        varchar(30) phone "NULL"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    firm_member {
        bigint firm_id PK, FK
        bigint account_id PK, FK
        bigint role_id FK
        varchar(20) role_scope FK
        boolean is_active
        timestamptz joined_at
    }
    permission {
        bigint id PK
        varchar(60) code
        varchar(20) scope
        text description "NULL"
    }
    platform_member {
        bigint account_id PK, FK
        bigint role_id PK, FK
        varchar(20) role_scope FK
        timestamptz assigned_at
    }
    project {
        bigint id PK
        bigint firm_id FK
        varchar(150) name
        text description "NULL"
        varchar(255) address "NULL"
        date estimated_start_date "NULL"
        bigint created_by FK
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    project_member {
        bigint project_id PK, FK
        bigint account_id PK, FK
        bigint firm_id FK
        bigint role_id FK
        varchar(20) role_scope FK
        varchar(40) role_code FK
        timestamptz joined_at
    }
    project_recipe {
        bigint id PK
        bigint project_id FK
        bigint firm_id FK
        bigint recipe_id FK
        numeric quantity "14,3"
        varchar(150) note "NULL"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    recipe {
        bigint id PK
        bigint firm_id FK "NULL"
        varchar(150) name
        text description "NULL"
        bigint unit_of_measure_id FK
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    recipe_resource {
        bigint recipe_id PK, FK
        bigint resource_id PK, FK
        numeric quantity_per_unit "12,4"
    }
    resource {
        bigint id PK
        varchar(20) type
        varchar(150) name
        bigint unit_of_measure_id FK
        numeric reference_price "14,2"
        varchar(3) currency
        timestamptz price_updated_at
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    role {
        bigint id PK
        varchar(40) code
        varchar(20) scope
        varchar(60) name
        text description "NULL"
        boolean is_system
    }
    role_permission {
        bigint role_id PK, FK
        bigint permission_id PK, FK
        varchar(20) scope FK
    }
    unit_of_measure {
        bigint id PK
        varchar(20) code UK
        varchar(60) name
        varchar(10) abbreviation
        varchar(30) magnitude
        boolean is_active
    }

    account ||--o{ budget_version : "created_by"
    project ||--o{ budget_version : "project_id, firm_id"
    budget_version ||--o{ budget_version_item : "budget_version_id"
    budget_version ||--o{ budget_version_line : "budget_version_id"
    recipe ||--o{ budget_version_line : "recipe_id"
    account ||--o{ firm_member : "account_id"
    firm ||--o{ firm_member : "firm_id"
    role ||--o{ firm_member : "role_id, role_scope"
    account ||--o{ platform_member : "account_id"
    role ||--o{ platform_member : "role_id, role_scope"
    account ||--o{ project : "created_by"
    firm ||--o{ project : "firm_id"
    firm_member ||--o{ project_member : "firm_id, account_id"
    project ||--o{ project_member : "project_id, firm_id"
    role ||--o{ project_member : "role_id, role_scope, role_code"
    project ||--o{ project_recipe : "project_id, firm_id"
    recipe ||--o{ project_recipe : "recipe_id"
    firm |o--o{ recipe : "firm_id"
    unit_of_measure ||--o{ recipe : "unit_of_measure_id"
    recipe ||--o{ recipe_resource : "recipe_id"
    resource ||--o{ recipe_resource : "resource_id"
    unit_of_measure ||--o{ resource : "unit_of_measure_id"
    permission ||--o{ role_permission : "permission_id, scope"
    role ||--o{ role_permission : "role_id, scope"
```

## Identidad y autorización

Definida en: [ADR-002](adr/0002-authorization-model.md), [ADR-004](adr/0004-authentication.md).

```mermaid
erDiagram
    account {
        bigint id PK
        varchar(120) name
        varchar(255) email UK
        varchar(255) password_hash
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    firm {
        bigint id PK
        varchar(120) name
        varchar(255) contact_email
        varchar(30) phone "NULL"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    firm_member {
        bigint firm_id PK, FK
        bigint account_id PK, FK
        bigint role_id FK
        varchar(20) role_scope FK
        boolean is_active
        timestamptz joined_at
    }
    permission {
        bigint id PK
        varchar(60) code
        varchar(20) scope
        text description "NULL"
    }
    platform_member {
        bigint account_id PK, FK
        bigint role_id PK, FK
        varchar(20) role_scope FK
        timestamptz assigned_at
    }
    role {
        bigint id PK
        varchar(40) code
        varchar(20) scope
        varchar(60) name
        text description "NULL"
        boolean is_system
    }
    role_permission {
        bigint role_id PK, FK
        bigint permission_id PK, FK
        varchar(20) scope FK
    }

    account ||--o{ firm_member : "account_id"
    firm ||--o{ firm_member : "firm_id"
    role ||--o{ firm_member : "role_id, role_scope"
    account ||--o{ platform_member : "account_id"
    role ||--o{ platform_member : "role_id, role_scope"
    permission ||--o{ role_permission : "permission_id, scope"
    role ||--o{ role_permission : "role_id, scope"
```

| Tabla | Regla | Definición |
|---|---|---|
| `account` | CHECK | `email = lower(email)` |
| `account` | UNIQUE | `(email)` |
| `firm_member` | CHECK | `role_scope = 'firm'` |
| `firm_member` | FK compuesta | `(role_id, role_scope) → role (id, scope)` |
| `permission` | CHECK | `scope IN ('platform', 'firm', 'project')` |
| `permission` | UNIQUE | `(code, scope)` |
| `permission` | UNIQUE | `(id, scope)` |
| `platform_member` | CHECK | `role_scope = 'platform'` |
| `platform_member` | FK compuesta | `(role_id, role_scope) → role (id, scope)` |
| `role` | CHECK | `scope IN ('platform', 'firm', 'project')` |
| `role` | UNIQUE | `(code, scope)` |
| `role` | UNIQUE | `(id, scope)` |
| `role` | UNIQUE | `(id, scope, code)` |
| `role_permission` | FK compuesta | `(permission_id, scope) → permission (id, scope)` |
| `role_permission` | FK compuesta | `(role_id, scope) → role (id, scope)` |
| `role_permission` | ON DELETE CASCADE | `(permission_id, scope) → permission (id, scope)` |
| `role_permission` | ON DELETE CASCADE | `(role_id, scope) → role (id, scope)` |

## Catálogo

Definida en: [ADR-003](adr/0003-recipe-catalog.md), [ADR-005](adr/0005-catalog-administration.md), [ADR-006](adr/0006-firm-recipes.md).

```mermaid
erDiagram
    recipe {
        bigint id PK
        bigint firm_id FK "NULL"
        varchar(150) name
        text description "NULL"
        bigint unit_of_measure_id FK
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    recipe_resource {
        bigint recipe_id PK, FK
        bigint resource_id PK, FK
        numeric quantity_per_unit "12,4"
    }
    resource {
        bigint id PK
        varchar(20) type
        varchar(150) name
        bigint unit_of_measure_id FK
        numeric reference_price "14,2"
        varchar(3) currency
        timestamptz price_updated_at
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    unit_of_measure {
        bigint id PK
        varchar(20) code UK
        varchar(60) name
        varchar(10) abbreviation
        varchar(30) magnitude
        boolean is_active
    }

    firm |o--o{ recipe : "firm_id"
    unit_of_measure ||--o{ recipe : "unit_of_measure_id"
    recipe ||--o{ recipe_resource : "recipe_id"
    resource ||--o{ recipe_resource : "resource_id"
    unit_of_measure ||--o{ resource : "unit_of_measure_id"
```

| Tabla | Regla | Definición |
|---|---|---|
| `recipe` | UNIQUE parcial | `(firm_id, lower(recipe.name)) WHERE is_active AND firm_id IS NOT NULL` |
| `recipe` | UNIQUE parcial | `(lower(recipe.name)) WHERE is_active AND firm_id IS NULL` |
| `recipe_resource` | CHECK | `quantity_per_unit > 0` |
| `recipe_resource` | ON DELETE CASCADE | `(recipe_id) → recipe (id)` |
| `recipe_resource` | ON DELETE CASCADE | `(resource_id) → resource (id)` |
| `resource` | CHECK | `currency ~ '^[A-Z]{3}$'` |
| `resource` | CHECK | `reference_price >= 0` |
| `resource` | CHECK | `type IN ('material', 'labor', 'equipment')` |
| `resource` | UNIQUE parcial | `(lower(resource.name)) WHERE is_active` |
| `unit_of_measure` | UNIQUE | `(code)` |

## Obra y cómputo

Definida en: [ADR-002](adr/0002-authorization-model.md) §3-§5, [ADR-003](adr/0003-recipe-catalog.md).

```mermaid
erDiagram
    project {
        bigint id PK
        bigint firm_id FK
        varchar(150) name
        text description "NULL"
        varchar(255) address "NULL"
        date estimated_start_date "NULL"
        bigint created_by FK
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    project_member {
        bigint project_id PK, FK
        bigint account_id PK, FK
        bigint firm_id FK
        bigint role_id FK
        varchar(20) role_scope FK
        varchar(40) role_code FK
        timestamptz joined_at
    }
    project_recipe {
        bigint id PK
        bigint project_id FK
        bigint firm_id FK
        bigint recipe_id FK
        numeric quantity "14,3"
        varchar(150) note "NULL"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    account ||--o{ project : "created_by"
    firm ||--o{ project : "firm_id"
    firm_member ||--o{ project_member : "firm_id, account_id"
    project ||--o{ project_member : "project_id, firm_id"
    role ||--o{ project_member : "role_id, role_scope, role_code"
    project ||--o{ project_recipe : "project_id, firm_id"
    recipe ||--o{ project_recipe : "recipe_id"
```

| Tabla | Regla | Definición |
|---|---|---|
| `project` | UNIQUE | `(id, firm_id)` |
| `project_member` | CHECK | `role_scope = 'project'` |
| `project_member` | FK compuesta | `(firm_id, account_id) → firm_member (firm_id, account_id)` |
| `project_member` | FK compuesta | `(project_id, firm_id) → project (id, firm_id)` |
| `project_member` | FK compuesta | `(role_id, role_scope, role_code) → role (id, scope, code)` |
| `project_member` | UNIQUE parcial | `(project_id) WHERE role_code = 'client'` |
| `project_member` | UNIQUE parcial | `(project_id) WHERE role_code = 'lead'` |
| `project_recipe` | CHECK | `quantity > 0` |
| `project_recipe` | FK compuesta | `(project_id, firm_id) → project (id, firm_id)` |

## Versiones del presupuesto

Definida en: [ADR-007](adr/0007-budget-versions.md).

```mermaid
erDiagram
    budget_version {
        bigint id PK
        bigint project_id FK
        bigint firm_id FK
        integer version_number
        varchar(150) note "NULL"
        numeric total "14,2"
        varchar(3) currency
        timestamptz prices_as_of
        bigint created_by FK
        timestamptz created_at
    }
    budget_version_item {
        bigint id PK
        bigint budget_version_id FK
        bigint resource_id
        varchar(150) resource_name
        varchar(20) resource_type
        varchar(10) unit_abbreviation
        numeric quantity "14,3"
        numeric unit_price "14,2"
        varchar(3) currency
        numeric subtotal "14,2"
    }
    budget_version_line {
        bigint id PK
        bigint budget_version_id FK
        bigint recipe_id FK
        numeric quantity "14,3"
        varchar(150) note "NULL"
    }

    account ||--o{ budget_version : "created_by"
    project ||--o{ budget_version : "project_id, firm_id"
    budget_version ||--o{ budget_version_item : "budget_version_id"
    budget_version ||--o{ budget_version_line : "budget_version_id"
    recipe ||--o{ budget_version_line : "recipe_id"
```

| Tabla | Regla | Definición |
|---|---|---|
| `budget_version` | CHECK | `currency ~ '^[A-Z]{3}$'` |
| `budget_version` | CHECK | `total >= 0` |
| `budget_version` | CHECK | `version_number > 0` |
| `budget_version` | FK compuesta | `(project_id, firm_id) → project (id, firm_id)` |
| `budget_version` | UNIQUE | `(project_id, version_number)` |
| `budget_version_item` | CHECK | `currency ~ '^[A-Z]{3}$'` |
| `budget_version_item` | CHECK | `quantity > 0` |
| `budget_version_item` | CHECK | `resource_type IN ('material', 'labor', 'equipment')` |
| `budget_version_item` | CHECK | `subtotal >= 0` |
| `budget_version_item` | CHECK | `unit_price >= 0` |
| `budget_version_item` | ON DELETE CASCADE | `(budget_version_id) → budget_version (id)` |
| `budget_version_line` | CHECK | `quantity > 0` |
| `budget_version_line` | ON DELETE CASCADE | `(budget_version_id) → budget_version (id)` |
