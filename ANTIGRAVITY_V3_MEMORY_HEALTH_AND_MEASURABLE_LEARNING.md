# ANTIGRAVITY V3 — Memory Health, Selective Learning, and Measurable AI Improvement

**Purpose:** Copy this file into a Google Antigravity workspace or upload it to a new coding-assistant conversation. It is an **implementation instruction**, not evidence that these features already exist.

**Project:** Gemini + Python multi-agent assistant + Obsidian knowledge vault + optional Streamlit dashboard / n8n automation  
**Environment:** Windows 10/11, Python 3.11+, local-first  
**AI:** Gemini Developer API, **free-tier eligible model only** (verify the current model and project quota; never assume unlimited requests)  
**Memory:** Local Obsidian Markdown, approved and concise; operational metrics in local SQLite *outside* the vault  
**Version:** 3.0 — October 29, 2026

## A. Instructions for Antigravity / a new AI chat

You are the implementation engineer, working **inside the user's existing codebase**. Read this entire file, inspect the workspace, and implement the requested changes in phases. **Do not stop at architecture or advice.** When possible, provide executable code, run local tests, preserve existing features, and update `BUILD_PROGRESS.md`.

1. If present, read `ANTIGRAVITY_V2_SMART_MEMORY_AND_TEAM_COLLABORATION.md` and the actual source files first. **V3 extends V2** and overrides it only on memory-health, continuous improvement, and evaluation details. The project must still support the seven specialist roles, collaborative Team Ideas, selective memory, and a local chat dashboard. If V2 is absent, this file remains usable as a standalone implementation brief.
2. **Never overwrite the user's `.env`, erase Obsidian notes, delete prior run data, or change approved memories without explicit user approval.** Back up the workspace or make a safe Git checkpoint before migration.
3. Do not claim that Gemini updates its model weights. Improvement means **better retrieval, accurate reusable memories, verified corrections, task evaluations, and versioned agent instructions**. It does not mean self-training the hosted Gemini model.
4. Keep the initial deployment free and local. Do not silently enable billing, expose secrets, or install unapproved paid services.
5. The application must offer clear **Review, Approve, Reject, Archive, Restore, and Evaluate** actions in the dashboard. A CLI equivalent is welcome; do not remove existing commands.
6. Use the minimum number of Gemini calls needed; use deterministic Python logic for metadata, filtering, duplicates, scheduling decisions, and statistics. Do not ask the model to assess every trivial task.
7. Report what actually ran and passed versus what remains **unverified** (especially live Gemini calls if an API key is unavailable).

**Ready-to-paste prompt:**

> Read `ANTIGRAVITY_V3_MEMORY_HEALTH_AND_MEASURABLE_LEARNING.md` fully and treat it as the latest extension of the V2 Gemini + Obsidian multi-agent system. Inspect my existing project, preserve my files and working commands, implement the selective memory health-check engine and measurable learning/evaluation loop, add review controls to the dashboard, write tests, and update BUILD_PROGRESS.md. Do not automatically erase notes or promote AI guesses to trusted memory. Demonstrate improvement with memory ON versus OFF using the same benchmark tasks. Build the working feature, not just a plan.

---

## B. What the user wants

Build an AI team that becomes **more reliable and personalized over time**, without accumulating unnecessary notes.

### Required outcomes

- Agents **learn from verified outcomes and user feedback** rather than saving every conversation.
- Obsidian stores only **high-value, concise, reusable, approved memories**, scoped to a project or globally if the user explicitly chooses.
- The Memory Manager can conduct a **Memory Health Check** that detects duplicates, conflicts, stale facts, weak evidence, oversized notes, unsafe content, and memories never used.
- Memory cleanup produces **non-destructive proposals** for user review; no silent deletion of user-authored or approved information.
- Agents can collaborate: independent relevant ideas are compared, related ideas are linked, contradictory ideas are challenged, and a final **Team Idea** is reviewed before use. Do not save the entire discussion.
- A measurable **evaluation system** compares task performance **with memory** and **without memory**, so growth is demonstrated with evidence rather than simply assumed.
- Long-term changes to agent prompts or procedures must be versioned, tested, approved, and reversible.

