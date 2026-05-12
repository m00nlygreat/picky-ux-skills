---
name: wiki
description: Initialize and maintain a lightweight project wiki under ./wiki, with selectable modules such as LOG, TERMS, REQUIREMENT, and MVP. Use when Codex needs to create wiki files from templates, update project terminology or requirements docs, append decision logs, or inject wiki usage instructions into AGENTs.md.
---

# Wiki

Create and maintain a compact project wiki in `./wiki`. Keep documents Korean, short, and operational.

## Modules

Available modules:

-   `LOG`: chronological project decisions, facts, and direction changes.
    
-   `TERMS` or `TERM`: project terms, naming rules, and GUI display names.
    
-   `REQUIREMENT`: current requirements summary.
    
-   `MVP`: current minimum product scope.
    

Templates live in `templates/`:

-   `templates/LOG.md`
    
-   `templates/TERMS.md`
    
-   `templates/REQUIREMENT.md`
    
-   `templates/MVP.md`
    

Each template includes YAML frontmatter describing the document role and how to use it. Preserve that frontmatter when copying or updating wiki documents.

Use `scripts/init_wiki.py` for initialization when possible:

```bash
python path/to/wiki/scripts/init_wiki.py --project-root . LOG TERMS REQUIREMENT MVP
```
## Initialize

1. Work from the project root and use `./wiki`.
2. Inspect existing `wiki/` and `AGENTs.md` before editing.
3. If the user names modules, create only those modules. Normalize `TERM` to `TERMS`.
4. If the user asks to initialize a wiki but does not choose modules, ask which modules to include. Offer `LOG`, `TERMS`, `REQUIREMENT`, and `MVP`.
5. Create `./wiki` if needed.
6. Copy selected templates into `./wiki/{MODULE}.md`; prefer `scripts/init_wiki.py` for this.
7. Do not overwrite existing wiki files unless the user explicitly asks. If a file exists, update it in place only when the requested change requires it.
8. Inject or update the `## 위키 관리` section in `AGENTs.md`.

## [AGENTs.md](http://AGENTs.md) Injection

Add or maintain instructions like this, adjusted to the selected modules:
```
## 위키 관리

- 이 저장소의 간단한 위키는 `wiki/`에 둔다.
- 위키 문서는 한국어로 짧고 명확하게 작성한다.
- `wiki/REQUIREMENT.md`는 현재 요구사항 요약의 유지본이다. 요구사항을 정리하거나 갱신할 때 이 파일을 함께 관리한다.
- `wiki/MVP.md`는 현재 MVP 범위의 유지본이다. MVP 범위를 정리하거나 갱신할 때 이 파일을 함께 관리한다.
- `wiki/TERMS.md`는 프로젝트 용어와 GUI 표시명의 유지본이다. 용어, 명명 기준, 화면 표시명을 정리하거나 갱신할 때 이 파일을 함께 관리한다.
- `wiki/LOG.md`에는 프로젝트 관련 중대 결정사항, 새로 알아낸 사실, 방향 변경을 시간순으로 남긴다.
- 원본 자료 폴더는 사용자가 요청하지 않는 한 수정하지 않는다.
```

Only include bullets for modules that exist or are being created, except for the general wiki rules.

## Maintain

- Keep wiki files as living summaries, not raw dumps.
- Update `wiki/LOG.md` when a major decision, new fact, or direction change is made.
- Update `wiki/TERMS.md` when naming, GUI labels, or forbidden/주의 표현 change.
- Update `wiki/REQUIREMENT.md` when current requirements are summarized or changed.
- Update `wiki/MVP.md` when scope, exclusions, or MVP workflow changes.
- Do not edit original source material folders such as `requirement/` unless the user asks.
