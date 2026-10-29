import pytest
from pathlib import Path
import shutil
import tempfile
import json

from app.config import SystemConfig
from app.memory_store import MemoryStore
from app.gemini_client import GeminiClient
from app.orchestrator import MultiAgentOrchestrator
from app.safety import sanitize_text, contains_secret
from app.tools.safe_test_runner import run_bounded_test

@pytest.fixture
def temp_vault():
    temp_dir = Path(tempfile.mkdtemp())
    vault = temp_dir / "Obsidian-Brain"
    workspace = temp_dir / "workspace"
    
    # Initialize basic vault structure
    (vault / "00_Project").mkdir(parents=True)
    (vault / "01_Memory" / "Approved").mkdir(parents=True)
    (vault / "01_Memory" / "Pending").mkdir(parents=True)
    (vault / "01_Memory" / "Rejected").mkdir(parents=True)
    (vault / "02_Agents").mkdir(parents=True)
    (vault / "03_Runs").mkdir(parents=True)
    (vault / "04_Feedback").mkdir(parents=True)
    workspace.mkdir(parents=True)

    # Seed baseline
    (vault / "00_Project" / "project.md").write_text("# Project Test Baseline\n- Rule: Zero cost only.", encoding="utf-8")
    (vault / "01_Memory" / "shared_memory.md").write_text("# Shared Memory\n- Rule: Human approval required.", encoding="utf-8")

    yield vault, workspace, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def create_test_config(vault: Path, workspace: Path, max_calls: int = 12, max_revisions: int = 1) -> SystemConfig:
    return SystemConfig(
        project_root=vault.parent,
        vault_path=vault,
        workspace_path=workspace,
        gemini_api_key="mock-key",
        gemini_model="gemini-2.5-flash",
        max_review_revisions=max_revisions,
        max_api_calls_per_run=max_calls,
        allow_live_tools=False
    )

# 1. Valid Gemini call (mocked / structured format)
def test_valid_gemini_call(temp_vault):
    vault, workspace, _ = temp_vault
    client = GeminiClient(api_key="mock", mock_mode=True)
    res = client.generate_json_response("Plan task", system_instruction="Planner prompt")
    assert res["agent"] == "planner"
    assert "acceptance_criteria" in res
    assert client.call_count == 1

# 2. Vault note read
def test_vault_note_read(temp_vault):
    vault, workspace, _ = temp_vault
    store = MemoryStore(vault)
    baseline = store.load_project_baseline()
    assert "Zero cost only" in baseline
    assert "Human approval required" in baseline

# 3. Two different tasks get separate run folders
def test_separate_run_folders(temp_vault):
    vault, workspace, _ = temp_vault
    config = create_test_config(vault, workspace)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res1 = orchestrator.execute_task("Task 1: Email validator")
    import time
    time.sleep(1.1)  # Ensure unique second timestamp
    res2 = orchestrator.execute_task("Task 2: URL validator")

    assert res1["run_id"] != res2["run_id"]
    folder1 = vault / "03_Runs" / res1["run_id"]
    folder2 = vault / "03_Runs" / res2["run_id"]
    assert folder1.exists() and (folder1 / "task.md").exists()
    assert folder2.exists() and (folder2 / "task.md").exists()

# 4. Reviewer triggers at most one revision
def test_reviewer_bounded_revision(temp_vault):
    vault, workspace, _ = temp_vault
    config = create_test_config(vault, workspace, max_revisions=1)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    # Monkey patch reviewer to request REVISE
    orig_run = orchestrator.runner.run_agent
    def mock_run(agent_name, task, ctx):
        res = orig_run(agent_name, task, ctx)
        if agent_name == "reviewer":
            res.verdict = "REVISE"
            from app.validators import ReviewIssue
            res.issues = [ReviewIssue(severity="HIGH", description="Needs fix", remediation="Fix it")]
        return res
    orchestrator.runner.run_agent = mock_run

    result = orchestrator.execute_task("Task with revision")
    # Must cap revision at max_revisions (1)
    assert result["run_metadata"]["revisions_count"] == 1
    assert result["verdict"] == "REVISE"

