from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import uuid
import json
import base64
from datetime import datetime

from app.config import load_config
from app.orchestrator import MultiAgentOrchestrator
from app.memory_store import MemoryStore
from app.runs import RunStore
from app.memory_health import MemoryHealthService
from app.evaluations import run_system_evaluations, run_memory_on_off_experiment

config = load_config()
memory_store = MemoryStore(config.vault_path)
run_store = RunStore(config.app_data_path / "state.sqlite")
health_service = MemoryHealthService(config.vault_path, config.app_data_path)

api_app = FastAPI(
    title="Gemini Multi-Agent AI API",
    description="REST backend for Clean UI and Cytoscape Knowledge Graph",
    version="3.0"
)

# Enable CORS for local Vite dev server and production frontend
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_app.on_event("startup")
def startup_event():
    run_store.reconcile_startup_tasks()

@api_app.get("/api/status")
def get_status():
    storage_rep = memory_store.get_storage_report()
    return {
        "status": "connected",
        "gemini_model": config.gemini_model,
        "api_key_configured": bool(config.gemini_api_key),
        "vault_connected": config.vault_path.exists(),
        "vault_stats": storage_rep,
        "max_calls": config.max_model_calls_per_task,
        "timestamp": datetime.now().isoformat()
    }

@api_app.get("/api/conversations")
def list_conversations(project_id: str = "default"):
    convs = run_store.list_conversations(project_id=project_id)
    return {"conversations": convs}

@api_app.post("/api/conversations")
def create_conversation(payload: Dict[str, Any] = Body(...)):
    conv_id = payload.get("id") or f"conv-{uuid.uuid4().hex[:8]}"
    title = payload.get("title") or "New Task Session"
    project_id = payload.get("project_id") or "default"
    run_store.create_conversation(conv_id, title, project_id)
    return {"conversation_id": conv_id, "title": title, "project_id": project_id}

@api_app.get("/api/messages")
def get_messages(conversation_id: str):
    msgs = run_store.get_messages(conversation_id)
    return {"messages": msgs}