### What the system must NOT do

- Store all email messages, conversations, scratchpads, agent deliberations, code dumps, or raw model responses in Obsidian.
- Promote unverified LLM assertions or unsuccessful attempts to trusted memory.
- Fill the vault with duplicate lessons for the same issue.
- Automatically modify Gemini model weights.
- Run endless self-improvement loops or silently spend API quota.
- Delete memories or change agent instructions without review and approval.

---

## C. Operating system — full flow

```text
USER PROMPT / SCHEDULED APPROVED TASK
                |
                v
        PYTHON ORCHESTRATOR
                |
        Memory Manager: search approved, relevant, scoped memories
                |
        Planner: understand goal and choose ONLY needed agents
                |
       +--------+----------------------------------------+
       |        |                                        |
  Researcher  Developer                            Other needed roles
       |        |                                        |
       +--------+----------------------------------------+
                |
      TEAM COLLABORATION / IDEA SYNTHESIS
      (related? combine; contradictory? verify; unrelated? separate)
                |
      Tester: actual authorized tests where possible
                |
      Reviewer: validate requirements and verified outcomes
                |
           Final answer
                |
      Learning assessment (may yield ZERO memories)
                |
      Novel + durable + supported + safe + concise?
        | YES                              | NO
        v                                  v
     Pending lesson                    No vault write
        |
   User edits / approves / rejects / merges
        |
   Approved Obsidian memory, indexed for later retrieval
        |
   Periodic/manual MEMORY HEALTH CHECK
        |
   Suggested merges / conflicts / stale notes / cleanup (approval required)
        |
   EVALUATION: benchmark memory ON vs OFF
        |
   Dashboard metrics and optional versioned improvement proposals
        |
   Approved, reversible changes inform later tasks
```

The seven specialist roles remain **Memory Manager, Planner, Researcher, Developer, Tester, Reviewer, and Learning Agent**. The Python Orchestrator routes requests and coordinates collaboration. Not every task requires all seven roles or seven API calls.

---

## D. Selective memory: how learning is stored

### D1. A normal task may produce zero memories

On completion, assess if a lesson would materially help later work. Examples:

| Candidate | Decision | Reason |
|---|---|---|
| "The user said hello" | Do not save | No reusable value |
| Temporary brainstorming options | Do not save | Not a decision |
| AI claimed an approach worked, without test | Do not approve | Unverified |
| Confirmed Laravel project uses MySQL, not SQLite | Propose | Durable project fact |
| Exact fix for a recurring migration error, confirmed by a passing test | Propose | Verified reusable lesson |
| Repeated general programming tutorial paragraph | Do not save | Non-specific and duplicative |
| Approved writing preference for client email drafts | Propose | Helps future communication |
| An AI-generated password or sensitive email content | Never save | Secret/private material |

### D2. Admission criteria (all must pass)

1. **Relevant:** Applicable to a specific ongoing project, workflow, or user-approved global preference.
2. **Durable:** Likely useful beyond the current run. Temporary status belongs in short-lived activity metadata, not the vault.
3. **Novel:** Not substantially duplicated by an existing canonical note. If partially overlapping, suggest updating/merging.
4. **Grounded:** Comes from explicit user instruction, documented source, or actual test evidence. Record evidence type; never infer validation from the model saying “passed.”
5. **Safe:** No access tokens, passwords, personal/private client records, sensitive message bodies, or chain-of-thought.
6. **Concise:** Prefer one atomic lesson with a brief situation, applicable rule, verified evidence, and limitations.
7. **Approved:** User reviewed and approved it before inclusion in trusted retrieval.

**Defaults:** Generate **0–2 candidate lessons per completed task**; limit each lesson's **main explanatory text to 100 words**; retrieve **at most 5 relevant approved memories per task**, bounded by a configurable context-token budget. These are defaults, not hard limits on user-authored notes.

### D3. Memory note format (illustrative only)

