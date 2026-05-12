#!/usr/bin/env node

const childProcess = require("node:child_process");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { URL } = require("node:url");

const APP_NAME = "codex-interact";
const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 5199;
const DEFAULT_TIMEOUT_SECONDS = 600;

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});

async function main() {
  const [command = "help", ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);
  const root = path.resolve(args.root || process.cwd());
  const dirs = getDirs(root);

  if (command === "help" || args.help) {
    printHelp();
    return;
  }

  if (command === "serve") {
    await serve(root, {
      host: args.host || DEFAULT_HOST,
      port: Number(args.port || DEFAULT_PORT),
    });
    return;
  }

  if (command === "ensure") {
    const state = await ensureServer(root, args);
    printJson(state);
    return;
  }

  if (command === "status") {
    const state = await readState(dirs);
    if (!state) {
      printJson({ running: false });
      return;
    }
    const live = await pingState(state);
    printJson(live ? { running: true, ...live } : { running: false, staleState: state });
    return;
  }

  if (command === "ask") {
    const state = await ensureServer(root, args);
    const schema = await readSchema(args);
    const interaction = normalizeInteraction(schema, args);
    await postJson(`${state.url}/api/interactions`, interaction);
    const result = {
      id: interaction.id,
      url: `${state.url}/i/${encodeURIComponent(interaction.id)}`,
      markdownLink: `[Open interact GUI](${state.url}/i/${encodeURIComponent(interaction.id)})`,
      answerFile: path.join(dirs.answers, `${interaction.id}.json`),
      stateFile: dirs.stateFile,
    };

    if (args.wait) {
      const answer = await waitForAnswer(state, interaction.id, Number(args.timeout || DEFAULT_TIMEOUT_SECONDS));
      printJson({ ...result, answer });
      return;
    }

    printJson(result);
    return;
  }

  if (command === "wait") {
    const id = required(args.id, "--id is required for wait");
    const state = await ensureServer(root, args);
    const answer = await waitForAnswer(state, id, Number(args.timeout || DEFAULT_TIMEOUT_SECONDS));
    printJson(answer);
    return;
  }

  if (command === "stop") {
    const state = await readState(dirs);
    if (!state) {
      printJson({ stopped: false, reason: "no state file" });
      return;
    }
    try {
      process.kill(state.pid, "SIGTERM");
    } catch {
      // The process may already be gone.
    }
    await rmIfExists(dirs.stateFile);
    printJson({ stopped: true, pid: state.pid });
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

async function ensureServer(root, args) {
  const dirs = getDirs(root);
  await ensureDirs(dirs);

  const existing = await readState(dirs);
  if (existing) {
    const live = await pingState(existing);
    if (live && sameRoot(live.root, root)) {
      await writeJson(dirs.stateFile, live);
      return live;
    }
  }

  const host = args.host || DEFAULT_HOST;
  const preferredPort = Number(args.port || existing?.port || DEFAULT_PORT);
  const port = await findAvailablePort(host, preferredPort, root);
  const logFile = path.join(dirs.dir, "server.log");

  const child = childProcess.spawn(process.execPath, [__filename, "serve", "--host", host, "--port", String(port), "--root", root], {
    cwd: root,
    detached: true,
    stdio: ["ignore", fs.openSync(logFile, "a"), fs.openSync(logFile, "a")],
    windowsHide: true,
  });
  child.unref();

  const url = `http://${host}:${port}`;
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    await sleep(200);
    const live = await pingState({ url });
    if (live && sameRoot(live.root, root)) {
      await writeJson(dirs.stateFile, live);
      return live;
    }
  }

  throw new Error(`Server did not become ready. See ${logFile}`);
}

async function serve(root, options) {
  const dirs = getDirs(root);
  await ensureDirs(dirs);

  const host = options.host;
  const port = options.port;
  const url = `http://${host}:${port}`;
  const startedAt = new Date().toISOString();

  const server = http.createServer(async (req, res) => {
    try {
      const requestUrl = new URL(req.url, url);

      if (req.method === "GET" && requestUrl.pathname === "/") {
        const active = await readActiveInteraction(dirs);
        return sendHtml(res, renderPage(active));
      }

      if (req.method === "GET" && requestUrl.pathname.startsWith("/i/")) {
        const id = decodeURIComponent(requestUrl.pathname.slice(3));
        const interaction = await readInteraction(dirs, id);
        return sendHtml(res, renderPage(interaction));
      }

      if (req.method === "GET" && requestUrl.pathname === "/api/state") {
        const state = await buildState(dirs, { host, port, startedAt });
        return sendJson(res, state);
      }

      if (req.method === "POST" && requestUrl.pathname === "/api/interactions") {
        const payload = normalizeInteraction(JSON.parse(await readBody(req) || "{}"), {});
        await writeJson(path.join(dirs.prompts, `${payload.id}.json`), payload);
        await writeJson(dirs.activeFile, { id: payload.id, updatedAt: new Date().toISOString() });
        await rmIfExists(path.join(dirs.answers, `${payload.id}.json`));
        return sendJson(res, {
          ok: true,
          id: payload.id,
          url: `${url}/i/${encodeURIComponent(payload.id)}`,
          markdownLink: `[Open interact GUI](${url}/i/${encodeURIComponent(payload.id)})`,
        });
      }

      if (req.method === "GET" && requestUrl.pathname.startsWith("/api/interactions/")) {
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const id = decodeURIComponent(parts[2] || "");

        if (parts[3] === "answer") {
          const answer = await readJson(path.join(dirs.answers, `${id}.json`), null);
          return sendJson(res, answer);
        }

        const interaction = await readInteraction(dirs, id);
        return sendJson(res, interaction);
      }

      if (req.method === "POST" && requestUrl.pathname.startsWith("/api/interactions/") && requestUrl.pathname.endsWith("/answer")) {
        const parts = requestUrl.pathname.split("/").filter(Boolean);
        const id = decodeURIComponent(parts[2] || "");
        const interaction = await readInteraction(dirs, id);
        if (!interaction) return sendJson(res, { error: "interaction not found" }, 404);

        const payload = JSON.parse(await readBody(req) || "{}");
        const validation = validateAnswer(interaction, payload.values || {});
        if (validation.errors.length > 0) {
          return sendJson(res, { ok: false, errors: validation.errors }, 400);
        }

        const answer = {
          id,
          values: validation.values,
          submittedAt: new Date().toISOString(),
        };
        await writeJson(path.join(dirs.answers, `${id}.json`), answer);
        return sendJson(res, { ok: true, answer });
      }

      return sendText(res, "Not found", 404);
    } catch (error) {
      return sendJson(res, { error: error.message || String(error) }, 500);
    }
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, resolve);
  });

  await writeJson(dirs.stateFile, await buildState(dirs, { host, port, startedAt }));

  const shutdown = async () => {
    await rmIfExists(dirs.stateFile);
    server.close(() => process.exit(0));
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

async function buildState(dirs, { host, port, startedAt }) {
  const active = await readJson(dirs.activeFile, null);
  return {
    app: APP_NAME,
    pid: process.pid,
    host,
    port,
    url: `http://${host}:${port}`,
    markdownLink: `[Open interact GUI](http://${host}:${port})`,
    root: dirs.root,
    activeInteractionId: active?.id || null,
    startedAt,
  };
}

async function readActiveInteraction(dirs) {
  const active = await readJson(dirs.activeFile, null);
  if (!active?.id) return null;
  return readInteraction(dirs, active.id);
}

async function readInteraction(dirs, id) {
  if (!id) return null;
  return readJson(path.join(dirs.prompts, `${id}.json`), null);
}

async function readSchema(args) {
  if (args.schema) {
    return JSON.parse(stripBom(await fsp.readFile(path.resolve(args.schema), "utf8")));
  }
  if (args["schema-json"]) {
    return JSON.parse(stripBom(args["schema-json"]));
  }
  if (args.title || args.message) {
    return {
      title: args.title || "Question",
      description: args.message || "",
      fields: [
        {
          id: "answer",
          type: "textarea",
          label: "Answer",
          required: true,
        },
      ],
    };
  }
  throw new Error("ask requires --schema, --schema-json, or --title");
}

function stripBom(value) {
  return String(value).replace(/^\uFEFF/, "");
}

function normalizeInteraction(schema, args) {
  const id = schema.id || args.id || makeId();
  const fields = Array.isArray(schema.fields) && schema.fields.length > 0
    ? schema.fields.map(normalizeField)
    : [normalizeField({ id: "answer", type: "textarea", label: "Answer", required: true })];

  return {
    id,
    title: String(schema.title || args.title || "Question"),
    description: String(schema.description || schema.message || ""),
    submitLabel: String(schema.submitLabel || "Submit"),
    fields,
    createdAt: schema.createdAt || new Date().toISOString(),
  };
}

function normalizeField(field, index = 0) {
  const type = field.type || "text";
  const normalized = {
    id: String(field.id || `field_${index + 1}`),
    type,
    label: String(field.label || field.id || `Field ${index + 1}`),
    description: field.description ? String(field.description) : "",
    placeholder: field.placeholder ? String(field.placeholder) : "",
    required: Boolean(field.required),
    default: field.default,
    min: field.min,
    max: field.max,
  };

  if (Array.isArray(field.options)) {
    normalized.options = field.options.map((option) => {
      if (typeof option === "string") return { value: option, label: option };
      return {
        value: String(option.value ?? option.label ?? ""),
        label: String(option.label ?? option.value ?? ""),
        description: option.description ? String(option.description) : "",
      };
    });
  }

  return normalized;
}

function validateAnswer(interaction, rawValues) {
  const values = {};
  const errors = [];

  for (const field of interaction.fields) {
    if (field.type === "info") continue;

    const raw = rawValues[field.id];
    const empty = raw === undefined || raw === null || raw === "" || (Array.isArray(raw) && raw.length === 0);
    if (field.required && empty) {
      errors.push({ field: field.id, message: "required" });
      continue;
    }

    if (field.type === "multi-select") {
      const selected = Array.isArray(raw) ? raw.map(String) : empty ? [] : [String(raw)];
      if (field.min !== undefined && selected.length < Number(field.min)) {
        errors.push({ field: field.id, message: `select at least ${field.min}` });
      }
      if (field.max !== undefined && selected.length > Number(field.max)) {
        errors.push({ field: field.id, message: `select at most ${field.max}` });
      }
      values[field.id] = selected;
      continue;
    }

    if (field.type === "boolean") {
      values[field.id] = Boolean(raw);
      continue;
    }

    if (field.type === "number") {
      values[field.id] = empty ? null : Number(raw);
      if (!empty && Number.isNaN(values[field.id])) {
        errors.push({ field: field.id, message: "must be a number" });
      }
      if (!empty && field.min !== undefined && values[field.id] < Number(field.min)) {
        errors.push({ field: field.id, message: `must be at least ${field.min}` });
      }
      if (!empty && field.max !== undefined && values[field.id] > Number(field.max)) {
        errors.push({ field: field.id, message: `must be at most ${field.max}` });
      }
      continue;
    }

    values[field.id] = empty ? "" : String(raw);
  }

  return { values, errors };
}

async function waitForAnswer(state, id, timeoutSeconds) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  while (Date.now() < deadline) {
    const answer = await getJson(`${state.url}/api/interactions/${encodeURIComponent(id)}/answer`);
    if (answer) return answer;
    await sleep(500);
  }
  throw new Error(`Timed out waiting for answer: ${id}`);
}

async function pingState(state) {
  if (!state?.url) return null;
  try {
    const live = await getJson(`${state.url}/api/state`, 1000);
    return live?.app === APP_NAME ? live : null;
  } catch {
    return null;
  }
}

async function findAvailablePort(host, startPort, root) {
  for (let port = startPort; port < startPort + 50; port += 1) {
    const occupiedByInteract = await pingState({ url: `http://${host}:${port}` });
    if (occupiedByInteract) {
      if (sameRoot(occupiedByInteract.root, root)) return port;
      continue;
    }
    if (await canListen(host, port)) return port;
  }
  throw new Error(`No available port found from ${startPort} to ${startPort + 49}`);
}

function sameRoot(left, right) {
  if (!left || !right) return false;
  const leftPath = path.resolve(String(left));
  const rightPath = path.resolve(String(right));
  if (process.platform === "win32") {
    return leftPath.toLowerCase() === rightPath.toLowerCase();
  }
  return leftPath === rightPath;
}

function canListen(host, port) {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once("error", () => resolve(false));
    tester.once("listening", () => tester.close(() => resolve(true)));
    tester.listen(port, host);
  });
}

