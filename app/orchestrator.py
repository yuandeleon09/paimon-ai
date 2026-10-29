import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.config import SystemConfig
from app.memory_store import MemoryStore
from app.gemini_client import (
    GeminiClient,
    GeminiQuotaExhaustedError,
    GeminiRateLimitError,
    GeminiTransientError,
    GeminiConfigurationError
)
from app.agent_runner import AgentRunner
from app.task_router import TaskRouter
from app.tools.safe_test_runner import run_bounded_test
from app.collaboration import AgentIdea, Relationship, TeamIdea, correlate_ideas, synthesize_team_idea
from app.memory_filter import evaluate_memory_value, MemoryCandidate
from app.runs import RunStore
from app.attachment_service import AttachmentIngestionService, AttachmentEvidencePacket
from app.budget_manager import TaskBudget, TaskClassifier, TaskWorkType

class MultiAgentOrchestrator:
    def __init__(self, config: SystemConfig, mock_mode: bool = False):
        self.config = config
        self.mock_mode = mock_mode
        self.memory_store = MemoryStore(config.vault_path)
        self.run_store = RunStore(config.app_data_path / "state.sqlite")
        self.client = GeminiClient(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
            max_calls=config.max_model_calls_per_task,
            mock_mode=mock_mode,
            run_store=self.run_store
        )
        self.runner = AgentRunner(self.client, self.memory_store)

    def _run_agent(
        self,
        agent_name: str,
        task: str,
        context_data: Dict[str, Any],
        task_budget: Optional[TaskBudget] = None,
        task_id: str = "default",
        step_key: str = ""
    ):
        import inspect
        sig = inspect.signature(self.runner.run_agent)
        kwargs = {}
        if "task_budget" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs["task_budget"] = task_budget
        if "task_id" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs["task_id"] = task_id
        if "step_key" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            kwargs["step_key"] = step_key
        return self.runner.run_agent(agent_name, task, context_data, **kwargs)

    def execute_task(
        self,
        task: str,
        project_id: str = "default",
        allow_revise: bool = True,
        collaborative: bool = False,
        feedback: Optional[str] = None,
        conversation_id: Optional[str] = None,
        attachments: Optional[List[Tuple[str, bytes]]] = None,
        idempotency_key: Optional[str] = None,
        task_id: Optional[str] = None,
        resume_existing: bool = False
    ) -> Dict[str, Any]:
        self.client.reset_call_count()

        # Idempotency / Duplicate Submission Check
        if idempotency_key and not resume_existing:
            existing_task = self.run_store.get_task_by_idempotency(idempotency_key)
            if existing_task and existing_task.get("status", "").lower() in ("completed", "completed_partial", "running", "queued", "learning_pending"):
                existing_steps = self.run_store.get_step_checkpoints(existing_task["id"])
                return {
                    "task_id": existing_task["id"],
                    "run_id": existing_task["id"],
                    "status": existing_task["status"],
                    "verdict": "PASS" if existing_task.get("status", "").lower() in ("completed", "learning_pending") else "PARTIAL",
                    "result": existing_task.get("result") or existing_task.get("partial_result") or "",
                    "is_deduplicated": True,
                    "steps": [{"agent": s["agent_role"], "status": s["status"]} for s in existing_steps],
                    "logical_budget": {
                        "used_known_attempts": existing_task["used_attempts"],
                        "limit": existing_task["budget_limit"],
                        "remaining": max(0, existing_task["budget_limit"] - existing_task["used_attempts"])
                    },
                    "provider_quota": {
                        "status": "Not available — check Google AI Studio",
                        "source": "https://aistudio.google.com/usage"
                    },
                    "can_resume_now": existing_task["status"] in ("paused_budget", "paused_rate_limit", "paused_quota", "paused_transient", "interrupted"),
                    "run_metadata": {"task": existing_task["task_text"], "api_calls": existing_task["used_attempts"]}
                }

        run_id = task_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        run_status = "CREATED"
        artifacts: Dict[str, str] = {}
        pipeline_steps: List[Dict[str, Any]] = []
        revision_count = 0
        max_revisions = self.config.max_revisions if allow_revise else 0
        current_result = ""

        # Initialize or restore Task Budget
        existing_record = self.run_store.get_task(run_id)
        if existing_record and resume_existing:
            budget_limit = existing_record["budget_limit"]
            used_attempts = existing_record["used_attempts"]
        else:
            budget_limit = self.config.max_model_calls_per_task
            used_attempts = 0

        budget = TaskBudget(max_attempts=budget_limit, used_attempts=used_attempts)

        # Deterministic Task Classification & Work Type Selection (Paimon Phase 1)
        work_type, recommended_route = TaskClassifier.classify(
            task,
            has_attachments=bool(attachments),
            collaborative=collaborative
        )

        if not existing_record:
            self.run_store.create_task(
                task_id=run_id,
                task_text=task,
                project_id=project_id,
                conversation_id=conversation_id,
                budget_limit=budget.max_attempts,
                idempotency_key=idempotency_key,
                work_type=work_type.value
            )
        self.run_store.update_task_state(run_id, status="running", current_stage="starting")

        # Load any existing checkpoints from prior steps
        checkpoints = {cp["step_key"]: cp for cp in self.run_store.get_step_checkpoints(run_id)}

        def is_cancelled() -> bool:
            t = self.run_store.get_task(run_id)
            return bool(t and t.get("status") == "cancelled")

        def make_paused_response(status_code: str, reason: str, partial_res: str = "") -> Dict[str, Any]:
            self.run_store.update_task_state(
                run_id,
                status=status_code,
                partial_result=partial_res,
                last_error=reason,
                used_attempts=budget.used_attempts
            )
            return {
                "task_id": run_id,
                "run_id": run_id,
                "status": status_code,
                "verdict": "PARTIAL" if partial_res else "BLOCKED",
                "result": partial_res or f"Task paused: {reason}",
                "partial_result_available": bool(partial_res),
                "can_resume_now": True,
                "pause_reason": reason,
                "steps": pipeline_steps,
                "logical_budget": budget.to_dict(),
                "provider_quota": {
                    "status": "Not available — check Google AI Studio",
                    "source": "https://aistudio.google.com/usage"
                },
                "run_metadata": {
                    "run_id": run_id,
                    "project_id": project_id,
                    "task": task,
                    "status": status_code,
                    "verdict": "PARTIAL",
                    "api_calls": budget.used_attempts,
                    "completed_at": datetime.now().isoformat()
                },
                "attachments": [
                    {
                        "filename": f.filename,
                        "extension": f.extension,
                        "size_bytes": f.size_bytes,
                        "category": f.category,
                        "warnings": f.warnings,
                    }
                    for f in evidence_packet.files
                ] if evidence_packet.has_attachments else [],
                "attachment_warnings": evidence_packet.warnings
            }

        # Step 0: Attachment Processing & Multimodal Analysis (V4)
        evidence_packet = AttachmentEvidencePacket(has_attachments=False)
        if attachments:
            attachment_service = AttachmentIngestionService()
            evidence_packet = attachment_service.validate_and_process(attachments)
            if evidence_packet.has_attachments:
                if "attachment_analyst" in checkpoints:
                    pipeline_steps.append({
                        "agent": "attachment_analyst",
                        "status": f"Processed {len(evidence_packet.files)} file(s) (Cached)"
                    })
                else:
                    if not budget.can_call():
                        return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit. Your Google daily quota is not known.", current_result)
                    try:
                        attachment_service.analyze_multimodal_evidence(task, evidence_packet, self.client)
                        budget.consume_attempt()
                        self.run_store.save_step_checkpoint(run_id, "attachment_analyst", "attachment_analyst", "Completed", {"summary": evidence_packet.analysis_summary})
                        pipeline_steps.append({
                            "agent": "attachment_analyst",
                            "status": f"Processed {len(evidence_packet.files)} file(s)"
                        })
                    except GeminiRateLimitError as e:
                        return make_paused_response("paused_rate_limit", str(e), current_result)
                    except GeminiQuotaExhaustedError as e:
                        return make_paused_response("paused_quota", str(e), current_result)
                    except GeminiTransientError as e:
                        return make_paused_response("paused_transient", str(e), current_result)
                artifacts["attachments.md"] = evidence_packet.to_evidence_markdown()

        # Check early budget guard
        if not budget.can_call():
            return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit. Your Google daily quota is not known.", current_result)

        # Check cancellation
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        # Step 1: Initial Task Document
        artifacts["task.md"] = f"# Task: {task}\n\n- **Run ID**: {run_id}\n- **Project**: {project_id}\n- **Started**: {datetime.now().isoformat()}\n"

        # ----------------------------------------------------------------------------------
        # PATH A: SIMPLE_DIRECT WORK TYPE (Single Agent Execution, Target: 1 call)
        # ----------------------------------------------------------------------------------
        if work_type == TaskWorkType.SIMPLE_DIRECT:
            run_status = "COMPLETED"
            pipeline_steps.append({"agent": "planner", "status": "Skipped (Direct Route)"})

            if "developer" in checkpoints:
                dev_data = json.loads(checkpoints["developer"]["result_json"])
                current_result = dev_data.get("result", "")
                pipeline_steps.append({"agent": "developer", "status": "Completed (Cached)"})
            else:
                if not budget.can_call():
                    return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit. Your Google daily quota is not known.", current_result)
                try:
                    dev_output = self._run_agent("developer", task, {"task": task}, task_budget=budget, task_id=run_id, step_key="developer")
                    current_result = dev_output.result
                    self.run_store.save_step_checkpoint(run_id, "developer", "developer", "Completed", dev_output.model_dump())
                    pipeline_steps.append({"agent": "developer", "status": "Completed"})
                except GeminiRateLimitError as e:
                    return make_paused_response("paused_rate_limit", str(e), current_result)
                except GeminiQuotaExhaustedError as e:
                    return make_paused_response("paused_quota", str(e), current_result)
                except GeminiTransientError as e:
                    return make_paused_response("paused_transient", str(e), current_result)

            artifacts["final.md"] = current_result
            run_metadata = {
                "run_id": run_id,
                "project_id": project_id,
                "task": task,
                "status": run_status,
                "verdict": "PASS",
                "revisions_count": 0,
                "qa_status": "PASSED",
                "api_calls": budget.used_attempts,
                "memory_score": 0,
                "memory_stored": False,
                "memory_rationale": "Direct simple query; no durable long-term lesson created.",
                "completed_at": datetime.now().isoformat()
            }
            self.memory_store.save_run(run_id, artifacts, run_metadata)
            self.run_store.record_run(
                run_id=run_id,
                task=task,
                project_id=project_id,
                status=run_status,
                verdict="PASS",
                api_calls=budget.used_attempts,
                final_result=current_result,
                conversation_id=conversation_id
            )
            self.run_store.update_task_state(run_id, status=run_status, current_stage="completed", result=current_result, used_attempts=budget.used_attempts)

            return {
                "task_id": run_id,
                "run_id": run_id,
                "status": run_status,
                "verdict": "PASS",
                "result": current_result,
                "artifacts": artifacts,
                "steps": pipeline_steps,
                "logical_budget": budget.to_dict(),
                "provider_quota": {"status": "Not available — check Google AI Studio"},
                "can_resume_now": False,
                "run_metadata": run_metadata,
                "attachments": [],
                "attachment_warnings": []
            }

        # ----------------------------------------------------------------------------------
        # PATH B & C: MULTI-STEP, CODING, DOCUMENT, OR COLLABORATIVE WORKFLOW
        # ----------------------------------------------------------------------------------

        # Step 2: Retrieve Context via Memory Manager
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        run_status = "CONTEXT_READY"
        memory_context = self.memory_store.retrieve_context(
            project_id=project_id,
            query=task,
            max_memories=self.config.max_retrieved_memories,
            max_tokens=self.config.max_memory_context_tokens
        )

        if "memory_manager" in checkpoints:
            mm_data = json.loads(checkpoints["memory_manager"]["result_json"])
            pipeline_steps.append({"agent": "memory_manager", "status": "Completed (Cached)"})
        else:
            if not budget.can_call():
                return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
            try:
                memory_manager_output = self._run_agent("memory_manager", task, memory_context, task_budget=budget, task_id=run_id, step_key="memory_manager")
                self.run_store.save_step_checkpoint(run_id, "memory_manager", "memory_manager", "Completed", memory_manager_output.model_dump())
                pipeline_steps.append({"agent": "memory_manager", "status": "Completed"})
            except GeminiRateLimitError as e:
                return make_paused_response("paused_rate_limit", str(e), current_result)
            except GeminiQuotaExhaustedError as e:
                return make_paused_response("paused_quota", str(e), current_result)
            except GeminiTransientError as e:
                return make_paused_response("paused_transient", str(e), current_result)

        context_md = [
            f"# Context for Task: {task}",
            f"- **Project Scope**: {project_id}",
            "",
            "## Baseline Rules & Constraints",
            memory_context.get("baseline", "None defined."),
            "",
            "## Approved Knowledge Excerpts",
        ]
        for note in memory_context.get("approved_notes", []):
            context_md.append(f"### Source: `{note.note_path}` (Trust: {note.trust_status})")
            context_md.append(note.excerpt)
            context_md.append("")
        artifacts["context.md"] = "\n".join(context_md)

        # Step 3: Planner
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        run_status = "PLANNED"
        if "planner" in checkpoints:
            planner_data = json.loads(checkpoints["planner"]["result_json"])
            from app.validators import PlannerOutput
            planner_output = PlannerOutput.model_validate(planner_data)
            pipeline_steps.append({"agent": "planner", "status": "Completed (Cached)"})
        else:
            if not budget.can_call():
                return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
            try:
                planner_context = {
                    "baseline": memory_context.get("baseline", ""),
                    "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
                }
                planner_output = self._run_agent("planner", task, planner_context, task_budget=budget, task_id=run_id, step_key="planner")
                self.run_store.save_step_checkpoint(run_id, "planner", "planner", "Completed", planner_output.model_dump())
                pipeline_steps.append({"agent": "planner", "status": "Completed"})
            except GeminiRateLimitError as e:
                return make_paused_response("paused_rate_limit", str(e), current_result)
            except GeminiQuotaExhaustedError as e:
                return make_paused_response("paused_quota", str(e), current_result)
            except GeminiTransientError as e:
                return make_paused_response("paused_transient", str(e), current_result)

        plan_md = [
            f"# Plan for Task: {task}",
            f"**Summary**: {planner_output.summary}",
            "",
            "## Steps",
            *[f"- {step}" for step in planner_output.steps],
            "",
            "## Acceptance Criteria",
            *[f"- [ ] {ac}" for ac in planner_output.acceptance_criteria],
        ]
        artifacts["plan.md"] = "\n".join(plan_md)

        # Step 4: Optional Team Room Collaboration (Priority 2)
        team_idea: Optional[TeamIdea] = None
        is_collab = collaborative or (work_type == TaskWorkType.COMPLEX_COLLABORATIVE)

        if is_collab:
            if is_cancelled():
                return make_paused_response("cancelled", "Task was cancelled by user.", current_result)
            run_status = "TEAM_COLLABORATING"

            if "team_room" in checkpoints:
                tr_data = json.loads(checkpoints["team_room"]["result_json"])
                team_idea = TeamIdea.model_validate(tr_data)
                pipeline_steps.append({"agent": "team_room", "status": "Completed (Cached)"})
            else:
                if not budget.can_call():
                    return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
                try:
                    specialist_roles = ["developer", "researcher"]
                    idea_cards: List[AgentIdea] = []
                    for role in specialist_roles:
                        idea_prompt = f"Submit an independent concise AgentIdea card for task: {task}. Do not copy other roles."
                        raw_idea = self.client.generate_json_response(
                            idea_prompt,
                            system_instruction=f"Agent: {role}",
                            agent_name=role,
                            task_budget=budget,
                            task_id=run_id,
                            step_key=f"team_idea_{role}"
                        )
                        if isinstance(raw_idea, dict) and "proposal" in raw_idea:
                            idea_cards.append(AgentIdea.model_validate(raw_idea))
                        else:
                            idea_cards.append(AgentIdea(
                                role=role,
                                goal=task,
                                proposal=f"{role.capitalize()} technical strategy for {task}",
                                assumptions=["Standard architecture requirements"],
                                dependencies=["validation"],
                                related_tags=["architecture", "security"]
                            ))

                    relationships = correlate_ideas(idea_cards)
                    team_idea = synthesize_team_idea(task, idea_cards, relationships, self.client)
                    self.run_store.save_step_checkpoint(run_id, "team_room", "team_room", "Completed", team_idea.model_dump())
                    pipeline_steps.append({"agent": "team_room", "status": "Completed"})
                except GeminiRateLimitError as e:
                    return make_paused_response("paused_rate_limit", str(e), current_result)
                except GeminiQuotaExhaustedError as e:
                    return make_paused_response("paused_quota", str(e), current_result)
                except GeminiTransientError as e:
                    return make_paused_response("paused_transient", str(e), current_result)

            if team_idea:
                artifacts["team_idea.md"] = f"# {team_idea.title}\n\n{team_idea.synthesis}\n"

        # Step 5: Researcher (if route warrants and not already collaborated)
        researcher_output = None
        route = TaskRouter.determine_route(task, planner_output.needs_research, planner_output.needs_testing)
        if "researcher" in route and not team_idea:
            if is_cancelled():
                return make_paused_response("cancelled", "Task was cancelled by user.", current_result)
            run_status = "RESEARCHED"
            if "researcher" in checkpoints:
                r_data = json.loads(checkpoints["researcher"]["result_json"])
                from app.validators import ResearcherOutput
                researcher_output = ResearcherOutput.model_validate(r_data)
                pipeline_steps.append({"agent": "researcher", "status": "Completed (Cached)"})
            else:
                if not budget.can_call():
                    return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
                try:
                    researcher_output = self._run_agent("researcher", task, {"plan": planner_output.model_dump()}, task_budget=budget, task_id=run_id, step_key="researcher")
                    self.run_store.save_step_checkpoint(run_id, "researcher", "researcher", "Completed", researcher_output.model_dump())
                    pipeline_steps.append({"agent": "researcher", "status": "Completed"})
                except GeminiRateLimitError as e:
                    return make_paused_response("paused_rate_limit", str(e), current_result)
                except GeminiQuotaExhaustedError as e:
                    return make_paused_response("paused_quota", str(e), current_result)
                except GeminiTransientError as e:
                    return make_paused_response("paused_transient", str(e), current_result)

        # Step 6: Developer / Builder
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        run_status = "DRAFTED"
        dev_context = {
            "plan": planner_output.model_dump(),
            "context": artifacts.get("context.md", ""),
            "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
        }
        if team_idea:
            dev_context["team_idea"] = team_idea.model_dump()
        elif researcher_output:
            dev_context["research"] = researcher_output.model_dump()

        if "developer" in checkpoints:
            d_data = json.loads(checkpoints["developer"]["result_json"])
            from app.validators import DeveloperOutput
            developer_output = DeveloperOutput.model_validate(d_data)
            current_result = developer_output.result
            pipeline_steps.append({"agent": "developer", "status": "Completed (Cached)"})
        else:
            if not budget.can_call():
                return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
            try:
                developer_output = self._run_agent("developer", task, dev_context, task_budget=budget, task_id=run_id, step_key="developer")
                current_result = developer_output.result
                self.run_store.save_step_checkpoint(run_id, "developer", "developer", "Completed", developer_output.model_dump())
                self.run_store.update_task_state(run_id, current_stage="developer", partial_result=current_result, used_attempts=budget.used_attempts)
                pipeline_steps.append({"agent": "developer", "status": "Completed"})
            except GeminiRateLimitError as e:
                return make_paused_response("paused_rate_limit", str(e), current_result)
            except GeminiQuotaExhaustedError as e:
                return make_paused_response("paused_quota", str(e), current_result)
            except GeminiTransientError as e:
                return make_paused_response("paused_transient", str(e), current_result)

        artifacts["build.md"] = f"# Deliverable / Build Artifact\n\n**Summary**: {developer_output.summary}\n\n## Implementation\n```\n{developer_output.result}\n```\n"

        # Step 7: Tester / QA
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        run_status = "TESTED_OR_BLOCKED"
        tester_context = {
            "plan": planner_output.model_dump(),
            "deliverable": developer_output.model_dump(),
            "allow_live_tools": self.config.allow_live_tools
        }

        if "tester" in checkpoints:
            t_data = json.loads(checkpoints["tester"]["result_json"])
            from app.validators import TesterOutput
            tester_output = TesterOutput.model_validate(t_data)
            pipeline_steps.append({"agent": "tester", "status": f"{tester_output.overall_status} (Cached)"})
        else:
            if not budget.can_call():
                return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
            try:
                tester_output = self._run_agent("tester", task, tester_context, task_budget=budget, task_id=run_id, step_key="tester")
                self.run_store.save_step_checkpoint(run_id, "tester", "tester", tester_output.overall_status, tester_output.model_dump())
                pipeline_steps.append({"agent": "tester", "status": tester_output.overall_status})
            except GeminiRateLimitError as e:
                return make_paused_response("paused_rate_limit", str(e), current_result)
            except GeminiQuotaExhaustedError as e:
                return make_paused_response("paused_quota", str(e), current_result)
            except GeminiTransientError as e:
                return make_paused_response("paused_transient", str(e), current_result)

        test_verified = False
        if self.config.allow_live_tools:
            for tc in tester_output.test_cases:
                exec_res = run_bounded_test(tc.test_command, self.config.workspace_path, enabled=True)
                tc.executed = exec_res["executed"]
                tc.exit_code = exec_res["exit_code"]
                tc.output = exec_res["stdout"] or exec_res["stderr"]
                if exec_res["status"] == "PASSED":
                    test_verified = True

        qa_md = [
            f"# QA & Testing Report",
            f"**Summary**: {tester_output.summary}",
            f"**Overall Status**: `{tester_output.overall_status}`",
            "",
            "## Test Cases"
        ]
        for tc in tester_output.test_cases:
            qa_md.append(f"### Test: {tc.name}")
            qa_md.append(f"- Command: `{tc.test_command}`")
            qa_md.append(f"- Executed: {tc.executed}")
            qa_md.append(f"- Exit Code: {tc.exit_code}")
            qa_md.append(f"- Output:\n```\n{tc.output}\n```\n")
        artifacts["qa.md"] = "\n".join(qa_md)

        # Step 8: Reviewer
        if is_cancelled():
            return make_paused_response("cancelled", "Task was cancelled by user.", current_result)

        run_status = "REVIEWED"
        reviewer_context = {
            "plan": planner_output.model_dump(),
            "deliverable": developer_output.model_dump(),
            "qa": tester_output.model_dump(),
            "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
        }

        if "reviewer" in checkpoints:
            rev_data = json.loads(checkpoints["reviewer"]["result_json"])
            from app.validators import ReviewerOutput
            reviewer_output = ReviewerOutput.model_validate(rev_data)
            pipeline_steps.append({"agent": "reviewer", "status": f"{reviewer_output.verdict} (Cached)"})
        else:
            if not budget.can_call():
                return make_paused_response("paused_budget", f"This task reached Paimon's configured {budget.max_attempts}-attempt limit.", current_result)
            try:
                reviewer_output = self._run_agent("reviewer", task, reviewer_context, task_budget=budget, task_id=run_id, step_key="reviewer")
                self.run_store.save_step_checkpoint(run_id, "reviewer", "reviewer", reviewer_output.verdict, reviewer_output.model_dump())
                pipeline_steps.append({"agent": "reviewer", "status": reviewer_output.verdict})
            except GeminiRateLimitError as e:
                return make_paused_response("paused_rate_limit", str(e), current_result)
            except GeminiQuotaExhaustedError as e:
                return make_paused_response("paused_quota", str(e), current_result)
            except GeminiTransientError as e:
                return make_paused_response("paused_transient", str(e), current_result)

        # Step 9: Revision Loop (Bounded by max_revisions and remaining budget)
        while reviewer_output.verdict == "REVISE" and revision_count < max_revisions:
            if not budget.can_call():
                break
            run_status = "REVISING"
            revision_count += 1
            dev_context["reviewer_feedback"] = reviewer_output.model_dump()
            try:
                developer_output = self._run_agent("developer", task, dev_context, task_budget=budget, task_id=run_id, step_key=f"developer_rev_{revision_count}")
                current_result = developer_output.result
                artifacts["build.md"] += f"\n\n## Revision {revision_count}\n```\n{developer_output.result}\n```\n"

                tester_context["deliverable"] = developer_output.model_dump()
                tester_output = self._run_agent("tester", task, tester_context, task_budget=budget, task_id=run_id, step_key=f"tester_rev_{revision_count}")

                reviewer_context["deliverable"] = developer_output.model_dump()
                reviewer_context["qa"] = tester_output.model_dump()
                reviewer_output = self._run_agent("reviewer", task, reviewer_context, task_budget=budget, task_id=run_id, step_key=f"reviewer_rev_{revision_count}")
                pipeline_steps.append({"agent": "reviewer", "status": f"Revision {revision_count}: {reviewer_output.verdict}"})
            except Exception:
                break

        run_status = "COMPLETED" if reviewer_output.verdict == "PASS" else "BLOCKED"

        # Final Document
        final_md = [
            f"# Final Delivery for Task: {task}",
            f"- **Run ID**: {run_id}",
            f"- **Status**: `{run_status}`",
            f"- **Reviewer Verdict**: `{reviewer_output.verdict}`",
            f"- **QA Status**: `{tester_output.overall_status}`",
            "",
            "## Result / Solution",
            developer_output.result,
        ]
        artifacts["final.md"] = "\n".join(final_md)

        # Step 10: V2 Selective Memory Value Filter
        existing_approved = [n.model_dump() for n in memory_context.get("approved_notes", [])]
        filter_result = evaluate_memory_value(
            task=task,
            outcome_result=developer_output.result,
            feedback=feedback,
            test_verified=test_verified,
            existing_approved_notes=existing_approved,
            min_score=self.config.memory_min_score,
            max_words=self.config.max_memory_words,
            max_candidates=self.config.max_candidate_memories_per_task
        )

        memory_created = False
        saved_candidate_ids = []
        if filter_result.should_store:
            run_status = "LEARNING_PENDING"
            for cand in filter_result.candidates:
                cand.source_run_ids = [run_id]
                self.memory_store.save_candidate_memory(cand)
                saved_candidate_ids.append(cand.lesson_id)
            memory_created = True

        pipeline_steps.append({
            "agent": "learning_agent",
            "status": "Saved Candidate" if memory_created else "Evaluated (No Memory)"
        })

        run_metadata = {
            "run_id": run_id,
            "project_id": project_id,
            "task": task,
            "status": run_status,
            "verdict": reviewer_output.verdict,
            "revisions_count": revision_count,
            "qa_status": tester_output.overall_status,
            "api_calls": budget.used_attempts,
            "memory_score": filter_result.score,
            "memory_stored": memory_created,
            "memory_rationale": filter_result.rationale,
            "completed_at": datetime.now().isoformat()
        }
        self.memory_store.save_run(run_id, artifacts, run_metadata)
        self.run_store.record_run(
            run_id=run_id,
            task=task,
            project_id=project_id,
            status=run_status,
            verdict=reviewer_output.verdict,
            api_calls=budget.used_attempts,
            final_result=developer_output.result,
            conversation_id=conversation_id,
            team_idea=team_idea.model_dump() if team_idea else None
        )
        self.run_store.update_task_state(run_id, status=run_status, current_stage="completed", result=developer_output.result, used_attempts=budget.used_attempts)

        return {
            "task_id": run_id,
            "run_id": run_id,
            "status": run_status,
            "verdict": reviewer_output.verdict,
            "result": developer_output.result,
            "artifacts": artifacts,
            "team_idea": team_idea.model_dump() if team_idea else None,
            "memory_decision": filter_result.model_dump(),
            "saved_candidate_ids": saved_candidate_ids,
            "steps": pipeline_steps,
            "run_metadata": run_metadata,
            "logical_budget": budget.to_dict(),
            "provider_quota": {
                "status": "Not available — check Google AI Studio",
                "source": "https://aistudio.google.com/usage"
            },
            "can_resume_now": False,
            "attachments": [
                {
                    "filename": f.filename,
                    "extension": f.extension,
                    "size_bytes": f.size_bytes,
                    "category": f.category,
                    "warnings": f.warnings,
                }
                for f in evidence_packet.files
            ] if evidence_packet.has_attachments else [],
            "attachment_warnings": evidence_packet.warnings
        }

    def resume_task(self, task_id: str, extra_budget: int = 0) -> Dict[str, Any]:
        """Resumes a paused or interrupted task from its last valid checkpoint."""
        task = self.run_store.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")
        self.run_store.resume_task_record(task_id, extra_budget=extra_budget)
        return self.execute_task(
            task=task["task_text"],
            project_id=task.get("project_id", "default"),
            conversation_id=task.get("conversation_id"),
            task_id=task_id,
            resume_existing=True
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a task, preventing future model calls while preserving partial deliverables."""
        return self.run_store.cancel_task(task_id)

