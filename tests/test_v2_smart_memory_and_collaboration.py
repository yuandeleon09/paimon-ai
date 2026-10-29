import pytest
from pathlib import Path
import shutil
import tempfile
import json

from app.config import SystemConfig
from app.memory_store import MemoryStore
from app.collaboration import AgentIdea, Relationship, TeamIdea, correlate_ideas, synthesize_team_idea
from app.memory_filter import evaluate_memory_value, MemoryCandidate
from app.runs import RunStore
from app.evaluations import run_system_evaluations
from app.orchestrator import MultiAgentOrchestrator
from app.safety import sanitize_text

@pytest.fixture
def temp_env():
    temp_dir = Path(tempfile.mkdtemp())
    vault = temp_dir / "Obsidian-Brain"
    workspace = temp_dir / "workspace"
    app_data = temp_dir / "app_data"

    vault.mkdir(parents=True)
    workspace.mkdir(parents=True)
    app_data.mkdir(parents=True)

    config = SystemConfig(
        project_root=temp_dir,
        vault_path=vault,
        workspace_path=workspace,
        app_data_path=app_data,
        gemini_api_key="mock-key",
        gemini_model="gemini-3.5-flash-lite",
        max_model_calls_per_task=8,
        max_revisions=1,
        max_retrieved_memories=5,
        max_memory_context_tokens=700,
        memory_min_score=7,
        max_memory_words=100,
        max_candidate_memories_per_task=2,
        allow_live_tools=False
    )
    yield config, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

