# ANTIGRAVITY — UI-ONLY BUILD SPECIFICATION
## Clean Multi-Agent Dashboard + Interactive Knowledge Graph (No Gradients)

**Project:** Gemini Free-Tier + Python Multi-Agent AI + Obsidian Memory + Optional n8n Automations  
**Document type:** Standalone, copy-paste-ready instructions for Google Antigravity or another coding assistant  
**Scope:** **USER INTERFACE ONLY** — no agent logic, memory policy, automation workflows, Gemini calls, or backend redesign  
**Platform:** Local Windows 10/11, browser-based application  
**Target UI:** React + TypeScript, preferably Vite; Cytoscape.js for the interactive 2D relationship graph  
**Date:** October 29, 2026  
**Design direction:** Clean, quiet, professional, well-spaced, functional, dark-first. **Absolutely no gradients.**

---

## 1. READ THIS FIRST — INSTRUCTIONS TO ANTIGRAVITY

You are acting as the **frontend/UI implementation engineer** for an EXISTING Gemini + Obsidian multi-agent project. **Build the actual UI**, not merely a design description or static screenshot.

1. **Inspect the workspace before coding.** Determine what frontend already exists (React, Streamlit, HTML, etc.), its existing routes, FastAPI endpoints, WebSockets, and authentication/configuration. Reuse the existing application where practical; avoid creating two competing dashboards.
2. This document overrides earlier project instructions **only on UI layout, look, frontend interactions, and frontend integration**. V2/V3 agent collaboration, selective memory, learning, and approval rules remain unchanged.
3. **Do not rewrite the Python orchestrator, agent prompts, Gemini provider, Obsidian file structures, memory ranking algorithms, or n8n workflows.** Backend changes, if absolutely required to display already-existing data, must be minimal, additive, backward-compatible, and clearly identified before making them.
4. Do not replace, clear, or migrate existing user data. Do not modify `.env` secrets. Preserve current CLI commands and working endpoints.
5. **No gradient colors anywhere.** No `linear-gradient`, `radial-gradient`, blurred colorful blobs, glassmorphism, neon glow, luminous shadows, or heavy animation. Prioritize alignment, readable typography, borders, spacing, hierarchy, and solid-color surfaces.
6. Make **every visible control functional**. A UI element without an implemented or supported action must be visibly disabled with an explanation, or omitted. Never fake live AI activity, memory approvals, automation execution, or task success.
7. Use **actual API responses where available**. If the backend feature is not implemented, show a clear empty/unsupported state and optionally a **clearly labeled development-only mock** (off by default). Do not invent task history or connections for production mode.
8. Implement incrementally, run local build and interaction checks, and update `BUILD_PROGRESS.md` with what actually works, what is blocked by missing backend APIs, and the launch commands.
9. **Do not implement GraphQL now.** Use the current REST API and WebSocket/streaming if already available. Keep frontend API calls inside a small service layer so GraphQL can be adopted later if truly needed.
10. This specification is **self-contained**: implement from it even if the earlier project Markdown files or the original screenshot are not attached.

**Exact implementation request:** Build a simple, beautiful, usable multi-agent control dashboard with a prominent chat interface, real agent activity when available, a dedicated interactive knowledge graph, a selective-memory review interface, and a basic automation overview. Keep the existing AI functionality intact; focus on improving how the user interacts with it.

---

## 2. VISUAL TARGET AND PRINCIPLES

### Overall feel

The reference image showed a dark interactive network of connected nodes. Preserve the **idea of linked agents, tasks, memories, and related ideas**, but **do NOT copy its bright neon/glowing style**. Our version should look like a polished productivity application: calm, uncluttered, compact but comfortably spaced.

### Non-negotiable visual rules