```markdown
---
id: lesson-laravel-migration-001
status: approved
scope: project:example-app
topic: migrations
source_type: executed_test
verified: true
approved_at: 2026-10-29
review_after: 2027-01-29
version: 1
supersedes: []
---
# Avoid duplicate Laravel migrations

**Situation:** A migration attempted to recreate a database column.
**Lesson:** Inspect existing schema and prior migrations before adding a new column.
**Verified by:** A migration test and schema check in the referenced project.
**Limits:** Recheck against the actual database before applying in another project.
```

This is a **sample schema**, not a claim of an executed test. `verified: true` must be set only when actual evidence exists; `approved` and `verified` are different concepts (a user preference may be approved without a software test).

### D4. Memory promotion workflow

`Candidate -> Pending -> [Edit / Reject / Merge / Approve] -> Approved -> [Superseded / Archived with approval]`

- Pending lessons are **not trusted for retrieval**.
- Approved memories require human approval time and provenance.
- Keep a canonical note per topic and project when possible.
- Maintain cross-project separation by default. Ask before making a local lesson global.
- Store a short provenance pointer to the run ID or verified source, **not** full transcripts.
- Retrieval excludes superseded, archived, pending, or explicitly restricted notes.

---

## E. Memory Health Check — most important new feature

### E1. How it starts

- A **Run Memory Health Check** button in the dashboard and a CLI command.
- An optional **weekly scheduled check**, disabled by default and only available while a configured scheduler is actually running. Never promise 24/7 checks from a powered-off PC.
- A lightweight duplicate/conflict warning when approving a new note; this should be deterministic and low-cost.

### E2. Audits to perform (read-only first)

| Check | What to look for | Safe recommendation |
|---|---|---|
| Duplicate lessons | Same meaning, same project or shared canonical topic | Propose merge; show both notes |
| Contradictions | E.g. one note says SQLite, another says MySQL for the same project and date | Flag conflict; request evidence, don't pick automatically |
| Outdated notes | Version/time-sensitive information due for review | Propose re-verification, not automatic invalidation |
| Weak evidence | Claims marked `verified` without test/source record | Downgrade proposal pending user review |
| Never-used notes | No retrieval for a configurable observation window | Suggest archive candidate; don't archive blindly |
| Overlarge notes | Lesson exceeds concise target or includes a pasted transcript | Offer human-readable condensed replacement |
| Sensitive content | Potential API keys, credentials, personal/client data | Mask in display; recommend manual removal or redaction |
| Missing metadata | No project scope, approval status, or provenance | Suggest metadata repair without inventing it |
| Broken links | Referenced note or evidence no longer exists | Suggest fixing link or re-verifying |

### E3. Health report

Generate a compact report with:

- Vault-approved note count, pending count, and total **bytes of approved memory**.
- Potential duplicates, contradictions, stale notes, and items awaiting review.
- Last scan time, number of recommendations, and whether any were accepted.
- Before/after storage size **only if actual changes were approved and measured**.
- Each recommendation must include **affected note IDs, reason, risk, proposed diff, and actions**: `View`, `Approve`, `Reject`, `Edit`, `Restore`.

**Default behavior: scanning is read-only.** Do not automatically merge, overwrite, archive, delete, or globally reclassify notes. For approved merges, keep a backup or reversible version history and maintain valid references.

### E4. Storage protection

- Store final approved knowledge inside `Obsidian-Brain/01_Memory/Approved/` and candidates inside `Obsidian-Brain/01_Memory/Pending/`.
- Keep operational events, evaluation scores, and brief error metadata in `app_data/state.sqlite` **outside Obsidian**.
- Do not start adding full `03_Runs/...` content to the vault. Preserve legacy notes if already present; never remove old content without permission.
- Purge only the application's **temporary diagnostic metadata** under a configurable policy (suggested default 14 days), after clearly labeling it as disposable and excluding user-authored records.
- Run semantic deduplication with lexical comparison first; optionally use local embeddings later. Do not require a GPU or paid embedding API.

---

## F. Prove the AI is improving (not just storing more)

### F1. Evaluation modes

Provide a **Learning & Evaluations** view with two modes:

