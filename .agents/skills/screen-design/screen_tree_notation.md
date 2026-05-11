# Screen Tree Notation (STN)

A notation for representing screen and component element trees using Markdown lists.

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

- `design/GLOBAL.md` defines the shared layout wrapper and uses `{content}` as the screen insertion point.
- `design/{ScreenName}.md` defines one screen.
- `design/components/{ItemName}.md` defines one reusable component.

## Frontmatter Imports

Screen files declare reusable components in YAML frontmatter. Import paths must be relative to the screen file.

```markdown
---
imports:
  - "./components/ProductCard.md"
  - "./components/FilterBar.md"
---
```

Imported components are referenced in the screen tree by component name:

```markdown
- Screen: Product List
  - Header
    - Title "Products"
  - Body
    - FilterBar "{filters}"
    - ProductGrid "{products}"
      - ProductCard "{product}"
```

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
| `PascalCase` | Component / element type | `Header`, `Button`, `TextInput` |
| `- Screen: Name` | Screen root | `- Screen: Dashboard` |
| `- Component: Name` | Component root | `- Component: ProductCard` |
| `imports` frontmatter | Component imports | `imports: ["./components/ProductCard.md"]` |
| `"..."` | Visible text or placeholder | `"Submit"`, `"Write a comment..."` |
| `{...}` | Dynamic data binding | `{author.name}`, `{post.body}` |
| `[...]` | Variant or icon | `[primary]`, `[bookmark]` |
| `(...)` | Supplementary info (layout, state) | `(scrollable)`, `(sticky)`, `(caption)` |
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
- Component props are represented through data bindings such as `{product}`, `{user}`, or `{order.items}`
- A component may include responsive annotations using the same rules as screens

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
    - DataTable "{projects}" @mobile(-> CardList)
  - BottomNav @desktop(hidden)
    - NavItem "Home"
    - NavItem "Projects"
    - NavItem "Settings"
```

### Responsive Rules

| Notation | Meaning | Example |
|----------|---------|---------|
| `@mobile(hidden)` | Hidden at this breakpoint | `Sidebar @mobile(hidden)` |
| `@mobile(-> Alt)` | Replaced with another element | `DataTable @mobile(-> CardList)` |
| `@mobile(change)` | Layout/property change | `StatsSection (row) @mobile(column)` |
| `@desktop(hidden)` | Hidden on desktop (mobile-only) | `BottomNav @desktop(hidden)` |
| No annotation | Same across all breakpoints | `StatCard "{revenue}"` |

- Extensible with `@tablet(...)` and other breakpoints using the same pattern
- Most cases are covered by just two modifiers: replace (`->`) and hide (`hidden`)

## Validation Rules

A well-formed STN must satisfy:

1. **Single root**: Every screen tree starts with exactly one `- Screen: {name}` node; every component tree starts with exactly one `- Component: {name}` node
2. **Valid imports**: Screen frontmatter imports must use paths relative to the screen file, and imported component names must match their filenames
3. **No empty containers**: Every node with children must have at least one meaningful child; avoid wrapper-only nodes
4. **Leaf nodes carry content**: Leaf elements must have either `"text"`, `{binding}`, or a self-evident type (e.g. `Avatar`, `Divider`)
5. **No duplicate siblings**: Sibling nodes at the same level must be distinguishable; two `Button "Save"` siblings are invalid unless differentiated with variant or context
6. **Depth <= 5**: If nesting exceeds 5 levels, flatten the tree or extract a named component
7. **Responsive consistency**: `@mobile(-> Alt)` replacement must be a single element, not a subtree. If the replacement needs children, extract it as a named component
8. **Conditional prefix only on optional elements**: `?` must not appear on structural nodes like `Header` or `Body`

## Examples: Good vs Bad

### Naming

```markdown
# Good: uses domain component name
- UserCard
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
  - PostCard
    - Text "{post.title}"
    - Text "{post.summary}" (caption)

# Bad: unnecessary nesting
- Body
  - Section
    - ContentArea
      - PostCard
        - TextGroup
          - Text "{post.title}"
          - Text "{post.summary}" (caption)
```

### Responsive

```markdown
# Good: difference expressed inline
- DataTable "{users}" @mobile(-> CardList)

# Bad: duplicated tree for each breakpoint
- @desktop DataTable "{users}"
- @mobile CardList "{users}"
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
      - ProductCard "{product}"

# Bad: component exists but is not imported
- Screen: Product List
  - Body
    - ProductGrid "{products}"
      - ProductCard "{product}"
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
