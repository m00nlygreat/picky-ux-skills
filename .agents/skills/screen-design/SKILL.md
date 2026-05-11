---
name: screen-design
description: Design a screen's element tree in Screen Tree Notation (STN) format. Uses ./design/GLOBAL.md and reusable STN components from ./design/components.
---

# Screen Design Generator

Design individual screen element trees using Screen Tree Notation (STN).

Default workspace:
- Screen files live in `./design`
- The shared global layout is `./design/GLOBAL.md`
- Reusable components live in `./design/components/{ItemName}.md`

## When to Use This Skill

Trigger phrases: "screen design", "design screen", "screen tree", "STN", "화면 설계", "화면 구조", "요소 트리"

## Reference

Read `screen_tree_notation.md` in this skill's directory for STN syntax, YAML frontmatter imports, components, responsive notation, validation rules, and good/bad examples. All output must conform to that specification.

## Flow

### Step 1: Gather Screen Requirements

Ask the user what screen they need. Accept any of:
- A screen name and brief description (e.g. "user profile page")
- A reference to an existing IA document or SCREENS.md entry
- A detailed feature list for the screen

Clarify if unclear:
- What is the primary purpose of this screen?
- What data does it display or collect?
- Are there any user actions on this screen?

### Step 2: Establish Global Layout

Check if `./design/GLOBAL.md` exists.

**If it exists:** Read it and use it as the shared layout wrapper. Inform the user which global layout is being applied.

**If it does not exist:** Ask the user about their preferences for shared layout elements:
- Header: brand logo, user menu, notifications, search?
- Navigation: sidebar, top nav, bottom tab bar?
- Footer: links, legal, support?
- Responsive behavior: how should navigation change on mobile?

Then generate `./design/GLOBAL.md` in STN format based on the user's answers and save it. Use `{content}` to mark where individual screen content is inserted.

### Step 3: Check Reusable Components

Check `./design/components` for existing component STN files that match the screen requirements.

Use existing components when their meaning and structure fit. Create a new component when:
- The same UI pattern appears more than once
- A subtree would exceed the recommended depth
- The component has a domain-specific name and can be reused by another screen

Save each new component as `./design/components/{ItemName}.md`. Each component file must contain one STN component tree starting with `- Component: {ItemName}`.

### Step 4: Generate Screen Element Tree

Build the screen's element tree in STN format:

1. Add YAML frontmatter at the top of the screen document. List every component used under `imports`, with paths relative to the screen file, e.g. `imports: ["./components/ProductCard.md"]`
2. Start the tree with `- Screen: {ScreenName}`
3. Embed the global layout structure, replacing `{content}` with the screen-specific elements
4. Reference imported components by their component name in the tree
5. Apply responsive annotations where desktop and mobile differ
6. Validate against STN rules:
   - Single root
   - No empty containers
   - Leaf nodes carry content
   - No duplicate siblings
   - Depth <= 5
   - Responsive replacements are single elements
   - `?` prefix only on optional elements
   - Frontmatter import paths are relative to the screen file
   - Component names match their filenames

Present the full STN output to the user.

### Step 5: Save

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

### Step 6: Suggest Wireframe Preview

After saving, always suggest the next step:

> "저장 완료. `/wireframe`을 실행하면 HTML 와이어프레임 뷰어로 바로 확인할 수 있습니다."

- 이미 `wireframe.html`이 존재하면 변경된 파일만 재생성(증분 빌드)하므로 빠르게 반영됩니다.
- 처음 실행이라면 모든 STN 파일을 변환하여 `wireframe.html`을 생성합니다.