1. **Deterministic local tests (no Gemini cost):** Memory filtering, note deduplication, retrieval ranking, project separation, approval gating, conflict detection, archive/restore, secret masking, and agent-routing decisions.
2. **Optional Gemini quality evaluation:** A fixed, representative benchmark set run in two configurations:
   - **Memory ON:** approved, relevant memories may be retrieved.
   - **Memory OFF:** the same tasks, agent prompts, model, and settings, but with all saved memory retrieval disabled. Do not quietly include saved notes in a system prompt.

Run the comparison only when the user deliberately requests it or opts into a bounded schedule. Show the estimated number of model requests before running. Don't exceed configured API call and rate budgets.

### F2. Good benchmarks

Create 8–12 **local test cases** initially, each with an explicit rubric/expected behavior. Include:

1. Recall a saved, approved project constraint.
2. Refuse to use an unapproved pending lesson.
3. Retrieve the right project memory instead of another project's.
4. Reuse a verified fix to avoid a known bug.
5. Recognize and flag two conflicting approved notes.
6. Deduplicate two paraphrases of one lesson.
7. Don't write memory for trivial or speculative tasks.
8. Connect related ideas from two specialists into one useful Team Idea.
9. Keep unrelated ideas separate.
10. Correct a known problem following user feedback without changing unrelated preferences.
11. Avoid saving secrets or private content.
12. Handle missing notes or no available Gemini quota gracefully.

Use synthetic/redacted data. Do not include sensitive personal/client emails or source code in benchmark fixtures. Keep any user-created holdout tasks separate from memories that agents can retrieve, to reduce leakage.

### F3. Metrics to track

| Metric | Definition | Expected direction |
|---|---|---|
| Task success | Proportion meeting predefined rubric or passing actual tests | Up |
| Repeated-error rate | Same verified mistake recurring across comparable tasks | Down |
| Human corrections | Corrections needed per completed task | Down |
| Relevant-memory precision | Retrieved notes judged relevant / retrieved notes reviewed | Up |
| Incorrect-memory usage | Outputs relying on stale, conflicting, or unapproved notes | Down |
| Memory writes/task | Approved useful notes / tasks | Low and purposeful, not necessarily zero |
| Storage consumption | Bytes/notes in approved Obsidian memory | Controlled |
| Gemini usage | Requests and tokens **when provider metadata is available** | Controlled |
| Collaboration quality | Relevant ideas synthesized correctly vs forced or contradictory merges | Up |

**Do not equate more notes, more model calls, or a higher AI self-rating with improvement.** Always identify evidence type: deterministic unit test, actual executed code test, human rating, or LLM judgment. Treat LLM-only ratings as weak signals, not verified truth.

### F4. Fair memory ON/OFF experiment

- Use the **same fixed benchmark tasks**, same agent instructions, Gemini model ID, temperature/settings where supported, call budgets, tools, and test environment.
- Change **only the availability of approved memories**; make sure the baseline does not get memory through logs or hidden prompt context.
- Alternate run order or perform repeats to reduce noise from probabilistic responses; present sample sizes.
- Score with deterministic assertions and real tool/test results where possible; use blind human grading for subjective writing.
- Record timestamps, versions, test-set version, task ID, cost/usage metadata if exposed, and unresolved errors.
- Display per-task outcomes plus aggregate scores, confidence caveats for small samples, and runs that were skipped due to quotas.
- A single successful demonstration is **not** proof of systematic improvement. Prefer a repeated trend across comparable benchmarks.

### F5. Improvement proposal policy

When recurring failures are measured, propose a narrow fix:

`Evidence -> Proposed change -> Test on holdout tasks -> Show ON/OFF or before/after differences -> User approves -> Apply as new version -> Re-evaluate -> Roll back if worse`

Allowed proposals: change retrieval thresholds, add a missing test, amend a verified memory, adjust an agent role instruction, or improve routing. Never silently auto-edit core system prompts or execute generated code to “improve itself.” Require explicit approval before changing prompts that govern agent autonomy or tool permissions.

---

## G. Agent collaboration and memory health together

