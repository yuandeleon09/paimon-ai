# PAIMON — Phase 1: Stability & Efficiency

**Antigravity-ready implementation specification and new-chat handoff**  
**Version:** 1.0  
**Date:** 2026-10-29  
**Status:** Proposed improvement — not yet implemented by this document  
**Scope:** Smart Gemini API Budget Manager, Rate-Limit / Quota Handling, Durable Task Queue & Recovery  
**Applies to:** The existing Paimon Gemini + Obsidian multi-agent assistant

> **Instructions to the implementing AI (including Google Antigravity):** Read this entire file before changing code. Treat it as the governing specification **only for Phase 1**. Inspect the real project before selecting filenames, libraries, or database migration steps. Implement and test the changes in the *existing* project; do not replace working components or claim to have tested a feature unless you actually have. Record the work in `BUILD_PROGRESS.md` or the project's existing progress file. If the project structure differs from the examples below, adapt the implementation to reality and document the differences.

---

## 1. Project identity and locked baseline

**Project name: Paimon.** Paimon is a personal, Windows-friendly AI assistant composed of specialized cooperating agents, coordinated by a Python orchestrator and using the **Gemini API free tier** for hosted reasoning. **Obsidian** stores approved, reusable long-term knowledge. The project may have a React-based chat dashboard, agent activity screens, an interactive 2D knowledge graph, a FastAPI backend, and file/image reading, depending on what is already implemented. The goal of this phase is **reliability**, not a redesign.

**Intended agent responsibilities:** Planner, Researcher/Context Analyst, Developer/Builder, Tester, Reviewer, Learning Agent, and Memory Manager, with an orchestrator. An older starter implemented only five roles; inspect the actual repository to see what is real. Do **not** create unnecessary new agents merely to satisfy a role count.

**Preserve these decisions:**

1. Existing working chat prompts, agent outputs, team synthesis, task history, file/image uploads, and dashboard functionality must remain intact.
2. Existing agent collaboration is kept. Make the *number of Gemini calls* adaptive, not the feature set smaller.
3. Obsidian memory stays selective: store only important, verified, reusable lessons with the user's approval; do not dump API logs, entire conversations, files, images, or temporary reasoning into Obsidian.
4. UI remains **simple, functional, and professionally laid out, with solid colors and no gradients**. Keep the optional knowledge graph.
5. Keep Gemini free-tier operation; **never enable paid billing, add payment methods, or switch models without the user's approval**. Do not use extra keys/accounts to evade provider limits.
6. The previously proposed Gmail / Google Calendar / Google Drive / Google Docs expansion (**V5**) was canceled. **Do not implement or reintroduce it** in Phase 1. Future GraphQL integration remains optional, not part of this phase.
7. Do not overwrite `.env`, credentials, existing Obsidian data, or Git history. Use a safe, reversible migration approach.

**Phase 1 is complete only when Paimon can intelligently limit API calls, handle temporary failures, and resume interrupted tasks without incorrectly repeating completed steps.**

---

## 2. Problem to solve

The dashboard previously showed **“Gemini calls used: 7 / 8”**. This most likely represents an **application-level call budget for a single task**, not necessarily the account's daily Gemini quota. The implementation must clearly distinguish them.

Current or potential failure modes to investigate:

- Simple questions unnecessarily run through many agents, wasting free-tier requests/tokens.
- Gemini returns `429`, network errors, timeouts, or `5xx`, and the workflow crashes or retries too aggressively.
- The application cannot tell a *temporary rate limit* from a *daily quota exhausted* condition.
- A browser refresh, process crash, or PC restart causes a multi-step task to start from zero.
- Duplicate button clicks cause duplicate task execution or extra API calls.
- The UI implies that a local `7/8` counter reflects live Google's full daily allowance.
- Intermediate analysis or failed attempts get mistakenly saved as trusted Obsidian memories.

**Expected behavior:** Paimon should stop early when sufficient evidence exists, gracefully pause when further calls are unavailable, explain what happened, and resume when permitted without losing verified work.

---

## 3. Required runtime workflow

