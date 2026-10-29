import json
import pytest
from pathlib import Path
import tempfile
import shutil
from starlette.testclient import TestClient

from app.config import SystemConfig
from app.orchestrator import MultiAgentOrchestrator
from app.budget_manager import TaskBudget, TaskClassifier, TaskWorkType, UsageLedger
from app.gemini_client import (
    GeminiClient,
    GeminiRateLimitError,
    GeminiQuotaExhaustedError,
    GeminiTransientError,
    GeminiConfigurationError
)
from app.runs import RunStore
from app.api_server import api_app


@pytest.fixture
def temp_vault():
    temp_dir = Path(tempfile.mkdtemp())
    vault = temp_dir / "Obsidian-Brain"
    workspace = temp_dir / "workspace"
    app_data = temp_dir / "app_data"
    app_data.mkdir(parents=True)

    # Initialize basic vault structure
    (vault / "00_Project").mkdir(parents=True)
    (vault / "01_Memory" / "Approved").mkdir(parents=True)
    (vault / "01_Memory" / "Pending").mkdir(parents=True)
    (vault / "01_Memory" / "Rejected").mkdir(parents=True)
    (vault / "02_Agents").mkdir(parents=True)
    (vault / "03_Runs").mkdir(parents=True)
    (vault / "04_Feedback").mkdir(parents=True)
    workspace.mkdir(parents=True)

    (vault / "00_Project" / "project.md").write_text("# Project Test Baseline\n- Rule: Zero cost only.", encoding="utf-8")
    (vault / "01_Memory" / "shared_memory.md").write_text("# Shared Memory\n- Rule: Human approval required.", encoding="utf-8")

    yield vault, workspace, app_data, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def create_test_config(vault: Path, workspace: Path, app_data: Path, max_calls: int = 8) -> SystemConfig:
    return SystemConfig(
        project_root=vault.parent,
        vault_path=vault,
        workspace_path=workspace,
        app_data_path=app_data,
        gemini_api_key="mock-key",
        gemini_model="gemini-3.5-flash-lite",
        max_model_calls_per_task=max_calls,
        max_revisions=1,
        allow_live_tools=False
    )