- The Planner picks only agents relevant to the current goal.
- Specialists first give **short independent candidate ideas**. Avoid automatic agreement and repeating the same answer.
- The Orchestrator labels relationships: `supports`, `extends`, `conflicts`, `unrelated`, or `needs_evidence`.
- Combine only compatible, evidence-supported ideas into a **Team Idea**; ask a Reviewer to check whether the combined proposal truly satisfies the task.
- Tester checks executable claims when permissions and environment permit; no invented test success.
- Learning Agent considers whether the **final verified outcome** teaches something reusable. Usually **zero** memory notes are needed.
- Store a concise, approved decision or verified pattern if truly useful—not the complete group discussion, agent chatter, speculative disagreements, or every proposed idea.
- When the Memory Health Check finds conflicting lessons, do **not** ask the agents to vote and automatically overwrite a note. Show evidence and request user resolution.

---

## H. Suggested data model and implementation interfaces

Use the existing project structures where possible; avoid unnecessary dependencies.

```text
project/
├── app/
│   ├── agents/                   # 7 logical agent roles
│   ├── orchestrator.py
│   ├── memory/
│   │   ├── retrieval.py
│   │   ├── admission.py         # worth remembering? -> pending candidate
│   │   ├── approvals.py
│   │   ├── health_check.py      # readonly audits and change proposals
│   │   ├── versioning.py       # backup, rollback, provenance
│   │   └── redaction.py
│   ├── evaluations/
│   │   ├── benchmarks.py
│   │   ├── experiment.py       # memory ON/OFF controls
│   │   └── metrics.py
│   └── ui/                       # Streamlit pages or existing dashboard
├── Obsidian-Brain/
│   └── 01_Memory/
│       ├── Pending/
│       └── Approved/
├── app_data/                     # local DB and compact evaluations, NOT vault
│   └── state.sqlite
├── tests/
│   ├── test_memory_admission.py
│   ├── test_memory_health.py
│   ├── test_memory_approval_and_restore.py
│   ├── test_memory_retrieval.py
│   ├── test_collaboration.py
│   └── test_evaluation_isolation.py
├── BUILD_PROGRESS.md
└── README.md
```

Suggested Python interfaces (adapt to existing source code):

```python
class MemoryStore:
    def retrieve(self, query: str, project_id: str, max_items: int = 5): ...
    def propose(self, candidate: dict) -> str | None: ...
    def approve(self, note_id: str, edited_text: str | None = None): ...
    def reject(self, note_id: str): ...
    def archive(self, note_id: str, approval_id: str): ...
    def restore(self, note_id: str, approval_id: str): ...

class MemoryHealthService:
    def scan(self, scope: str | None = None) -> dict: ...  # read-only
    def propose_fix(self, finding_id: str) -> dict: ...   # include diff
    def apply_approved_fix(self, proposal_id: str, approval_id: str): ...

class EvaluationService:
    def local_checks(self) -> dict: ...
    def compare_memory_modes(self, benchmark_ids: list[str], max_calls: int) -> dict: ...
```

Required UI tabs/actions:

- **Chat:** user prompt, agent status, final Team Idea, minimal cited retrieved memories.
- **Memory:** search/inspect approved notes; pending approve/edit/reject; scope labels.
- **Memory Health:** scan button, risk-ranked findings, diff preview, approval/restore controls; no destructive default.
- **Learning & Evaluations:** run cheap local checks, optional explicit memory ON/OFF benchmark, per-task scores, usage data, trends, and versioned improvement proposals.
- **Settings:** vault path, retention days, retrieval count/token budget, model ID, evaluation call budget, schedule opt-in; avoid showing API secrets.

Keep API secrets out of logs/Markdown. Require user approval before external side effects such as sending emails or modifying repositories.

---

## I. Implementation phases Antigravity should complete

### Phase 0 — Inspect and protect
- Find actual app source, vault, existing approval behavior, evaluation code, and docs.
- Record a baseline in `BUILD_PROGRESS.md` and create a safe backup/Git checkpoint.
- Preserve existing lessons, runs, `.env`, Streamlit UI, CLI, and agent workflow.

