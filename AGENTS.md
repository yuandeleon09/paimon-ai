# Workspace Agent Rules & Governing Instructions

## Governing Specifications
This workspace is governed by [`ANTIGRAVITY_V2_SMART_MEMORY_AND_TEAM_COLLABORATION.md`](file:///c:/Projects/AiAgents/ANTIGRAVITY_V2_SMART_MEMORY_AND_TEAM_COLLABORATION.md) (V2 Master Specification, superseding previous blueprints).

## Core Principles
1. **Zero-Cost / Free-Tier Only**: Always operate within eligible Gemini free-tier limits (default model: `gemini-3.5-flash-lite`). Never activate billing or assume unlimited quota.
2. **Priority 1 — Selective Memory**: Only store high-value, durable, reusable, and verified knowledge in `Obsidian-Brain/`. Routine tasks, chatter, and temporary ideas must produce zero new Obsidian notes. Run metadata goes to `app_data/state.sqlite` outside the vault. Never delete existing user notes.
3. **Priority 2 — Team Collaboration**: Specialized agents generate independent idea cards before seeing peer proposals. Correlate relationships (`supports`, `complements`, `depends_on`, `contradicts`, `unrelated`), preserve conflicts, and synthesize one coherent `TeamIdea`.
4. **Priority 3 — Continuous Improvement**: Retain verified lessons, evaluate benchmarks, and learn from human feedback and real test evidence. Never claim Gemini model weights are retrained.
5. **Priority 4 — Quota Minimization**: Route tasks through minimal agent sequences. Cap at `MAX_MODEL_CALLS_PER_TASK=8` and `MAX_REVISIONS=1`.
6. **No Fabricated Evidence**: Tester must truthfully report execution status or mark as `NOT RUN` / `BLOCKED`. Never claim unrun tests passed.
7. **Human-in-the-Loop Approval**: All candidate lessons are strictly `Pending` until the human operator approves or edits them.
