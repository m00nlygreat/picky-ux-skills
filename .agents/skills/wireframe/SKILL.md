---
name: wireframe
description: Generate ./wireframe.html directly from STN Markdown files in ./design. Use when Codex needs to turn STN screen/component trees into a GUI-like wireframe prototype without using a generator script; use $stn as the canonical STN syntax reference while parsing.
---

# Wireframe Skill

Generate `./wireframe.html` directly from STN design files in `./design/`.

## Core Contract

This skill is for rapid GUI prototyping from STN. The output must look like a real application wireframe, not a visualization of the STN tree.

- Render the screen structure as recognizable product UI: app bars, navigation, panes, toolbars, tables, cards, lists, tabs, forms, actions, assistant panels, empty states, and content areas.
- Do not render STN as a nested outline, raw block tree, inline label dump, or generic placeholder stack.
- Treat STN as semantic intent. Parent/child/sibling relationships, quoted strings, bindings, variants, conditional markers, and responsive annotations together determine the interface.
- Parse STN syntax deterministically, then let the agent infer UI intent. Do not build exact-name mapping tables as the primary rendering strategy.
- The viewer template provides chrome, controls, and a baseline wireframe vocabulary. The generated wireframe output is **not limited** to the CSS already present in `viewer.html`.
- Generate additional document-specific CSS whenever it improves fidelity, as long as it keeps the output wireframe-like rather than high-fidelity visual design.

No standalone generator script owns the semantic rendering. The agent reads the design files, builds a syntax tree, infers UI intent, copies the canonical viewer shell, injects generated CSS and document payloads, and writes `wireframe.html`.

## STN Reference

Use `$stn` as the canonical syntax reference before interpreting STN. `$wireframe` should be forgiving enough to render imperfect files when possible, but it must understand these STN conventions:

- STN is a Markdown nested-list notation; indentation defines parent, child, and sibling relationships.
- Screen roots start with `- Screen: {Name}` and component roots start with `- Component: {Name}`.
- `./design/GLOBAL.md` is inserted by the reserved `<GLOBAL />` node, not through frontmatter imports.
- `<ComponentName "instruction" />` references reusable components listed in YAML frontmatter `imports`.
- `?Element` marks optional or conditional UI.
- `@mobile(...)`, `@desktop(...)`, and similar annotations describe responsive differences.
- Quoted strings, `{dataBinding}`, `[variant-or-icon]`, and `(state-or-layout)` are semantic hints for visual rendering.

Do not treat STN as a raw outline. Preserve the source text in the viewer, but render the semantic UI structure.

## Rendering Philosophy

### Syntax Parser vs Semantic Interpreter

Use two distinct mental passes:

1. **Syntax parse:** Recover the tree and metadata from Markdown indentation, imports, component references, quoted text, bindings, variants, hints, optional markers, and responsive annotations. This pass can be deterministic.
2. **UI intent interpretation:** Infer what kind of product surface the tree describes. This pass is agentic. It must use context and structure, not exact string equality.

Do not add brittle rules such as "if node text equals `DataTable`, output this exact HTML" as the main design. Instead infer archetypes from multiple signals:

- Container role from position: app shell child, header child, collection child, panel child, form child.
- Sibling pattern: title + search + filters + rows implies collection management; tabs + body implies tabbed panel; avatar + status + sections implies detail profile.
- Binding names and instruction strings: `{instructors}`, `{selectedInstructor}`, `{alerts}`, `{pagination}` inform sample data and content density.
- Variants and icons: `[primary]`, `[table]`, `[calendar]`, `[filter]`, `[bell]` affect control appearance.
- Responsive annotations: `@mobile(hidden)` and `@mobile(-> ...)` affect mobile preview.

### UI Intent Graph

Before writing HTML, form a compact UI intent graph for each document. It should include:

- `surface`: screen, app shell, collection surface, detail panel, assistant panel, card list, form, dashboard, timeline, settings, etc.
- `layout`: column, split pane, three-pane shell, table-centric workspace, mobile single-column replacement, etc.
- `regions`: navigation, top bar, collection toolbar, content body, detail drawer, right assistant panel, footer.
- `interactions`: tabs, segment controls, filters, sort, search, selection, pagination, row actions, collapse controls.
- `sampleData`: realistic domain examples derived from screen/component names, quoted strings, and bindings.
- `confidenceNotes`: any uncertainty to report in the final answer.

Keep this graph implicit or in `wf-data`; do not create separate temp files.

### Rich Fallback

If a node cannot be classified precisely, still render a useful UI approximation. A rich fallback should include a label, content density, one or more representative rows/cards/actions, and a clear visual role. Avoid empty rectangles unless the source explicitly asks for a placeholder/skeleton/loading state.

Visible bindings such as `{row.primary}` should not dominate the preview. Prefer realistic sample values in the preview and preserve original bindings in `title`, `data-binding`, subtle captions, source panel text, or `wf-data`.

## Files

- `./design/GLOBAL.md`: optional shared layout STN.
- `./design/*.md`: screen STN files.
- `./design/components/*.md`: reusable component STN files.
- `.agents/skills/wireframe/template/viewer.html`: canonical viewer shell, CSS, and JavaScript. Copy it before modifying `wireframe.html`.
- `./wireframe.html`: final self-contained HTML output written directly by the agent.
- `./CURRENT.md`: current implementation notes and decisions.

If `./design` does not exist, tell the user STN design files are missing and suggest creating them with `$design`.

## Workflow

### 1. Read Design Files

Read all available STN Markdown files:

- `./design/GLOBAL.md`
- `./design/*.md`
- `./design/components/*.md`

Ignore non-STN artifacts in `design/`, such as exported HTML files.

### 2. Parse STN By Inspection

For each file, identify the STN list under `## Element Tree`, `## STN`, `## Screen Tree`, or the first Markdown list that represents the screen tree.

Track for each node:

- raw node text
- depth
- parent
- siblings
- children
- source file path

Also resolve STN-specific structure:

- Parse YAML frontmatter imports for component references.
- Detect `<GLOBAL />` and map it to `./design/GLOBAL.md`.
- Keep component references as component nodes while rendering the referenced component payload where useful.
- Preserve optional markers and responsive annotations as metadata; render the default desktop structure unless generating mobile-specific preview behavior.
- Treat malformed but recognizable STN as renderable, and report uncertain classifications instead of failing silently.

### 3. Infer UI Intent

Infer UI intent from the parsed tree. Use the render type vocabulary as a shared language, not as a closed set of templates.

Required interpretation work:

- Identify the primary surface archetype for each document.
- Identify main regions and their relative layout.
- Decide which children are structural containers and which are visible controls/content.
- Resolve component references into meaningful previews where useful.
- Synthesize realistic sample labels and row/card content from bindings and domain text.
- Preserve binding provenance without making raw `{...}` tokens the main visible content.
- Prefer high-fidelity wireframe primitives over `generic` and `generic-leaf`.

Avoid brittle exact-name rendering. Names can inform the decision, but parent context, children, siblings, variants, and bindings must carry at least as much weight as the raw node text.

### 4. Create Or Update Viewer Shell, Then Inject CSS And Payloads

Write a complete self-contained HTML document to `./wireframe.html`.

Do not visually inspect `viewer.html` and recreate it from memory. On the first generation, copy `.agents/skills/wireframe/template/viewer.html` to `./wireframe.html`, then edit the copied file in place. On later STN-only updates, keep the existing `wireframe.html` shell and replace only the generated slots unless the viewer template itself changed or the existing shell fails verification.

On Windows, do not generate or replace long HTML/CSS/JSON payloads with inline PowerShell commands. PowerShell is unreliable for long strings, quotes, and escaping in this workflow. Use a Node.js script as the default path for reading the template, replacing slots, serializing JSON payloads, and writing `wireframe.html`.

Mandatory shell-preservation rules:

- Preserve the copied viewer chrome, canvas, source panel, controls, and JavaScript unless the user explicitly asks to change the viewer itself.
- Treat `.wf-*` styles as a fallback starting point, not a constraint on generated output.
- Generate additional CSS classes for the actual wireframe when the STN calls for richer layout or domain-specific controls.
- Preserve zoom, fit, width slider, mouse wheel zoom, and space/middle-button pan behavior exactly as provided by `template/viewer.html`.
- Replace only these template slots during normal generation and STN-only incremental updates:
  - `<meta name="wf-generated" content="">` with the current timestamp.
  - `<style id="wf-generated-style"></style>` with generated wireframe CSS when needed.
  - `<script id="wf-docs-tpl" type="application/json">[]</script>` with the generated documents payload.
  - `<script id="wf-data" type="application/json">[]</script>` with render type metadata when useful.
- If viewer shell changes are required, edit `template/viewer.html` first, then copy the updated shell to `wireframe.html` and inject the payloads.
- Do not hand-rewrite the whole HTML document, simplify the viewer JavaScript, or omit controls that exist in the template.

The document must include:

- `<meta name="wf-generated" content="...">` with the current timestamp.
- A sidebar navigation for Global, Screens, and Components.
- A main preview canvas with desktop/mobile/fit controls.
- A source panel showing the STN source for the selected document.
- Inline viewer CSS, generated wireframe CSS, and JavaScript.
- A JSON payload such as `<script id="wf-docs-tpl" type="application/json">...</script>` containing each document's rendered HTML and source.
- Optional `<script id="wf-data" type="application/json">...</script>` with render type maps for future incremental updates.

Do not create temporary classification files. Keep the render type decisions in the HTML payload.

### 5. Verify

Run static verification first. Do not automatically open a browser after generation because `file://`, `localhost`, or `127.0.0.1` access can be blocked by app or browser policy. Browser-based visual verification is optional and should be left to the user's choice unless they explicitly request it.

Static verification should check:

- `wireframe.html` exists and is non-empty.
- The copied viewer shell still contains the expected chrome, canvas, source panel, controls, and JavaScript anchors.
- Template slots were replaced with valid content:
  - `<meta name="wf-generated" content="...">`
  - `<style id="wf-generated-style">...</style>`
  - `<script id="wf-docs-tpl" type="application/json">...</script>`
  - `<script id="wf-data" type="application/json">...</script>`
- JSON payloads parse successfully.
- The generated document payload includes at least one renderable document when screen/component sources exist.
- Raw bindings such as `{row.primary}` are not the dominant preview content when realistic sample data can be inferred.

If the user asks for browser verification, open `wireframe.html` in the browser. If direct `file://` access is blocked, serve the workspace with a local static server and open the localhost URL.

Browser verification should check:

- The page loads without console errors.
- The first screen is visible.
- At least one screen/component navigation click works.
- Desktop, Mobile, Fit, width slider, wheel zoom, and space/middle-button pan controls still work.
- GUI structures such as app shell, panes, toolbars, tables, cards, or tabs render as visual interface elements.
- Rich structures are visually recognizable without reading the STN source panel.
- Raw bindings such as `{row.primary}` are not the dominant preview content when realistic sample data can be inferred.

### 6. Report

Report:

- Output path.
- Number of global/screen/component documents processed.
- Verification result.
- Any uncertain classification decisions.

## Incremental Update

When `wireframe.html` already exists:

1. Inspect `<meta name="wf-generated">` and the existing `wf-data` payload if present.
2. Identify changed design files using `git diff --name-only -- design/` and `git status --short -- design/` when available. If that is not enough, compare file mtimes against the generated timestamp.
3. If no design files changed and the viewer structure does not need changes, report `wireframe is up to date`.
4. If only STN/design content changed, read the changed files plus any directly referenced components or `GLOBAL.md`, then update only the generated slots in the existing `wireframe.html`.
5. Preserve unchanged document payload entries from the existing `wf-docs-tpl` where their source files did not change and their referenced components did not change.
6. Preserve previous UI intent decisions from `wf-data` when they still match the STN context.
7. Recopy `template/viewer.html` only when `wireframe.html` is missing, the existing shell fails verification, `template/viewer.html` changed, or the user explicitly asks to refresh the viewer shell.
8. When recopying the shell, inject the current generated CSS, document payload, and `wf-data` slots after the copy so existing documents are not lost.

