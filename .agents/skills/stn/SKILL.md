---
name: stn
description: Canonical reference for Screen Tree Notation (STN) syntax, validation, imports, components, GLOBAL layout, responsive annotations, and examples. Use when Codex needs to read, write, validate, refactor, render, or transform STN files in ./design, including work for $design and $wireframe.
---

# Screen Tree Notation (STN)

STN is a notation for representing screen, global layout, and component element trees using Markdown lists.

Use this skill as the canonical syntax reference. Other skills should make product or rendering decisions themselves, then use these rules to keep STN files valid and interoperable.

## File Layout

Use this default structure:

```text
design/
  GLOBAL.md
  ProductList.md
  components/
    ProductCard.md
    FilterBar.md
```

- `design/GLOBAL.md` optionally defines the shared layout wrapper and uses `{content}` as the screen insertion point.
- `design/{ScreenName}.md` defines one screen.
- `design/components/{ItemName}.md` defines one reusable component.

## Frontmatter Imports

Screen files declare reusable components in YAML frontmatter. Import paths must be relative to the screen file. `GLOBAL.md` is not imported through frontmatter; screens reference it with the reserved `<GLOBAL />` layout reference when needed.

```markdown
---
imports:
  - "./components/ProductCard.md"
  - "./components/FilterBar.md"
---
```

Imported components are referenced in the screen tree with self-closing JSX-like syntax:

```markdown
- Screen: Product List
  - Header
    - Title "Products"
  - Body
    - <FilterBar "{filters}" />
    - ProductGrid "{products}"
      - <ProductCard "{product}" />
```

## Global Layout Reference

`GLOBAL.md` is an optional shared layout. A screen that uses it references it with `<GLOBAL />` instead of copying the global layout tree into the screen file.

```markdown
---
imports:
  - "./components/ProductCard.md"
---

- Screen: Product List
  - <GLOBAL />
  - Content
    - PageHeader
      - Title "Products"
    - ProductGrid "{products}"
      - <ProductCard "{product}" />
```

Use `<GLOBAL />` for screens that belong inside the shared app shell. Omit it for screens that need an independent layout, such as onboarding, login, error, full-screen editors, or modal-like standalone flows.

Rules:
- `<GLOBAL />` is optional
- `<GLOBAL />` must be the first child of `Screen` when present
- `<GLOBAL />` is not listed in frontmatter imports
- `<GLOBAL />` takes no instruction string, props, or children
- `<GLOBAL />` resolves to `./design/GLOBAL.md`
- `GLOBAL.md` must include exactly one `{content}` slot
- When `<GLOBAL />` is present, screen-specific nodes should be placed under `Content`
- When `<GLOBAL />` is absent, the screen tree must define the full screen layout directly

## Basic Syntax

```markdown
- Screen: Post Detail
  - Header
    - BackButton
    - Title "Post Detail"
    - IconButton [bookmark]
  - Body (scrollable)
    - AuthorCard
      - Avatar
      - Text "{author.name}"
      - Text "{createdAt}" (caption)
    - Text "{post.body}"
    - ImageGrid "{post.images}"
  - BottomBar (sticky)
    - TextInput "Write a comment..." (placeholder)
    - Button "Submit" [primary]
```

### Notation Rules

| Notation | Meaning | Example |
|----------|---------|---------|
| `PascalCase` | Element type | `Header`, `Button`, `TextInput` |
| `- Screen: Name` | Screen root | `- Screen: Dashboard` |
| `- Component: Name` | Component root | `- Component: ProductCard` |
| `<GLOBAL />` | Optional shared layout reference | `<GLOBAL />` |
| `<ComponentName "..." />` | Component reference | `<ProductCard "{product}" />` |
| `imports` frontmatter | Component imports | `imports: ["./components/ProductCard.md"]` |
| `"..."` | Visible text or placeholder | `"Submit"`, `"Write a comment..."` |
| `{...}` | Dynamic data binding | `{author.name}`, `{post.body}` |
| `[...]` | Variant or icon | `[primary]`, `[bookmark]` |
| `(...)` | Supplementary info, layout, or state | `(scrollable)`, `(sticky)`, `(caption)` |
| `?` prefix | Conditional rendering | `?AuthBanner (if: !isLoggedIn)` |

