---
name: wireframe
description: Generate a single HTML wireframe viewer from ./design Markdown files written in STN (Screen Tree Notation). Use when Codex needs to read design/GLOBAL.md, design/*.md screens, and design/components/*.md components, then output and preview a quick prototype or predefined-style wireframe viewer.
---

# Wireframe Viewer

STN 디자인 파일을 읽고 HTML 와이어프레임 뷰어를 생성한다.  
Python 스크립트 없이 **에이전트가 직접** STN 노드를 HTML 요소로 변환한다.

## 입력 파일

- `./design/GLOBAL.md` — 전역 레이아웃 (선택)
- `./design/*.md` — 화면 STN 파일
- `./design/components/*.md` — 재사용 컴포넌트 STN 파일

`./design` 디렉토리가 없으면 사용자에게 알리고 `$screen-design`으로 먼저 STN을 작성하도록 안내한다.

---

## 워크플로우

### 0. 변경 감지 (증분 생성)

`./wireframe.html`이 존재하면 전체 재생성을 건너뛰고 **변경된 파일만** 처리한다.

1. `./wireframe.html`의 수정 시각(mtime)을 확인한다.
2. 각 STN 파일의 mtime과 비교한다.
3. **모든 STN 파일이 wireframe.html보다 오래됨** → `"wireframe.html is up to date"` 메시지 출력 후 종료.
4. **일부 STN 파일이 더 최신** → 해당 파일만 재변환. 나머지는 `./wireframe.docs.json` 캐시에서 재사용.

mtime 확인 방법 (PowerShell):
```powershell
(Get-Item "wireframe.html").LastWriteTime
(Get-Item "design/foo.md").LastWriteTime
```

또는 Python:
```python
import os
os.path.getmtime("wireframe.html")
os.path.getmtime("design/foo.md")
```

`./wireframe.docs.json`이 없으면 전체 재생성한다.

### 1. STN 파일 읽기

변경된 STN 파일만 읽는다 (단계 0에서 결정된 파일만).  
각 파일에서 `## Element Tree` 아래의 들여쓰기 목록(`- ...`)을 STN 트리로 파싱한다.

- `GLOBAL.md` → `kind: "global"`
- `design/*.md` → `kind: "screen"`
- `design/components/*.md` → `kind: "component"`

### 2. STN → HTML 변환 (에이전트가 직접 수행)

각 STN 트리를 읽고 노드 타입을 **의미적으로 판단**하여 HTML 와이어프레임 마크업을 생성한다.  
노드 이름은 camelCase 컴포넌트명이며, 다음 규칙을 따른다.

#### 레이블 추출
- `Button "저장"` → 레이블은 `저장`
- `Text "{user.name}"` → 레이블은 `{user.name}` (동적 바인딩, 그대로 표시)
- `Title: 강사풀` → 레이블은 `강사풀`
- `?Component` → optional (`.wf-optional` 클래스 추가, opacity 낮춤)

#### HTML 요소 매핑

| STN 노드 패턴 | HTML 출력 |
|---|---|
| `Screen:`, `Page:` | `<div class="wf-screen">…</div>` |
| `AppShell`, `Layout`, `Shell` 포함 | `<div class="wf-layout">…</div>` |
| `MainWorkspace`, `Workspace` | `<div class="wf-workspace">…</div>` |
| `LeftSidebar`, `LeftPanel`, `Drawer` | `<aside class="wf-sidebar wf-sidebar-left">…</aside>` |
| `RightPanel`, `AssistantPanel` | `<aside class="wf-sidebar wf-sidebar-right">…</aside>` |
| `TopAppBar`, `AppBar`, `TopBar` | `<header class="wf-topbar">…</header>` |
| `NavBar`, `NavigationBar` | `<nav class="wf-navbar">…</nav>` |
| `BottomBar`, `BottomNav` | `<footer class="wf-bottombar">…</footer>` |
| `Toolbar`, `ContentToolbar` | `<div class="wf-toolbar">…</div>` |
| `FilterBar`, `SearchBar` | `<div class="wf-filterbar">…</div>` |
| `NavigationMenu`, `NavMenu` | `<nav class="wf-navmenu">…</nav>` |
| `*Tabs`, `TabGroup`, `TabList` | `<div class="wf-tabgroup">…</div>` — 쉼표로 나뉜 레이블은 각각 `<button class="wf-tab">` |
| `Tab`, `NavItem` | `<button class="wf-tab">레이블</button>` |
| `PrimaryActionButton`, `PrimaryButton` | `<button class="wf-btn wf-btn-primary">레이블</button>` |
| `IconButton`, `PanelToggleButton` | `<button class="wf-btn-icon" title="아이콘명">□</button>` |
| `Button … [primary]` | `<button class="wf-btn wf-btn-primary">레이블</button>` |
| `Button … [secondary]` | `<button class="wf-btn wf-btn-secondary">레이블</button>` |
| `Button` (기타) | `<button class="wf-btn">레이블</button>` |
| `FilterButton`, `SortButton`, `ColumnMenuButton` | `<button class="wf-btn wf-btn-tool">레이블</button>` |
| `SearchInput` | `<div class="wf-input wf-input-search"><span class="wf-search-icon">⌕</span><span class="wf-placeholder">레이블</span></div>` |
| `*Input`, `*Field`, `*TextInput` | `<div class="wf-input"><span class="wf-placeholder">레이블</span></div>` |
| `*Select`, `*Dropdown` | `<div class="wf-select"><span>레이블</span><span class="wf-caret">▾</span></div>` |
| `Checkbox` | `<label class="wf-checkbox"><span class="wf-checkbox-box"></span><span>레이블</span></label>` |
| `Toggle`, `Switch` | `<label class="wf-toggle"><span class="wf-toggle-track"><span class="wf-toggle-thumb"></span></span><span>레이블</span></label>` |
| `Avatar` | `<div class="wf-avatar"></div>` |
| `Image`, `Photo`, `Thumbnail`, `BrandLogo` | `<div class="wf-image"><span>레이블</span></div>` |
| `Icon`, `*Icon` | `<span class="wf-icon" title="아이콘명">□</span>` |
| `DataTable`, `Table` | `<div class="wf-table">헤더행+데이터행</div>` |
| `TableHeader` | `<div class="wf-table-header-row">…</div>` |
| `*Row` | `<div class="wf-table-row">…</div>` |
| `*Cell`, `PersonCell` | `<div class="wf-table-cell">…</div>` |
| `*CardList`, `*ListView`, `*List`, `ActionList` | `<div class="wf-list">…</div>` |
| `*Item`, `ActionItem`, `NavItem` | `<div class="wf-list-item">…</div>` |
| `SummaryGrid`, `*Grid` | `<div class="wf-grid">…</div>` |
| `*Card`, `AiSummaryCard`, `InternalMemoCard` | `<div class="wf-card">…</div>` |
| `SummaryMetric`, `MetricCard` | `<div class="wf-metric"><div class="wf-metric-label">레이블</div>…</div>` |
| `StatusBadge`, `NotificationBadge`, `*Badge` | `<span class="wf-badge">레이블</span>` |
| `SkillTagList`, `*TagList` | `<div class="wf-tag-list">…</div>` |
| `SkillTag`, `*Tag` | `<span class="wf-tag">레이블</span>` |
| `PersonCell`, `ProfileCell` | `<div class="wf-person-cell"><div class="wf-avatar wf-avatar-sm"></div><span>레이블</span></div>` |
| `Pagination` | `<div class="wf-pagination"><button class="wf-btn wf-btn-sm">‹</button><button class="wf-btn wf-btn-sm wf-btn-active">1</button>…</div>` |
| `Timeline` | `<div class="wf-timeline">타임라인 항목들</div>` |
| `UserMenu`, `RowActionMenu`, `*Menu` | `<button class="wf-menu-trigger">레이블 ▾</button>` |
| `Title`, `*Title` | `<h2 class="wf-title">레이블</h2>` |
| `Text … (caption)` | `<p class="wf-caption">레이블</p>` |
| `Text`, `Label` | `<p class="wf-text">레이블</p>` |
| `Divider`, `Separator` | `<hr class="wf-divider">` |
| `StepView` | `<div class="wf-stepview"><div class="wf-stepview-label">레이블</div>…</div>` |
| `Modal`, `Dialog` | `<div class="wf-modal"><div class="wf-modal-header">레이블</div><div class="wf-modal-body">…</div></div>` |
| 인식 불가 (leaf) | `<div class="wf-generic">레이블</div>` |
| 인식 불가 (자식 있음) | `<div class="wf-section"><div class="wf-section-label">레이블</div>…</div>` |

#### 레이아웃 자동 배치
`AppShell`이 `LeftSidebar` + `MainWorkspace` + `RightPanel` 구조를 자식으로 가지면 `wf-layout`으로 감싸 flex row 배치가 자동 적용된다.

### 3. docs JSON 구성

아래 구조의 JSON 배열을 만든다:

```json
[
  {
    "kind": "screen",
    "name": "Instructor Management",
    "path": "design/instructor-management.md",
    "source": "- Screen: Instructor Management\n  - TopAppBar ...",
    "html": "<div class=\"wf-screen\">...</div>"
  }
]
```

`source` 필드: 원본 STN 텍스트 그대로 (뷰어 우측 패널에 표시)  
`html` 필드: 에이전트가 변환한 HTML

**증분 병합**: `./wireframe.docs.json`이 있으면 캐시를 읽어 변경되지 않은 doc은 그대로 가져오고, 새로 변환한 doc으로 해당 항목을 교체한다. 순서는 global → screen → component 유지.

### 4. 캐시 및 템플릿 저장

두 파일을 모두 저장한다:

1. `./wireframe.docs.json` — docs 배열 전체를 JSON으로 저장 (다음 실행 시 캐시로 사용)
2. `./wireframe.html` — `{skill_base}/template/viewer.html`의 `__DOCS_JSON__` 플레이스홀더를 docs JSON으로 교체한 결과

```
viewer.html 내: const docs = __DOCS_JSON__;
교체 후:        const docs = [{...}, {...}];
```

### 5. 출력

생성 또는 갱신된 파일과 재생성한 doc 목록을 보고한다.  
브라우저로 열어 미리보기. Browser Use가 불가하면 파일 경로를 안내한다.

---

## 생성 규칙

- STN 파일은 수정하지 않는다 (소스 보존).
- 모든 화면과 컴포넌트를 뷰어 하나에 포함한다.
- 인식 불가 노드는 드롭하지 않고 `.wf-generic` 또는 `.wf-section`으로 렌더링한다.
- `?` 접두사 노드는 `.wf-optional` 클래스 추가 (반투명 표시).
- `@desktop(hidden)`, `@mobile(hidden)` 어노테이션은 뷰어에서 표시하되 메모 텍스트로만 표기한다.
- 동적 바인딩 `{prop.name}`은 그레이 이탤릭 텍스트로 표시한다.
- 뷰어는 완전 self-contained (외부 리소스 없음).