# 5. QA never claims non-executed tests passed
def test_qa_never_claims_unrun_tests_passed(temp_vault):
    vault, workspace, _ = temp_vault
    config = create_test_config(vault, workspace)
    config.allow_live_tools = False

    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)
    res = orchestrator.execute_task("Build function with test")
    
    qa_file = vault / "03_Runs" / res["run_id"] / "qa.md"
    assert qa_file.exists()
    qa_content = qa_file.read_text(encoding="utf-8")
    assert "Executed: False" in qa_content
    assert "Overall Status**: `NOT_RUN`" in qa_content

# 6. Pending lesson is not included in trusted retrieval
def test_pending_lesson_not_in_trusted_retrieval(temp_vault):
    vault, workspace, _ = temp_vault
    store = MemoryStore(vault)
    
    # Save a pending lesson
    store.save_pending_lesson("run-pending-1", [{"claim": "Secret pending knowledge", "reason": "test"}])
    assert (vault / "01_Memory" / "Pending" / "run-pending-1.md").exists()

    # Query context
    ctx = store.retrieve_context("default", "Secret pending knowledge")
    # Retrieved notes must be empty because it is strictly Pending
    assert len(ctx["approved_notes"]) == 0

# 7. Approved lesson is retrieved on relevant next task
def test_approved_lesson_retrieved(temp_vault):
    vault, workspace, _ = temp_vault
    store = MemoryStore(vault)

    # Save and approve
    store.save_pending_lesson("run-app-1", [{"claim": "Always sanitize email inputs.", "evidence": "Run evidence", "reason": "Security"}])
    store.approve_run_lesson("run-app-1")
    assert (vault / "01_Memory" / "Approved" / "run-app-1.md").exists()

    # Retrieve with relevant keyword
    ctx = store.retrieve_context("default", "Validate email inputs safely")
    assert len(ctx["approved_notes"]) >= 1
    assert "Always sanitize email inputs." in ctx["approved_notes"][0].excerpt

# 8. Rejected lesson remains excluded
def test_rejected_lesson_remains_excluded(temp_vault):
    vault, workspace, _ = temp_vault
    store = MemoryStore(vault)

    store.save_pending_lesson("run-rej-1", [{"claim": "Do not sanitize inputs.", "reason": "Bad idea"}])
    store.reject_run_lesson("run-rej-1", reason="Violates security standard")
    
    assert (vault / "01_Memory" / "Rejected" / "run-rej-1.md").exists()
    assert not (vault / "01_Memory" / "Pending" / "run-rej-1.md").exists()

    ctx = store.retrieve_context("default", "sanitize inputs")
    assert len(ctx["approved_notes"]) == 0

# 9. Invalid API key and quota limit fail safely
def test_quota_limit_fails_safely():
    client = GeminiClient(api_key="mock", max_calls=2, mock_mode=True)
    client.generate_json_response("call 1")
    client.generate_json_response("call 2")
    
    with pytest.raises(RuntimeError) as exc_info:
        client.generate_json_response("call 3")
    assert "PAUSED_QUOTA" in str(exc_info.value)

# 10. Secrets are not copied into vault outputs
def test_secrets_not_copied_into_outputs(temp_vault):
    vault, workspace, _ = temp_vault
    secret_key = "AIzaSyD-dummyGoogleApiKey123456789012"
    raw_text = f"My secret key is {secret_key} and should be hidden."
    
    sanitized = sanitize_text(raw_text)
    assert secret_key not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

    # Also test orchestrator artifact sanitization
    store = MemoryStore(vault)
    store.save_run("run-sec-1", {"leak.md": raw_text}, {"meta": raw_text})
    saved_file = vault / "03_Runs" / "run-sec-1" / "leak.md"
    assert secret_key not in saved_file.read_text(encoding="utf-8")
