---
name: interact
description: Open a reusable local GUI for human-in-the-loop interaction and wait for the user's answer. Use when Codex needs the user to choose between visual options, answer multiple structured questions, fill a temporary form, approve a direction, or provide feedback that is awkward to collect in plain chat. The skill runs a project-scoped local server, updates the current prompt dynamically, and reads the submitted answer before continuing.
---

# Interact

Use this skill to ask the user through a local browser UI, then wait for the submitted JSON answer before continuing the task.

## Workflow

Run commands from the project root. The server and answer files are project-scoped under `.interact/`.

1. Build a concise interaction schema.
2. Ensure the server is running or let `ask` start it.
3. Send the schema with `ask`.
4. Open the returned URL for the user, preferably with the in-app browser when available.
5. Wait for the answer with `wait` or use `ask --wait`.
6. Read the returned JSON and continue the original task.

## Commands

Use the bundled script:

```powershell
node .agents/skills/interact/scripts/interact-server.js ensure
node .agents/skills/interact/scripts/interact-server.js ask --schema path/to/schema.json
node .agents/skills/interact/scripts/interact-server.js wait --id <interaction-id>
node .agents/skills/interact/scripts/interact-server.js status
node .agents/skills/interact/scripts/interact-server.js stop
```

For quick one-off prompts, pass inline JSON:

```powershell
node .agents/skills/interact/scripts/interact-server.js ask --schema-json '{"title":"Choose a direction","fields":[{"id":"direction","type":"single-select","label":"Direction","required":true,"options":["A","B"]}]}'
```

`ask` returns:

```json
{
  "id": "interaction-id",
  "url": "http://127.0.0.1:5199/i/interaction-id",
  "answerFile": ".interact/answers/interaction-id.json"
}
```

## Schema

Top-level fields:

```json
{
  "id": "optional-stable-id",
  "title": "Question shown at the top",
  "description": "Optional context",
  "submitLabel": "Submit",
  "fields": []
}
```

Supported field types:

- `single-select`: radio-style option cards. Use for exactly one choice.
- `multi-select`: checkbox option cards. Use `min` and `max` when needed.
- `text`: short text input.
- `textarea`: long-form input.
- `number`: numeric input. Use `min` and `max` for bounds when needed.
- `select`: dropdown.
- `boolean`: checkbox toggle.
- `info`: non-answer explanatory text.

Each answer field should have an `id`, `type`, `label`, and optional `description`, `placeholder`, `required`, and `default`.

Options can be strings:

```json
{ "options": ["Continue", "Revise", "Stop"] }
```

Or objects:

```json
{
  "options": [
    { "value": "continue", "label": "Continue", "description": "Proceed with the current plan" },
    { "value": "revise", "label": "Revise", "description": "Change direction before implementation" }
  ]
}
```

## Reuse Rules

- Reuse the same server during a conversation. Every `ask` call replaces the active GUI with a new interaction.
- Give each interaction a stable `id` only when the caller needs to refer to it later; otherwise let the script generate one.
- Prefer `.interact/answers/<id>.json` or the `wait` command as the source of truth.
- Keep schemas small and task-specific. Do not use the GUI when a normal chat question is clearer.
- Stop the server with `stop` when it is no longer useful.