@api_app.post("/api/chat")
async def execute_chat(request: Request):
    content_type = request.headers.get("content-type", "")
    attachments: List[Tuple[str, bytes]] = []
    idempotency_key: Optional[str] = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        task = str(form.get("task", "")).strip()
        if not task:
            raise HTTPException(status_code=400, detail="Task prompt is required")
        project_id = str(form.get("project_id", "default"))
        conv_id = form.get("conversation_id")
        conv_id = str(conv_id) if conv_id else f"conv-{uuid.uuid4().hex[:8]}"
        allow_revise_val = form.get("allow_revise", "true")
        allow_revise = str(allow_revise_val).lower() in ("true", "1")
        collaborative_val = form.get("collaborative", "true")
        collaborative = str(collaborative_val).lower() in ("true", "1")
        mock_val = form.get("mock")
        if mock_val is not None:
            mock = str(mock_val).lower() in ("true", "1")
        else:
            mock = not bool(config.gemini_api_key)

        idempotency_key = form.get("idempotency_key") or form.get("client_request_id")
        if idempotency_key:
            idempotency_key = str(idempotency_key).strip()

        uploaded_files = form.getlist("files")
        for uf in uploaded_files:
            if hasattr(uf, "read"):
                file_bytes = await uf.read()
                filename = getattr(uf, "filename", "uploaded_file") or "uploaded_file"
                attachments.append((filename, file_bytes))
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        task = str(payload.get("task", "")).strip()
        if not task:
            raise HTTPException(status_code=400, detail="Task prompt is required")

        project_id = payload.get("project_id", "default")
        conv_id = payload.get("conversation_id") or f"conv-{uuid.uuid4().hex[:8]}"
        allow_revise = payload.get("allow_revise", True)
        collaborative = payload.get("collaborative", True)
        mock = payload.get("mock", not bool(config.gemini_api_key))
        idempotency_key = payload.get("idempotency_key") or payload.get("client_request_id")
        if idempotency_key:
            idempotency_key = str(idempotency_key).strip()

        json_attachments = payload.get("attachments", [])
        if isinstance(json_attachments, list):
            for att in json_attachments:
                if isinstance(att, dict) and "filename" in att and "content_base64" in att:
                    try:
                        b_data = base64.b64decode(att["content_base64"])
                        attachments.append((att["filename"], b_data))
                    except Exception:
                        pass
                elif isinstance(att, (tuple, list)) and len(att) == 2:
                    attachments.append((att[0], att[1] if isinstance(att[1], bytes) else str(att[1]).encode("utf-8")))

    # Save user message to database
    if attachments:
        file_names_str = ", ".join([f[0] for f in attachments])
        user_display = f"[Attached: {file_names_str}]\n\n{task}"
    else:
        user_display = task
    run_store.add_message(conv_id, "user", user_display)

    orchestrator = MultiAgentOrchestrator(config, mock_mode=mock)

    try:
        result = orchestrator.execute_task(
            task=task,
            project_id=project_id,
            allow_revise=allow_revise,
            collaborative=collaborative,
            conversation_id=conv_id,
            attachments=attachments,
            idempotency_key=idempotency_key
        )

        # Save assistant delivery
        run_store.add_message(
            conv_id,
            "assistant",
            result["result"],
            agent_name="orchestrator"
        )

        steps = result.get("steps") or [
            {"agent": "memory_manager", "status": "Completed"},
            {"agent": "planner", "status": "Completed"},
            {"agent": "developer", "status": "Completed"},
            {"agent": "tester", "status": result.get("run_metadata", {}).get("qa_status", "Passed")},
            {"agent": "reviewer", "status": result.get("verdict", "Approved")},
            {"agent": "learning_agent", "status": "Completed" if result.get("saved_candidate_ids") else "Evaluated"},
        ]

        return {
            "task_id": result.get("task_id", result["run_id"]),
            "run_id": result["run_id"],
            "status": result["status"],
            "verdict": result["verdict"],
            "result": result["result"],
            "steps": steps,
            "team_idea": result.get("team_idea"),
            "memory_decision": result.get("memory_decision"),
            "saved_candidate_ids": result.get("saved_candidate_ids", []),
            "run_metadata": result.get("run_metadata", {}),
            "logical_budget": result.get("logical_budget", {
                "used_known_attempts": result.get("run_metadata", {}).get("api_calls", 1),
                "limit": config.max_model_calls_per_task,
                "remaining": max(0, config.max_model_calls_per_task - result.get("run_metadata", {}).get("api_calls", 1))
            }),
            "provider_quota": result.get("provider_quota", {
                "status": "Not available — check Google AI Studio",
                "source": "https://aistudio.google.com/usage"
            }),
            "can_resume_now": result.get("can_resume_now", False),
            "pause_reason": result.get("pause_reason"),
            "attachments": result.get("attachments", []),
            "attachment_warnings": result.get("attachment_warnings", [])
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_msg = f"Task execution failed: {str(e)}"
        run_store.add_message(conv_id, "assistant", error_msg, agent_name="system")
        raise HTTPException(status_code=500, detail=error_msg)

@api_app.get("/api/tasks/{task_id}")
def get_task_endpoint(task_id: str):
    task = run_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    steps = run_store.get_step_checkpoints(task_id)
    can_resume = task["status"] in ("paused_budget", "paused_rate_limit", "paused_quota", "paused_transient", "interrupted")
    return {
        "task_id": task["id"],
        "task": task,
        "status": task["status"],
        "current_stage": task.get("current_stage"),
        "work_type": task.get("work_type"),
        "result": task.get("result") or task.get("partial_result") or "",
        "partial_result_available": bool(task.get("partial_result")),
        "pause_reason": task.get("last_error"),
        "can_resume_now": can_resume,
        "logical_budget": {
            "used_known_attempts": task.get("used_attempts", 0),
            "limit": task.get("budget_limit", 8),
            "remaining": max(0, task.get("budget_limit", 8) - task.get("used_attempts", 0))
        },
        "provider_quota": {
            "status": "Not available — check Google AI Studio",
            "source": "https://aistudio.google.com/usage"
        },
        "steps": [{"agent": s["agent_role"], "status": s["status"], "finished_at": s.get("finished_at")} for s in steps],
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at")
    }

@api_app.post("/api/tasks/{task_id}/resume")
def resume_task_endpoint(task_id: str, payload: Dict[str, Any] = Body(default={})):
    extra_budget = int(payload.get("extra_budget", 0))
    orchestrator = MultiAgentOrchestrator(config, mock_mode=not bool(config.gemini_api_key))
    try:
        result = orchestrator.resume_task(task_id, extra_budget=extra_budget)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume task: {str(e)}")

@api_app.post("/api/tasks/{task_id}/cancel")
def cancel_task_endpoint(task_id: str):
    success = run_store.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "Task cancelled successfully."
    }