## Components

Components are reusable STN subtrees stored as separate files under `design/components`.

```markdown
# design/components/ProductCard.md

- Component: ProductCard
  - Image "{product.image}"
  - Text "{product.name}"
  - Text "{product.price}" (caption)
  - Button "Add" [primary]
```

Use a component when:
- The same UI pattern appears more than once
- A subtree would make the screen exceed the recommended depth
- The unit has a clear domain-specific name
- The unit is likely to be reused by another screen

Do not extract a component only to rename structural nodes such as `Header`, `Body`, `Main`, or `Footer`.

### Component Rules

- A component file contains exactly one root: `- Component: {ItemName}`
- `{ItemName}` must be PascalCase and must match the filename: `ItemName.md`
- Component imports appear in screen file frontmatter, not inside component files by default
- Component references must use self-closing syntax: `<ComponentName "instruction" />`
- The instruction must be exactly one quoted string
- Use the instruction string to pass data context or rendering intent, such as `{product}`, `{user}`, or `Compact read-only summary for {order}`
- Key-value props, children, multiple instruction strings, and omitted instructions are not allowed
- A component may include responsive annotations using the same rules as screens
- `<GLOBAL />` is a reserved layout reference, not a component reference

## Responsive Notation

Desktop is the default. Use `@mobile(...)` to override only the differences.

```markdown
- Screen: Dashboard
  - Sidebar (fixed, w:240) @mobile(hidden)
  - Main
    - Header
      - Title "Dashboard"
      - SearchInput "Search" (placeholder) @mobile(-> IconButton [search])
    - StatsSection (row) @mobile(column)
      - StatCard "{activeUsers}"
      - StatCard "{revenue}"
      - StatCard "{conversionRate}"
    - DataTable "{projects}" @mobile(-> <ProjectCardList "{projects}" />)
  - BottomNav @desktop(hidden)
    - NavItem "Home"
    - NavItem "Projects"
    - NavItem "Settings"
```

### Responsive Rules

| Notation | Meaning | Example |
|----------|---------|---------|
| `@mobile(hidden)` | Hidden at this breakpoint | `Sidebar @mobile(hidden)` |
| `@mobile(-> Alt)` | Replaced with another element or component reference | `DataTable @mobile(-> <CardList "{items}" />)` |
| `@mobile(change)` | Layout/property change | `StatsSection (row) @mobile(column)` |
| `@desktop(hidden)` | Hidden on desktop, mobile-only | `BottomNav @desktop(hidden)` |
| No annotation | Same across all breakpoints | `StatCard "{revenue}"` |

- Extensible with `@tablet(...)` and other breakpoints using the same pattern
- Most cases are covered by two modifiers: replace (`->`) and hide (`hidden`)

## Markdown Bundle Compilation

STN compilation means bundling related Markdown sources into a single Markdown document for agent consumption. It does not inline, replace, render, or semantically reinterpret STN nodes.

Use compilation when a downstream skill or agent needs enough context to understand one screen or the whole app without repeatedly opening `GLOBAL.md` and component files.

Do not manually compile STN bundles by copying Markdown in the chat context. Use the compiler script whenever it is available:

```bash
python .agents/skills/stn/scripts/compile_stn.py --project-root . --screen ProductList
python .agents/skills/stn/scripts/compile_stn.py --project-root . --app
python .agents/skills/stn/scripts/compile_stn.py --project-root . --all
```

- `--screen {Name}` generates one screen bundle. Repeat it to generate multiple selected screens.
- `--app` generates all screen bundles and `.stn/compiled/app.md`.
- `--all` is the default when no target is provided; it generates all screen bundles and the app bundle.