- **Zero gradients** (including page backgrounds, headers, buttons, node fills, and charts).
- Use **flat solid colors**, clean 1px borders, modest corner radii, subtle *neutral* shadows only if needed.
- No decorative pictures, animated star backgrounds, fake glass panels, or unnecessary visual effects.
- No giant cards full of statistics. The main UI is **task-first**, not analytics-first.
- Use one consistent icon family (e.g. Lucide) and one system-safe sans-serif font stack.
- Use text labels alongside important icons; tooltips are not a substitute for clear labels.
- Emphasize quality of **spacing, alignment, contrast, and information hierarchy** over visual effects.
- Use responsive layouts and keyboard-accessible controls.

### Suggested dark-theme design tokens (adjust as needed for contrast)

| Token | Solid color | Intended use |
|---|---|---|
| `--bg` | `#0D1420` | Main app background |
| `--sidebar` | `#111B29` | Left navigation |
| `--surface` | `#172333` | Cards and panels |
| `--surface-hover` | `#1F2D40` | Hover and selected surfaces |
| `--border` | `#304054` | Thin separators and outlines |
| `--text` | `#F1F5F9` | Primary text |
| `--muted` | `#A8B5C6` | Secondary text |
| `--primary` | `#6EA8F7` | Active selections and primary action |
| `--success` | `#48BFA1` | Verified success states |
| `--warning` | `#E6B85C` | Pending approval/warning |
| `--error` | `#E47B81` | Errors and destructive prompts |

Use these as design starting values, not an excuse to compromise accessible contrast. Primary buttons can use solid `--primary` with a suitably dark text color. Node types should be distinguishable with **text, shapes, or icons**, not color alone.

### Typography and spacing

- Font: `Inter` if already installed, otherwise `system-ui, Segoe UI, sans-serif`; do not require downloading paid fonts.
- Base size: **14–16px**; ordinary body 15px, supporting metadata 12–13px.
- Heading scale: page title 22–24px; section title 16–18px; card title 14–16px.
- Spacing system: 4 / 8 / 12 / 16 / 24 / 32px.
- Default panel padding: 16–20px. Content page padding: 24px desktop, 16px mobile.
- Border radii: 8–12px, consistent; avoid exaggerated pill-shaped cards everywhere.
- Keep text measure comfortable, especially in chat messages.

---

## 3. INFORMATION ARCHITECTURE — KEEP IT SIMPLE

### Main navigation (six entries maximum)

1. **Chat** — Default landing screen; type prompts and view answers.
2. **Agents** — View agents, task progress, and the combined Team Idea.
3. **Knowledge Graph** — Explore actual related nodes/edges interactively.
4. **Memory** — View approved lessons, pending suggestions, and memory health information.
5. **Automations** — View available automation workflows, status, and approvals if integrated.
6. **Settings** — Theme and connection/status configuration already supported by the backend.

A compact logo/app name and current project context belong at the top of the sidebar. Bottom of sidebar: API/backend connection status and a Settings link. Avoid adding unnecessary pages such as Marketplace, Revenue, Admin, or social feeds.

### Desktop shell

- **Left sidebar:** fixed ~220–240px width; collapsible to an icon bar.
- **Top bar:** ~56–64px; current page title / current project, small backend connection badge, and optional settings button.
- **Main content:** flexible available width, max-width only when useful (e.g. chat).
- **Right contextual panel:** ~300–340px only on Chat or selected graph inspector, and collapsible. Do **not** permanently use three columns on every page.

### Proposed desktop Chat layout

```text
+----------------------+--------------------------------------------------+----------------------------+
| App name / project   | Chat                                  Connection | Activity                   |
|----------------------|--------------------------------------------------|----------------------------|
| Chat             [*] |                                                  | Current task               |
| Agents               |  Conversation / final answer                     | - Planner: complete        |
| Knowledge Graph      |                                                  | - Developer: working       |
| Memory               |  Messages, referenced lessons, action summaries  | - Reviewer: queued         |
| Automations          |                                                  |                            |
|                      |                                                  | Team Idea (if available)   |
|                      |                                                  |                            |
|                      |--------------------------------------------------|----------------------------|
| Settings             |  Ask your AI team...                      [Send] |  [Hide activity]           |
+----------------------+--------------------------------------------------+----------------------------+
```