@api_app.get("/api/usage/local")
def get_local_usage_endpoint(time_window_hours: int = 24):
    return run_store.get_local_usage(time_window_hours=time_window_hours)

@api_app.get("/api/agents")
def get_agents():
    # Retrieve seven logical specialist roles
    roles = [
        {"role": "planner", "title": "Planner", "description": "Interprets goals and breaks tasks down into structured phases", "status": "Idle"},
        {"role": "researcher", "title": "Researcher", "description": "Gathers relevant context, files, and background information", "status": "Idle"},
        {"role": "developer", "title": "Developer", "description": "Produces requested implementations and concrete solutions", "status": "Idle"},
        {"role": "tester", "title": "Tester", "description": "Formulates verification suites and reports truthful test outcomes", "status": "Idle"},
        {"role": "reviewer", "title": "Reviewer", "description": "Evaluates completeness, correctness, and adherence to boundaries", "status": "Idle"},
        {"role": "learning_agent", "title": "Learning Agent", "description": "Assesses durable value and extracts atomic verified lessons", "status": "Idle"},
        {"role": "memory_manager", "title": "Memory Manager", "description": "Retrieves, filters, audits, and organizes approved vault knowledge", "status": "Idle"},
    ]

    recent_runs = run_store.list_runs(limit=5)
    last_run = recent_runs[0] if recent_runs else None

    # Mark roles that contributed in the latest run
    if last_run and last_run.get("steps"):
        for step in last_run["steps"]:
            role_name = step.get("agent", "")
            for r in roles:
                if r["role"] == role_name:
                    r["status"] = "Completed"
                    r["last_task"] = last_run.get("task", "")

    return {
        "roles": roles,
        "recent_runs": recent_runs,
        "latest_team_idea": json.loads(last_run["team_idea_json"]) if last_run and last_run.get("team_idea_json") else None
    }