```text
User submits prompt (+ optional attachments)
        |
        v
Validate request / identify or create task ID / deduplicate submission
        |
        v
Retrieve small set of relevant APPROVED Obsidian memories (local; no Gemini call if avoidable)
        |
        v
Deterministic complexity check + role selection + per-task budget reservation
        |
        +--> simple request: direct qualified agent, optionally reviewer only if needed
        +--> file summary: analyst, optional reviewer
        +--> coding/research: relevant specialists + reviewer / synthesis when valuable
        +--> higher-risk/complex: planner + relevant specialists + verifier
        |
        v
Execute steps one at a time, checkpoint each completed step in local durable storage
        |
        +--> Before EVERY model request: check remaining task budget and local usage controls
        +--> On response: record outcome/token metadata where available, checkpoint result
        +--> On temporary error: bounded retry/backoff or pause task
        +--> On likely daily quota exhaustion: pause; don't loop/retry continuously
        +--> On cancellation: stop future work safely; retain prior completed steps
        |
        v
Reviewer/tester (only when required and affordable) -> final / partial result
        |
        v
Learning Agent proposes at most a small number of verified-useful lessons
        |
        v
Only user-approved lessons go to Obsidian; runtime logs remain outside vault
        |
        v
Return final/partial output + accurate task status + call usage + resume option
```

**Agent teamwork rule:** Select specialists by the work they can contribute. Related ideas should be synthesized, but do not call every agent for trivial tasks or force unrelated ideas together. Use deterministic routing first; optional model-assisted routing is only permitted when demonstrably worth its request cost.

---

## 4. Improvement A — Smart API Budget Manager

### 4.1 Separate three different measurements

1. **Per-task logical budget:** Paimon's configured maximum count of **physical outgoing Gemini API attempts** for one task (example default: **8**). This is a local safety cap, not Google's official quota.
2. **Local provider usage ledger:** Counts requests and, when exposed by responses, input/output/total token counts. Includes failed attempts and retries. This is **observed local usage**, potentially missing requests from other applications or devices using the same Google project.
3. **Actual Google quota:** Provider-controlled per-model/per-project limits (such as RPM, TPM, and RPD), viewed in Google AI Studio. **Do not fabricate a live remaining-quota number.** If there's no authorized, reliable quota source, display **“Not available — check Google AI Studio.”**

### 4.2 Routing rules (initial configurable targets, NOT promises)

| Work type | Preferred execution | Typical target |
| --- | --- | --- |
| Simple explanation / formatting | One suitable agent; no unnecessary planner/reviewer | 1 call |
| Straightforward document summary | One analysis pass; reviewer only for uncertain/high-impact output | 1–2 calls |
| Coding / debugging / multi-step research | Relevant builder/researcher and independent reviewer | 3–5 calls |
| Complex task with conflicting ideas | Planner + selected specialists + synthesis + review | Up to task budget |

- **Never use the full budget just because it is available.**
- Preserve an independent review on tasks where accuracy matters; if the budget cannot support required verification, deliver a **clearly labeled unverified/partial result** rather than claiming PASS.
- Prefer rule-based classification using request length, attachment presence, task type, and prior verification requirements. Do not add a routing-model request to every task.
- Avoid repeating identical prompts or attachment analysis in the same task. Reuse previously computed **task-scoped** summaries and intermediate outputs when inputs are unchanged.
- Limit recalled Obsidian context to up to **5 relevant approved memories** (existing V2 preference) and avoid loading the whole vault.
- Bound prompt/context size and output length according to the currently configured Gemini model capabilities. Track token usage when available, without inventing estimates as actual metrics.
- Default to **one model request in flight at a time** in a single local worker until concurrency/rate handling is demonstrated safe. Cross-task concurrency can be expanded later with explicit controls.

### 4.3 Configurable settings (example names; adapt to existing config)

Create or extend `.env.example` with **non-secret default values**:

```ini
# Values are APPLICATION controls, not Google's actual quotas.
PAIMON_MAX_CALL_ATTEMPTS_PER_TASK=8
PAIMON_MAX_PARALLEL_GEMINI_REQUESTS=1
PAIMON_MAX_TRANSIENT_RETRIES=2
PAIMON_RETRY_BASE_SECONDS=1
PAIMON_RETRY_CAP_SECONDS=30
PAIMON_TASK_TIMEOUT_SECONDS=900
PAIMON_AUTO_RESUME_RATE_LIMITED=false
PAIMON_USAGE_TRACKING_ENABLED=true
PAIMON_TASK_DB_PATH=./runtime/paimon_tasks.sqlite3
```

- Follow the existing project's configuration naming when already established. Do not create competing settings with different meanings.
- Use the **configured model**; do not hard-code a model ID that may be unavailable to the user's Google project.
- Any *retry initiated by the SDK* may generate additional physical requests. Inspect the currently installed Gemini SDK; avoid stacking SDK retries and application retries without a defined total attempt bound. If SDK retry counts cannot be observed accurately, label the ledger **estimated/known attempts** and don't pretend it is exact. Do not count the UI's agent stages as API requests.
- No paid-tier auto-upgrade or silent model fallback.

### 4.4 Safe request admission

Before a call, evaluate:

- Is the task canceled, completed, waiting for approval, or paused?
- Is there an allocated remaining *local attempt budget*?
- Is the model currently in a known cooldown/quota-pause state?
- Has this exact task step already completed with the same input fingerprint?
- Does a request require user approval under existing rules?

If any guard fails, **do not call Gemini**. Return a structured state explaining the reason.

---

## 5. Improvement B — Rate limits, quota handling, and reliable errors

Google may return temporary `429` rate limits, a `429` associated with daily quota exhaustion, `503` service unavailability, network timeouts, or non-retryable errors. **Use the provider's structured error details when available**; do not guess solely from a `429` status. If the cause is ambiguous, be conservative and pause rather than hammer the API.

### 5.1 Error policy

| Case | Required behavior |
| --- | --- |
| Temporary `429` / per-minute throttling | Honor `Retry-After` or structured retry delay when present; otherwise bounded exponential backoff + jitter; then **pause** if not resolved |
| Daily/project quota exhausted | Persist `paused_quota`; show explanation and safe manual resume option; do not retry rapidly or claim a precise reset time unless proven |
| `503`, `500`, temporary network failure | Small bounded retries with jitter, then persist `paused_transient` or `failed_recoverable` |
| `408` / timeout | Retry only when safe, bounded; mark uncertain outcome if an external side effect may have occurred |
| `400`, `401`, `403`, invalid key, bad model/configuration | **Do not auto-retry**; show actionable configuration/error message |
| Local task budget depleted | Stop this task with `paused_budget` or complete a partial result; do not call more agents |
| Safety-blocked or invalid model output | Report honestly, avoid blind retry loops; preserve user data and any verified partial work |

**Retry policy:** Follow the currently installed SDK's actual retry behavior. If writing an application-level retry wrapper, prefer only **up to 2 additional retries** for a transient failure, with exponential backoff and jitter, and make sure total physical requests fit the task budget. Never retry indefinitely. Use shorter cooldowns for interactive tasks and offer manual resumption for long waits. Do not automatically wake a daily-quota-paused task merely because a local clock passed an assumed reset time.

**Technical notes:**

- Store `error_code`, `http_status`, sanitized `message`, `retry_after`/`next_eligible_at` (if trustworthy), and `model` for each failed attempt.
- Do not log API keys, raw user prompts, full model responses, or private attachments in usage/error telemetry.
- Unknown quota metadata must be shown as **unknown**, not as zero, infinity, or “unlimited.”
- Frontend messaging should distinguish **“Task call budget reached”** from **“Gemini API rate-limited”** and **“Daily quota may be exhausted.”**
- If the user manually increases a local budget, that must **not bypass** Gemini provider quotas or a safety-required approval step.

### 5.2 Gemini documentation to check before implementing

- Official rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Official troubleshooting/retries: https://ai.google.dev/gemini-api/docs/troubleshooting
- Official API errors: https://ai.google.dev/gemini-api/docs/api-errors
- Usage and limits in Google AI Studio: https://aistudio.google.com/usage