The chat composer **must stay visible** at the bottom of the conversation region (sticky within the content, not overlaying text). On small screens, the activity panel becomes a tab/drawer.

### Other responsive breakpoints

- **>=1200px:** left nav + primary content + optional right context panel.
- **768–1199px:** collapsible left nav; activity panel collapsed by default.
- **<768px:** drawer/hamburger nav; main content one column; graph details in bottom sheet or side drawer; chat composer full width.
- Avoid horizontal scrolling on normal pages. The graph canvas itself supports pan/zoom.

---

## 4. SCREEN SPECIFICATIONS

### 4.1 Chat — MAIN INTERFACE (highest priority)

**Must show:**

- Conversation thread with clear distinction between user messages and final agent responses.
- Multi-line input textarea with placeholder `Ask your AI team...`.
- Send button; `Enter` sends, `Shift+Enter` creates a new line (or provide an accessible option).
- Loading and cancel/stop controls **only if supported by the backend**.
- Clear status during requests: `Queued`, `Working`, `Completed`, `Failed`, or `Connection unavailable` from actual task state.
- Optional short agent activity timeline beside chat, using factual state updates when available.
- A compact `Team Idea` summary when the backend has produced one; do not display long private reasoning chains.
- Context/source chips for **actually used** memories (title and open-memory action); do not show invented citations.
- Human-readable API failure messages, retry action when safe, and clear empty state.

**Important UX behavior:**

- Submitting sends **exactly one** request, avoiding duplicate clicks and Enter races.
- Show submitted prompt immediately as pending; replace its status with real server feedback.
- Persist messages across navigation only if the app already stores them; otherwise clearly explain that the current chat is local/session-only.
- If chat execution is not connected yet, show `Chat backend not connected` and configuration instructions. Never fabricate a completed response.
- Use ordinary Markdown rendering for assistant text if supported; escape untrusted HTML and avoid unsafe rendering.

### 4.2 Agents — TEAM STATUS AND COLLABORATION

Show a clean grid/list of the **seven logical roles**, even if a role is unavailable. Distinguish **configured role** from **actively running**:

| Role | Brief display description |
|---|---|
| Planner | Interprets goals and breaks tasks down |
| Researcher | Finds relevant supporting information |
| Developer | Produces requested implementations |
| Tester | Checks verifiable results |
| Reviewer | Evaluates completeness and correctness |
| Learning Agent | Extracts reusable, verified lessons |
| Memory Manager | Retrieves, filters, and organizes memory |

Show last known state where available: `Idle`, `Active`, `Completed`, `Error`, `Unavailable`. Do not imply seven separate background services; these are logical roles and can share one Gemini API.

A task detail region should show:

- Current task and status.
- Ordered steps/agents actually used.
- Compact per-agent **contribution summary** if available.
- Related ideas grouped by topic; compatible ideas combined into a **Team Idea** card with authors/roles.
- Conflicts/alternative approaches clearly labeled instead of forced into a single answer.
- Reviewer verdict when available.

**No fake agent-to-agent live chat.** Summaries and statuses must come from the actual workflow; display `No activity reported` when that telemetry does not exist.

### 4.3 Knowledge Graph — INTERACTIVE VIEW FROM REFERENCE IMAGE

**Purpose:** See real relationships among agents, projects, tasks, ideas, and **approved** memories. This is a *2D interactive network*, not a static background image.

**Recommended library:** Cytoscape.js, using the existing React application. Use a supported layout suitable for modest graphs (`cose` or preset positions) and do not require GPU-accelerated 3D rendering.

**Node kinds and solid colors:**