@api_app.get("/api/graph")
def get_knowledge_graph(project_id: Optional[str] = None):
    """
    Constructs the real 2D relationship network for Cytoscape.js:
    - Nodes: Projects, Agents, Tasks, Memories, Ideas
    - Edges: contributed_to, used_memory, belongs_to_project, produced_idea, related_to
    """
    nodes = []
    edges = []
    seen_nodes = set()

    # 1. Project Node
    proj_id = project_id or "default"
    proj_node_id = f"proj-{proj_id}"
    nodes.append({
        "data": {
            "id": proj_node_id,
            "label": f"Project: {proj_id}",
            "kind": "Project",
            "type": "project",
            "description": f"Active Project Scope ({proj_id})"
        }
    })
    seen_nodes.add(proj_node_id)

    # 2. Agent Nodes (The 7 logical roles)
    agent_roles = [
        ("planner", "Planner"),
        ("researcher", "Researcher"),
        ("developer", "Developer"),
        ("tester", "Tester"),
        ("reviewer", "Reviewer"),
        ("learning_agent", "Learning Agent"),
        ("memory_manager", "Memory Manager")
    ]
    for r_id, r_label in agent_roles:
        a_node_id = f"agent-{r_id}"
        nodes.append({
            "data": {
                "id": a_node_id,
                "label": r_label,
                "kind": "Agent",
                "type": "agent",
                "description": f"Specialist Role: {r_label}"
            }
        })
        seen_nodes.add(a_node_id)

    # 3. Approved Memory Nodes
    approved_files = list(memory_store.approved_dir.glob("*.md")) if memory_store.approved_dir.exists() else []
    for f in approved_files:
        mem_id = f"mem-{f.stem}"
        try:
            content = f.read_text(encoding="utf-8")
            title = f.stem
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break
            nodes.append({
                "data": {
                    "id": mem_id,
                    "label": title[:30] + ("..." if len(title) > 30 else ""),
                    "kind": "Memory",
                    "type": "memory",
                    "note_id": f.stem,
                    "status": "approved",
                    "description": content[:200]
                }
            })
            seen_nodes.add(mem_id)

            # Link Memory to Project
            edges.append({
                "data": {
                    "id": f"edge-{mem_id}-{proj_node_id}",
                    "source": mem_id,
                    "target": proj_node_id,
                    "label": "belongs_to_project",
                    "type": "belongs_to_project"
                }
            })
        except Exception:
            continue

    # 4. Recent Tasks & Associated Ideas from DB
    runs = run_store.list_runs(limit=15)
    for r in runs:
        task_node_id = f"task-{r['run_id'][:8]}"
        task_label = r["task"][:25] + ("..." if len(r["task"]) > 25 else "")
        nodes.append({
            "data": {
                "id": task_node_id,
                "label": f"Task: {task_label}",
                "kind": "Task",
                "type": "task",
                "run_id": r["run_id"],
                "status": r["status"],
                "description": r["task"]
            }
        })
        seen_nodes.add(task_node_id)

        # Edge: Task -> Project
        edges.append({
            "data": {
                "id": f"edge-{task_node_id}-{proj_node_id}",
                "source": task_node_id,
                "target": proj_node_id,
                "label": "belongs_to_project",
                "type": "belongs_to_project"
            }
        })

        # Edges: Agents -> Task (who contributed)
        if r.get("steps"):
            for step in r["steps"]:
                ag = step.get("agent")
                if ag:
                    agent_node = f"agent-{ag}"
                    if agent_node in seen_nodes:
                        edge_id = f"edge-{agent_node}-{task_node_id}"
                        edges.append({
                            "data": {
                                "id": edge_id,
                                "source": agent_node,
                                "target": task_node_id,
                                "label": "contributed_to",
                                "type": "contributed_to"
                            }
                        })

        # 5. Team Ideas (if task had collaboration)
        if r.get("team_idea_json"):
            try:
                ti = json.loads(r["team_idea_json"])
                idea_id = f"idea-{r['run_id'][:8]}"
                nodes.append({
                    "data": {
                        "id": idea_id,
                        "label": f"Idea: {ti.get('title', 'Team Idea')[:20]}",
                        "kind": "Idea",
                        "type": "idea",
                        "description": ti.get("synthesis", "")[:200]
                    }
                })
                seen_nodes.add(idea_id)

                # Edge: Task -> Idea
                edges.append({
                    "data": {
                        "id": f"edge-{task_node_id}-{idea_id}",
                        "source": task_node_id,
                        "target": idea_id,
                        "label": "produced_idea",
                        "type": "produced_idea"
                    }
                })
            except Exception:
                pass

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }

@api_app.get("/api/memory")
def get_memory_list():
    approved = []
    if memory_store.approved_dir.exists():
        for f in memory_store.approved_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            approved.append({
                "id": f.stem,
                "filename": f.name,
                "content": content,
                "preview": content[:150],
                "bytes": f.stat().st_size
            })

    pending = []
    if memory_store.pending_dir.exists():
        for f in memory_store.pending_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            pending.append({
                "id": f.stem,
                "filename": f.name,
                "content": content,
                "preview": content[:150],
                "bytes": f.stat().st_size
            })

    conflicts = []
    if memory_store.conflicts_dir.exists():
        for f in memory_store.conflicts_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            conflicts.append({
                "id": f.stem,
                "filename": f.name,
                "content": content,
                "bytes": f.stat().st_size
            })

    archived = []
    if memory_store.archived_dir.exists():
        for f in memory_store.archived_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            archived.append({
                "id": f.stem,
                "filename": f.name,
                "content": content,
                "bytes": f.stat().st_size
            })

    return {
        "approved": approved,
        "pending": pending,
        "conflicts": conflicts,
        "archived": archived
    }