### Phase 1 — Selective memory guarantees
- Implement project-scoped retrieval, pending exclusions, evidence provenance, concise admission filters, deduplication, and secret checks.
- Add unit tests for zero-write trivial tasks and no accidental promotion.
- Retain existing legacy files; disable future raw transcript writes inside Obsidian.

### Phase 2 — Memory Health Check
- Implement read-only scan for duplicates, contradictions, outdated notes, weak evidence, unused notes, missing metadata, oversized notes, broken links, and likely secrets.
- Add diff-preview proposals, user approval gates, backup/version history, and restore.
- Create dashboard Memory Health page and optional explicit CLI command.

### Phase 3 — Benchmark and improvement tracking
- Implement 8–12 benchmark cases, deterministic cheap checks, optional gated Gemini memory ON/OFF trials, fair comparisons, and transparent metrics.
- Store only compact reports outside the vault; record run IDs, versions, and evidence type.
- Add Learning & Evaluations dashboard page; run unit tests in mock/offline mode.

### Phase 4 — Team collaboration integration
- Ensure the Orchestrator correlates related ideas, flags conflicts, and synthesizes compatible Team Ideas without forcing all agents to run.
- Add tests for related/unrelated/conflicting proposals and verify that only a final eligible lesson can become Pending.

### Phase 5 — Windows documentation, live verification, and handoff
- Document `venv`, dependencies, `.env.example`, vault setup, Streamlit launch, and where users type prompts.
- Demonstrate a real health scan, note-merge preview/restore, no-memory-write task, and mock benchmark.
- If the user supplies their Gemini key locally, validate the live integration within free-tier limits; otherwise label it unverified and document the exact next step.
- Update `BUILD_PROGRESS.md` after every milestone and summarize test results honestly.

### Acceptance tests — mark complete only if proven

- [ ] Trivial task adds **no** Obsidian memory.
- [ ] Pending and rejected memories **never** enter trusted retrieval.
- [ ] Two equivalent lessons generate a merge suggestion, not two independent approved notes.
- [ ] Contradictory facts generate a warning, not an automatic winner.
- [ ] Scan is read-only; cleanup requires approval and supports restoration.
- [ ] Sensitive/credential-like data is excluded or safely flagged without exposure.
- [ ] Cross-project memories remain isolated by default.
- [ ] Health reports show actual note counts and measured bytes.
- [ ] Local benchmark suite passes with mock providers; no live API key needed.
- [ ] Memory ON/OFF comparison changes only retrieval, logs both outcomes, and respects call budgets.
- [ ] Team Idea synthesis merges compatible proposals and flags unrelated/conflicting ones.
- [ ] Agent instruction or memory modifications are versioned, reviewable, and reversible.
- [ ] Existing app functionality remains working; user can run the UI on Windows.
- [ ] `BUILD_PROGRESS.md` distinguishes implemented, tested, blocked, and unverified features.

---

## J. Day-to-day use after implementation

1. Open the local Streamlit dashboard and give a task in normal language.
2. Agents retrieve **only relevant approved memories**, collaborate as needed, and answer.
3. If the task teaches a durable, verified lesson, the Learning Agent proposes one compact candidate. Otherwise nothing is saved.
4. In **Memory**, review or edit proposed notes. Approve only useful, correct memories.
5. Periodically click **Run Memory Health Check**. Review its suggested merge/repair/archive actions; nothing is changed unless you approve.
6. In **Learning & Evaluations**, run the cheap tests freely. Run the Gemini memory ON/OFF comparison occasionally, within your free-tier quotas, to see if memory really helps.
7. Review any proposed workflow or prompt changes; apply only ones supported by test evidence and keep the ability to roll back.

**Core rule:** *Remember less, verify more, retrieve precisely, collaborate intentionally, and measure actual improvement.*

## K. Current-state caution

This Markdown is a **design and development handoff**. It does **not** assert that a Memory Health Check screen, benchmark engine, memory ON/OFF evaluation, or all seven agent roles are already implemented. Antigravity must inspect the user's actual workspace and demonstrate the completed features with tests. If only the older five-agent CLI starter is present, migrate it safely and incrementally instead of claiming the full application exists.