- `Agent`: muted blue (`#6EA8F7`), round node.
- `Memory`: teal (`#48BFA1`), round/rounded-square node.
- `Task`: amber (`#E6B85C`), rounded rectangle.
- `Idea`: muted violet (`#AA96DD`), diamond/rounded polygon.
- `Project`: gray (`#9CAFC5`), rounded rectangle.

**Edges:** plain thin solid lines, lower opacity than nodes. Labels or tooltips describe the **actual relationship**, such as `used_memory`, `contributed_to`, `related_to`, `belongs_to_project`, or `produced_idea`. Never draw fabricated relationships merely to make the graph look dense.

**Controls that must work:**

1. Pan by dragging the empty canvas; zoom by wheel/pinch or +/- controls.
2. `Fit to screen` and `Reset layout` buttons.
3. Search node by name/title.
4. Filters for Agent, Memory, Task, Idea, Project; optionally status.
5. Click node to open a **details inspector** with title, type, description, actual source/status, connected nodes, and `Open in Memory` where a valid note exists.
6. Click a relationship/edge to show its type and why it exists if the backend provides that reason.
7. Toggle labels or zoom for readability.
8. Empty state: `No relationships to display yet` with an explanation; do not generate a decorative fake graph.

**Data semantics:**

- The graph **visualizes known relationships**, not GraphQL. The existing memory/relation engine must supply the data, or the UI can derive only simple, explicitly recorded links from already available metadata.
- If cross-idea semantic linking is not implemented, show only the links actually available; do **not** silently add semantic memory infrastructure under this UI-only task.
- The graph does not write random relationships into Obsidian.
- Suggested links, if exposed in data, must be visually different from verified links and clearly marked `Suggested / unverified`.

**Performance rules:**

- Initial view: up to ~100 relevant nodes; provide filtering and neighborhood expansion instead of dumping the whole vault.
- For larger graphs (e.g. >300 visible nodes) use warnings, grouping, or progressive loading rather than rendering everything at once.
- Pause or stop layout animation when settled. Respect `prefers-reduced-motion`.
- Only redraw nodes/edges when graph data or filters actually change; clean up Cytoscape instances/listeners when unmounting.
- Smooth interactions are more important than visual effects.

**Suggested knowledge graph layout:**

```text
+-----------------------------------------------------------------------+
| Knowledge Graph | [Search nodes...] [Types v] [Fit] [+] [-] [Reset]    |
|-----------------------------------------------------------------------|
|                                                   | Node details       |
|                interactive 2D network             |--------------------|
|                                                   | Title              |
|         o---o          o                           | Type / status      |
|        /  / \         / \                          | Description        |
|       o--o---o-------o---o                         | Related nodes      |
|              \        /                            | [Open memory]      |
|               o------o                             |                    |
+-----------------------------------------------------------------------+
```

### 4.4 Memory — SELECTIVE MEMORY CONTROL PANEL

**Display, don't redesign memory logic.** A clean table/list with tabs:

- **Approved** — durable lessons and verified requirements.
- **Pending** — candidate lessons awaiting user review.
- **Health** — existing duplicate/conflict/stale/oversized proposals and review outcomes, if implemented.

Each item card/row: short title, project/scope, importance or status, updated date if known, and short preview. Click to see complete note.

Where supported by existing endpoints, provide `Approve`, `Reject`, `Edit before approval`, `Merge proposal`, `Archive`, and `Restore`. For destructive/irreversible actions, show a confirmation. **Never approve, delete, or rewrite memories merely because a UI panel was opened.**

If any action is not backed by a real API, mark it `Not available yet` and do not simulate success. Keep full conversation transcripts and raw task logs out of the Obsidian vault per previous memory rules.

### 4.5 Automations — BASIC STATUS VIEW ONLY

This request is not to implement n8n. Make a **simple integrations/automation page** that can display whatever already exists:

- Connected services and state (actual data only).
- Workflow title, enabled/disabled status, last run, next run if known.
- Pending approval count where exposed by the backend.
- Read-only event log with concise errors where exposed.
- `Open n8n` external link only when the configured local URL is known.

If n8n is not yet configured: show `No automations connected`, a short explanation, and a documentation/settings link. Do not show pretend scheduled workflows or active email sends. New workflow creation and OAuth setup are **out of scope**.

### 4.6 Settings — KEEP MINIMAL

Display only actual settings/capabilities:

- Backend connectivity status.
- Model identifier returned by backend if exposed, otherwise `Not available`.
- Obsidian vault connection/path status **without revealing private full paths unnecessarily**.
- Graph display preferences (labels on/off, reduced animation if needed).
- Theme: dark default; optional light only if easily supported and accessible.

**Never display or request Gemini API secrets in the regular settings UI** unless the existing application already has a safe secrets-handling design. No tokens in frontend bundles, logs, or localStorage.

---

## 5. FRONTEND ARCHITECTURE — LIGHTWEIGHT, REUSABLE

### Preferred stack

- React + TypeScript + Vite **if no suitable existing frontend exists**.
- Reuse the current frontend and UI framework if already stable and meets requirements. Avoid a full rewrite just to change appearance.
- Cytoscape.js for the network graph.
- Existing CSS solution or plain CSS variables + CSS Modules. Tailwind is optional **only if already present or clearly beneficial**, not mandatory.
- Lucide React icons if adding an icon package is appropriate.
- HTTP client via native `fetch` or current existing API utility; use WebSocket for live updates **only when the backend actually implements it**. Otherwise use bounded polling, not a tight infinite loop.
- Keep app local, minimal dependencies, and simple npm scripts.

### Suggested files (adapt to the actual repo)

```text
frontend/
  src/
    app/
      App.tsx
      routes.tsx
    components/
      AppShell.tsx
      Sidebar.tsx
      Topbar.tsx
      StatusBadge.tsx
      EmptyState.tsx
      ConfirmDialog.tsx
    features/
      chat/ChatPage.tsx
      agents/AgentsPage.tsx
      graph/KnowledgeGraphPage.tsx
      graph/GraphInspector.tsx
      memory/MemoryPage.tsx
      automations/AutomationsPage.tsx
      settings/SettingsPage.tsx
    services/
      api.ts
      adapters.ts
      types.ts
    styles/
      tokens.css
      global.css
```

Do **not** create this entire folder tree if the existing frontend already has clean equivalents. Code organization should remain understandable rather than overengineered.

### Connection to existing backend

Before coding, inspect the actual available endpoints. Record an API capability map in `BUILD_PROGRESS.md`:

| UI feature | Backend capability needed | Behavior if missing |
|---|---|---|
| Send prompt | Existing task/chat execution route | Disable Send with setup guidance |
| Chat history | Existing chat history or session state | Show session-only conversation |
| Agent statuses | Existing task/agent execution events | Show `Activity not available` |
| Team Ideas | Existing collaboration result | Hide section or show empty state |
| Graph | Existing node/edge relationships | Empty graph + explanation |
| Approved/pending memories | Existing read endpoints | Show unavailable state |
| Memory actions | Existing approval/reject API | Disabled controls, no fake success |
| Automations | Existing n8n integration/status | Read-only not connected state |

**Rules:**

- Centralize API base URL configuration rather than hardcoding a developer's machine.
- Do not expose secrets in client-side code.
- Use typed interfaces for `Task`, `AgentStatus`, `MemoryItem`, `GraphNode`, `GraphEdge`, `AutomationSummary`, etc., matching observed backend payloads rather than invented mandatory schemas.
- Support `loading`, `empty`, `error`, `offline`, and `success` states for all data views.
- Show actual `last updated` information only where returned by backend.
- Handle reconnects and timeouts gracefully.

---

## 6. INTERACTION AND ACCESSIBILITY REQUIREMENTS

