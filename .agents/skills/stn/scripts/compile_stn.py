#!/usr/bin/env python3
import argparse
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


GLOBAL_REF_RE = re.compile(r"<GLOBAL\s*/>")
SCREEN_ROOT_RE = re.compile(r"^\s*-\s*Screen:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class Reference:
    title: str
    path: Path
    kind: str


@dataclass
class ScreenBundle:
    name: str
    title: str
    source: Path
    compiled: Path
    content: str
    references: list[Reference] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), root.resolve()).replace(os.sep, "/")


def strip_quotes(value: str) -> str:
    value = value.strip().rstrip(",")
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_inline_imports(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        parts = []
        current = []
        quote = None
        escape = False
        for char in body:
            if escape:
                current.append(char)
                escape = False
                continue
            if char == "\\":
                current.append(char)
                escape = True
                continue
            if quote:
                current.append(char)
                if char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                current.append(char)
                quote = char
                continue
            if char == ",":
                parts.append("".join(current).strip())
                current = []
                continue
            current.append(char)
        if current:
            parts.append("".join(current).strip())
        return [strip_quotes(part) for part in parts if strip_quotes(part)]
    return [strip_quotes(value)] if strip_quotes(value) else []


def extract_frontmatter(content: str) -> str:
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", content, re.DOTALL)
    return match.group(1) if match else ""


def parse_imports(content: str) -> list[str]:
    frontmatter = extract_frontmatter(content)
    if not frontmatter:
        return []

    imports = []
    in_imports = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = re.match(r"^imports\s*:\s*(.*)$", stripped)
        if match:
            imports.extend(parse_inline_imports(match.group(1)))
            in_imports = True
            continue

        if in_imports:
            item = re.match(r"^-\s+(.+)$", stripped)
            if item:
                value = strip_quotes(item.group(1))
                if value:
                    imports.append(value)
                continue
            if not line.startswith((" ", "\t")):
                in_imports = False

    deduped = []
    seen = set()
    for item in imports:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def screen_title(content: str, fallback: str) -> str:
    match = SCREEN_ROOT_RE.search(content)
    return match.group(1).strip() if match else fallback


def discover_screens(design_dir: Path) -> list[Path]:
    if not design_dir.exists():
        raise SystemExit(f"Design directory not found: {design_dir}")
    return sorted(
        [
            path
            for path in design_dir.glob("*.md")
            if path.name.lower() != "global.md" and path.is_file()
        ],
        key=lambda path: path.name.lower(),
    )


def resolve_screen_arg(screen: str, project_root: Path, design_dir: Path) -> Path:
    raw = Path(screen)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(project_root / raw)
        candidates.append(design_dir / raw)
        if raw.suffix.lower() != ".md":
            candidates.append(design_dir / f"{screen}.md")

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    screen_key = raw.stem.lower()
    for candidate in discover_screens(design_dir):
        if candidate.stem.lower() == screen_key or candidate.name.lower() == raw.name.lower():
            return candidate.resolve()

    raise SystemExit(f"Screen not found: {screen}")


def resolve_import(screen_path: Path, import_path: str) -> Path:
    candidate = Path(import_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (screen_path.parent / candidate).resolve()


def collect_references(screen_path: Path, content: str, design_dir: Path) -> tuple[list[Reference], list[str]]:
    references = []
    diagnostics = []
    seen = set()

    if GLOBAL_REF_RE.search(content):
        global_path = (design_dir / "GLOBAL.md").resolve()
        if global_path.exists():
            references.append(Reference("GLOBAL", global_path, "global"))
            seen.add(global_path)
        else:
            diagnostics.append(f"Missing GLOBAL reference: {rel_path(global_path, design_dir.parent)}")

    for import_path in parse_imports(content):
        resolved = resolve_import(screen_path, import_path)
        if resolved in seen:
            continue
        if resolved.exists() and resolved.is_file():
            references.append(Reference(f"Component: {resolved.stem}", resolved, "component"))
            seen.add(resolved)
        else:
            diagnostics.append(
                f"Missing component import from {rel_path(screen_path, design_dir.parent)}: {import_path}"
            )

    return references, diagnostics


def build_screen_bundle(screen_path: Path, project_root: Path, design_dir: Path, out_dir: Path) -> ScreenBundle:
    content = read_text(screen_path)
    name = screen_path.stem
    title = screen_title(content, name)
    references, diagnostics = collect_references(screen_path, content, design_dir)
    compiled = out_dir / "screens" / f"{name}.md"
    return ScreenBundle(name, title, screen_path, compiled, content, references, diagnostics)


def append_source_section(parts: list[str], heading: str, source: Path, content: str, project_root: Path) -> None:
    parts.extend([heading, "", f"<!-- source: {rel_path(source, project_root)} -->", "", content])
    if not content.endswith("\n"):
        parts.append("\n")
    parts.append("")


def render_diagnostics(diagnostics: list[str]) -> str:
    if not diagnostics:
        return "- None\n"
    return "\n".join(f"- {item}" for item in diagnostics) + "\n"


def render_screen_bundle(bundle: ScreenBundle, project_root: Path) -> str:
    parts = [f"# Compiled Screen: {bundle.name}", ""]
    append_source_section(parts, "## Main", bundle.source, bundle.content, project_root)

    parts.extend(["## References", ""])
    if bundle.references:
        for reference in bundle.references:
            append_source_section(
                parts,
                f"### {reference.title}",
                reference.path,
                read_text(reference.path),
                project_root,
            )
    else:
        parts.extend(["- None", ""])

    parts.extend(["## Diagnostics", "", render_diagnostics(bundle.diagnostics)])
    return "\n".join(parts)


def render_app_bundle(bundles: list[ScreenBundle], project_root: Path) -> str:
    parts = ["# Compiled STN App", "", "## Screens", ""]
    diagnostics = []

    for bundle in bundles:
        append_source_section(parts, f"### Screen: {bundle.name}", bundle.source, bundle.content, project_root)
        diagnostics.extend(bundle.diagnostics)

    parts.extend(["## References", ""])
    seen = set()
    references = []
    for bundle in bundles:
        for reference in bundle.references:
            if reference.path not in seen:
                references.append(reference)
                seen.add(reference.path)

    if references:
        for reference in references:
            append_source_section(
                parts,
                f"### {reference.title}",
                reference.path,
                read_text(reference.path),
                project_root,
            )
    else:
        parts.extend(["- None", ""])

    parts.extend(["## Diagnostics", "", render_diagnostics(diagnostics)])
    return "\n".join(parts)


def manifest_entry(bundle: ScreenBundle, project_root: Path) -> dict:
    sources = [bundle.source] + [reference.path for reference in bundle.references]
    return {
        "name": bundle.name,
        "title": bundle.title,
        "source": rel_path(bundle.source, project_root),
        "compiled": rel_path(bundle.compiled, project_root),
        "sources": [rel_path(path, project_root) for path in sources],
        "diagnostics": bundle.diagnostics,
    }


def write_manifest(
    bundles: list[ScreenBundle],
    project_root: Path,
    out_dir: Path,
    app_compiled: Path | None,
    diagnostics: list[str],
) -> Path:
    manifest = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "screens": [manifest_entry(bundle, project_root) for bundle in bundles],
        "app": {
            "compiled": rel_path(app_compiled, project_root),
            "screenCount": len(bundles),
        }
        if app_compiled
        else None,
        "diagnostics": diagnostics,
    }
    path = out_dir / "manifest.json"
    write_text(path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile STN Markdown sources into screen/app Markdown bundles."
    )
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--design-dir", default="design", help="Design directory relative to project root.")
    parser.add_argument("--out-dir", default=".stn/compiled", help="Output directory relative to project root.")
    parser.add_argument("--screen", action="append", default=[], help="Screen name or path. May be repeated.")
    parser.add_argument("--app", action="store_true", help="Generate the app bundle.")
    parser.add_argument("--all", action="store_true", help="Generate every screen bundle and the app bundle.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    design_dir = (project_root / args.design_dir).resolve()
    out_dir = (project_root / args.out_dir).resolve()

    if args.all or (not args.screen and not args.app):
        screen_paths = discover_screens(design_dir)
        generate_app = True
    else:
        screen_paths = [resolve_screen_arg(screen, project_root, design_dir) for screen in args.screen]
        if args.app:
            app_paths = discover_screens(design_dir)
            existing = {path.resolve() for path in screen_paths}
            screen_paths.extend(path.resolve() for path in app_paths if path.resolve() not in existing)
        generate_app = args.app

    bundles = [build_screen_bundle(path, project_root, design_dir, out_dir) for path in screen_paths]
    diagnostics = [item for bundle in bundles for item in bundle.diagnostics]

    wrote = []
    should_write_screens = args.all or bool(args.screen) or args.app or (not args.screen and not args.app)
    if should_write_screens:
        for bundle in bundles:
            write_text(bundle.compiled, render_screen_bundle(bundle, project_root))
            wrote.append(bundle.compiled)

    app_compiled = None
    if generate_app:
        app_compiled = out_dir / "app.md"
        write_text(app_compiled, render_app_bundle(bundles, project_root))
        wrote.append(app_compiled)

    manifest_path = write_manifest(bundles, project_root, out_dir, app_compiled, diagnostics)
    wrote.append(manifest_path)

    for path in wrote:
        print(f"wrote {rel_path(path, project_root)}")
    for diagnostic in diagnostics:
        print(f"diagnostic {diagnostic}")


if __name__ == "__main__":
    main()
