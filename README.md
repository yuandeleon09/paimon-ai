# Gemini Free-Tier + Obsidian Smart Memory Multi-Agent System (V4)

A modular, zero-cost, local-first multi-agent system on Windows powered by the Google Gemini free-tier Developer API (`gemini-3.5-flash-lite`), backed by an Obsidian Markdown knowledge vault, an interactive React + Cytoscape clean dashboard, and local file/image reading.

Governed by [`ANTIGRAVITY_V4_FILE_IMAGE_READING_AND_CHAT_ATTACHMENTS.md`](file:///c:/Projects/AiAgents/ANTIGRAVITY_V4_FILE_IMAGE_READING_AND_CHAT_ATTACHMENTS.md), [`ANTIGRAVITY_UI_ONLY_CLEAN_DASHBOARD_AND_KNOWLEDGE_GRAPH.md`](file:///c:/Projects/AiAgents/ANTIGRAVITY_UI_ONLY_CLEAN_DASHBOARD_AND_KNOWLEDGE_GRAPH.md), [`ANTIGRAVITY_V3_MEMORY_HEALTH_AND_MEASURABLE_LEARNING.md`](file:///c:/Projects/AiAgents/ANTIGRAVITY_V3_MEMORY_HEALTH_AND_MEASURABLE_LEARNING.md), and [`ANTIGRAVITY_V2_SMART_MEMORY_AND_TEAM_COLLABORATION.md`](file:///c:/Projects/AiAgents/ANTIGRAVITY_V2_SMART_MEMORY_AND_TEAM_COLLABORATION.md).

---

## Key Features

1. **Multimodal File & Attachment Reading (V4 Core Feature)**
   - **Attach Directly in Chat**: Upload screenshots, images, PDFs, Word documents (`.docx`), Excel spreadsheets (`.xlsx`), PowerPoint slides (`.pptx`), and plain text/code (`.txt`, `.md`, `.py`, `.sql`, etc.).
   - **Gemini Multimodal Analysis**: Single targeted analysis pass across all attached images/PDFs (`Part.from_bytes`), shared concisely with downstream agents without wasting API quota.
   - **Local Document Parsers**: `python-docx`, `openpyxl`, and `python-pptx` parse documents locally without model token cost.
   - **Security & Privacy Defense**: Magic byte signature verification, zip-bomb decompression protection, max 4 files, max 8 MB/file, max 12 MB total media.
   - **Zero Raw Vault Storage**: Files are treated as transient evidence; **no raw uploads or screenshots enter Obsidian**. Only high-value, verified, approved lessons enter long-term memory.

2. **Memory Health Check Engine (V3)**
   - **Read-Only Vault Audit**: Scans for semantic duplicates, policy contradictions, leaked API keys/secrets, oversized notes (>150 words), weak evidence claims, and outdated notes.
   - **Human-in-the-Loop Fixes**: Generates readable diff proposals before changes occur. No notes are deleted silently.
   - **Safety Backups & Full Reversibility**: Automatic versioned backup created in `app_data/versioning/` prior to applying any fix. Rollback via one click or CLI.
   - **Archival & Restoration**: Safely archives obsolete notes out of trusted retrieval, with instant restoration.

3. **Selective Long-Term Learning & Lean Vault**
   - 5-dimension scoring gate (Durability, Reuse, Novelty, Impact, Evidence) requiring $\ge 7/10$.
   - Trivial queries, chit-chat, and intermediate outputs produce **ZERO** new Obsidian notes.
   - Verified candidate lessons require **human approval** in `01_Memory/Pending/` before becoming trusted memory.
   - Diagnostic run logs and chat sessions stored outside the vault in `app_data/state.sqlite`.

4. **Measurable Performance Evaluations (V3)**
   - **10 Deterministic Local Benchmarks**: Instant free checks verifying all memory gates, safety redactions, and team synthesis.
   - **Fair Memory ON vs Memory OFF Trials**: Compares performance on holdout benchmark tasks with memory retrieval vs zero memory, measuring transparent percentage gains.

5. **Team Collaboration (Team Room)**
   - Specialists formulate independent idea cards before seeing peer proposals.
   - Deterministic correlation maps relationships (`supports`, `complements`, `depends_on`, `contradicts`, `unrelated`).
   - Unified `TeamIdea` synthesizes contributor proposals while transparently surfacing active contradictions.

6. **Gemini Free-Tier Quota Protection**
   - Single API key for all 7 specialist agents (`gemini-3.5-flash-lite`).
   - Minimal agent routing (calls only the agents needed for the task).
   - Strict caps: `MAX_MODEL_CALLS_PER_TASK=8`, `MAX_REVISIONS=1`.

---

## Quick Start Guide (Windows)

### 1. Launch the Modern Clean Dashboard & Knowledge Graph (React + Cytoscape)
Launch the unified web dashboard with interactive Cytoscape knowledge graph and real-time multi-agent activity:

**Via PowerShell:**
```powershell
.\scripts\start_ui.ps1
```

**Via Windows Explorer:**
Double-click [`scripts\start_ui.bat`](file:///c:/Projects/AiAgents/scripts/start_ui.bat).

The clean dashboard opens in your browser at:
👉 **`http://127.0.0.1:8000`**

*(For live frontend development: `.\.venv\Scripts\python.exe server.py` in one terminal, and `cd frontend; npm run dev` in another for `http://localhost:5173`)*

---

### 2. Launch the Streamlit Dashboard (Alternative)
You can also launch the classic Streamlit interface:

**Via PowerShell:**
```powershell
.\scripts\start_windows.ps1
```

**Via Windows Explorer:**
Double-click [`scripts\start_windows.bat`](file:///c:/Projects/AiAgents/scripts/start_windows.bat).

The dashboard opens in your browser at:
👉 **`http://localhost:8501`**

---

### 2. Streamlit Dashboard Tabs

1. **💬 Chat & Task Workspace**: Select project scope, toggle Team Collaboration, and chat with the 7-agent team.
2. **📚 Memory Center**: Review pending candidate lessons, inspect approved memory notes, review conflicts, and archive/restore notes.
3. **🩺 Memory Health**: Run read-only health audits, inspect risk-ranked findings with diff previews, approve fixes, or rollback backups.
4. **🤝 Team Room**: Inspect specialist idea cards, relationship links, and synthesized Team Ideas.
5. **📈 Improvement & Evaluations**: Run the 10-case local benchmark suite or the Memory ON vs Memory OFF trial.

---

### 3. Command Line Interface (CLI)

```powershell
# Run a task
.\.venv\Scripts\python.exe main.py run "Write an idempotent payment callback"

# Run the Memory Health Check audit
.\.venv\Scripts\python.exe main.py health-check

# Apply an approved health fix (with automated safety rollback backup)
.\.venv\Scripts\python.exe main.py health-check --fix FIND-001

# Restore from a safety backup
.\.venv\Scripts\python.exe main.py health-check --restore-backup backup_FIND-001_20261029_173000

# Run local deterministic benchmarks
.\.venv\Scripts\python.exe main.py evaluate

# Run fair Memory ON vs OFF comparative experiment
.\.venv\Scripts\python.exe main.py evaluate --on-off

# Approve a pending lesson into trusted memory
.\.venv\Scripts\python.exe main.py approve <lesson_id>

# Reject a pending lesson
.\.venv\Scripts\python.exe main.py reject <lesson_id> "Outdated approach"

# Archive an approved lesson
.\.venv\Scripts\python.exe main.py archive <lesson_id> --reason "Superseded"

# Restore an archived lesson back to approved
.\.venv\Scripts\python.exe main.py restore <lesson_id>

# Check system status
.\.venv\Scripts\python.exe main.py status
```

---

## Automated Acceptance Testing
Run the complete automated test suite covering AT-01 through AT-35:
```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v
```
*(All 31 automated tests pass with a 100% success rate)*