- Visible keyboard focus (`:focus-visible`) for all buttons, inputs, tabs, and links.
- Semantic headings, labeled inputs, tooltips for icon-only controls, and ARIA labeling where needed.
- Minimum practical click/tap target about 40–44px for touch interactions.
- Status must be conveyed with **text + icon**, not color alone.
- Confirmations for Reject/Archive/Merge or any data-changing action where appropriate.
- Proper scrollbar behavior: keep chat input available without clipping messages; graph pan must not break app navigation.
- Escape key closes dialogs and drawers where applicable.
- Accessibility: aim for WCAG AA text contrast; test dark palette in browser.
- Use a simple spinner/skeleton only while actually loading. Avoid endlessly pulsing interfaces.
- Responsive layout must not hide the Send button, navigation, memory approval actions, or node inspector.

---

## 7. IMPLEMENTATION ORDER — DO NOT SCOPE CREEP

### Phase 0 — Inspect and safeguard

- Inspect current frontend/backend and identify real capabilities.
- Make a Git checkpoint or non-destructive backup where appropriate.
- Write a short API and UI inventory in `BUILD_PROGRESS.md`.

### Phase 1 — Foundation

- Create or refactor layout shell, navigation, top bar, responsive behavior.
- Apply **solid-color-only** design tokens and consistent typography.
- Establish reusable Button, Input, Card/Panel, Status, EmptyState, and Dialog components where useful.

### Phase 2 — Chat (highest priority)

- Build working prompt composer and message thread, connect to existing task execution endpoint.
- Display actual task state and result; show activity panel from real events where available.
- Handle loading, network failures, and session navigation correctly.

### Phase 3 — Agents + Team Idea

- Show seven agent roles and actual availability/activity.
- Add selected task view, contributions, and combined idea when the API provides them.
- No invented activity streams.

### Phase 4 — Knowledge Graph

- Integrate Cytoscape.js with known node/edge data.
- Implement search, type filter, pan, zoom, fit, node click, and details inspector.
- Implement empty/large-graph/reduced-motion behavior.

### Phase 5 — Memory + Automations + Settings

- Add read views and available approval actions for memory.
- Add truthful automation connection view without building n8n integrations.
- Add minimal connection/status settings UI.

### Phase 6 — Polish and verify

- Check desktop, laptop, tablet, and phone widths.
- Validate keyboard flow and contrast.
- Run the project's build and tests; fix console and runtime errors.
- Confirm no gradients anywhere.
- Update `BUILD_PROGRESS.md`, including which UI actions remain disabled due to backend limitations.

---

## 8. ACCEPTANCE CRITERIA / DEFINITION OF DONE

**Design and structure**

- [ ] No gradients, neon/glow, glassmorphism, or decorative visual clutter.
- [ ] Navigation is clear, and Chat is the landing view.
- [ ] Typography, spacing, buttons, panel surfaces, and status indicators are consistent.
- [ ] Layout works at approx. 1440px, 1024px, 768px, and 390px without broken controls.

**Core interaction**

- [ ] A real chat prompt can be submitted if the existing execution backend is available.
- [ ] If backend is unavailable, UI clearly explains why rather than showing fake answers.
- [ ] Agent view distinguishes configured roles from live activity.
- [ ] Team Idea appears only when an actual collaboration result exists.

**Interactive graph**

- [ ] Cytoscape.js graph displays real nodes/edges or an honest empty state.
- [ ] Search, filters, pan, zoom, fit, node selection, and inspector work.
- [ ] Nodes visually differentiate Agent, Task, Memory, Idea, Project without requiring color alone.
- [ ] Rendering stays responsive at expected graph size; no perpetual layout animation.

**Memory and automations**

- [ ] Approved/pending memory views are accurate; unsupported actions are disabled or omitted.
- [ ] No UI action silently stores unnecessary notes or modifies approved knowledge.
- [ ] Automation section shows real connection state rather than fictitious workflows.