@api_app.post("/api/memory/approve")
def approve_memory(payload: Dict[str, Any] = Body(...)):
    lesson_id = payload.get("lesson_id")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")

    edited_text = payload.get("edited_text")
    if edited_text:
        pending_file = memory_store.pending_dir / f"{lesson_id}.md"
        if pending_file.exists():
            pending_file.write_text(edited_text, encoding="utf-8")

    success = memory_store.approve_candidate(lesson_id)
    if not success:
        # Fallback to approve_run_lesson
        success = memory_store.approve_run_lesson(lesson_id)

    if not success:
        raise HTTPException(status_code=404, detail="Pending lesson not found")

    return {"success": True, "lesson_id": lesson_id, "status": "approved"}

@api_app.post("/api/memory/reject")
def reject_memory(payload: Dict[str, Any] = Body(...)):
    lesson_id = payload.get("lesson_id")
    reason = payload.get("reason", "Rejected via UI")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")

    success = memory_store.reject_candidate(lesson_id, reason=reason)
    if not success:
        success = memory_store.reject_run_lesson(lesson_id, reason=reason)

    if not success:
        raise HTTPException(status_code=404, detail="Pending lesson not found")

    return {"success": True, "lesson_id": lesson_id, "status": "rejected"}

@api_app.post("/api/memory/archive")
def archive_memory(payload: Dict[str, Any] = Body(...)):
    lesson_id = payload.get("lesson_id")
    reason = payload.get("reason", "Archived via UI")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")

    success = memory_store.archive_lesson(lesson_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail="Approved note not found")

    return {"success": True, "lesson_id": lesson_id, "status": "archived"}

@api_app.post("/api/memory/restore")
def restore_memory(payload: Dict[str, Any] = Body(...)):
    lesson_id = payload.get("lesson_id")
    if not lesson_id:
        raise HTTPException(status_code=400, detail="lesson_id is required")

    success = memory_store.restore_lesson(lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="Archived note not found")

    return {"success": True, "lesson_id": lesson_id, "status": "restored"}

@api_app.get("/api/memory/health")
def scan_memory_health():
    report = health_service.scan()
    return report.model_dump()

@api_app.post("/api/memory/health/fix")
def apply_health_fix(payload: Dict[str, Any] = Body(...)):
    finding_id = payload.get("finding_id")
    if not finding_id:
        raise HTTPException(status_code=400, detail="finding_id is required")

    res = health_service.apply_approved_fix(finding_id)
    return res

@api_app.post("/api/memory/health/restore")
def restore_health_backup(payload: Dict[str, Any] = Body(...)):
    backup_id = payload.get("backup_id")
    if not backup_id:
        raise HTTPException(status_code=400, detail="backup_id is required")

    success = health_service.restore_backup(backup_id)
    return {"success": success, "backup_id": backup_id}

@api_app.get("/api/automations")
def get_automations():
    return {
        "connected": False,
        "service": "n8n",
        "url": None,
        "message": "No automations connected. Configure n8n webhook URL to activate scheduled workflows.",
        "workflows": []
    }

@api_app.get("/api/settings")
def get_settings():
    return {
        "gemini_model": config.gemini_model,
        "has_api_key": bool(config.gemini_api_key),
        "vault_connected": config.vault_path.exists(),
        "vault_name": config.vault_path.name,
        "max_calls": config.max_model_calls_per_task,
        "max_revisions": config.max_revisions,
        "retention_days": config.run_metadata_retention_days,
        "theme": "dark"
    }
