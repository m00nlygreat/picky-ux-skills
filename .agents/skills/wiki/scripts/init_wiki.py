#!/usr/bin/env python3
import argparse
import re
import shutil
from pathlib import Path


MODULE_ORDER = ["REQUIREMENT", "MVP", "TERMS", "LOG"]
MODULE_ALIASES = {
    "REQ": "REQUIREMENT",
    "REQUIREMENTS": "REQUIREMENT",
    "REQUIREMENT": "REQUIREMENT",
    "MVP": "MVP",
    "TERM": "TERMS",
    "TERMS": "TERMS",
    "LOG": "LOG",
}

AGENTS_BULLETS = {
    "REQUIREMENT": "- `wiki/REQUIREMENT.md`는 현재 요구사항 요약의 유지본이다. 요구사항을 정리하거나 갱신할 때 이 파일을 함께 관리한다.",
    "MVP": "- `wiki/MVP.md`는 현재 MVP 범위의 유지본이다. MVP 범위를 정리하거나 갱신할 때 이 파일을 함께 관리한다.",
    "TERMS": "- `wiki/TERMS.md`는 프로젝트 용어와 GUI 표시명의 유지본이다. 용어, 명명 기준, 화면 표시명을 정리하거나 갱신할 때 이 파일을 함께 관리한다.",
    "LOG": "- `wiki/LOG.md`에는 프로젝트 관련 중대 결정사항, 새로 알아낸 사실, 방향 변경을 시간순으로 남긴다.",
}


def normalize_modules(raw_modules):
    tokens = []
    for raw in raw_modules:
        tokens.extend(part for part in re.split(r"[,\s]+", raw.strip()) if part)

    if not tokens:
        raise SystemExit("Choose modules: LOG, TERMS, REQUIREMENT, MVP, or ALL.")

    if any(token.upper() == "ALL" for token in tokens):
        return MODULE_ORDER

    selected = []
    for token in tokens:
        key = token.upper()
        if key not in MODULE_ALIASES:
            raise SystemExit(f"Unknown module: {token}")
        module = MODULE_ALIASES[key]
        if module not in selected:
            selected.append(module)
    return [module for module in MODULE_ORDER if module in selected]


def existing_modules(wiki_dir):
    found = []
    for module in MODULE_ORDER:
        if (wiki_dir / f"{module}.md").exists():
            found.append(module)
    return found


def render_agents_section(modules):
    lines = [
        "## 위키 관리",
        "",
        "- 이 저장소의 간단한 위키는 `wiki/`에 둔다.",
        "- 위키 문서는 한국어로 짧고 명확하게 작성한다.",
    ]
    for module in MODULE_ORDER:
        if module in modules:
            lines.append(AGENTS_BULLETS[module])
    lines.append("- 원본 자료 폴더는 사용자가 요청하지 않는 한 수정하지 않는다.")
    return "\n".join(lines) + "\n"


def inject_agents_section(agents_path, section):
    if agents_path.exists():
        content = agents_path.read_text(encoding="utf-8")
    else:
        content = "# 에이전트 메모\n"

    pattern = re.compile(r"(?ms)^## 위키 관리\s*\n.*?(?=^##\s|\Z)")
    if pattern.search(content):
        updated = pattern.sub(section.rstrip() + "\n\n", content).rstrip() + "\n"
    else:
        updated = content.rstrip() + "\n\n" + section

    agents_path.write_text(updated, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Initialize a lightweight ./wiki folder.")
    parser.add_argument("modules", nargs="*", help="Modules: LOG TERMS REQUIREMENT MVP, or ALL.")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing wiki module files.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    skill_root = Path(__file__).resolve().parents[1]
    template_dir = skill_root / "templates"
    wiki_dir = project_root / "wiki"
    agents_path = project_root / "AGENTs.md"
    if not agents_path.exists() and (project_root / "AGENTS.md").exists():
        agents_path = project_root / "AGENTS.md"

    modules = normalize_modules(args.modules)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    created = []
    skipped = []
    overwritten = []
    for module in modules:
        source = template_dir / f"{module}.md"
        target = wiki_dir / f"{module}.md"
        existed = target.exists()
        if existed and not args.force:
            skipped.append(target)
            continue
        shutil.copyfile(source, target)
        if existed and args.force:
            overwritten.append(target)
        else:
            created.append(target)

    agent_modules = sorted(set(existing_modules(wiki_dir) + modules), key=MODULE_ORDER.index)
    inject_agents_section(agents_path, render_agents_section(agent_modules))

    for path in created:
        print(f"created {path}")
    for path in overwritten:
        print(f"overwritten {path}")
    for path in skipped:
        print(f"skipped existing {path}")
    print(f"updated {agents_path}")


if __name__ == "__main__":
    main()
