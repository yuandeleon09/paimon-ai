import pytest
import shutil
import tempfile
from pathlib import Path

from app.config import SystemConfig
from app.memory_store import MemoryStore
from app.memory_health import MemoryHealthService
from app.memory_filter import evaluate_memory_value
from app.evaluations import run_system_evaluations, run_memory_on_off_experiment

@pytest.fixture
def temp_v3_env():
    temp_dir = Path(tempfile.mkdtemp())
    vault = temp_dir / "Obsidian-Brain"
    app_data = temp_dir / "app_data"
    workspace = temp_dir / "workspace"

    config = SystemConfig(
        project_root=temp_dir,
        vault_path=vault,
        workspace_path=workspace,
        app_data_path=app_data,
        gemini_model="gemini-3.5-flash-lite",
        gemini_api_key="mock-key",
        allow_live_tools=False
    )
    store = MemoryStore(vault)
    health_svc = MemoryHealthService(vault, app_data)
    yield config, store, health_svc, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

# 1. Trivial tasks add NO memory & High-value admission is gated
def test_v3_admission_zero_write_and_high_value_gate(temp_v3_env):
    _, _, _, _ = temp_v3_env
    # Trivial task
    t_trivial = evaluate_memory_value("What is 10 * 10?", "100")
    assert not t_trivial.should_store
    assert t_trivial.score < 7

    # High-value verified task
    t_valuable = evaluate_memory_value(
        task="Fix database connection timeout with exponential backoff retry",
        outcome_result="Apply exponential backoff with jitter on database transaction retry to prevent pool exhaustion.",
        test_verified=True
    )
    assert t_valuable.should_store
    assert t_valuable.score >= 7
    assert len(t_valuable.candidates) <= 2

# 2. Health check scan is strictly read-only and calculates actual bytes
def test_v3_health_scan_read_only_and_metrics(temp_v3_env):
    config, store, health_svc, _ = temp_v3_env
    # Create approved note
    sample_text = "---\nstatus: approved\nproject: default\n---\n# Rule\nStandard clean note for testing."
    note_path = store.approved_dir / "note1.md"
    note_path.write_text(sample_text, encoding="utf-8")
    original_mtime = note_path.stat().st_mtime

    rep = health_svc.scan()
    assert rep.approved_notes_count == 1
    assert rep.total_approved_bytes == note_path.stat().st_size
    # Read-only verification: file mtime untouched
    assert note_path.stat().st_mtime == original_mtime
    assert note_path.exists()

# 3. Sensitive content detection, diff preview, redaction, and rollback restoration
def test_v3_sensitive_content_redaction_and_rollback(temp_v3_env):
    _, store, health_svc, _ = temp_v3_env
    leaked_secret = "AIzaSyD-unmaskedLiveCredential123456789012"
    secret_note = store.approved_dir / "secret_note.md"
    original_content = f"---\nstatus: approved\nproject: default\n---\nKey: {leaked_secret}\nVerified rule."
    secret_note.write_text(original_content, encoding="utf-8")

    rep = health_svc.scan()
    sens_findings = [f for f in rep.findings if f.finding_type == "sensitive_content"]
    assert len(sens_findings) == 1
    f = sens_findings[0]
    assert f.risk_level == "HIGH"
    assert f.suggested_action == "redact"
    assert "[REDACTED_SECRET]" in f.proposed_diff

    # Apply approved fix
    res = health_svc.apply_approved_fix(f.finding_id)
    assert res["success"] is True
    backup_id = res["backup_id"]
    # Secret must now be redacted in the note
    redacted_content = secret_note.read_text(encoding="utf-8")
    assert "[REDACTED_SECRET]" in redacted_content
    assert leaked_secret not in redacted_content

    # Rollback restoration from versioned backup
    restored_ok = health_svc.restore_backup(backup_id)
    assert restored_ok is True
    assert secret_note.read_text(encoding="utf-8") == original_content

# 4. Duplicate detection, proposed merge, non-destructive archival, and rollback
def test_v3_duplicate_detection_merge_and_backup(temp_v3_env):
    _, store, health_svc, _ = temp_v3_env
    # Two notes sharing 4+ significant semantic words
    note1 = store.approved_dir / "note_canonical.md"
    note1.write_text("---\nstatus: approved\nproject: default\n---\nAuthentication session timeout security guideline.", encoding="utf-8")
    note2 = store.approved_dir / "note_dup.md"
    note2.write_text("---\nstatus: approved\nproject: default\n---\nAuthentication session timeout security policy supplement.", encoding="utf-8")

    rep = health_svc.scan()
    dup_findings = [f for f in rep.findings if f.finding_type == "duplicate"]
    assert len(dup_findings) >= 1
    finding = dup_findings[0]
    assert finding.suggested_action == "merge"
    assert "note_canonical" in finding.affected_note_ids
    assert "note_dup" in finding.affected_note_ids

    # Apply approved merge
    res = health_svc.apply_approved_fix(finding.finding_id)
    assert res["success"] is True
    # note2 should be archived, NOT deleted
    assert not note2.exists()
    assert (store.archived_dir / "note_dup.md").exists()
    # Canonical note should have merged content
    assert "Merged Guideline" in note1.read_text(encoding="utf-8")

    # Restore from backup
    rest_ok = health_svc.restore_backup(res["backup_id"])
    assert rest_ok is True
    assert note2.exists()