Official documentation changes; verify the currently installed SDK and API response shape. Do not assume old rate-limit numbers apply to this Google project.

---

## 6. Improvement C — Durable task queue, checkpoints, and recovery

### 6.1 Task state machine

Use an explicit, persisted lifecycle (or map to the project's existing compatible states):

```text
queued -> running -> completed
             |--> completed_partial
             |--> paused_budget ----> queued/running (user explicitly raises budget)
             |--> paused_rate_limit -> queued/running (eligible retry/manual resume)
             |--> paused_quota -----> queued/running (manual resume after quota available)
             |--> paused_transient -> queued/running (manual retry)
             |--> waiting_approval -> running (user approves)
             |--> failed
             |--> cancelled
```

- Do not show `completed` or `PASS` for tasks whose required stages failed or weren't executed.
- Show completed verified stages, skipped stages, unresolved issues, and an available partial result.
- Canceling prevents new calls; in-flight SDK requests may not be immediately cancellable. Record cancellation accurately.
- A paused task is not a failed task unless it cannot recover or the user explicitly ends it.

### 6.2 Durable persistence

Use a small **local SQLite database** or the project's already functioning durable store. No external database or paid infrastructure required. Suggested conceptual entities (adapt to existing schema; don't force new tables):

- `tasks`: `id`, `user_request_ref_or_redacted_preview`, `status`, `model`, `budget_limit`, `created_at`, `updated_at`, `next_eligible_at`, `last_error`, `version`.
- `steps`: `id`, `task_id`, `step_key`, `agent_role`, `input_fingerprint`, `status`, `result_path_or_json`, `started_at`, `finished_at`, `verification_status`.
- `api_attempts`: `id`, `task_id`, `step_id`, `model`, `timestamp`, `attempt_index`, `outcome`, `http_status`, `error_code`, `input_tokens_nullable`, `output_tokens_nullable`, `total_tokens_nullable`.
- `task_events`: compact events for start/pause/resume/cancel/complete, for UI activity and diagnosis.

Avoid storing sensitive messages, files, email contents, credentials, or full internal prompts in usage logs. Where resumability requires outputs, store task artifacts in a dedicated **private local runtime directory** with limited retention and clear deletion controls, **not Obsidian**. Local task artifacts can contain personal data; warn the user and protect the directory.

**Important:** Store enough to resume accurately while minimizing sensitive data. Use atomic transactions for state transitions, SQLite WAL where appropriate, and an explicit schema migration/backup plan. Use an application lock or safe single-worker queue so two tabs/processes cannot execute the same task twice.

### 6.3 Resume and idempotency

When Paimon starts:

1. Read persisted tasks; do **not** silently restart every incomplete task.
2. Mark `running` tasks from an interrupted process as `interrupted`/recoverable, or transition them to a recoverable paused state.
3. On user resumption, validate the task's previously saved context, current model availability, pending approvals, and remaining budget.
4. Skip steps marked completed **only if their input fingerprint and dependencies still match**.
5. Reuse saved verified results; if a step may have committed an external side effect but confirmation is missing, require review before repeating it.
6. Persist a checkpoint after each successful agent stage and after state changes.
7. Allow **resume, cancel, retry failed stage**, and view partial output without creating a new task ID.

Use an idempotency key for UI submission (`client_request_id` / `task_id`) to prevent double-clicks and refreshes from duplicating work. If a request is already active, return the existing task state instead of starting a second copy.

### 6.4 Background and Windows constraints

- On a user's Windows PC, scheduled processing runs only while the necessary Python process and computer are awake. **Do not promise background operation when Paimon is not running.**
- Initial implementation should use one reliable worker loop and a local queue. Don't introduce Redis, Celery, n8n, cloud servers, or complex distributed queues without demonstrated need and approval.
- If auto-resume is added, it must be explicitly opt-in and respect `next_eligible_at`, user cancellation, API budgets, and the PC's actual running state.

---

