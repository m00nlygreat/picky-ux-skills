#!/usr/bin/env python3
"""Generate a single-file HTML wireframe viewer from STN Markdown files."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


@dataclass
class Node:
    text: str
    children: list["Node"] = field(default_factory=list)


@dataclass
class Doc:
    kind: str
    name: str
    path: Path
    source: str
    tree: list[Node]


def strip_frontmatter(markdown: str) -> str:
    return FRONTMATTER_RE.sub("", markdown, count=1)


def extract_stn(markdown: str) -> str:
    body = strip_frontmatter(markdown).replace("\t", "  ")
    lines = body.splitlines()

    element_tree_index = None
    for index, line in enumerate(lines):
        if line.strip().lower() in {"## element tree", "## stn", "## screen tree"}:
            element_tree_index = index + 1
            break
    if element_tree_index is not None:
        lines = lines[element_tree_index:]

    stn_lines: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            if re.match(r"^\s*-\s+", line):
                stn_lines.append(line.rstrip())
            continue
        if re.match(r"^\s*-\s+", line):
            stn_lines.append(line.rstrip())
        elif stn_lines and stripped == "":
            stn_lines.append("")
        elif stn_lines and stripped.startswith("#"):
            break

    while stn_lines and stn_lines[-1] == "":
        stn_lines.pop()
    return "\n".join(stn_lines)


def parse_stn(stn: str) -> list[Node]:
    roots: list[Node] = []
    stack: list[tuple[int, Node]] = []

    for line in stn.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^(\s*)-\s+(.*)$", line)
        if not match:
            continue
        indent = len(match.group(1))
        node = Node(match.group(2).strip())
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((indent, node))
    return roots


def infer_name(path: Path, tree: list[Node]) -> str:
    if tree:
        root = tree[0].text
        root = re.sub(r"^(Screen|Component)\s*:\s*", "", root).strip()
        root = re.sub(r"\s*\(.*?\)", "", root).strip()
        if root:
            return root
    return path.stem


def collect_docs(design_dir: Path) -> list[Doc]:
    docs: list[Doc] = []
    if not design_dir.exists():
        raise FileNotFoundError(f"Design directory not found: {design_dir}")

    files: list[Path] = []
    global_file = design_dir / "GLOBAL.md"
    if global_file.exists():
        files.append(global_file)
    files.extend(sorted(p for p in design_dir.glob("*.md") if p.name != "GLOBAL.md"))
    components_dir = design_dir / "components"
    if components_dir.exists():
        files.extend(sorted(components_dir.glob("*.md")))

    for path in files:
        try:
            markdown = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown = path.read_text(encoding="utf-8-sig")
        stn = extract_stn(markdown)
        tree = parse_stn(stn)
        if not stn and path.name != "GLOBAL.md":
            continue
        if path.name == "GLOBAL.md":
            kind = "global"
        elif path.parent.name == "components":
            kind = "component"
        else:
            kind = "screen"
        docs.append(Doc(kind=kind, name=infer_name(path, tree), path=path, source=stn, tree=tree))
    return docs


# ---------------------------------------------------------------------------
# STN → HTML rendering
# ---------------------------------------------------------------------------

def get_base(text: str) -> str:
    """First camelCase token, stripped of ? prefix and annotations."""
    t = re.sub(r"^[?]", "", text).strip()
    t = t.split("(")[0].split("[")[0].split('"')[0].split("{")[0].strip()
    parts = t.split()
    return parts[0] if parts else t


def extract_label(text: str) -> str:
    """Extract display string: quoted literal > colon notation > base name."""
    m = re.search(r'"([^"]+)"', text)
    if m:
        return m.group(1)
    m = re.match(r'^[?]?\w[\w]*\s*[：:]\s*(.+)$', text)
    if m:
        val = m.group(1).strip().split("(")[0].strip()
        if val and not val.startswith("{"):
            return val
    base = get_base(text)
    # Un-camelCase for display: TopAppBar → Top App Bar
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', base)


def classify(base: str) -> str:
    b = base.lower()

    # ── Layout shells ──────────────────────────────────────────────────────
    if b in {"screen", "page"}:
        return "screen"
    if any(x in b for x in ["appshell", "shell", "layout", "mobileflow"]):
        return "layout"
    if any(x in b for x in ["leftsidebar", "leftpanel", "leftpane", "drawer"]):
        return "sidebar-left"
    if any(x in b for x in ["rightpanel", "rightpane", "assistantpanel", "sidepanel"]):
        return "sidebar-right"
    if any(x in b for x in ["mainworkspace", "workspace", "contentarea", "mainpane"]):
        return "workspace"
    if any(x in b for x in ["stepview"]):
        return "stepview"

    # ── Navigation bars ────────────────────────────────────────────────────
    if any(x in b for x in ["topappbar", "appbar", "topbar"]):
        return "topbar"
    if any(x in b for x in ["navbar", "navigationbar"]):
        return "navbar"
    if any(x in b for x in ["bottombar", "bottomnav", "bottomnavigation"]):
        return "bottombar"
    if any(x in b for x in ["toolbar", "contenttoolbar", "rostertoolbar", "pageheader"]):
        return "toolbar"
    if any(x in b for x in ["filterbar", "searchbar"]):
        return "filterbar"
    if any(x in b for x in ["navigationmenu", "navmenu"]):
        return "navmenu"
    if any(x in b for x in ["headeractions"]):
        return "header-actions"

    # ── Tabs ───────────────────────────────────────────────────────────────
    if any(x in b for x in ["detailtabs", "paneltabs", "viewtabs", "tabgroup", "tablist", "assistanttabs"]):
        return "tabgroup"
    if b.endswith("tab") or b == "tab":
        return "tab"
    if any(x in b for x in ["tabbar"]):
        return "tabbar"

    # ── Buttons ────────────────────────────────────────────────────────────
    if any(x in b for x in ["primaryactionbutton", "primarybutton"]):
        return "btn-primary"
    if any(x in b for x in ["iconbutton"]):
        return "btn-icon"
    if any(x in b for x in ["paneltogglebutton", "togglebutton"]):
        return "btn-icon"
    if any(x in b for x in ["filterbutton", "sortbutton", "columnmenubutton"]):
        return "btn-tool"
    if b.endswith("button") or b in {"button", "btn"}:
        variant = ""
        return "btn-secondary" if "[secondary]" in b else "btn"
    if any(x in b for x in ["rowactionmenu", "usermenu", "dropdownmenu", "actionmenu"]):
        return "menu-trigger"

    # ── Inputs ─────────────────────────────────────────────────────────────
    if any(x in b for x in ["searchinput"]):
        return "input-search"
    if b.endswith("input") or b in {"input", "textinput", "textfield", "field"}:
        return "input"
    if b.endswith("select") or b in {"select", "dropdown", "combobox"}:
        return "select"
    if "checkbox" in b:
        return "checkbox"
    if "toggle" in b or "switch" in b:
        return "toggle"
    if "radio" in b:
        return "radio"

    # ── Media ──────────────────────────────────────────────────────────────
    if b == "avatar" or b.endswith("avatar"):
        return "avatar"
    if any(x in b for x in ["image", "img", "photo", "thumbnail", "cover", "brandlogo"]):
        return "image"
    if "icon" in b:
        return "icon"

    # ── Data display ───────────────────────────────────────────────────────
    if any(x in b for x in ["datatable", "table"]):
        return "table"
    if any(x in b for x in ["tableheader"]):
        return "table-header"
    if b.endswith("row") or b == "row":
        return "table-row"
    if b.endswith("cell") or b == "cell":
        return "table-cell"
    if any(x in b for x in ["cardlist", "rosterlist", "listpane", "listview", "actionlist", "filelist", "memolist"]):
        return "list"
    if b.endswith("list") or b == "list":
        return "list"
    if b.endswith("grid") or b == "grid" or any(x in b for x in ["summarygrid"]):
        return "grid"
    if b.endswith("card") or b == "card":
        return "card"
    if any(x in b for x in ["summarymetric", "metriccard", "statcard"]):
        return "metric"
    if b.endswith("item") or b == "item" or any(x in b for x in ["actionitem", "navitem"]):
        return "list-item"
    if b.endswith("badge") or b in {"badge", "chip", "tag", "statustag"}:
        return "badge"
    if any(x in b for x in ["statusbadge", "notificationbadge"]):
        return "badge"
    if any(x in b for x in ["skilltag", "skilltaglist"]):
        return "tag-list"
    if any(x in b for x in ["personcell", "profilecell"]):
        return "person-cell"
    if any(x in b for x in ["pagination", "paginator"]):
        return "pagination"
    if any(x in b for x in ["timeline"]):
        return "timeline"

    # ── Typography ─────────────────────────────────────────────────────────
    if b == "title" or b.endswith("title"):
        return "title"
    if b in {"text", "paragraph", "body"} or b.endswith("text"):
        return "text"
    if b in {"label"}:
        return "label"
    if b in {"caption", "subtitle", "description", "helptext"}:
        return "caption"

    # ── Misc ───────────────────────────────────────────────────────────────
    if any(x in b for x in ["divider", "separator"]):
        return "divider"
    if any(x in b for x in ["modal", "dialog", "popup", "overlay"]):
        return "modal"
    if any(x in b for x in ["rosterfoot", "detailaction", "detailheader", "detailsummary"]):
        return "section-footer" if "foot" in b or "action" in b else "section-header"

    return "generic"


def is_optional(text: str) -> bool:
    return text.strip().startswith("?")


def is_mobile_hidden(text: str) -> bool:
    return "@desktop(hidden)" in text


def render_children(nodes: list[Node], depth: int) -> str:
    return "".join(render_node(n, depth) for n in nodes)


def btn_variant(text: str) -> str:
    tl = text.lower()
    if "[primary]" in tl or "primary" in get_base(text).lower():
        return "wf-btn wf-btn-primary"
    if "[secondary]" in tl:
        return "wf-btn wf-btn-secondary"
    if "[download]" in tl or "[export]" in tl:
        return "wf-btn wf-btn-secondary"
    return "wf-btn"


def render_node(node: Node, depth: int = 0) -> str:  # noqa: C901
    text = node.text
    base = get_base(text)
    etype = classify(base)
    lbl = html.escape(extract_label(text))
    ch = render_children(node.children, depth + 1)
    opt = ' wf-optional' if is_optional(text) else ''

    # ── Screen / layout shells ────────────────────────────────────────────
    if etype == "screen":
        return f'<div class="wf-screen{opt}">{ch}</div>'

    if etype == "layout":
        return f'<div class="wf-layout{opt}">{ch}</div>'

    if etype == "workspace":
        return f'<div class="wf-workspace{opt}">{ch}</div>'

    if etype == "sidebar-left":
        return f'<aside class="wf-sidebar wf-sidebar-left{opt}">{ch or f"<span class=\'wf-sidebar-label\'>{lbl}</span>"}</aside>'

    if etype == "sidebar-right":
        return f'<aside class="wf-sidebar wf-sidebar-right{opt}">{ch or f"<span class=\'wf-sidebar-label\'>{lbl}</span>"}</aside>'

    if etype == "stepview":
        return f'<div class="wf-stepview{opt}"><div class="wf-stepview-label">{lbl}</div>{ch}</div>'

    # ── Navigation bars ───────────────────────────────────────────────────
    if etype == "topbar":
        return f'<header class="wf-topbar{opt}">{ch or f"<span class=\'wf-topbar-brand\'>{lbl}</span>"}</header>'

    if etype == "navbar":
        return f'<nav class="wf-navbar{opt}">{ch or lbl}</nav>'

    if etype == "bottombar":
        return f'<footer class="wf-bottombar{opt}">{ch or lbl}</footer>'

    if etype == "toolbar":
        return f'<div class="wf-toolbar{opt}">{ch or f"<span class=\'wf-toolbar-title\'>{lbl}</span>"}</div>'

    if etype == "filterbar":
        return f'<div class="wf-filterbar{opt}">{ch or f"<div class=\'wf-input wf-input-search\'><span>필터 / 검색</span></div>"}</div>'

    if etype == "navmenu":
        items = ch or (
            '<div class="wf-navitem">메뉴 항목 1</div>'
            '<div class="wf-navitem">메뉴 항목 2</div>'
            '<div class="wf-navitem">메뉴 항목 3</div>'
        )
        return f'<nav class="wf-navmenu{opt}">{items}</nav>'

    if etype == "header-actions":
        return f'<div class="wf-header-actions{opt}">{ch or lbl}</div>'

    # ── Tabs ──────────────────────────────────────────────────────────────
    if etype == "tabgroup":
        if ch:
            return f'<div class="wf-tabgroup{opt}">{ch}</div>'
        # Render tab labels from quoted string
        tabs = [t.strip() for t in lbl.split(",")]
        tab_html = "".join(
            f'<button class="wf-tab{" wf-tab-active" if i == 0 else ""}">{html.escape(t)}</button>'
            for i, t in enumerate(tabs)
        )
        return f'<div class="wf-tabgroup{opt}">{tab_html}</div>'

    if etype in {"tab", "tabbar"}:
        return f'<button class="wf-tab{opt}" type="button">{lbl}</button>'

    # ── Buttons ───────────────────────────────────────────────────────────
    if etype == "btn-primary":
        return f'<button class="wf-btn wf-btn-primary{opt}" type="button">{lbl}</button>'

    if etype == "btn-icon":
        icon_m = re.search(r'\[([^\]]+)\]', text)
        icon = html.escape(icon_m.group(1)) if icon_m else "•"
        return f'<button class="wf-btn-icon{opt}" type="button" title="{icon}">□</button>'

    if etype == "btn-tool":
        icon_m = re.search(r'\[([^\]]+)\]', text)
        icon = html.escape(icon_m.group(1)) if icon_m else ""
        return f'<button class="wf-btn wf-btn-tool{opt}" type="button">{lbl}{(" [" + icon + "]") if icon else ""}</button>'

    if etype in {"btn", "btn-secondary"}:
        cls = btn_variant(text)
        return f'<button class="{cls}{opt}" type="button">{lbl}</button>'

    if etype == "menu-trigger":
        return f'<button class="wf-menu-trigger{opt}" type="button">{lbl} ▾</button>'

    # ── Inputs ────────────────────────────────────────────────────────────
    if etype == "input-search":
        return f'<div class="wf-input wf-input-search{opt}"><span class="wf-search-icon">⌕</span><span class="wf-placeholder">{lbl}</span></div>'

    if etype == "input":
        return f'<div class="wf-input{opt}"><span class="wf-placeholder">{lbl}</span></div>'

    if etype == "select":
        return f'<div class="wf-select{opt}"><span>{lbl or "선택..."}</span><span class="wf-caret">▾</span></div>'

    if etype == "checkbox":
        return f'<label class="wf-checkbox{opt}"><span class="wf-checkbox-box"></span><span>{lbl}</span></label>'

    if etype == "toggle":
        return f'<label class="wf-toggle{opt}"><span class="wf-toggle-track"><span class="wf-toggle-thumb"></span></span><span>{lbl}</span></label>'

    if etype == "radio":
        return f'<label class="wf-radio{opt}"><span class="wf-radio-dot"></span><span>{lbl}</span></label>'

    # ── Media ─────────────────────────────────────────────────────────────
    if etype == "avatar":
        return f'<div class="wf-avatar{opt}" title="{lbl}"></div>'

    if etype == "image":
        return f'<div class="wf-image{opt}"><span>{lbl}</span></div>'

    if etype == "icon":
        icon_m = re.search(r'\[([^\]]+)\]', text)
        icon = html.escape(icon_m.group(1)) if icon_m else lbl
        return f'<span class="wf-icon{opt}" title="{icon}">□</span>'

    # ── Data display ──────────────────────────────────────────────────────
    if etype == "table":
        inner = ch or (
            '<div class="wf-table-header-row">'
            '<div class="wf-table-cell">이름</div>'
            '<div class="wf-table-cell">스킬</div>'
            '<div class="wf-table-cell">상태</div>'
            '<div class="wf-table-cell">액션</div>'
            '</div>'
            '<div class="wf-table-row"><div class="wf-table-cell">───</div>'
            '<div class="wf-table-cell">───</div>'
            '<div class="wf-table-cell"><span class="wf-badge">활성</span></div>'
            '<div class="wf-table-cell">•••</div></div>'
        )
        return f'<div class="wf-table{opt}">{inner}</div>'

    if etype == "table-header":
        return f'<div class="wf-table-header-row{opt}">{ch or f"<div class=\'wf-table-cell\'>{lbl}</div>"}</div>'

    if etype == "table-row":
        return f'<div class="wf-table-row{opt}">{ch or f"<div class=\'wf-table-cell\'>{lbl}</div>"}</div>'

    if etype == "table-cell":
        return f'<div class="wf-table-cell{opt}">{ch or lbl}</div>'

    if etype == "list":
        items = ch or f'<div class="wf-list-item">{lbl}</div>'
        return f'<div class="wf-list{opt}">{items}</div>'

    if etype == "list-item":
        return f'<div class="wf-list-item{opt}">{ch or lbl}</div>'

    if etype == "grid":
        cells = ch or (
            '<div class="wf-grid-cell">항목</div>'
            '<div class="wf-grid-cell">항목</div>'
            '<div class="wf-grid-cell">항목</div>'
            '<div class="wf-grid-cell">항목</div>'
        )
        return f'<div class="wf-grid{opt}">{cells}</div>'

    if etype == "card":
        return f'<div class="wf-card{opt}">{ch or f"<p class=\'wf-placeholder\'>{lbl}</p>"}</div>'

    if etype == "metric":
        return (
            f'<div class="wf-metric{opt}">'
            f'<div class="wf-metric-label">{lbl}</div>'
            f'{ch or "<div class=\'wf-metric-value\'>—</div>"}'
            f'</div>'
        )

    if etype == "tag-list":
        return (
            f'<div class="wf-tag-list{opt}">'
            f'{ch or "<span class=\'wf-tag\'>스킬1</span><span class=\'wf-tag\'>스킬2</span>"}'
            f'</div>'
        )

    if etype == "person-cell":
        return (
            f'<div class="wf-person-cell{opt}">'
            f'<div class="wf-avatar wf-avatar-sm"></div>'
            f'<span>{lbl or "이름"}</span>'
            f'</div>'
        )

    if etype == "badge":
        return f'<span class="wf-badge{opt}">{lbl}</span>'

    if etype == "pagination":
        return (
            f'<div class="wf-pagination{opt}">'
            f'<button class="wf-btn wf-btn-sm">‹</button>'
            f'<button class="wf-btn wf-btn-sm wf-btn-active">1</button>'
            f'<button class="wf-btn wf-btn-sm">2</button>'
            f'<button class="wf-btn wf-btn-sm">3</button>'
            f'<button class="wf-btn wf-btn-sm">›</button>'
            f'</div>'
        )

    if etype == "timeline":
        return (
            f'<div class="wf-timeline{opt}">'
            f'<div class="wf-timeline-item"><span class="wf-timeline-dot"></span><span>이력 항목 1</span></div>'
            f'<div class="wf-timeline-item"><span class="wf-timeline-dot"></span><span>이력 항목 2</span></div>'
            f'</div>'
        )

    # ── Typography ────────────────────────────────────────────────────────
    if etype == "title":
        tag = "h2" if depth <= 2 else "h3"
        return f'<{tag} class="wf-title{opt}">{lbl}</{tag}>'

    if etype == "caption":
        return f'<p class="wf-caption{opt}">{lbl}</p>'

    if etype == "label":
        return f'<span class="wf-label-text{opt}">{lbl}</span>'

    if etype == "text":
        # caption modifier
        if "(caption)" in text.lower():
            return f'<p class="wf-caption{opt}">{lbl}</p>'
        return f'<p class="wf-text{opt}">{lbl}</p>'

    # ── Misc ──────────────────────────────────────────────────────────────
    if etype == "divider":
        return f'<hr class="wf-divider{opt}">'

    if etype == "modal":
        return (
            f'<div class="wf-modal{opt}">'
            f'<div class="wf-modal-header">{lbl}</div>'
            f'<div class="wf-modal-body">{ch}</div>'
            f'</div>'
        )

    if etype in {"section-header", "section-footer"}:
        return f'<div class="wf-section-bar{opt}">{ch or lbl}</div>'

    # ── Generic: container or leaf ────────────────────────────────────────
    if ch:
        return (
            f'<div class="wf-section{opt}" data-depth="{depth}">'
            f'<div class="wf-section-label">{lbl}</div>'
            f'{ch}'
            f'</div>'
        )
    return f'<div class="wf-generic{opt}">{lbl}</div>'


def doc_to_payload(doc: Doc, root: Path) -> dict:
    rendered = "".join(render_node(n) for n in doc.tree)
    return {
        "kind": doc.kind,
        "name": doc.name,
        "path": str(doc.path.relative_to(root) if doc.path.is_relative_to(root) else doc.path),
        "source": doc.source,
        "html": rendered or '<div class="wf-empty">STN 트리를 찾을 수 없습니다.</div>',
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

CSS = """
:root {
  --bg: #f0f2f5;
  --panel: #ffffff;
  --ink: #1b1f24;
  --muted: #68707c;
  --line: #d0d7e0;
  --accent: #2563eb;
  --accent-soft: #e8f0ff;
  --bar: #e8eaf0;
  --bar-border: #c8cdd8;
  --btn-bg: #f3f4f6;
  --btn-border: #b8c0cc;
  --input-bg: #ffffff;
  --badge-bg: #e0f2fe;
  --badge-ink: #0369a1;
  --metric-bg: #f8fafc;
  --sidebar-bg: #f3f4f6;
  --card-bg: #ffffff;
  --shadow: 0 1px 3px rgba(0,0,0,.10);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, "Pretendard", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
  font-size: 14px;
}
/* ── Viewer shell ─────────────────────────────────────────────────────── */
.app { display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; }
.sidebar {
  border-right: 1px solid var(--line);
  background: var(--panel);
  padding: 20px 14px;
  overflow-y: auto;
}
.brand { margin: 0 0 2px; font-size: 18px; font-weight: 700; }
.sub { margin: 0 0 16px; color: var(--muted); font-size: 12px; }
.group-title {
  margin: 16px 8px 6px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.nav-button {
  width: 100%; border: 0; border-radius: 7px; background: transparent;
  color: var(--ink); display: block; margin: 2px 0; padding: 8px 10px;
  text-align: left; cursor: pointer; font-size: 13px;
}
.nav-button:hover { background: #eef1f6; }
.nav-button.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.main { min-width: 0; padding: 20px; }
.toolbar-bar {
  display: flex; align-items: center; gap: 10px;
  justify-content: space-between; margin-bottom: 14px;
}
.title h2 { margin: 0; font-size: 20px; }
.title p { margin: 3px 0 0; color: var(--muted); font-size: 12px; }
.controls { display: flex; gap: 8px; }
.seg {
  border: 1px solid var(--line); border-radius: 7px; background: var(--panel);
  display: flex; padding: 3px;
}
.seg button {
  border: 0; border-radius: 5px; background: transparent;
  cursor: pointer; padding: 5px 10px; font-size: 12px;
}
.seg button.active { background: var(--ink); color: white; }
.workspace {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(260px, 400px);
  gap: 14px;
}
.preview, .source-panel {
  background: var(--panel); border: 1px solid var(--line);
  border-radius: 8px; min-width: 0;
}
.preview { padding: 16px; overflow: auto; }
.source-panel { overflow: hidden; }
.source-panel pre {
  margin: 0; max-height: calc(100vh - 140px); overflow: auto;
  padding: 14px; white-space: pre-wrap; font-size: 11.5px; line-height: 1.5;
  color: var(--muted);
}
.frame {
  background: #f7f8fa; border: 1px solid #ccd2dc; border-radius: 10px;
  margin: 0 auto; min-height: 560px; padding: 0; overflow: hidden;
  transition: width .15s ease;
}
.desktop .frame { width: min(100%, 960px); }
.mobile .frame { width: min(100%, 390px); }
.wf-empty { color: var(--muted); padding: 24px; text-align: center; }

/* ── Wireframe: layout shells ────────────────────────────────────────── */
.wf-screen { display: flex; flex-direction: column; height: 100%; min-height: 560px; }
.wf-layout { display: flex; flex: 1; overflow: hidden; }
.wf-workspace { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.wf-sidebar {
  background: var(--sidebar-bg); border: 1px solid var(--line);
  padding: 10px 8px; display: flex; flex-direction: column; gap: 6px;
  flex-shrink: 0; overflow-y: auto;
}
.wf-sidebar-left { width: 180px; border-right: 1px solid var(--line); }
.wf-sidebar-right { width: 220px; border-left: 1px solid var(--line); }
.wf-sidebar-label { color: var(--muted); font-size: 11px; padding: 4px 6px; }
.wf-stepview {
  flex: 1; border: 1px dashed var(--line); border-radius: 6px;
  margin: 4px; padding: 8px;
}
.wf-stepview-label {
  font-size: 10px; color: var(--muted); font-weight: 600;
  text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px;
}

/* ── Navigation bars ─────────────────────────────────────────────────── */
.wf-topbar {
  background: var(--bar); border-bottom: 1px solid var(--bar-border);
  padding: 0 14px; height: 48px; display: flex; align-items: center;
  gap: 8px; flex-shrink: 0;
}
.wf-topbar-brand { font-weight: 700; font-size: 15px; margin-right: 8px; }
.wf-navbar {
  background: var(--bar); border-bottom: 1px solid var(--bar-border);
  padding: 0 12px; height: 40px; display: flex; align-items: center; gap: 6px;
}
.wf-bottombar {
  background: var(--bar); border-top: 1px solid var(--bar-border);
  padding: 0 12px; height: 48px; display: flex; align-items: center;
  gap: 8px; justify-content: space-around; flex-shrink: 0;
}
.wf-toolbar {
  background: var(--panel); border-bottom: 1px solid var(--line);
  padding: 8px 12px; display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}
.wf-toolbar-title { font-weight: 600; }
.wf-filterbar {
  background: #fafbfc; border-bottom: 1px solid var(--line);
  padding: 6px 12px; display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}
.wf-navmenu { display: flex; flex-direction: column; gap: 2px; padding: 4px 0; }
.wf-navitem {
  padding: 7px 10px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: var(--ink);
}
.wf-navitem:hover { background: #e8eaf0; }
.wf-header-actions { display: flex; gap: 6px; align-items: center; }

/* ── Tabs ────────────────────────────────────────────────────────────── */
.wf-tabgroup {
  display: flex; gap: 2px; padding: 4px 6px;
  border-bottom: 1px solid var(--line); background: var(--panel); flex-shrink: 0;
}
.wf-tab {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg);
  padding: 5px 14px; cursor: pointer; font-size: 12px; color: var(--muted);
}
.wf-tab-active, .wf-tab:first-child {
  background: var(--panel); color: var(--accent);
  border-color: var(--accent); font-weight: 600;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
.wf-btn {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg);
  padding: 6px 14px; cursor: pointer; font-size: 12px; color: var(--ink);
  white-space: nowrap;
}
.wf-btn-primary {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
.wf-btn-secondary {
  background: var(--panel); color: var(--accent); border-color: var(--accent);
}
.wf-btn-tool {
  background: var(--btn-bg); color: var(--muted); border-color: var(--btn-border);
  padding: 4px 10px; font-size: 11px;
}
.wf-btn-active { background: var(--accent); color: #fff; }
.wf-btn-sm { padding: 3px 8px; font-size: 11px; }
.wf-btn-icon {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg);
  width: 30px; height: 30px; display: inline-flex; align-items: center;
  justify-content: center; cursor: pointer; font-size: 13px; color: var(--muted);
  flex-shrink: 0;
}
.wf-menu-trigger {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--btn-bg);
  padding: 4px 8px; cursor: pointer; font-size: 12px; color: var(--muted);
}

/* ── Inputs ──────────────────────────────────────────────────────────── */
.wf-input {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--input-bg);
  padding: 6px 10px; display: flex; align-items: center; gap: 6px; min-width: 140px;
}
.wf-input-search { background: #f8fafc; }
.wf-search-icon { color: var(--muted); font-size: 15px; }
.wf-placeholder { color: var(--muted); font-size: 12px; }
.wf-select {
  border: 1px solid var(--btn-border); border-radius: 6px; background: var(--input-bg);
  padding: 6px 10px; display: flex; align-items: center; justify-content: space-between;
  min-width: 120px;
}
.wf-caret { color: var(--muted); font-size: 10px; }
.wf-checkbox {
  display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px;
}
.wf-checkbox-box {
  width: 14px; height: 14px; border: 1.5px solid var(--btn-border);
  border-radius: 3px; flex-shrink: 0;
}
.wf-toggle { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; }
.wf-toggle-track {
  width: 34px; height: 18px; background: #d0d7e0; border-radius: 9px;
  position: relative; flex-shrink: 0;
}
.wf-toggle-thumb {
  width: 14px; height: 14px; background: #fff; border-radius: 50%;
  position: absolute; top: 2px; left: 2px; box-shadow: 0 1px 2px rgba(0,0,0,.2);
}
.wf-radio { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; }
.wf-radio-dot {
  width: 14px; height: 14px; border: 1.5px solid var(--btn-border);
  border-radius: 50%; flex-shrink: 0;
}

/* ── Media ───────────────────────────────────────────────────────────── */
.wf-avatar {
  width: 36px; height: 36px; background: #c8d0dc; border-radius: 50%; flex-shrink: 0;
}
.wf-avatar-sm { width: 26px; height: 26px; }
.wf-image {
  background: #dde3ec; border-radius: 6px; min-height: 72px;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted); font-size: 12px; width: 100%;
}
.wf-icon { color: var(--muted); font-size: 14px; display: inline-block; }

/* ── Data display ────────────────────────────────────────────────────── */
.wf-table { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; width: 100%; }
.wf-table-header-row {
  display: flex; background: #f0f2f6; border-bottom: 1px solid var(--line);
}
.wf-table-row {
  display: flex; border-bottom: 1px solid #eef0f4;
}
.wf-table-row:last-child { border-bottom: 0; }
.wf-table-cell {
  flex: 1; padding: 7px 10px; font-size: 12px; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.wf-table-header-row .wf-table-cell { font-weight: 600; color: var(--muted); font-size: 11px; }
.wf-list { display: flex; flex-direction: column; gap: 2px; }
.wf-list-item {
  padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--card-bg); font-size: 12px; display: flex; align-items: center; gap: 8px;
}
.wf-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.wf-grid-cell {
  border: 1px solid var(--line); border-radius: 6px; background: var(--card-bg);
  padding: 10px; font-size: 12px; text-align: center; color: var(--muted);
}
.wf-card {
  border: 1px solid var(--line); border-radius: 8px; background: var(--card-bg);
  padding: 12px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 6px;
}
.wf-metric {
  border: 1px solid var(--line); border-radius: 8px; background: var(--metric-bg);
  padding: 12px 14px; min-width: 100px; flex: 1;
}
.wf-metric-label { font-size: 11px; color: var(--muted); font-weight: 600; margin-bottom: 4px; }
.wf-metric-value { font-size: 22px; font-weight: 700; }
.wf-badge {
  display: inline-block; background: var(--badge-bg); color: var(--badge-ink);
  border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: 600;
}
.wf-tag {
  display: inline-block; background: #f0f4ff; color: #3b5bdb;
  border-radius: 4px; padding: 2px 7px; font-size: 11px;
}
.wf-tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.wf-person-cell { display: flex; align-items: center; gap: 8px; }
.wf-pagination { display: flex; gap: 4px; align-items: center; }
.wf-timeline { display: flex; flex-direction: column; gap: 10px; padding: 8px 0; }
.wf-timeline-item { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.wf-timeline-dot {
  width: 10px; height: 10px; border: 2px solid var(--accent);
  border-radius: 50%; flex-shrink: 0;
}

/* ── Typography ──────────────────────────────────────────────────────── */
.wf-title { margin: 0 0 6px; font-size: 16px; font-weight: 700; color: var(--ink); }
.wf-text { margin: 0 0 4px; font-size: 13px; color: var(--ink); }
.wf-caption { margin: 0 0 2px; font-size: 11px; color: var(--muted); }
.wf-label-text { font-size: 12px; font-weight: 600; }
.wf-placeholder { color: var(--muted); font-size: 12px; }

/* ── Misc ────────────────────────────────────────────────────────────── */
.wf-divider { border: none; border-top: 1px solid var(--line); margin: 8px 0; }
.wf-optional { opacity: .55; }
.wf-section {
  display: flex; flex-direction: column; gap: 8px; padding: 10px;
  background: var(--panel); border-radius: 8px;
}
.wf-section-label {
  font-size: 10px; color: var(--muted); font-weight: 700;
  text-transform: uppercase; letter-spacing: .07em;
}
.wf-section-bar {
  background: #f8fafc; border: 1px solid var(--line); border-radius: 6px;
  padding: 8px 12px; display: flex; align-items: center; gap: 8px;
}
.wf-generic {
  border: 1px dashed var(--line); border-radius: 6px;
  padding: 8px 10px; font-size: 12px; color: var(--muted); background: #fafbfc;
}
.wf-modal {
  border: 1px solid var(--line); border-radius: 10px; background: var(--panel);
  box-shadow: 0 4px 16px rgba(0,0,0,.12); max-width: 480px; margin: 12px auto;
}
.wf-modal-header {
  padding: 12px 16px; font-weight: 600; border-bottom: 1px solid var(--line);
}
.wf-modal-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
@media (max-width: 860px) {
  .app { grid-template-columns: 1fr; }
  .sidebar { border-right: 0; border-bottom: 1px solid var(--line); max-height: 38vh; }
  .workspace { grid-template-columns: 1fr; }
}
"""

JS = r"""
const docs = DOCS_JSON;
const nav = document.getElementById('nav');
const frame = document.getElementById('frame');
const source = document.getElementById('source');
const title = document.getElementById('doc-title');
const path = document.getElementById('doc-path');
const preview = document.getElementById('preview');
let active = 0;

function renderNav() {
  nav.innerHTML = '';
  for (const kind of ['global', 'screen', 'component']) {
    const items = docs.map((d, i) => [d, i]).filter(([d]) => d.kind === kind);
    if (!items.length) continue;
    const labels = { global: 'Global', screen: 'Screens', component: 'Components' };
    const hdr = document.createElement('div');
    hdr.className = 'group-title';
    hdr.textContent = labels[kind];
    nav.appendChild(hdr);
    for (const [d, i] of items) {
      const btn = document.createElement('button');
      btn.className = 'nav-button';
      btn.type = 'button';
      btn.textContent = d.name;
      btn.onclick = () => select(i);
      btn.dataset.index = i;
      nav.appendChild(btn);
    }
  }
}

function select(index) {
  active = index;
  const doc = docs[index];
  title.textContent = doc ? doc.name : '—';
  path.textContent = doc ? doc.path : '';
  frame.innerHTML = doc ? doc.html : '<div class="wf-empty">디자인 파일이 없습니다.</div>';
  source.textContent = doc ? doc.source : '';
  for (const btn of nav.querySelectorAll('.nav-button'))
    btn.classList.toggle('active', Number(btn.dataset.index) === index);
}

document.getElementById('desktop').onclick = () => {
  preview.classList.replace('mobile', 'desktop') || preview.classList.add('desktop');
  document.getElementById('desktop').classList.add('active');
  document.getElementById('mobile').classList.remove('active');
};
document.getElementById('mobile').onclick = () => {
  preview.classList.replace('desktop', 'mobile') || preview.classList.add('mobile');
  document.getElementById('mobile').classList.add('active');
  document.getElementById('desktop').classList.remove('active');
};

renderNav();
const firstScreen = docs.findIndex(d => d.kind === 'screen');
select(firstScreen >= 0 ? firstScreen : 0);
"""


def build_html(docs: Iterable[Doc], root: Path, title: str) -> str:
    payload = [doc_to_payload(doc, root) for doc in docs]
    data = json.dumps(payload, ensure_ascii=False)
    et = html.escape(title)
    script = JS.replace("DOCS_JSON", data)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{et}</title>
<style>{CSS}</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <h1 class="brand">{et}</h1>
    <p class="sub">STN Wireframe Viewer</p>
    <div id="nav"></div>
  </aside>
  <main class="main">
    <div class="toolbar-bar">
      <div class="title">
        <h2 id="doc-title"></h2>
        <p id="doc-path"></p>
      </div>
      <div class="controls">
        <div class="seg" aria-label="Viewport">
          <button id="desktop" class="active" type="button">Desktop</button>
          <button id="mobile" type="button">Mobile</button>
        </div>
      </div>
    </div>
    <div class="workspace">
      <section id="preview" class="preview desktop">
        <div class="frame" id="frame"></div>
      </section>
      <section class="source-panel"><pre id="source"></pre></section>
    </div>
  </main>
</div>
<script>{script}</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default="./design", help="Path to the design directory.")
    parser.add_argument("--out", default="./wireframe.html", help="Output HTML file path.")
    parser.add_argument("--title", default="Wireframe Viewer", help="Viewer title.")
    args = parser.parse_args()

    design_dir = Path(args.design).resolve()
    out_path = Path(args.out).resolve()
    docs = collect_docs(design_dir)
    html_text = build_html(docs, root=design_dir.parent, title=args.title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Documents: {len(docs)}")
    for doc in docs:
        print(f"- {doc.kind}: {doc.name} ({doc.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