# 5. Direct contradiction detection and conflict preservation
def test_v3_contradiction_preservation(temp_v3_env):
    _, store, health_svc, _ = temp_v3_env
    note_a = store.approved_dir / "policy_a.md"
    note_a.write_text("---\nstatus: approved\nproject: default\n---\nAlways use client-side only token verification.", encoding="utf-8")
    note_b = store.approved_dir / "policy_b.md"
    note_b.write_text("---\nstatus: approved\nproject: default\n---\nAlways enforce server-side validation on every token.", encoding="utf-8")

    rep = health_svc.scan()
    con_findings = [f for f in rep.findings if f.finding_type == "contradiction"]
    assert len(con_findings) >= 1
    cf = con_findings[0]
    assert cf.risk_level == "HIGH"
    assert cf.suggested_action == "resolve_conflict"
    # Verify neither note was modified or removed
    assert note_a.exists()
    assert note_b.exists()

# 6. Oversized note detection
def test_v3_oversized_note_detection(temp_v3_env):
    _, store, health_svc, _ = temp_v3_env
    large_body = "word " * 160
    large_note = store.approved_dir / "oversized.md"
    large_note.write_text(f"---\nstatus: approved\nproject: default\n---\n{large_body}", encoding="utf-8")

    rep = health_svc.scan()
    over_findings = [f for f in rep.findings if f.finding_type == "oversized"]
    assert len(over_findings) == 1
    assert over_findings[0].suggested_action == "condense"

# 7. Outdated note detection (elapsed review_after date)
def test_v3_outdated_note_detection(temp_v3_env):
    _, store, health_svc, _ = temp_v3_env
    stale_note = store.approved_dir / "stale.md"
    stale_note.write_text("---\nstatus: approved\nproject: default\nreview_after: 2021-01-01\n---\n# Old Rule", encoding="utf-8")

    rep = health_svc.scan()
    out_findings = [f for f in rep.findings if f.finding_type == "outdated"]
    assert len(out_findings) == 1
    assert out_findings[0].suggested_action == "review_date"

# 8. Archival and Restoration lifecycle with isolation
def test_v3_archive_and_restore_lifecycle(temp_v3_env):
    _, store, _, _ = temp_v3_env
    rule_note = store.approved_dir / "lifecycle_rule.md"
    rule_note.write_text("---\nstatus: approved\nproject: default\n---\n# Rule\nUnique lifecycle guideline.", encoding="utf-8")

    # Before archive, retrievable
    ctx1 = store.retrieve_context("default", "lifecycle guideline")
    assert any("lifecycle_rule" in n.note_path for n in ctx1["approved_notes"])

    # Archive
    arch_ok = store.archive_lesson("lifecycle_rule", reason="Superceded")
    assert arch_ok is True
    assert not rule_note.exists()
    assert (store.archived_dir / "lifecycle_rule.md").exists()

    # Excluded from retrieval
    ctx2 = store.retrieve_context("default", "lifecycle guideline")
    assert not any("lifecycle_rule" in n.note_path for n in ctx2["approved_notes"])

    # Restore
    rest_ok = store.restore_lesson("lifecycle_rule")
    assert rest_ok is True
    assert rule_note.exists()
    assert not (store.archived_dir / "lifecycle_rule.md").exists()

    # Retrievable once again
    ctx3 = store.retrieve_context("default", "lifecycle guideline")
    assert any("lifecycle_rule" in n.note_path for n in ctx3["approved_notes"])

# 9. Memory ON vs OFF comparative experiment
def test_v3_memory_on_off_experiment(temp_v3_env):
    config, store, _, _ = temp_v3_env
    # Seed an approved note
    note = store.approved_dir / "auth_rule.md"
    note.write_text("---\nstatus: approved\nproject: default\n---\nAlways enforce server-side validation.", encoding="utf-8")

    exp_report = run_memory_on_off_experiment(config)
    assert exp_report.tasks_count >= 3
    assert exp_report.memory_on_pass_rate_pct > exp_report.memory_off_pass_rate_pct
    assert exp_report.difference_pct > 0
    # Verify isolation
    for tr in exp_report.task_results:
        assert tr.memories_used_off == 0
        assert tr.memory_on_success is True

    # Verify report saved to disk in app_data/evaluations/
    eval_files = list((config.app_data_path / "evaluations").glob("experiment_*.json"))
    assert len(eval_files) >= 1

# 10. System evaluations 10 deterministic benchmarks
def test_v3_system_evaluations_suite(temp_v3_env):
    config, _, _, _ = temp_v3_env
    eval_rep = run_system_evaluations(config)
    assert eval_rep.total_benchmarks == 10
    assert eval_rep.passed_benchmarks == 10
    assert eval_rep.pass_rate_pct == 100.0