## 7. Backend boundaries and API contracts

**Inspect current FastAPI/other backend first.** Reuse endpoints where possible; these are examples of desired capabilities, **not mandatory exact routes**.

| Suggested route | Purpose | Behavior |
| --- | --- | --- |
| `POST /api/tasks` | Create task | Accept request + idempotency key; return `task_id` and status |
| `GET /api/tasks/{task_id}` | Task details | Status, partial/final result, step progress, usage, pause reason |
| `POST /api/tasks/{task_id}/resume` | Resume task | Check state, permissions, remaining budget, retry eligibility |
| `POST /api/tasks/{task_id}/cancel` | Cancel task | Stop future steps; preserve checkpoints |
| `GET /api/usage/local` | Local usage | Observed attempts/tokens, scoped by task/model/time window |
| `GET /api/health` | Health check | Backend, queue, database, Gemini config readiness (never reveal secrets) |

- Keep existing chat endpoints/contracts compatible; migrate UI calls only when needed. Avoid introducing a second competing orchestrator.
- Emit task progress through the current mechanism (WebSocket or polling) and retain a polling fallback. Do not fire multiple Gemini calls because the UI polls.
- Require authentication/localhost-only access as appropriate to the existing design. Validate input, bound uploads, and avoid unauthenticated external control endpoints.
- Provide clear error payloads with a **machine-readable reason** and a **safe human-readable message**.

Suggested response fragment for UI (illustrative only):

```json
{
  "task_id": "example-task-id",
  "status": "paused_budget",
  "current_stage": "review",
  "logical_budget": {"used_known_attempts": 8, "limit": 8},
  "provider_quota": {"status": "unknown", "source": "Google AI Studio"},
  "completed_steps": 3,
  "partial_result_available": true,
  "can_resume_now": false,
  "message": "This task reached Paimon's configured 8-attempt limit. Your Google daily quota is not known."
}
```

---

## 8. Minimal UI improvements — no redesign

Preserve the current layout and theme. Add or refine a compact **API & Task Status** section in existing Chat or Agent Activity views.

**Must show:**