### Output Layout

Use this default generated structure:

```text
.stn/
  compiled/
    manifest.json
    app.md
    screens/
      ProductList.md
```

- `.stn/compiled/screens/{ScreenName}.md` contains one screen plus the references it uses.
- `.stn/compiled/app.md` contains all screens plus shared references.
- `.stn/compiled/manifest.json` indexes generated files, sources, dependencies, and diagnostics.

Compiled files are generated artifacts. Do not treat them as the source of truth when editing STN.

### Screen Bundle

For `design/{ScreenName}.md`, create `.stn/compiled/screens/{ScreenName}.md`.

The generated document should use this shape:

```markdown
# Compiled Screen: ProductList

## Main

<!-- source: design/ProductList.md -->

{original screen markdown}

## References

### GLOBAL

<!-- source: design/GLOBAL.md -->

{original GLOBAL.md markdown}

### Component: ProductCard

<!-- source: design/components/ProductCard.md -->

{original component markdown}

## Diagnostics

{missing references or warnings, if any}
```

Rules:

- Keep the screen file content unchanged under `## Main`, including frontmatter, headings, comments, and STN body.
- If the screen contains `<GLOBAL />`, attach `design/GLOBAL.md` under `## References`.
- Attach only component files declared in the screen frontmatter `imports`.
- Do not replace `<GLOBAL />` with `GLOBAL.md` content.
- Do not replace `<ComponentName "instruction" />` with component content.
- Do not rewrite component roots, instruction strings, bindings, annotations, or indentation.
- Attach each referenced document at most once.
- If a reference is missing or unreadable, keep generating the bundle and record the issue under `## Diagnostics`.
- By default, do not recursively follow component references inside component files. A compiler may support an explicit deep mode, but shallow screen imports are the default.

### App Bundle

For app-level compilation, create `.stn/compiled/app.md`.

The generated document should use this shape:

```markdown
# Compiled STN App

## Screens

### Screen: ProductList

<!-- source: design/ProductList.md -->

{original screen markdown}

### Screen: Settings

<!-- source: design/Settings.md -->

{original screen markdown}

## References

### GLOBAL

<!-- source: design/GLOBAL.md -->

{original GLOBAL.md markdown}

### Component: ProductCard

<!-- source: design/components/ProductCard.md -->

{original component markdown}

## Diagnostics

{missing references or warnings, if any}
```

Rules:

- Treat `design/*.md` files as screens, excluding `GLOBAL.md`.
- Do not treat files under `design/components/` as screens.
- Include screens in filename-sorted order unless the caller provides an explicit order.
- Collect references from all included screens.
- Attach `GLOBAL.md` once if any included screen contains `<GLOBAL />`.
- Attach each imported component once, even when multiple screens import it.
- Preserve every source document exactly as Markdown text.
- Do not inline, expand, deduplicate, or normalize STN element trees.

### Manifest

Generate `manifest.json` with enough information for agents to open only the compiled document they need.

```json
{
  "generatedAt": "2026-05-13T00:00:00+09:00",
  "screens": [
    {
      "name": "ProductList",
      "source": "design/ProductList.md",
      "compiled": ".stn/compiled/screens/ProductList.md",
      "sources": [
        "design/ProductList.md",
        "design/GLOBAL.md",
        "design/components/ProductCard.md"
      ]
    }
  ],
  "app": {
    "compiled": ".stn/compiled/app.md",
    "screenCount": 1
  },
  "diagnostics": []
}
```

Manifest paths should be workspace-relative and use `/` separators.

## Validation Rules

A well-formed STN must satisfy:

1. **Single root**: Every screen tree starts with exactly one `- Screen: {name}` node; every component tree starts with exactly one `- Component: {name}` node
2. **Valid imports**: Screen frontmatter imports must use paths relative to the screen file, and imported component names must match their filenames
3. **Valid global reference**: `<GLOBAL />` is optional. If present, it must be the first child of `Screen`, must not appear in frontmatter imports, must take no instruction string, props, or children, and must resolve to `./design/GLOBAL.md` with exactly one `{content}` slot
4. **Valid component references**: Imported components must be referenced as `<ComponentName "instruction" />` with exactly one quoted instruction string, no key-value props, no children, and no omitted instruction. Every component reference must point to a component listed in frontmatter imports
5. **No empty containers**: Every node with children must have at least one meaningful child; avoid wrapper-only nodes
6. **Leaf nodes carry content**: Leaf elements must have either `"text"`, `{binding}`, or a self-evident type such as `Avatar` or `Divider`
7. **No duplicate siblings**: Sibling nodes at the same level must be distinguishable; two `Button "Save"` siblings are invalid unless differentiated with variant or context
8. **Depth <= 5**: If nesting exceeds 5 levels, flatten the tree or extract a named component
9. **Responsive consistency**: `@mobile(-> Alt)` replacement must be a single element or a single component reference, not a subtree. If the replacement needs children, extract it as a named component
10. **Conditional prefix only on optional elements**: `?` must not appear on structural nodes like `Header` or `Body`

## Examples: Good vs Bad

### Naming

```markdown
# Good: uses domain-specific element or component names
- UserSummary
  - Avatar
  - Text "{user.name}"

# Bad: generic div-like wrapper with no semantic meaning
- Container
  - Wrapper
    - Text "{user.name}"
```

### Depth

```markdown
# Good: flat where possible
- Body
  - PostSummary
    - Text "{post.title}"
    - Text "{post.summary}" (caption)

# Bad: unnecessary nesting
- Body
  - Section
    - ContentArea
      - PostSummary
        - TextGroup
          - Text "{post.title}"
          - Text "{post.summary}" (caption)
```

### Responsive

```markdown
# Good: difference expressed inline
- DataTable "{users}" @mobile(-> <UserCardList "{users}" />)

# Bad: duplicated tree for each breakpoint
- @desktop DataTable "{users}"
- @mobile CardList "{users}"
```

### Global Layout

```markdown
# Good: app-shell screen references GLOBAL and keeps local content separate
---
imports:
  - "./components/ProductCard.md"
---

- Screen: Product List
  - <GLOBAL />
  - Content
    - PageHeader
      - Title "Products"
    - ProductGrid "{products}"
      - <ProductCard "{product}" />

# Good: standalone screen omits GLOBAL and defines the full layout directly
- Screen: Login
  - Header
    - Title "Sign in"
  - Body
    - TextInput "Email" (placeholder)
    - TextInput "Password" (placeholder)
    - Button "Continue" [primary]
```

```markdown
# Bad: GLOBAL is not imported through frontmatter
---
imports:
  - "./GLOBAL.md"
---

# Bad: GLOBAL must be the first child of Screen when present
- Screen: Product List
  - Content
    - Title "Products"
  - <GLOBAL />

# Bad: GLOBAL takes no instruction string, props, or children
- Screen: Product List
  - <GLOBAL "{content}" />
```

### Components

```markdown
# Good: screen imports a reusable component through frontmatter
---
imports:
  - "./components/ProductCard.md"
---

- Screen: Product List
  - Body
    - ProductGrid "{products}"
      - <ProductCard "{product}" />

# Bad: component exists but is not imported and is not referenced with component syntax
- Screen: Product List
  - Body
    - ProductGrid "{products}"
      - ProductCard "{product}"
```

```markdown
# Bad: key-value props are not allowed
- <ProductCard product="{product}" />

# Bad: component references must include exactly one quoted instruction
- <ProductCard />
- <ProductCard "{product}" "compact" />

# Bad: children are not allowed in component references
- <ProductCard "{product}">
  - Button "Add"
```

### Leaf Content

```markdown
# Good: leaf has visible content
- Button "Cancel" [secondary]
- Text "{order.total}"

# Bad: leaf with no content or binding
- Button
- InfoDisplay
```