# AT-21: Trivial task memory gate (Zero-write to Obsidian)
def test_at21_trivial_task_zero_write(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    res = evaluate_memory_value("What is 2 + 2?", "4")
    assert not res.should_store
    assert res.score < config.memory_min_score
    # Verify no file written to Pending
    assert len(list(store.pending_dir.glob("*.md"))) == 0

# AT-22: Valuable verified fix creates <= 2 concise Pending lessons, never auto-approved
def test_at22_valuable_verified_fix(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    res = evaluate_memory_value(
        task="Fix race condition in reservation checkout",
        outcome_result="Always ensure idempotent database transaction locks around reservation activations to prevent double booking.",
        test_verified=True,
        min_score=config.memory_min_score
    )
    assert res.should_store
    assert res.score >= 7
    assert len(res.candidates) <= 2
    for cand in res.candidates:
        store.save_candidate_memory(cand)
        # Word count check on body
        assert len(cand.body.split()) <= config.max_memory_words

    # Must be strictly Pending, zero notes in Approved
    assert len(list(store.pending_dir.glob("*.md"))) >= 1
    assert len(list(store.approved_dir.glob("*.md"))) == 0

# AT-23: Duplicate lesson proposes merge/revision to canonical note
def test_at23_duplicate_lesson_merge(temp_env):
    config, _ = temp_env
    mock_approved = [{
        "note_path": "01_Memory/Approved/payment_rules.md",
        "excerpt": "payment transaction rules standard"
    }]
    res = evaluate_memory_value(
        task="Update payment transaction rules",
        outcome_result="Add exponential retry backoff to payment transaction rules.",
        existing_approved_notes=mock_approved,
        test_verified=True
    )
    assert res.should_store
    assert res.candidates[0].is_merge
    assert res.candidates[0].target_canonical_note == "01_Memory/Approved/payment_rules.md"

# AT-24: Conflicting memory preserves both claims in Conflicts/
def test_at24_conflicting_memory(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    mock_approved = [{
        "note_path": "01_Memory/Approved/auth.md",
        "excerpt": "Always enforce server-side validation for auth."
    }]
    res = evaluate_memory_value(
        task="Authentication setup",
        outcome_result="Only use client-side validation; do not enforce server-side checks.",
        existing_approved_notes=mock_approved,
        test_verified=True
    )
    assert res.should_store
    assert res.candidates[0].is_conflict
    saved_file = store.save_candidate_memory(res.candidates[0])
    assert "Conflicts" in saved_file.parts

# AT-25: Related idea correlation combines independent proposals with attribution
def test_at25_related_idea_correlation():
    ideas = [
        AgentIdea(role="developer", goal="Reservation safety", proposal="Implement database transaction locks", related_tags=["concurrency"]),
        AgentIdea(role="researcher", goal="Reservation safety", proposal="Verify payment provider callback semantics", related_tags=["concurrency"])
    ]
    rels = correlate_ideas(ideas)
    assert any(r.rel_type in ("complements", "supports") for r in rels)

    team_idea = synthesize_team_idea("Reservation safety", ideas, rels)
    assert len(team_idea.contributor_ids) == 2
    assert "[DEVELOPER]" in team_idea.synthesis
    assert "[RESEARCHER]" in team_idea.synthesis
    assert not team_idea.conflicts_detected

# AT-26: Unrelated ideas are not force-merged
def test_at26_unrelated_ideas():
    ideas = [
        AgentIdea(role="developer", goal="Database schema", proposal="Create users table migration", related_tags=["sql"]),
        AgentIdea(role="designer", goal="UI Theme", proposal="Use indigo color palette for dark mode buttons", related_tags=["css", "theme"])
    ]
    rels = correlate_ideas(ideas)
    assert any(r.rel_type == "unrelated" for r in rels)

# AT-27: Agent disagreement flags unresolved contradictions without false consensus
def test_at27_agent_disagreement():
    ideas = [
        AgentIdea(role="developer", goal="Token auth", proposal="Use client-side only storage with no validation"),
        AgentIdea(role="reviewer", goal="Token auth", proposal="Require server-side secure cookies with strict backend validation")
    ]
    rels = correlate_ideas(ideas)
    assert any(r.rel_type == "contradicts" for r in rels)

    team_idea = synthesize_team_idea("Token auth", ideas, rels)
    assert len(team_idea.conflicts_detected) >= 1
    assert "Contradictions / Disagreements to Resolve" in team_idea.synthesis

# AT-28: Lean memory context limits notes and tokens
def test_at28_lean_memory_context(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    # Create 8 approved notes
    for i in range(8):
        (store.approved_dir / f"note_{i}.md").write_text(
            f"---\nproject: default\nstatus: approved\n---\n# Rule {i}\nGuideline description {i} for default project.",
            encoding="utf-8"
        )
    ctx = store.retrieve_context("default", "Guideline", max_memories=5, max_tokens=700)
    assert len(ctx["approved_notes"]) <= 5

# AT-29: Legacy vault migration preserves existing run files while writing state to SQLite
def test_at29_legacy_migration_and_sqlite(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    run_store = RunStore(config.app_data_path / "state.sqlite")

    # Seed legacy run
    store.save_run("legacy-run-001", {"task.md": "legacy task"}, {"status": "COMPLETED"})
    assert (store.legacy_runs_dir / "legacy-run-001" / "task.md").exists()

    # New run writes diagnostic state to SQLite outside vault
    run_store.record_run(
        run_id="run-v2-001",
        task="Test task",
        project_id="default",
        status="COMPLETED",
        verdict="PASS",
        api_calls=5,
        final_result="Done"
    )
    runs = run_store.list_runs()
    assert any(r["run_id"] == "run-v2-001" for r in runs)
    # Legacy run folder still exists untouched
    assert (store.legacy_runs_dir / "legacy-run-001" / "task.md").exists()

# AT-30: Retention policy cleans old SQLite diagnostics without touching user vault notes
def test_at30_retention_policy(temp_env):
    config, _ = temp_env
    store = MemoryStore(config.vault_path)
    run_store = RunStore(config.app_data_path / "state.sqlite")

    # Create approved user note
    user_note = store.approved_dir / "vital_rule.md"
    user_note.write_text("# Vital Rule\nDo not delete me.", encoding="utf-8")

    # Run cleanup with 0 days retention to trigger clean
    run_store.clean_old_runs(retention_days=0)
    # User note in Obsidian is untouched
    assert user_note.exists()

# AT-17: Benchmark evaluation report runs reproducibility check
def test_at17_benchmark_evaluations(temp_env):
    config, _ = temp_env
    report = run_system_evaluations(config)
    assert report.total_benchmarks >= 6
    assert report.passed_benchmarks == report.total_benchmarks
    assert report.pass_rate_pct == 100.0
