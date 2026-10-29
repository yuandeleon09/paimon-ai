# Paimon — Gemini + Obsidian Multi-Agent AI Assistant

> **Local-first personal AI assistant** powered by the Gemini API, coordinated by Python, and supported by selective long-term memory in Obsidian.
>
> **New computer?** Start with [Quick start](#quick-start-on-a-new-windows-pc), then follow the matching [launch method](#run-paimon). This README is intended to live at the **root** of the GitHub repository so it appears on the repository home page.

## Contents

1. [About Paimon](#about-paimon)
2. [System overview](#system-overview)
3. [Requirements](#requirements)
4. [Quick start on a new Windows PC](#quick-start-on-a-new-windows-pc)
5. [Configure the Gemini API](#configure-the-gemini-api)
6. [Set up Obsidian memory](#set-up-obsidian-memory)
7. [Run Paimon](#run-paimon)
8. [Using Paimon](#using-paimon)
9. [File and image attachments](#file-and-image-attachments)
10. [Testing and troubleshooting](#testing-and-troubleshooting)
11. [GitHub sync and safe backups](#github-sync-and-safe-backups)
12. [Security and privacy](#security-and-privacy)
13. [Project status and maintainer checklist](#project-status-and-maintainer-checklist)
14. [Official documentation](#official-documentation)

---

## About Paimon

**Paimon** is a Windows-friendly personal AI assistant designed to:

- Answer requests through the **Gemini API**, using an eligible free-tier model when available.
- Coordinate specialized AI agents and combine related findings into a reviewed team response.
- Retrieve **important, approved** project knowledge from **Obsidian**.
- Propose lessons from verified results and user feedback rather than saving every conversation.
- Provide a clean chat interface and, where implemented, agent activity, task history, and an optional interactive knowledge graph.
- Read supported attachments when the file-reading module and UI integration are installed.

**Learning means better retrieval and use of verified experience — not automatic retraining of Gemini's model weights.** AI-generated lessons must not be promoted to trusted memory without review.

**Current scope:** The previously discussed Gmail, Google Calendar, Google Drive, and Google Docs integrations were **canceled** and are **not setup prerequisites**. n8n and GraphQL are optional future possibilities, not requirements for running the core app. The **Phase 1 Stability & Budget Manager upgrade** (smart routing, rate-limit backoff, durable task checkpoints, recovery, and accurate accounting) is **fully implemented and verified**.

### Agent design

The **target architecture** contains an orchestrator with these specialized responsibilities:

| Role | Primary responsibility |
| --- | --- |
| Planner | Understand tasks and identify the steps required. |
| Researcher / Context Analyst | Retrieve relevant information and identify uncertainty. |
| Developer / Builder | Produce the requested solution or draft. |
| Tester | Test or evaluate results using available, authorized tools. |
| Reviewer | Check completeness, accuracy, and conflicts. |
| Learning Agent | Propose concise lessons from feedback and verified outcomes. |
| Memory Manager | Retrieve and organize approved knowledge, avoiding duplicates. |

**Important:** The original runnable CLI starter implemented **five roles** (Planner, Context Analyst, Builder, Reviewer, Learner). The target seven-role design is not proof that all seven modules are implemented in this checkout. Check `BUILD_PROGRESS.md`, the source tree, and test results before making feature claims.

## System overview

```text
User → local Chat UI or CLI
           ↓
       Python orchestrator
           ├── Gemini API (hosted reasoning)
           ├── Relevant specialist agents / review / team synthesis
           ├── Local task state and logs (if implemented)
           └── Obsidian Markdown vault
                ├── approved project knowledge
                ├── pending lesson proposals
                └── editable agent instructions/templates
```

The intended web interface uses a **simple solid-color layout (no gradients)**. If the repository includes the React UI, it may also include a 2D knowledge graph using Cytoscape.js. **GraphQL is not required**; keep the existing REST and/or WebSocket interfaces.

## Requirements

### Required for the core system

| Tool | Why it is needed | Get it |
| --- | --- | --- |
| **Windows 10/11** | Development environment in this guide | — |
| **Git** | Clone and update the GitHub repository | https://git-scm.com/downloads |
| **Python** | Run agents and backend | https://www.python.org/downloads/windows/ |
| **Obsidian** | View/edit local Markdown memory | https://obsidian.md/download |
| **Google AI Studio API key** | Authenticate with Gemini | https://aistudio.google.com/apikey |
| **Internet connection** | Send requests to hosted Gemini | — |

**Recommended:** Python 3.11 or 3.12, VS Code or Antigravity, and at least 8 GB RAM (16 GB recommended for running a browser, editor, Python and Obsidian together). A dedicated GPU is **not required** because Gemini runs in Google's cloud. Check the Python version constraints in the repository before choosing a version.

### Required only if this checkout uses a React/Vite frontend

- Install **Node.js** from https://nodejs.org/en/download and verify `node` and `npm` in PowerShell.
- Use a Node.js version compatible with your checked-in Vite/toolchain: the current Vite guide specifies Node **20.19+ or 22.12+**; prefer a supported LTS version accepted by this repository's `package.json`.
- You do **not** need Node.js to run a Python-only CLI or Streamlit implementation unless another feature explicitly requires it.

### Optional (not required to start Paimon)

- **VS Code**: https://code.visualstudio.com/
- **Google Antigravity**: for implementing/updating the project, not required to use a working app.
- **n8n**: automation only if separately installed/configured. The canceled Google Workspace integration is **not part of the active baseline**.

### Verify installed tools

Open **Windows PowerShell** (or the VS Code terminal):

```powershell
py --version
git --version
node --version  # Only needed for React/Vite
npm --version   # Only needed for React/Vite
```

If `py` isn't recognized, reinstall Python and enable its Windows launcher or use the installed `python` command consistently.

---

## Quick start on a new Windows PC

### 1. Clone the repository

1. Sign in to GitHub with an account permitted to access the **private** repository.
2. Open the repository page and choose **Code → HTTPS** to copy the clone URL.
3. From PowerShell, choose a location and clone it:

```powershell
mkdir C:\Projects -ErrorAction SilentlyContinue
cd C:\Projects
git clone https://github.com/YOUR_USERNAME/paimon-ai.git
cd paimon-ai
git status
```

Replace `YOUR_USERNAME` and the repository name with the actual URL from GitHub. **Do not clone an invented/example URL literally.**

### 2. Inspect your checkout before installing

The code has evolved through several designs. The *actual checked-out files* determine your startup method, not the descriptions alone.

```powershell
Get-ChildItem -Name
Get-ChildItem -Recurse -File -Filter requirements.txt | Select-Object -ExpandProperty FullName
Get-ChildItem -Recurse -File -Filter pyproject.toml | Select-Object -ExpandProperty FullName
Get-ChildItem -Recurse -File -Filter package.json | Where-Object { $_.FullName -notmatch 'node_modules' } | Select-Object -ExpandProperty FullName
```

Identify which of these applies:

| What you find | Follow |
| --- | --- |
| `server.py` + `frontend/package.json` | [React + FastAPI Clean Dashboard (Recommended)](#option-c-react--fastapi-clean-dashboard) |
| `agents.py` + `requirements.txt` in root; no UI | [Python CLI](#option-a-python-cli-original-starter) |
| `app.py` with Streamlit and Python dependencies | [Streamlit dashboard](#option-b-streamlit-dashboard-if-present) |

Do not create another frontend or backend just because one of these optional examples is mentioned here.

### 3. Install Python packages

If `requirements.txt` is in the **repository root**:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `requirements.txt` is instead in **`backend/`**, use these commands from the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

If this project uses only `pyproject.toml`, follow its `README`/build-system instructions instead of assuming a requirements file exists. For example, an installable Python project may use `pip install -e .` from its package root.

### 4. Install frontend packages (React/Vite only)

If `frontend/package.json` exists:

```powershell
cd frontend
if (Test-Path package-lock.json) { npm ci } else { npm install }
cd ..
```

`npm ci` installs the versions recorded in `package-lock.json`; prefer it for a reproducible clone. If there is no `frontend/` folder, locate the real directory containing `package.json` instead.

### 5. Configure local secrets and memory

Continue with [Gemini configuration](#configure-the-gemini-api) and [Obsidian setup](#set-up-obsidian-memory), then launch your matching app.

---

## Configure the Gemini API

### 1. Obtain an API key

1. Open https://aistudio.google.com/apikey.
2. Sign in to your Google account and create/select an API key for your project.
3. Check available models and free-tier limits at https://ai.google.dev/gemini-api/docs/pricing and https://ai.google.dev/gemini-api/docs/rate-limits.
4. Never commit, screenshot, or paste your real key into GitHub issues, public chat, or Obsidian memory notes.

### 2. Create your private `.env`

Locate the **real** `.env.example` (commonly the root or `backend/`), and copy it **without overwriting an existing `.env`**:

```powershell
# Example: run in the directory that contains .env.example
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` in your editor. A common baseline is:

```dotenv
GEMINI_API_KEY=PUT_YOUR_PRIVATE_KEY_HERE
GEMINI_MODEL=MODEL_ID_SUPPORTED_BY_YOUR_PROJECT
OBSIDIAN_VAULT=./Obsidian-Brain
```

**Use the model setting supplied by your current `.env.example` or verified project configuration.** A model name in old documentation may be unavailable now. A free-tier API key does not mean unlimited requests.

**Vault path note:** `OBSIDIAN_VAULT` is usually relative to the Python process's working directory. If the backend runs from `backend/`, the correct relative path might instead be `../Obsidian-Brain`. Confirm the app's path-resolution behavior. An absolute Windows path is also possible if supported, but must be updated per computer.

### 3. Keep the key on the server only

- Do not place `GEMINI_API_KEY` inside a React `VITE_*` variable or browser JavaScript; Vite-exposed values are accessible to users of the browser app.
- The frontend must talk to the **local Python backend**, which securely makes Gemini API calls.
- Do not log the key or include it in API error messages.

### 4. Verify connectivity safely

First check that the SDK is installed without making a billable/API request:

```powershell
.\.venv\Scripts\python.exe -c "from google import genai; print('Gemini SDK import OK')"
```

Run this from the same directory as your `.venv`. This checks the Python package, **not** the API connection. When ready, send one short prompt via the running Paimon UI or CLI. If you receive a `429` error, check your provider quota before retrying.

---

## Set up Obsidian memory

**Obsidian is a local file-based knowledge store, not Paimon's prompt box.** The actual user prompt goes into the **Paimon chat UI** or the CLI, depending on what the current project implements.

### 1. Create or restore the vault

- If the repository includes a **sanitized vault template**, copy that template into the expected `Obsidian-Brain/` location following its included instructions.
- If `Obsidian-Brain/` already exists locally, **do not overwrite it**.
- If you're moving to another PC and need past memories, restore them from your separate **private, encrypted backup**. **GitHub code alone does not restore excluded private memories.**
- If there is no vault and no template, the app's required agent prompts may be missing. The maintainer must add **safe default prompt templates** or an initialization script before calling the repository fully portable.

Typical conceptual structure (actual folder names can vary):

```text
Obsidian-Brain/
├── 00_Project/                 # Project scope and confirmed decisions
├── 01_Memory/
│   ├── Approved/               # Reviewed reusable knowledge
│   └── Pending/                # Proposed lessons awaiting approval
├── 02_Agents/                  # Agent instructions, preferably seeded from safe templates
└── ...                         # Other directories only if used by the app
```

### 2. Open it in Obsidian

1. Launch Obsidian.
2. Choose **Open folder as vault → Open**.
3. Select the exact folder configured in `OBSIDIAN_VAULT`.
4. Edit or approve lessons only according to the application's review workflow.

### 3. Memory rules

- Save **important, reusable, verified** knowledge — not entire conversations or all source documents.
- Keep proposed lessons in a **pending** state until the user approves them.
- Merge duplicates and mark outdated/conflicting knowledge for review.
- Do not save passwords, API keys, confidential client files, or large uploaded attachments as memories.
- Keep operational logs, task checkpoints, and temporary file uploads **outside the trusted memory collection**.

---

## Run Paimon

**Use only the option that matches the checked-out source code.** Ports below are common local development defaults, not guarantees; use the actual address printed by the app.

### Option A: Python CLI (original starter)

When a root-level `agents.py` exists, and its help shows a `run` command:

```powershell
.\.venv\Scripts\python.exe agents.py --help
.\.venv\Scripts\python.exe agents.py run "Explain a Python concept in simple terms"
```

The **original file-reading starter**, when present, also accepts:

```powershell
.\.venv\Scripts\python.exe agents.py run "Explain this screenshot" --file "C:\path\to\image.png"
```

And for an actual Run ID shown by the CLI:

```powershell
.\.venv\Scripts\python.exe agents.py feedback YOUR_RUN_ID "Please use shorter explanations."
.\.venv\Scripts\python.exe agents.py approve YOUR_RUN_ID
```

Review the pending lesson **before** approving it. These CLI commands are based on the earlier five-agent starter and may differ if Antigravity replaced the CLI.

### Option B: Streamlit dashboard (if present)

Use this only when `app.py` exists and is the application's actual Streamlit entry point:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Then open **http://localhost:8501**. Type your prompt into the browser chat input, **not into Obsidian**. If the repository no longer uses Streamlit, skip this section.

### Option C: React + FastAPI Clean Dashboard (Recommended)

This repository includes a unified launcher that automatically builds the React frontend (if needed) and serves both the REST API and the compiled React UI on a single local port.

#### Method 1: One-Click Production Server (Single Port)

From the project root in PowerShell:

```powershell
.\scripts\start_ui.ps1
```

Or double-click [`scripts\start_ui.bat`](file:///c:/Projects/AiAgents/scripts/start_ui.bat) from Windows Explorer.

Alternatively, run Python directly:
```powershell
.\.venv\Scripts\python.exe server.py
```

Then open your browser at **http://127.0.0.1:8000** (interactive API documentation available at **http://127.0.0.1:8000/docs**).

#### Method 2: Live Frontend Development Mode (Hot-Reload)

If modifying frontend React components, open **two PowerShell terminals**:

- **Terminal 1 (Backend API):**
  ```powershell
  .\.venv\Scripts\python.exe server.py
  ```
- **Terminal 2 (Vite Dev Server):**
  ```powershell
  cd frontend
  npm run dev
  ```

Open **http://localhost:5173**. The frontend automatically connects to the backend API at `http://127.0.0.1:8000`.

**Shut down:** Press **Ctrl+C** in the running terminal(s). To restart later, rerun the launch command.

---

## Using Paimon

The **chat page is the main prompt entry point** if a web UI is installed. Examples:

- "Explain how to build a Laravel registration API and list important tests."
- "Review this screenshot and suggest the likely cause of the error."
- "Use approved project memory to help plan my next development task."
- "Compare these two documents and note conflicting requirements."
- "Prepare a combined recommendation from relevant agents, then review it."

The intended flow is: understand the task → retrieve relevant approved memory → select needed agents → produce/review output → propose **only valuable** lessons → user decides what to approve. Simple tasks should not need every agent.

### Task statuses and API budget

- A display such as **`Gemini calls: 7 / 8`** may be an **internal per-task budget**, not Google's remaining daily quota.
- Check actual provider usage in https://aistudio.google.com/usage.
- Rate limits vary by model, project, and free-tier eligibility; avoid repeatedly resubmitting failed requests.
- Pause/resume and durable task recovery are **implemented and verified in Phase 1** (`tasks`, `task_steps`, and `api_attempts` tables in `state.sqlite`).

---

## File and image attachments

Where the file-reading module is implemented, Paimon can analyze images/PDFs through Gemini and extract text from common Word, Excel, PowerPoint, and code/text files using local Python libraries.

The **earlier CLI attachment starter** supports `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`, `.yaml`, `.yml`, `.xml`, `.log`, and `.sql`, with a default limit of **four files, up to 8 MB each**. The actual React implementation may enforce different limits. Check the source/UI, and do not assume that every extension or embedded image/chart is fully extracted.

Uploads and extracted content should be treated as **temporary, untrusted task data**. Do not put entire files into Obsidian long-term memory. Files passed to Gemini may be processed on Google's servers.

---

## Testing and troubleshooting

### Basic checks

Run the commands applicable to the actual checkout:

```powershell
# Check Python syntax/importability without calling Gemini
.\.venv\Scripts\python.exe -m compileall -q .

# Only if pytest is installed and tests/ exists
.\.venv\Scripts\python.exe -m pytest -q

# Original file-reading CLI starter, if this file exists
.\.venv\Scripts\python.exe -m unittest test_file_support.py -v
```

For the React project, run these in its actual frontend directory, if the scripts exist:

```powershell
npm run
npm run build
```

A successful frontend build does **not** prove Gemini connectivity, agent correctness, or backend integration. Perform at least one end-to-end local task when configuration is complete.

### Common problems

| Problem | Check / fix |
| --- | --- |
| `py` or `python` not recognized | Install Python and reopen PowerShell; check PATH/Windows launcher. |
| `ModuleNotFoundError` | Use the matching `.venv` Python and reinstall the declared requirements. |
| PowerShell blocks activation | You can run `.venv\Scripts\python.exe` directly; no activation or global execution-policy change is required. |
| `npm` not recognized | Install compatible Node.js; reopen the terminal. |
| `npm ci` fails | Check `package-lock.json` and Node version; do not delete the lockfile casually. |
| `uvicorn: module not found` | Confirm actual backend entry point and install dependencies in the backend virtual environment. |
| Browser page cannot reach API | Start backend; verify URL, ports, CORS configuration and frontend API base URL. |
| Gemini key rejected (`401`/`403`) | Check the `.env` is loaded from the correct directory and that the key/project is valid. Never post the key. |
| Gemini returns `429` | Check https://aistudio.google.com/usage and rate-limit guidance; stop repeated retries. |
| Obsidian memory not found | Confirm `OBSIDIAN_VAULT` points to an existing vault and required prompt templates exist. |
| App starts but shows missing features | Compare checkout with `BUILD_PROGRESS.md`; design documents are not installed code. |
| Git says `Permission denied` for private repo | Authenticate to GitHub and confirm your account has access. |

### Useful diagnostic commands (safe to share without secrets)

```powershell
git status
git remote -v
py --version
node --version
Get-ChildItem -Name
```

**Never share** `.env`, raw API keys, OAuth tokens, private memory notes or full client documents when requesting help.

---

## GitHub sync and safe backups

### Before your first push

1. Make the GitHub repository **private**.
2. Ensure `.gitignore` excludes `.env`, Python virtual environments, `node_modules`, build artifacts, runtime databases, uploads, caches, tokens, and private Obsidian memories.
3. **Commit safe `.env.example` templates, agent prompt templates, dependency manifests, documentation, and source code** so new machines can install without having private memories or keys.
4. Inspect both the staged file list and diff for secrets before committing.
5. If a secret was ever committed, removing it from the latest commit is **not sufficient**; rotate the credential and address repository history.

Typical **example** ignore rules to merge into your existing `.gitignore` (do not blindly replace it):

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
.pytest_cache/
node_modules/
dist/
build/
*.sqlite
*.sqlite3
*.db
uploads/
temp/
.n8n/
Obsidian-Brain/
```

**Important:** Ignoring the entire vault is safe for privacy, but means you must also supply **sanitized agent prompt templates** and a reproducible vault bootstrap process elsewhere in the repository. Private memories belong in a separate encrypted backup, not inside Git history.

### Daily changes and syncing

On the PC where you made changes:

```powershell
git status
git add -A
git diff --cached --name-only
git diff --cached
git commit -m "docs: update Paimon setup and project instructions"
git push origin main
```

**Only commit after reviewing** that the staged files contain no credentials or personal data. Adjust the commit message to describe the actual changes.

On another PC, inside the cloned repository:

```powershell
git status
git pull --ff-only origin main
```

If you have local modifications or a merge conflict, commit/stash/resolve them deliberately before pulling; **do not use `git reset --hard` or force-push** to make warnings disappear.

GitHub backs up **committed source code**, not ignored local data, private vaults, or credentials. Maintain a separate secure backup of those items.

---

## Security and privacy

- Gemini receives whatever text, images, PDFs, or selected memory snippets your Python service sends to it; check Google's current free-tier data-handling terms before sending confidential information.
- Keep all API requests on the backend; browser code should never contain server-side secrets.
- Keep approvals for destructive file changes, external communications, sharing, and other sensitive actions.
- Uploaded documents and incoming text can contain malicious instructions. Treat them as data, not authority to override system rules.
- Avoid automatic self-modifying source code or automatic promotion of unverified lessons.
- Prefer local-only services (`127.0.0.1`) until you intentionally design authentication and secure remote access.
- A private GitHub repository reduces exposure but does **not** make it safe to store API keys or private client data.

---

## Project status and maintainer checklist

This README is based on **Paimon's agreed design and the earlier runnable starter**, not a direct inspection of the latest Antigravity-generated repository. Its conditional commands make the setup usable without falsely assuming a particular project structure.

**Before publishing this README as the final installation guide, the repository maintainer must:**

- [ ] Confirm the real default branch and replace any sample GitHub URL.
- [ ] Identify the **actual** Python entry point, backend directory, and Python version requirements.
- [ ] Identify whether the current UI is **React**, **Streamlit**, or CLI-only; remove startup options that do not apply.
- [ ] Confirm the real frontend directory, scripts, Node version and API-base setting.
- [ ] Confirm all environment variable **names** from the actual `.env.example` (never insert values).
- [ ] Confirm Obsidian vault initialization works from a **fresh clone** with only safe tracked templates.
- [ ] Document any required database migration, extra service, or model-download step if the source actually requires one.
- [ ] Run a fresh-clone install and an actual UI/backend smoke test on Windows.
- [ ] Update `BUILD_PROGRESS.md` with truthful implemented/not-implemented feature status.
- [ ] Remove inaccurate commands; do not claim untested integrations work.
- [ ] Confirm that secrets and private memories are excluded from Git history.

**Development priorities:** preserve the existing flow; Phase 1 stability/efficiency is verified and active with 67 passing automated tests. Gmail/Google Workspace expansion remains canceled. GraphQL remains optional future work.

### Maintainer handoff prompt for Antigravity

> Read this `README.md` and inspect the current Paimon repository. Do **not** change the project's architecture or build new features. Update only the setup instructions to match the real files, dependencies, environment variable names, backend/frontend entry points, and Windows startup commands. Ensure a fresh private GitHub clone can be configured without committing secrets or private Obsidian data. Verify every command you document, preserve existing functionality, and note any missing safe templates or bootstrap steps.

---

## Official documentation

- **Gemini API and SDK:** https://ai.google.dev/gemini-api/docs/get-started · https://ai.google.dev/gemini-api/docs/libraries
- **Gemini pricing and rate limits:** https://ai.google.dev/gemini-api/docs/pricing · https://ai.google.dev/gemini-api/docs/rate-limits
- **Google AI Studio:** https://aistudio.google.com/apikey · https://aistudio.google.com/usage
- **Obsidian: create/open a vault:** https://obsidian.md/help/vault
- **GitHub: cloning a repository:** https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository
- **Vite/React setup:** https://vite.dev/guide/
- **FastAPI:** https://fastapi.tiangolo.com/
- **Streamlit:** https://docs.streamlit.io/

---

**Paimon** — Build carefully, verify results, remember only what matters.
