---
name: wireframe
description: Generate ./wireframe.html directly from STN Markdown files in ./design. Use when Codex needs to turn STN screen/component trees into a GUI-like wireframe prototype without using a generator script.
---

# Wireframe Skill

Generate `./wireframe.html` directly from STN design files in `./design/`.

## Core Contract

This skill is for rapid GUI prototyping from STN. The output must look like an application wireframe:

- Render the screen structure as recognizable UI: app bars, sidebars, panes, toolbars, tables, cards, lists, tabs, forms, actions, and content areas.
- Do not render STN as a nested outline, raw block tree, or inline label dump.
- Use the STN tree as layout intent. Parent/child/sibling relationships determine screen composition.
- Prefer semantic GUI containers (`shell`, `workspace`, `pane`, `toolbar`, `table`, `tabs`) over `generic`.
- Use `generic` and `generic-leaf` only when no useful GUI role can be inferred.

No generator script is used. The agent reads the design files, classifies the STN nodes, copies the canonical viewer shell, injects generated payloads, and writes `wireframe.html` itself.

## Files

- `./design/GLOBAL.md`: optional shared layout STN.
- `./design/*.md`: screen STN files.
- `./design/components/*.md`: reusable component STN files.
- `.agents/skills/wireframe/template/viewer.html`: canonical viewer shell, CSS, and JavaScript. Copy it before modifying `wireframe.html`.
- `./wireframe.html`: final self-contained HTML output written directly by the agent.
- `./CURRENT.md`: current implementation notes and decisions.

If `./design` does not exist, tell the user STN design files are missing and suggest creating them with `$screen-design`.

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

### 3. Classify Nodes Into Render Types

Classify each node using the render type vocabulary below.

Apply these rules in order:

1. Node semantics: `AppShell` -> `shell`, `TopAppBar` -> `header`, `DataTable` -> `table`.
2. Parent context: children under `AppShell` are usually `sidebar`, `workspace`, or `pane`.
3. Sibling pattern: repeated row-like children under `DataTable` -> `table-row`; tabs under `ViewTabs` -> `navitem`.
4. Explicit label: `Button: Log Out` -> `button`; the label text does not change the type.
5. GUI fidelity: choose the type that creates the closest real UI layout, not the type that mirrors the STN outline.
6. Fallback: use `generic` or `generic-leaf` only when no meaningful GUI role is implied.

Constraints:

- Same node text in the same file should use the same type.
- Same node text may differ across files if context differs.
- Component roots may use `component` when previewed as reusable UI, or `screen` when the component needs a full-frame preview.

### 4. Copy Viewer Shell, Then Inject Payloads

Write a complete self-contained HTML document to `./wireframe.html`.

Do not visually inspect `viewer.html` and recreate it from memory. First copy `.agents/skills/wireframe/template/viewer.html` to `./wireframe.html`, then edit the copied file in place.

Mandatory shell-preservation rules:

- Preserve the copied viewer chrome, canvas, source panel, controls, JavaScript, and `.wf-*` component styles unless the user explicitly asks to change the viewer itself.
- Preserve zoom, fit, width slider, mouse wheel zoom, and space/middle-button pan behavior exactly as provided by `template/viewer.html`.
- Replace only these template slots during normal generation:
  - `<meta name="wf-generated" content="">` with the current timestamp.
  - `<script id="wf-docs-tpl" type="application/json">[]</script>` with the generated documents payload.
  - `<script id="wf-data" type="application/json">[]</script>` with render type metadata when useful.
- If viewer shell changes are required, edit `template/viewer.html` first, then copy the updated shell to `wireframe.html` and inject the payloads.
- Do not hand-rewrite the whole HTML document, simplify the viewer JavaScript, or omit controls that exist in the template.

The document must include:

- `<meta name="wf-generated" content="...">` with the current timestamp.
- A sidebar navigation for Global, Screens, and Components.
- A main preview canvas with desktop/mobile/fit controls.
- A source panel showing the STN source for the selected document.
- Inline CSS and JavaScript.
- A JSON payload such as `<script id="wf-docs-tpl" type="application/json">...</script>` containing each document's rendered HTML and source.
- Optional `<script id="wf-data" type="application/json">...</script>` with render type maps for future incremental updates.

Do not create temporary classification files. Keep the render type decisions in the HTML payload.

### 5. Verify

Open `wireframe.html` in the browser. If direct `file://` access is blocked, serve the workspace with a local static server and open the localhost URL.

Verify:

- The page loads without console errors.
- The first screen is visible.
- At least one screen/component navigation click works.
- Desktop, Mobile, Fit, width slider, wheel zoom, and space/middle-button pan controls still work.
- GUI structures such as app shell, panes, toolbars, tables, cards, or tabs render as visual interface elements.

### 6. Report

Report:

- Output path.
- Number of global/screen/component documents processed.
- Verification result.
- Any uncertain classification decisions.

## Incremental Update

When `wireframe.html` already exists:

1. Inspect `<meta name="wf-generated">` and the existing `wf-data` payload if present.
2. Use `git diff --name-only HEAD@{"<wf-generated timestamp>"} -- design/` when available to identify changed design files.
3. If no design files changed and the viewer structure does not need changes, report `wireframe is up to date`.
4. Otherwise, read the changed files, regenerate the documents payload, copy `template/viewer.html` to `wireframe.html`, and inject the updated payload slots.
5. Preserve previous render type decisions from `wf-data` when they still match the STN context.
6. Do not patch the existing `wireframe.html` shell as the primary update path; recopy the template so viewer controls stay in sync.

## Render Type Vocabulary

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