# 1. Basic chat unchanged
def test_basic_chat_unchanged(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res = orchestrator.execute_task("Hello, can you help me understand Python?")
    assert res["status"] == "COMPLETED"
    assert res["verdict"] == "PASS"
    assert len(res["result"]) > 0
    assert "logical_budget" in res
    assert "provider_quota" in res
    assert res["provider_quota"]["status"] == "Not available — check Google AI Studio"


# 2. Smart routing: simple prompt uses 1 model call and selects developer role
def test_smart_routing_simple_prompt(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res = orchestrator.execute_task("What is Python?")
    assert res["status"] == "COMPLETED"
    assert res["verdict"] == "PASS"
    # Smart routing sends simple queries directly to developer (1 call target)
    assert res["logical_budget"]["used_known_attempts"] == 1
    # Check that planner was skipped
    planner_step = next((s for s in res["steps"] if s["agent"] == "planner"), None)
    assert planner_step is not None
    assert "Skipped (Direct Route)" in planner_step["status"]


# 3. Complex / architecture task invokes multi-agent collaborative pipeline
def test_complex_architecture_task_pipeline(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res = orchestrator.execute_task("Architect and implement a secure distributed payment processing pipeline", collaborative=True)
    assert res["status"] in ("COMPLETED", "LEARNING_PENDING")
    assert res["verdict"] == "PASS"

    agent_names = [s["agent"] for s in res["steps"]]
    assert "planner" in agent_names
    assert "team_room" in agent_names or "developer" in agent_names
    assert "reviewer" in agent_names
    assert res["team_idea"] is not None


# 4. Local budget enforced at zero
def test_local_budget_enforced_at_zero(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data, max_calls=0)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res = orchestrator.execute_task("Create a web scraper")
    assert res["status"] == "paused_budget"
    assert res["verdict"] == "BLOCKED"
    assert res["logical_budget"]["used_known_attempts"] == 0
    assert res["can_resume_now"] is True


# 5. Accurate accounting ledger
def test_accurate_accounting_ledger(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    res = orchestrator.execute_task("Draft a quick function")
    task_id = res["task_id"]

    db_task = orchestrator.run_store.get_task(task_id)
    assert db_task is not None
    assert db_task["used_attempts"] == res["logical_budget"]["used_known_attempts"]

    usage = orchestrator.run_store.get_local_usage()
    assert usage["total_requests"] >= 1
    assert usage["successful_requests"] >= 1
    assert "by_role" in usage


# 6. Temporary 429 backoff / pause (no infinite loop)
def test_temporary_429_backoff_and_paused_rate_limit(temp_vault, monkeypatch):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    def mock_generate(*args, **kwargs):
        raise GeminiRateLimitError("PAUSED_RATE_LIMIT: Rate limit reached. Paimon paused safely.")

    monkeypatch.setattr(orchestrator.client, "generate_json_response", mock_generate)

    res = orchestrator.execute_task("Test 429 rate limit")
    assert res["status"] == "paused_rate_limit"
    assert "PAUSED_RATE_LIMIT" in res["result"]
    assert res["can_resume_now"] is True


# 7. Quota exhaustion pauses task as paused_quota
def test_quota_exhausted_paused_quota(temp_vault, monkeypatch):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    def mock_generate(*args, **kwargs):
        raise GeminiQuotaExhaustedError("PAUSED_QUOTA: Daily quota exhausted.")

    monkeypatch.setattr(orchestrator.client, "generate_json_response", mock_generate)

    res = orchestrator.execute_task("Test quota exhaustion")
    assert res["status"] == "paused_quota"
    assert "PAUSED_QUOTA" in res["result"]
    assert res["can_resume_now"] is True


# 8. 503 transient error backoff and recoverable pause
def test_503_transient_error_paused_transient(temp_vault, monkeypatch):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    def mock_generate(*args, **kwargs):
        raise GeminiTransientError("PAUSED_TRANSIENT: Service temporarily unavailable (503).")

    monkeypatch.setattr(orchestrator.client, "generate_json_response", mock_generate)

    res = orchestrator.execute_task("Test transient error")
    assert res["status"] == "paused_transient"
    assert "PAUSED_TRANSIENT" in res["result"]
    assert res["can_resume_now"] is True


# 9. 401/403 no auto-retry (GeminiConfigurationError)
def test_401_403_no_auto_retry():
    client = GeminiClient(api_key="invalid-api-key", mock_mode=False)

    class MockHttp401Error(Exception):
        code = 401
        message = "API key not valid. Please pass a valid API key."

    def fail_with_401(*args, **kwargs):
        raise MockHttp401Error("API key not valid.")

    client.client = type("MockGenAiClient", (), {
        "models": type("MockModels", (), {"generate_content": fail_with_401})()
    })()

    with pytest.raises(GeminiConfigurationError):
        client.generate_json_response("Test prompt")
    # Verify no retry occurred (call_count was recorded once or 0 retries)
    assert client.call_count <= 1


# 10. App crash / restart reconciliation
def test_app_crash_restart_reconciliation(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    run_store = RunStore(app_data / "state.sqlite")

    # Insert a task left in "running" state
    run_store.create_task(
        task_id="crashed-task-1",
        task_text="Incomplete task during crash",
        project_id="test",
        budget_limit=8,
        status="running"
    )

    reconciled = run_store.reconcile_startup_tasks()
    assert "crashed-task-1" in reconciled

    task = run_store.get_task("crashed-task-1")
    assert task["status"] == "interrupted"


# 11. Resume task from checkpoint
def test_resume_task_from_checkpoint(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    # Create task with checkpoint for planner
    task_id = "test-resume-task"
    orchestrator.run_store.create_task(
        task_id=task_id,
        task_text="Build a robust cache layer",
        project_id="default",
        budget_limit=8,
        status="paused_rate_limit"
    )
    orchestrator.run_store.save_step_checkpoint(
        task_id=task_id,
        step_key="planner",
        agent_role="planner",
        status="Completed",
        result_data={
            "agent": "planner",
            "summary": "Cached Plan",
            "result": "Plan to build a robust cache layer",
            "next_action": "developer",
            "steps": ["Step 1"],
            "acceptance_criteria": ["Criteria 1"],
            "needs_research": False,
            "needs_testing": True
        }
    )

    # Resume task
    res = orchestrator.resume_task(task_id, extra_budget=4)
    assert res["status"] in ("COMPLETED", "LEARNING_PENDING")
    # Check that planner was loaded from cache
    planner_step = next((s for s in res["steps"] if s["agent"] == "planner"), None)
    assert planner_step is not None
    assert "Cached" in planner_step["status"]


# 12. Duplicate submission idempotency
def test_duplicate_submission_idempotency(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    idem_key = "client-req-999"
    res1 = orchestrator.execute_task("Idempotent task request", idempotency_key=idem_key)
    assert res1.get("is_deduplicated", False) is False

    # Second submission with the same idempotency key
    res2 = orchestrator.execute_task("Idempotent task request", idempotency_key=idem_key)
    assert res2.get("is_deduplicated") is True
    assert res2["task_id"] == res1["task_id"]


# 13. Cancel task stops execution
def test_cancel_task(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    task_id = "task-to-cancel"
    orchestrator.run_store.create_task(
        task_id=task_id,
        task_text="Long background task",
        project_id="default",
        budget_limit=8,
        status="paused_budget"
    )

    success = orchestrator.cancel_task(task_id)
    assert success is True

    task = orchestrator.run_store.get_task(task_id)
    assert task["status"] == "cancelled"


# 14. Phase 1 API endpoints
def test_phase1_api_endpoints():
    client = TestClient(api_app)

    # Test local usage endpoint
    usage_res = client.get("/api/usage/local")
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert "total_requests" in usage_data
    assert "google_account_quota_status" in usage_data

    # Test task submission with client_request_id (idempotency)
    chat_res = client.post("/api/chat", data={"task": "API endpoint test", "client_request_id": "api-idem-1", "mock": "true"})
    assert chat_res.status_code == 200
    data = chat_res.json()
    task_id = data["run_id"]

    # Test GET /api/tasks/{task_id}
    task_res = client.get(f"/api/tasks/{task_id}")
    assert task_res.status_code == 200
    task_info = task_res.json()
    assert task_info["task"]["id"] == task_id

    # Test POST /api/tasks/{task_id}/cancel
    cancel_res = client.post(f"/api/tasks/{task_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Test POST /api/tasks/{task_id}/resume
    resume_res = client.post(f"/api/tasks/{task_id}/resume", json={"extra_budget": 2})
    assert resume_res.status_code == 200


# 15. Memory preservation: Obsidian vault untouched by runtime logs
def test_obsidian_vault_untouched_by_runtime_logs(temp_vault):
    vault, workspace, app_data, _ = temp_vault
    config = create_test_config(vault, workspace, app_data)
    orchestrator = MultiAgentOrchestrator(config, mock_mode=True)

    # Run tasks with pauses, smart routes, and completions
    orchestrator.execute_task("Simple question 1")
    orchestrator.execute_task("Simple question 2")

    # Inspect 01_Memory directory
    approved_notes = list((vault / "01_Memory" / "Approved").glob("*.md"))
    pending_notes = list((vault / "01_Memory" / "Pending").glob("*.md"))
    rejected_notes = list((vault / "01_Memory" / "Rejected").glob("*.md"))

    # Verify no raw attempt logs, checkpoints, or SQLite tables were saved to 01_Memory
    for note in approved_notes + pending_notes + rejected_notes:
        content = note.read_text(encoding="utf-8")
        assert "api_attempts" not in content
        assert "task_steps" not in content
        assert "checkpoints" not in content