**Engineering**

- [ ] Existing Python CLI, agents, memory, and n8n workflow logic are preserved.
- [ ] No Gemini API keys, OAuth secrets, or tokens appear in the frontend bundle.
- [ ] Frontend builds successfully and has no serious browser console errors.
- [ ] `BUILD_PROGRESS.md` records tested features, limitations, and how to run the UI.
- [ ] If a screenshot-based demo is captured, it is clearly identified as a live or development-only mock view.

---

## 9. LOCAL WINDOWS RUN AND HANDOFF REQUIREMENTS

Antigravity must provide exact Windows PowerShell commands based on the **actual repository**. For a new Vite frontend, a typical sequence is:

```powershell
cd path\to\project\frontend
npm install
npm run dev
```

The typical Vite dev URL is `http://localhost:5173`, but report the **actual URL printed in the terminal**. If the existing project uses Streamlit or a different dev server, use its real startup command instead; **do not presume** these commands apply.

Tell the user:

1. Which folder to open in VS Code / Antigravity.
2. Which command starts the Python backend and which starts the frontend.
3. Where to enter an AI prompt (**Chat** page).
4. Where to see which agents contributed (**Agents** page).
5. How to interact with the knowledge graph (**Knowledge Graph** page).
6. Where to approve proposed lessons (**Memory** page), if supported.
7. Which pages/features are currently waiting for backend integration.

No paid plans or hardware upgrades are needed simply to render this browser-based 2D dashboard on a typical modern Windows PC with ~16 GB RAM. Responsiveness depends on the size of the graph, app workload, browser, and existing hardware; use filtering and bounded layouts. Gemini inference remains cloud-hosted.

---

## 10. READY-TO-PASTE ANTIGRAVITY PROMPT

> Read `ANTIGRAVITY_UI_ONLY_CLEAN_DASHBOARD_AND_KNOWLEDGE_GRAPH.md` completely. This is a **UI-only** task for my existing Gemini Free-Tier + Obsidian multi-agent system. Build a professional, simple, responsive dashboard using **solid colors only — no gradients, neon glows, or glass effects**. I want a working Chat screen, honest Agent Activity and Team Idea displays, an **interactive Cytoscape.js knowledge graph** with search/filter/clickable nodes, a concise Memory review screen, and a basic Automations status screen. Focus on quality of layout, spacing, typography, accessibility, and real user interactions. Inspect and reuse my existing frontend/backend; preserve Python agents, Gemini integration, Obsidian memories, n8n workflows, and current commands. Do not fabricate statuses or build unrelated backend features. Implement and test the actual UI, document unavailable integrations, and update `BUILD_PROGRESS.md` with exact Windows launch instructions. Don't stop after creating mockups or a plan.

---

## 11. PROJECT CONTEXT TO REMEMBER IN A NEW CHAT

- User wants an AI team of **seven logical specialists + an orchestrator**, coordinated by Python and powered by the **Gemini free tier**, subject to provider quotas.
- **Obsidian** is the persistent memory vault, holding only high-value, concise, approved lessons. Routine transcripts and unverified ideas do not belong there.
- Agents may collaborate by identifying overlapping ideas, combining compatible approaches, flagging conflicts, and returning a reviewed **Team Idea**.
- Memory Health Checks and measurable improvement are separate backend features described in previous V2/V3 specs; **this file does not authorize implementing or changing their algorithms**.
- Optional **n8n** integration automates outside services; **this UI task only presents existing connections and workflow status**.
- **GraphQL is explicitly deferred** to a possible future architecture update. Use REST and existing streaming mechanisms now.
- The user prefers a simple but high-quality UI. The visual reference is a connected-node network, but the desired styling is **minimal, flat, professional, and gradient-free**.
- Do not infer implementation completion from documentation. Always inspect the actual code, report what is verified, and be transparent about missing interfaces.

**End of UI-only specification.**
