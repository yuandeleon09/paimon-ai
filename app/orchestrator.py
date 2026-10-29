import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.config import SystemConfig
from app.memory_store import MemoryStore
from app.gemini_client import GeminiClient
from app.agent_runner import AgentRunner
from app.task_router import TaskRouter
from app.tools.safe_test_runner import run_bounded_test
from app.collaboration import AgentIdea, Relationship, TeamIdea, correlate_ideas, synthesize_team_idea
from app.memory_filter import evaluate_memory_value, MemoryCandidate
from app.runs import RunStore
from app.attachment_service import AttachmentIngestionService, AttachmentEvidencePacket

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
            mock_mode=mock_mode
        )
        self.runner = AgentRunner(self.client, self.memory_store)

    def execute_task(
        self,
        task: str,
        project_id: str = "default",
        allow_revise: bool = True,
        collaborative: bool = False,
        feedback: Optional[str] = None,
        conversation_id: Optional[str] = None,
        attachments: Optional[List[Tuple[str, bytes]]] = None
    ) -> Dict[str, Any]:
        self.client.reset_call_count()
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_status = "CREATED"
        artifacts: Dict[str, str] = {}
        pipeline_steps: List[Dict[str, Any]] = []
        revision_count = 0
        max_revisions = self.config.max_revisions if allow_revise else 0

        # Step 0: Attachment Processing & Multimodal Analysis (V4)
        evidence_packet = AttachmentEvidencePacket(has_attachments=False)
        if attachments:
            attachment_service = AttachmentIngestionService()
            evidence_packet = attachment_service.validate_and_process(attachments)
            if evidence_packet.has_attachments:
                attachment_service.analyze_multimodal_evidence(task, evidence_packet, self.client)
                pipeline_steps.append({
                    "agent": "attachment_analyst",
                    "status": f"Processed {len(evidence_packet.files)} file(s)"
                })
                artifacts["attachments.md"] = evidence_packet.to_evidence_markdown()

        # Step 1: Initial Task Document
        artifacts["task.md"] = f"# Task: {task}\n\n- **Run ID**: {run_id}\n- **Project**: {project_id}\n- **Started**: {datetime.now().isoformat()}\n"

        # Step 2: Retrieve Context via Memory Manager (V2 Lean Context)
        run_status = "CONTEXT_READY"
        memory_context = self.memory_store.retrieve_context(
            project_id=project_id,
            query=task,
            max_memories=self.config.max_retrieved_memories,
            max_tokens=self.config.max_memory_context_tokens
        )
        memory_manager_output = self.runner.run_agent("memory_manager", task, memory_context)
        pipeline_steps.append({"agent": "memory_manager", "status": "Completed"})

        context_md = [
            f"# Context for Task: {task}",
            f"- **Project Scope**: {project_id}",
            "",
            "## Baseline Rules & Constraints",
            memory_context.get("baseline", "None defined."),
            "",
            "## Approved Knowledge Excerpts",
        ]
        for note in memory_manager_output.retrieved_notes:
            context_md.append(f"### Source: `{note.note_path}` (Trust: {note.trust_status})")
            context_md.append(note.excerpt)
            context_md.append("")

        artifacts["context.md"] = "\n".join(context_md)

        # Step 3: Planner
        run_status = "PLANNED"
        planner_context = {
            "retrieved_memory": memory_manager_output.model_dump(),
            "baseline": memory_context.get("baseline", ""),
            "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
        }
        planner_output = self.runner.run_agent("planner", task, planner_context)
        pipeline_steps.append({"agent": "planner", "status": "Completed"})

        plan_md = [
            f"# Plan for Task: {task}",
            f"**Summary**: {planner_output.summary}",
            "",
            "## Steps",
            *[f"- {step}" for step in planner_output.steps],
            "",
            "## Acceptance Criteria",
            *[f"- [ ] {ac}" for ac in planner_output.acceptance_criteria],
            "",
            f"- **Needs Research**: {planner_output.needs_research}",
            f"- **Needs Testing**: {planner_output.needs_testing}",
        ]
        artifacts["plan.md"] = "\n".join(plan_md)

        # Step 4: Optional Team Room Collaboration (Priority 2)
        team_idea: Optional[TeamIdea] = None
        is_collab = collaborative or any(w in task.lower() for w in ["collaborate", "team", "design", "reservation", "checkout", "architecture"])
        
        if is_collab:
            run_status = "TEAM_COLLABORATING"
            # Selected specialists submit independent idea cards
            specialist_roles = ["developer", "researcher"]
            idea_cards: List[AgentIdea] = []

            for role in specialist_roles:
                idea_prompt = f"Submit an independent concise AgentIdea card for task: {task}. Do not copy other roles."
                raw_idea = self.client.generate_json_response(idea_prompt, system_instruction=f"Agent: {role}", agent_name=role)
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

            # Correlate relationships & synthesize Team Idea
            relationships = correlate_ideas(idea_cards)
            team_idea = synthesize_team_idea(task, idea_cards, relationships, self.client)
            artifacts["team_idea.md"] = f"# {team_idea.title}\n\n{team_idea.synthesis}\n"
            pipeline_steps.append({"agent": "team_room", "status": "Completed"})

        # Step 5: Researcher (if route warrants and not already collaborated)
        researcher_output = None
        route = TaskRouter.determine_route(task, planner_output.needs_research, planner_output.needs_testing)
        if "researcher" in route and not team_idea:
            run_status = "RESEARCHED"
            researcher_output = self.runner.run_agent("researcher", task, {"plan": planner_output.model_dump()})
            pipeline_steps.append({"agent": "researcher", "status": "Completed"})

        # Step 6: Developer / Builder
        run_status = "DRAFTED"
        dev_context = {
            "plan": planner_output.model_dump(),
            "context": artifacts["context.md"],
            "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
        }
        if team_idea:
            dev_context["team_idea"] = team_idea.model_dump()
        elif researcher_output:
            dev_context["research"] = researcher_output.model_dump()

        developer_output = self.runner.run_agent("developer", task, dev_context)
        pipeline_steps.append({"agent": "developer", "status": "Completed"})
        artifacts["build.md"] = f"# Deliverable / Build Artifact\n\n**Summary**: {developer_output.summary}\n\n## Implementation\n```\n{developer_output.result}\n```\n\n## Notes & Assumptions\n- {developer_output.implementation_notes}\n"

        # Step 7: Tester / QA
        run_status = "TESTED_OR_BLOCKED"
        tester_context = {
            "plan": planner_output.model_dump(),
            "deliverable": developer_output.model_dump(),
            "allow_live_tools": self.config.allow_live_tools
        }
        tester_output = self.runner.run_agent("tester", task, tester_context)
        pipeline_steps.append({"agent": "tester", "status": tester_output.overall_status})

        test_verified = False
        if self.config.allow_live_tools:
            for tc in tester_output.test_cases:
                exec_res = run_bounded_test(
                    tc.test_command,
                    self.config.workspace_path,
                    enabled=True
                )
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
        run_status = "REVIEWED"
        reviewer_context = {
            "plan": planner_output.model_dump(),
            "deliverable": developer_output.model_dump(),
            "qa": tester_output.model_dump(),
            "attachments_evidence": evidence_packet.to_evidence_markdown() if evidence_packet.has_attachments else ""
        }
        reviewer_output = self.runner.run_agent("reviewer", task, reviewer_context)
        pipeline_steps.append({"agent": "reviewer", "status": reviewer_output.verdict})

        # Step 9: Revision Loop (Bounded by max_revisions)
        while reviewer_output.verdict == "REVISE" and revision_count < max_revisions:
            run_status = "REVISING"
            revision_count += 1
            dev_context["reviewer_feedback"] = reviewer_output.model_dump()
            developer_output = self.runner.run_agent("developer", task, dev_context)
            artifacts["build.md"] += f"\n\n## Revision {revision_count}\n```\n{developer_output.result}\n```\n"

            tester_context["deliverable"] = developer_output.model_dump()
            tester_output = self.runner.run_agent("tester", task, tester_context)

            reviewer_context["deliverable"] = developer_output.model_dump()
            reviewer_context["qa"] = tester_output.model_dump()
            reviewer_output = self.runner.run_agent("reviewer", task, reviewer_context)
            pipeline_steps.append({"agent": "reviewer", "status": f"Revision {revision_count}: {reviewer_output.verdict}"})

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
            "",
            "## Caveats & Operating Boundaries",
            "- Operates under zero-cost Gemini free-tier rules.",
            "- Tested in bounded environment or verified truthful status.",
        ]
        artifacts["final.md"] = "\n".join(final_md)

        # Step 10: V2 Selective Memory Value Filter (Priority 1)
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

        # Save immutable run artifacts to legacy runs dir (for backward compatibility)
        run_metadata = {
            "run_id": run_id,
            "project_id": project_id,
            "task": task,
            "status": run_status,
            "verdict": reviewer_output.verdict,
            "revisions_count": revision_count,
            "qa_status": tester_output.overall_status,
            "api_calls": self.client.call_count,
            "memory_score": filter_result.score,
            "memory_stored": memory_created,
            "memory_rationale": filter_result.rationale,
            "completed_at": datetime.now().isoformat()
        }
        self.memory_store.save_run(run_id, artifacts, run_metadata)

        # Persist diagnostic run & conversation record outside vault to app_data/state.sqlite
        self.run_store.record_run(
            run_id=run_id,
            task=task,
            project_id=project_id,
            status=run_status,
            verdict=reviewer_output.verdict,
            api_calls=self.client.call_count,
            final_result=developer_output.result,
            conversation_id=conversation_id,
            team_idea=team_idea.model_dump() if team_idea else None
        )

        return {
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
