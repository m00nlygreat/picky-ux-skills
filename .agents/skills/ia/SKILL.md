---
name: ia
description: Generate an Information Architecture (IA) document from a service plan, PRD, or product idea. Outputs a structured screen hierarchy as Markdown nested lists and saves to SCREENS.md.
---

# Information Architecture Generator

Generate a complete Information Architecture (IA) for a product based on a service plan, PRD, or startup idea.

## When to Use This Skill

Use this skill when the user provides:
- A service planning document
- A PRD (Product Requirements Document)
- A startup or product idea description

Trigger phrases: "IA 작성", "정보구조도 만들어줘", "화면 위계 정리해줘", "create IA", "generate IA", "make information architecture"

---

## Knowledge Base: Navigation Flow Design Principles

An app or service is fundamentally **the automation of user data manipulation**.
The goal of screen design: *translate the user's mental model and task flow into DB operations (CRUD)*.

> **Scope**: This skill generates **frontend routes** (browser URLs). API endpoint design is a separate concern.

### Step 1: Define Entities

Identify the core concepts (entities) the service handles, then map each user action to a CRUD operation.

| User Action | DB Operation | Example (E-commerce) |
|-------------|-------------|----------------------|
| Create | Create | Sign up, add product, place order |
| View | Read | View profile, search/view product, order history |
| Edit | Update | Change password, update price, change order status |
| Remove | Delete | Delete account, remove product |

### Step 2: Design Screen Hierarchy

**Naming Rules:**
1. **Plural nouns for collections** — `/posts`, `/users`, `/fields` (not `/post`, `/field`)
2. **Entity-based naming** — use data model names (`/tasks`), not UI labels (`/warehouse`, `/feed`)
3. **Minimize action segments** — when a separate page is unavoidable, use a fixed set: `create`, `edit`, `settings`

**1-Depth: Top-Level — Entity Collections**
- URL pattern: `/{entities}` (e.g. `/posts`, `/users`, `/tasks`)
- Non-resource pages: `/{static-page}` (e.g. `/about`, `/pricing`)

**2-Depth: Record Detail & Entry Points**
- Rule: A single page handles only one entity unless absolutely necessary
- `/{entities}/:id` — Dynamic route, specific resource detail (e.g. `/posts/123`)
- `/{entities}/create` — Creation form (prefer modal when the form is simple)

**3-Depth: Sub-pages of a Parent Record**
- `/{entities}/:id/{sub-entities}` — Parent owns child records (e.g. `/farms/5/members`)
- `/{entities}/:id/settings` — Configuration page for the parent
- `/{entities}/:id/edit` — Edit form that needs its own page
- **Modal**: simple action; preserve current page context
- **Inline**: page handles view + edit together (e.g. settings with save button)
- **Separate page**: multi-step form or independent flow
- Modals and inline editing reduce the need for action routes

**Query Parameters: Reflect Page State in URL**
- URL pattern: `...?key=value`
- Filtering (`?category=tops`), sorting (`?sort=price`), pagination (`?page=2`), search (`?q=keyword`)
- Status view (`?status=backlog`), UI mode (`?mode=edit`)
- Use query params for view state instead of separate routes (e.g. `?status=backlog` not `/warehouse`)

### Step 3: Design Page Structure

**Global Layout** (areas shared across most pages):
- Header: brand, logged-in user info, notifications
- Sidebar: navigation aid / feature drawer (desktop & dashboards)
- Footer: legal info, copyright, support, sitemap
- Global Navigation: branches top-level paths; mobile → bottom tab bar or drawer

**Content Area Types:**
- Collection: a set of records for one entity — list, table, menu (e.g. `/posts`)
- Single Item: one element from a collection — detail view (e.g. `/posts/123`)
- Sub-page: child records, settings, or edit form of a parent (e.g. `/posts/123/settings`)

---

## How to Generate the IA

### Step 1: Analyze the Input

Read the provided service plan, PRD, or product idea. Extract:
1. **Core entities** (what data does this service manage?)
2. **User roles** (who uses this service? any admin/user separation?)
3. **Key features** per entity (what CRUD operations are needed?)
4. **Navigation structure** (what are the top-level sections?)

### Step 2: Map Entities to CRUD

For each entity, list the screens required:
- Collection screen (list of all records)
- Single Item screen (detail of one record)
- Action screens (create, edit, delete flows)

### Step 3: Build the Nested List

Output the IA as a Markdown nested list following this structure:

```
- /{entities}
  - Collection Screen (`/{entities}`)
    - Query params: `?status=`, `?sort=`, `?q=`
  - Single Item Screen (`/{entities}/:id`)
    - Sub-page (`/{entities}/:id/settings`) (modal, inline, or page)
    - Sub-page (`/{entities}/:id/edit`) (modal or page)
    - Child records (`/{entities}/:id/{sub-entities}`)
  - Create Screen (`/{entities}/create`) (modal or page)
- /{static-page}
```

**Rules:**
- 1-depth items = top-level navigation sections (plural entity names or standalone pages)
- 2-depth items = main screens within each section
- 3-depth items = sub-pages, child records, or action forms of a parent
- Resource paths use **plural nouns** and **entity-based naming**
- Allowed action segments: `create`, `edit`, `settings` — prefer modals/inline to reduce these
- Mark presentation format: append `(modal)`, `(inline)`, or `(page)` where relevant
- Mark dynamic routes: use `/:id` for record-specific screens
- Use query parameters for view state (filtering, status) instead of separate routes
- Include Global Layout section at the top (Header, GNB, Footer)
- Include Auth flow if the service requires login

### Step 4: Add Screen Metadata

After the nested list, include a table summarizing each screen:

| Screen | Type | URL Pattern | Description |
|--------|------|-------------|-------------|
| ... | Collection / Single Item / Action / Auth | `/...` | ... |

---

## Output Format

Always output:

1. **Service Summary** — 1–2 sentences summarizing the product
2. **Entities & CRUD Map** — bullet list of entities with their operations
3. **Information Architecture** — full nested list
4. **Screen Summary Table** — metadata table

---

## Save Instructions

When the task is complete, save the output to `SCREENS.md` in the current working directory unless the user specifies a different filename or location.

Use this format for the saved file:

```markdown
# [Service Name] — Information Architecture

> Generated: [date]

## Entities & CRUD Map
...

## Screen Hierarchy
...

## Screen Summary
...
```