- Current task status (queued, running, complete, partial, paused, canceled, failed).
- Which agent/stage is running, which stages have completed, and any skipped steps.
- **Local task API attempts: `N / max`** (label as Paimon's budget, not Google quota).
- **Locally observed Gemini calls/tokens** if instrumented; mark as local estimates if SDK-internal retries are hidden.
- **Google's current project quota: “Not available — check Google AI Studio”** unless an authorized live source actually exists.
- Pause reason, a concise actionable error, and when safe an **Resume** or **Retry** control.
- **Cancel** control and access to previously completed/partial outputs.

**Interaction rules:**

- All controls must call real backend actions; no decorative fake buttons.
- A disabled Resume button must state why (no budget, no running worker, invalid config, or waiting for user review).
- Browser refresh should recover the same task view using `task_id`.
- Do not display provider quota estimates as precise measured balances.
- Solid colors only; no gradients. Use compact spacing and accessible labels.

---

## 9. Security, privacy, data retention, and Git safety

1. Never log or commit `.env`, `GEMINI_API_KEY`, token files, private attachments, runtime DB, raw chat histories, or personal Obsidian vault contents.
2. Create sanitized `.env.example` only. Add `runtime/`, `*.sqlite3`, `uploads/`, `tmp/`, and caches to `.gitignore` where appropriate, **without overriding existing important patterns**.
3. Any debug logging must use redacted/sanitized messages; avoid full request/response dumps.
4. Do not silently delete existing memories, tasks, files, or databases. Use backups before migrations.
5. Keep pending learning suggestions separate from trusted Obsidian memory; do not store arbitrary success claims as verified lessons.
6. Avoid auto-executing code generated by agents. Preserve existing consent and sandbox/testing controls.
7. Before committing, run a secret scan if available and inspect staged filenames. Never force push just to complete Phase 1.
8. In local settings, clearly state that Gemini API inputs are transmitted to Google's service; this phase must not expand data access permissions.

---

## 10. Incremental build plan for Antigravity

### Stage 0 — Inspect and preserve

- Inspect code structure, active branch, environment/config, existing task orchestration, Gemini client, current UI, and tests.
- Read existing project instructions and progress files; establish how many agents and which screens are *actually implemented*.
- Back up the runtime database if one exists; avoid making changes while it is open/actively used.
- Create a dedicated feature branch such as `feature/phase1-reliability` if Git is configured and it is safe to do so. Never replace `main` or remove unrelated changes.
- Record baseline observed behavior, especially how the existing `7/8` or `N/8` counter is calculated.

### Stage 1 — Instrument Gemini calls

- Identify every code path that sends a Gemini request; route through one shared Gemini gateway/client adapter where feasible.
- Add an attempt ledger and safe token metadata capture. Ensure SDK auto-retries are not silently double-counted as exactly known requests.
- Keep existing AI output behavior unchanged and pass current regression tests.

### Stage 2 — Add smart routing and budgets

- Add local max attempt settings, deterministic task classification, selected specialist routing, early stop rules, and request admission guard.
- Ensure task budget is enforced across all agents, syntheses, reviews, and retries.
- Compare simple-task request count before and after; do not promise a percentage reduction without measurements.

### Stage 3 — Implement error states and retries

- Normalize Gemini exceptions and map known retryable vs non-retryable errors.
- Respect server retry hints, use bounded backoff/jitter, distinguish known daily quota from temporary limit, and store pause reason.
- Never create an infinite retry loop or switch to a paid tier.

### Stage 4 — Add durable queue and safe resume

- Introduce the compatible SQLite/persistent task store; migrate non-destructively.
- Implement checkpointing, startup reconciliation, idempotent submissions, cancellation, and manual resume.
- Verify restart recovery and no duplicate execution of completed stages.

### Stage 5 — Minimal UI status and controls

- Reuse existing React/dashboard components. Add task status, call budget, error reason, progress, Resume/Cancel, and partial output display.
- Maintain solid-color design, responsive layout, and current knowledge graph.

### Stage 6 — Test, document, and hand off

- Run automated tests, perform manual UI checks, review Git diff and secrets, and update `BUILD_PROGRESS.md`.
- Document user-facing setup, configs, exact run commands for the actual repository, and known limitations.
- Clearly identify any unverified live Gemini behavior if testing used mocks only.

---

## 11. Acceptance tests (must be demonstrated)

Use fakes/mocks for repeatable tests so they do **not consume free-tier Gemini quota**. Run a limited, explicitly authorized real-API smoke test only if credentials exist and the user allows it.

| Test | Required evidence |
| --- | --- |
| Basic chat unchanged | Existing simple prompt works; answer is displayed |
| Smart routing | Simple prompt omits unnecessary agent calls; role selection recorded |
| Local budget enforced | Task with remaining budget `0` makes **zero** new Gemini attempts |
| Accurate accounting | Known outgoing attempts recorded once; SDK-internal unknown attempts not falsely claimed as exact |
| Temporary `429` | Bounded retries and/or safe rate-limit pause; no rapid infinite loop |
| Known quota exhaustion | `paused_quota`, no rapid retry, informative message |
| `503` or temporary network error | Bounded retry and recoverable pause |
| Invalid key / `401` / `403` | No automatic retries; actionable configuration message |
| App crash/restart | Persisted task remains recoverable; existing verified outputs retained |
| Resume task | Continues from valid checkpoint; does not rerun completed step |
| Duplicate submission | Same idempotency key returns existing task; no double execution |
| Cancel | Prevents future stages; preserves prior results; communicates in-flight limitation |
| Browser refresh | Same task status displayed on reload |
| UI label honesty | `N/8` explicitly labeled local per-task budget; provider quota marked unknown if unavailable |
| Memory preservation | Obsidian approved notes unchanged; no logs/raw prompts added to vault |
| Git safety | No `.env`, API keys, personal vault, SQLite DB, or uploads staged |
| Feature preservation | Existing UI, file/image reading, team synthesis, memory approvals, and knowledge graph still function if already present |

**Minimum test suite:** unit tests for admission/budget, state transitions, retry classification, idempotency, quota messaging; integration tests for persistence/restart and API responses; UI check for progress buttons and accurate labels.

**Completion criteria:** No known high-severity data-loss/security regressions; all above tests pass or are honestly marked with evidence as blocked; measurable reduction in unnecessary model calls for at least one representative simple-task workflow; reliable partial results and resume behavior verified.

---

## 12. Definition of done / development report

When implementation finishes, report:

- Exact files changed and why; distinguish modified existing files from new files.
- What was **implemented and tested** versus only specified or mocked.
- How to start Paimon locally on Windows using real project commands.
- `.env.example` configuration values and safe default behaviors.
- Evidence for budget enforcement, temporary `429`, quota pause, crash/restart, and resume tests.
- Before/after model-call results for one simple and one complex representative task (or state why measurement wasn't available).
- Any migration/backup performed and roll-back instructions.
- Git branch and commit status; any secrets/security checks.
- Updated `BUILD_PROGRESS.md`: completed, remaining, blocked, and next recommended step.

**Do not claim Paimon has access to live Google quota if it doesn't.** Do not call Phase 1 complete merely because files or TODO markers were created.

---

## 13. User instructions after implementation (Windows)

These are **workflow instructions**, not an assertion about the current repository's exact launch commands:

1. Open the **existing Paimon repository** in VS Code / Antigravity.
2. Make sure Python environment, Gemini key, and existing frontend remain configured. Never paste the key in chat, commit it, or store it in Obsidian.
3. Run any project migrations/backups according to Antigravity's actual implementation report.
4. Start the backend and frontend using the commands documented for **your actual project**.
5. Submit a simple request; check whether Paimon uses only the agents needed.
6. Check the Chat / Agent Activity UI for the **local per-task call budget** and clear status.
7. Test safe **Pause → Resume** with a mocked quota/rate-limit or a developer test mode; do not intentionally burn through real free-tier quota.
8. Confirm a browser refresh or restart retains a recoverable task.
9. Check official usage/quotas in Google AI Studio instead of trusting a local counter as total account usage.
10. Confirm Obsidian contains only approved, valuable lessons and that the original project features still work.

---

## 14. Exact Antigravity prompt to use with this file

Copy and paste the text below into the Antigravity agent chat **after placing this Markdown file in the Paimon repository root**:

```text
Read PAIMON_PHASE_1_STABILITY_AND_EFFICIENCY.md completely and use it as the governing specification for Phase 1 improvements to my existing Paimon AI system.

Implement ONLY Phase 1: a smart Gemini API budget manager, rate-limit/quota/error handling, and a persistent resumable task queue with checkpoints. Keep the current Gemini free-tier model setup, agents, collaboration, Obsidian selective memory, file reading, clean UI, and knowledge graph working as they currently do. Do not implement the previously canceled Google Workspace (V5) integration or GraphQL.

Before coding, inspect the real repository and document how it currently operates. Preserve data and existing working code. Make focused and reversible changes, use safe migrations, and do not overwrite credentials. Use clear UI labels to distinguish Paimon's local task attempt budget from Google's actual Gemini quota. Avoid unnecessary model calls and infinite retries.

Implement the code, add offline/mock tests, run them, verify crash recovery and safe task resume, inspect the Git diff for secrets, and update BUILD_PROGRESS.md with completed work and any blockers. Do not stop after generating a plan. Do not claim an untested feature works.
```

---

## 15. Future phases — deliberately out of scope

- **Phase 2:** better selective memory retrieval, stronger collaboration, controlled feedback-based learning, and performance evaluation.
- **Phase 3:** better document retrieval, dashboard usability, and proactive memory health monitoring.
- **Phase 4:** integrations/automations only when explicitly reapproved; optional GraphQL only when real dashboard complexity justifies it.

**Phase 1 must not change the approved project flow or add new external integrations.**

---

### Guiding principle

> **Paimon should make only necessary calls, tell the truth about its limits, preserve useful work when interrupted, and resume safely instead of starting over.**