function getDirs(root) {
  const dir = path.join(root, ".interact");
  return {
    root,
    dir,
    prompts: path.join(dir, "prompts"),
    answers: path.join(dir, "answers"),
    stateFile: path.join(dir, "state.json"),
    activeFile: path.join(dir, "active.json"),
  };
}

async function ensureDirs(dirs) {
  await fsp.mkdir(dirs.prompts, { recursive: true });
  await fsp.mkdir(dirs.answers, { recursive: true });
}

async function readState(dirs) {
  return readJson(dirs.stateFile, null);
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await fsp.readFile(file, "utf8"));
  } catch {
    return fallback;
  }
}

async function writeJson(file, value) {
  await fsp.mkdir(path.dirname(file), { recursive: true });
  await fsp.writeFile(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function rmIfExists(file) {
  try {
    await fsp.rm(file, { force: true });
  } catch {
    // ignore cleanup failures
  }
}

async function getJson(url, timeoutMs = 5000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) return null;
    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) {
        reject(new Error("request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function sendHtml(res, html) {
  res.writeHead(200, {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(html);
}

function sendJson(res, value, status = 200) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(value));
}

function sendText(res, value, status = 200) {
  res.writeHead(status, { "content-type": "text/plain; charset=utf-8" });
  res.end(value);
}

function renderPage(interaction) {
  const boot = safeJson(interaction);
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Interact</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f8;
      color: #20242a;
    }
    body {
      margin: 0;
      min-height: 100vh;
      box-sizing: border-box;
      padding: 24px;
    }
    main {
      width: min(840px, 100%);
      margin: 0 auto;
    }
    header {
      padding: 18px 0 16px;
      border-bottom: 1px solid #d9dee5;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.35;
      font-weight: 760;
    }
    .description {
      margin: 8px 0 0;
      max-width: 72ch;
      color: #52606d;
      line-height: 1.55;
      white-space: pre-wrap;
    }
    form {
      display: grid;
      gap: 18px;
    }
    fieldset, .field {
      border: 1px solid #d9dee5;
      border-radius: 8px;
      background: #ffffff;
      padding: 16px;
      margin: 0;
    }
    legend, label.field-label {
      display: block;
      padding: 0;
      margin-bottom: 8px;
      font-size: 15px;
      font-weight: 720;
      color: #20242a;
    }
    .hint {
      margin: 0 0 12px;
      color: #66717f;
      font-size: 14px;
      line-height: 1.45;
    }
    .options {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }
    .option {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 10px;
      align-items: start;
      min-height: 48px;
      border: 1px solid #c8d0da;
      border-radius: 7px;
      padding: 11px;
      cursor: pointer;
      background: #ffffff;
    }
    .option:has(input:checked) {
      border-color: #14745f;
      background: #e9f6f2;
    }
    .option-title {
      display: block;
      font-weight: 680;
      line-height: 1.35;
    }
    .option-desc {
      display: block;
      margin-top: 3px;
      color: #66717f;
      font-size: 13px;
      line-height: 1.35;
    }
    input[type="text"], input[type="number"], select, textarea {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #c8d0da;
      border-radius: 7px;
      padding: 11px 12px;
      font: inherit;
      color: #20242a;
      background: #ffffff;
    }
    textarea {
      min-height: 120px;
      resize: vertical;
      line-height: 1.5;
    }
    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      min-height: 36px;
    }
    .actions {
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: flex-end;
      padding-bottom: 20px;
    }
    #status {
      flex: 1;
      min-height: 20px;
      color: #52606d;
      font-size: 14px;
    }
    button {
      min-height: 42px;
      min-width: 104px;
      border: 0;
      border-radius: 7px;
      background: #20242a;
      color: #ffffff;
      font: inherit;
      font-weight: 720;
      cursor: pointer;
    }
    .empty {
      border: 1px dashed #b8c2ce;
      border-radius: 8px;
      background: #ffffff;
      padding: 18px;
      color: #52606d;
    }
    @media (max-width: 560px) {
      body { padding: 16px; }
      h1 { font-size: 21px; }
      .options { grid-template-columns: 1fr; }
      .actions { align-items: stretch; flex-direction: column; }
      #status { width: 100%; }
      button { width: 100%; }
    }
  </style>
</head>
<body>
  <main id="app"></main>
  <script>
    const interaction = ${boot};
    const app = document.querySelector("#app");

    if (!interaction) {
      app.innerHTML = '<div class="empty">아직 열린 질문이 없습니다.</div>';
    } else {
      render(interaction);
    }

    function render(data) {
      app.innerHTML = "";
      const header = document.createElement("header");
      const title = document.createElement("h1");
      title.textContent = data.title || "Question";
      header.append(title);
      if (data.description) {
        const description = document.createElement("p");
        description.className = "description";
        description.textContent = data.description;
        header.append(description);
      }

      const form = document.createElement("form");
      form.noValidate = true;
      for (const field of data.fields || []) {
        form.append(renderField(field));
      }

      const actions = document.createElement("div");
      actions.className = "actions";
      const status = document.createElement("div");
      status.id = "status";
      status.setAttribute("role", "status");
      const submit = document.createElement("button");
      submit.type = "submit";
      submit.textContent = data.submitLabel || "Submit";
      actions.append(status, submit);
      form.append(actions);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "Submitting...";
        const response = await fetch("/api/interactions/" + encodeURIComponent(data.id) + "/answer", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ values: collectValues(data.fields || []) })
        });
        const result = await response.json();
        if (!response.ok) {
          status.textContent = (result.errors || []).map((error) => error.field + ": " + error.message).join(", ") || "제출할 수 없습니다.";
          return;
        }
        status.textContent = "제출되었습니다. agent가 이어서 진행할 수 있습니다.";
      });

      app.append(header, form);
    }

    function renderField(field) {
      if (field.type === "single-select" || field.type === "multi-select") {
        const set = document.createElement("fieldset");
        const legend = document.createElement("legend");
        legend.textContent = labelText(field);
        set.append(legend, hint(field));
        const options = document.createElement("div");
        options.className = "options";
        for (const option of field.options || []) {
          const row = document.createElement("label");
          row.className = "option";
          const input = document.createElement("input");
          input.type = field.type === "multi-select" ? "checkbox" : "radio";
          input.name = field.id;
          input.value = option.value;
          const body = document.createElement("span");
          const title = document.createElement("span");
          title.className = "option-title";
          title.textContent = option.label;
          body.append(title);
          if (option.description) {
            const desc = document.createElement("span");
            desc.className = "option-desc";
            desc.textContent = option.description;
            body.append(desc);
          }
          row.append(input, body);
          options.append(row);
        }
        set.append(options);
        return set;
      }

      const wrap = document.createElement("div");
      wrap.className = "field";
      if (field.type === "info") {
        const text = document.createElement("p");
        text.className = "description";
        text.textContent = field.description || field.label || "";
        wrap.append(text);
        return wrap;
      }

      const label = document.createElement("label");
      label.className = "field-label";
      label.setAttribute("for", field.id);
      label.textContent = labelText(field);
      wrap.append(label, hint(field));

      if (field.type === "textarea") {
        const input = document.createElement("textarea");
        input.id = field.id;
        input.name = field.id;
        input.placeholder = field.placeholder || "";
        input.value = field.default || "";
        wrap.append(input);
        return wrap;
      }

      if (field.type === "select") {
        const input = document.createElement("select");
        input.id = field.id;
        input.name = field.id;
        for (const option of field.options || []) {
          const item = document.createElement("option");
          item.value = option.value;
          item.textContent = option.label;
          input.append(item);
        }
        if (field.default !== undefined) input.value = field.default;
        wrap.append(input);
        return wrap;
      }

      if (field.type === "boolean") {
        const row = document.createElement("label");
        row.className = "toggle";
        const input = document.createElement("input");
        input.id = field.id;
        input.name = field.id;
        input.type = "checkbox";
        input.checked = Boolean(field.default);
        const text = document.createElement("span");
        text.textContent = field.placeholder || "Enabled";
        row.append(input, text);
        wrap.append(row);
        return wrap;
      }

      const input = document.createElement("input");
      input.id = field.id;
      input.name = field.id;
      input.type = field.type === "number" ? "number" : "text";
      input.placeholder = field.placeholder || "";
      if (field.type === "number" && field.min !== undefined) input.min = field.min;
      if (field.type === "number" && field.max !== undefined) input.max = field.max;
      if (field.default !== undefined) input.value = field.default;
      wrap.append(input);
      return wrap;
    }

    function hint(field) {
      const value = document.createElement("p");
      value.className = "hint";
      value.textContent = field.description || "";
      return value;
    }

    function labelText(field) {
      return field.label + (field.required ? " *" : "");
    }

    function collectValues(fields) {
      const values = {};
      for (const field of fields) {
        if (field.type === "info") continue;
        if (field.type === "multi-select") {
          values[field.id] = Array.from(document.querySelectorAll('[name="' + cssEscape(field.id) + '"]:checked')).map((item) => item.value);
          continue;
        }
        if (field.type === "single-select") {
          const selected = document.querySelector('[name="' + cssEscape(field.id) + '"]:checked');
          values[field.id] = selected ? selected.value : "";
          continue;
        }
        if (field.type === "boolean") {
          const input = document.querySelector('[name="' + cssEscape(field.id) + '"]');
          values[field.id] = Boolean(input && input.checked);
          continue;
        }
        const input = document.querySelector('[name="' + cssEscape(field.id) + '"]');
        values[field.id] = input ? input.value : "";
      }
      return values;
    }

    function cssEscape(value) {
      return String(value).replace(/["\\\\]/g, "\\\\$&");
    }
  </script>
</body>
</html>`;
}

function safeJson(value) {
  return JSON.stringify(value).replaceAll("<", "\\u003c").replaceAll(">", "\\u003e").replaceAll("&", "\\u0026");
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      index += 1;
    }
  }
  return parsed;
}

function required(value, message) {
  if (!value) throw new Error(message);
  return value;
}

function makeId() {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  return `${stamp}-${Math.random().toString(36).slice(2, 8)}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function printJson(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

function printHelp() {
  process.stdout.write(`Usage:
  node interact-server.js ensure [--port 5199]
  node interact-server.js ask --schema schema.json [--wait] [--timeout 600]
  node interact-server.js ask --schema-json '{"title":"...","fields":[...]}' [--wait]
  node interact-server.js wait --id <interaction-id> [--timeout 600]
  node interact-server.js status
  node interact-server.js stop

Schema fields:
  text, textarea, number, boolean, select, single-select, multi-select, info
`);
}
