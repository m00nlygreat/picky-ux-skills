---
name: design
description: Design product screens and shared layouts as STN files under ./design. Use when Codex needs to turn SCREENS.md entries, IA, PRDs, or screen requirements into UX element trees, decide layout/content/actions/responsive behavior, create or reuse components, and save screen design Markdown.
---

# Screen Design Skill

Design individual screen element trees using Screen Tree Notation (STN). This skill owns the UX structure decisions; `$stn` owns the notation rules.

Default workspace:
- Screen files live in `./design`
- The shared global layout is `./design/GLOBAL.md`
- Reusable components live in `./design/components/{ItemName}.md`

## Reference

Use `$stn` as the canonical syntax reference before writing or validating STN. Do not duplicate STN grammar in this skill; use this skill to decide what the screen should contain and how it should be structured.

## Flow

### Step 1: Gather Screen Requirements

Accept any of:
- A screen name and brief description, such as "user profile page"
- A reference to an existing IA document or `SCREENS.md` entry
- A detailed feature list for the screen

Clarify only when the missing information would change the screen structure:
- What is the primary purpose of this screen?
- What data does it display or collect?
- What user actions must be available?
- Are there role, state, or responsive differences that affect the layout?

### Step 2: Establish Global Layout

Check if `./design/GLOBAL.md` exists.

If it exists, read it and decide whether the current screen should use the shared layout. Use `<GLOBAL />` for screens that belong inside the shared app shell. Skip it for screens that need an independent layout, such as onboarding, login, error, full-screen editors, or modal-like standalone flows. Inform the user whether the global layout is being applied or intentionally skipped.

If it does not exist, create `GLOBAL.md` only when the screen requirements imply a reusable shared layout. If no shared layout is needed, proceed without `GLOBAL.md`. If a shared layout is needed, ask only for preferences that materially affect the reusable layout:
- Header: brand logo, user menu, notifications, search?
- Navigation: sidebar, top nav, bottom tab bar?
- Footer: links, legal, support?
- Responsive behavior: how should navigation change on mobile?

Generate `./design/GLOBAL.md` in STN format based on the user's answers and save it. Use `{content}` to mark where individual screen content is inserted. Screens that use the shared layout reference it with `<GLOBAL />`; they do not duplicate the `GLOBAL.md` tree.

### Step 3: Decide Screen Structure

Translate requirements into a screen hierarchy before writing STN:
- Identify the screen's primary job and dominant user workflow.
- Prioritize content from most decision-critical to least.
- Group related information into meaningful UI regions.
- Choose appropriate patterns: table, list, card grid, detail pane, form, editor, feed, wizard, or dashboard.
- Place actions near the content or state they affect.
- Include important states when structurally relevant: empty, loading, error, selected, permission-limited, or optional regions.
- Decide desktop and mobile structure differences explicitly.

### Step 4: Check Reusable Components

Check `./design/components` for existing component STN files that match the screen requirements.

Use existing components when their meaning and structure fit. Create a new component when:
- The same UI pattern appears more than once
- A subtree would exceed the recommended STN depth
- The component has a domain-specific name and can be reused by another screen

Save each new component as `./design/components/{ItemName}.md`. Each component file must contain one STN component tree starting with `- Component: {ItemName}`.

### Step 5: Generate Screen Element Tree

Build the screen's element tree in STN format:

1. Add YAML frontmatter at the top of the screen document. List every component used under `imports`, with paths relative to the screen file, e.g. `imports: ["./components/ProductCard.md"]`
2. Start the tree with `- Screen: {ScreenName}`
3. If the screen uses the shared layout, add `<GLOBAL />` as the first child of `Screen` and place screen-specific elements under `Content`. If not, define the complete screen tree directly
4. Reference imported components with the self-closing component reference syntax: `<ComponentName "instruction" />`
5. Apply responsive annotations where desktop and mobile differ
6. Validate against `$stn` rules before presenting the result

Present the full STN output to the user.

### Step 6: Save

After presenting the result, ask:

> "Save this as `{screen_name}.md`?"

If the user agrees, save to `./design/{screen_name}.md` with this format:

```markdown
# {Screen Name} Screen Design

> Generated: {date}

---
imports:
  - "./components/{ComponentName}.md"
---

## Element Tree

{STN output}
```

### Step 7: Suggest Wireframe Preview

After saving, always suggest the next step:

> 저장 완료. `$wireframe`을 실행하면 HTML 와이어프레임 뷰어에서 바로 확인할 수 있습니다.

- If `wireframe.html` already exists, `$wireframe` can update the changed STN files quickly.
- If this is the first run, `$wireframe` reads all STN files and creates `wireframe.html`.