## Render Type Vocabulary

Use this vocabulary for intent metadata and fallback rendering. It is not a restriction on generated CSS class names or richer composed UI.

### Layout

| type | renders as | examples |
|------|------------|----------|
| `screen` | full screen wrapper | Screen, Page, View |
| `component` | reusable component preview wrapper | Component |
| `shell` | application shell with horizontal panes | AppShell, Shell, Layout |
| `workspace` | primary work area inside a shell | MainWorkspace, Workspace |
| `pane` | bounded content/detail panel | ListPane, DetailPane, RightPanel |
| `body` | main scrollable content area | Body, Main, Content, ScrollView |
| `section` | labeled content group | Section, Group, Panel, Block |
| `toolbar` | horizontal command/header bar | ContentToolbar, PageHeader, FilterBar |
| `actionbar` | grouped action buttons | HeaderActions, DetailActions |
| `generic` | unknown container with children | fallback only |

### Chrome

| type | renders as | examples |
|------|------------|----------|
| `header` | top app bar | Header, AppBar, TopBar, NavigationBar |
| `navbar` | navigation menu/link row | NavBar, NavigationMenu, MenuBar |
| `tabs` | segmented tabs/control | Tabs, ViewTabs, DetailTabs, SegmentControl |
| `bottomnav` | bottom tab bar | BottomNav, TabBar, BottomBar |
| `footer` | bottom footer/status bar | Footer, RosterFooter |
| `sidebar` | side navigation panel | Sidebar, Drawer, LeftSidebar |

### Collections

| type | renders as | examples |
|------|------------|----------|
| `card` | card component | Card, Tile, Item |
| `list` | vertical list | List, Feed, Timeline, FileList |
| `grid` | grid/gallery | Grid, Gallery, CardGrid |
| `carousel` | horizontal scroll row | Carousel, HorizontalScroll |
| `table` | data table frame | DataTable, Table |
| `table-row` | table header or row | TableHeader, TableRow |

### Media

| type | renders as | examples |
|------|------------|----------|
| `image` | image placeholder | Image, Photo, Thumbnail, Banner |
| `avatar` | circular avatar | Avatar, ProfilePicture |
| `icon` | small icon placeholder | Icon, IconButton |
| `badge` | status/count pill | StatusBadge, NotificationBadge |

### Text

| type | renders as | examples |
|------|------------|----------|
| `title` | title text | Title, Heading, H1, ScreenTitle |
| `text` | body text | Text, Paragraph, Description |
| `caption` | secondary text | Caption, Subtitle, Hint, Meta |
| `logo` | brand/logo badge | Logo, Brand, AppName |

### Actions

| type | renders as | examples |
|------|------------|----------|
| `button` | command button | Button, CTA, Submit, PrimaryAction |
| `fab` | floating action button | FAB, FloatingButton |
| `navitem` | tab/navigation item | NavItem, Tab, ViewTab, SegmentItem |
| `link` | inline text link | Link, TextLink |

### Inputs

| type | renders as | examples |
|------|------------|----------|
| `input` | text field | Input, TextField, Field |
| `select` | dropdown | Select, Dropdown, Picker |
| `toggle` | switch | Toggle, Switch |
| `checkbox` | checkbox | Checkbox |
| `radio` | radio button | Radio, RadioButton |
| `search` | search bar | Search, SearchBar, SearchInput |
| `slider` | range slider | Slider, RangeSlider |

### Fallback

| type | renders as |
|------|------------|
| `generic` | unknown container, used only when a GUI role cannot be inferred |
| `generic-leaf` | unknown leaf placeholder, used only when a GUI role cannot be inferred |
