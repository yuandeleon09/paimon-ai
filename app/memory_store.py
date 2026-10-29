import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.validators import MemoryItem
from app.safety import sanitize_text
from app.memory_filter import MemoryCandidate

class MemoryStore:
    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.project_dir = self.vault_path / "00_Projects"
        self.legacy_project_dir = self.vault_path / "00_Project"
        self.memory_dir = self.vault_path / "01_Memory"
        self.approved_dir = self.memory_dir / "Approved"
        self.pending_dir = self.memory_dir / "Pending"
        self.conflicts_dir = self.memory_dir / "Conflicts"
        self.archived_dir = self.memory_dir / "Archived"
        self.rejected_dir = self.memory_dir / "Rejected"  # backward compatibility
        self.agents_dir = self.vault_path / "02_Agents"
        self.legacy_runs_dir = self.vault_path / "03_Runs"
        self.feedback_dir = self.vault_path / "04_Feedback"
        self.system_dir = self.vault_path / "99_System"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for d in [
            self.project_dir,
            self.legacy_project_dir,
            self.approved_dir,
            self.pending_dir,
            self.conflicts_dir,
            self.archived_dir,
            self.rejected_dir,
            self.agents_dir,
            self.legacy_runs_dir,
            self.feedback_dir,
            self.system_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def get_agent_prompt(self, agent_name: str) -> str:
        prompt_file = self.agents_dir / f"{agent_name}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return f"# Agent: {agent_name}\nYou are the {agent_name} agent."

    def load_project_baseline(self, project_id: str = "default") -> str:
        content = []
        p_file = self.project_dir / f"{project_id}.md"
        if not p_file.exists():
            p_file = self.legacy_project_dir / "project.md"
        if p_file.exists():
            content.append(p_file.read_text(encoding="utf-8"))

        shared_file = self.memory_dir / "shared_memory.md"
        if shared_file.exists():
            content.append(shared_file.read_text(encoding="utf-8"))
        return "\n\n".join(content)

    def retrieve_context(
        self,
        project_id: str,
        query: str,
        max_memories: int = 5,
        max_tokens: int = 700
    ) -> Dict[str, Any]:
        """
        Retrieves scoped project baseline rules and up to max_memories Approved notes.
        CRITICAL V2 RULES:
        - Never returns Pending, Conflicts, or Archived notes as trusted memory.
        - Respects token/word limits.
        """
        baseline = self.load_project_baseline(project_id)
        query_words = set(query.lower().split())

        retrieved_items: List[MemoryItem] = []
        scored_notes = []

        if self.approved_dir.exists():
            for note_path in self.approved_dir.glob("*.md"):
                try:
                    text = note_path.read_text(encoding="utf-8")
                    rel_path = note_path.relative_to(self.vault_path).as_posix()
                    text_lower = text.lower()

                    # Project scoping check
                    if "project:" in text_lower:
                        if f"project: {project_id.lower()}" not in text_lower and "project: default" not in text_lower and "scope: global" not in text_lower:
                            continue

                    matches = sum(1 for w in query_words if len(w) > 3 and w in text_lower)
                    scored_notes.append((matches, rel_path, text))
                except Exception:
                    continue

        # Sort by relevance
        scored_notes.sort(key=lambda x: x[0], reverse=True)

        current_token_est = 0
        for matches, rel_path, text in scored_notes[:max_memories]:
            excerpt = text[:600]
            est_tokens = len(excerpt.split()) * 1.3
            if current_token_est + est_tokens > max_tokens and retrieved_items:
                break
            current_token_est += est_tokens
            retrieved_items.append(
                MemoryItem(
                    note_path=rel_path,
                    trust_status="approved",
                    scope=project_id,
                    excerpt=excerpt
                )
            )

        return {
            "baseline": baseline,
            "approved_notes": retrieved_items,
            "contradictions": []
        }

    def save_candidate_memory(self, candidate: MemoryCandidate) -> Path:
        """Saves a high-value candidate lesson to Pending or Conflicts folder."""
        today = datetime.now().strftime("%Y-%m-%d")

        if candidate.is_conflict:
            target_dir = self.conflicts_dir
            status_val = "conflict"
        else:
            target_dir = self.pending_dir
            status_val = "pending"

        file_path = target_dir / f"{candidate.lesson_id}.md"

        frontmatter = [
            "---",
            f"id: {candidate.lesson_id}",
            f"project: {candidate.project_id}",
            f"status: {status_val}",
            f"scope: {candidate.scope}",
            f"created: {today}",
            f"score: {candidate.total_score}",
            f"verified_by: {candidate.evidence}",
            "---",
            f"# {candidate.title}",
            "",
            candidate.body
        ]
        if candidate.is_conflict:
            frontmatter.append(f"\n> [!WARNING]\n> **Conflict Detected**: {candidate.conflict_details}\n")
        elif candidate.is_merge:
            frontmatter.append(f"\n> [!NOTE]\n> **Proposed Merge Target**: `{candidate.target_canonical_note}`\n")

        clean_text = sanitize_text("\n".join(frontmatter))
        file_path.write_text(clean_text, encoding="utf-8")
        return file_path

    def approve_candidate(self, lesson_id: str, edited_text: Optional[str] = None) -> bool:
        """Approves a pending candidate lesson into Approved memory or merges it into a canonical note."""
        pending_file = self.pending_dir / f"{lesson_id}.md"
        if not pending_file.exists():
            # Check backwards compatibility run_id naming
            return self.approve_run_lesson(lesson_id, edited_text)

        content = edited_text if edited_text else pending_file.read_text(encoding="utf-8")
        content = content.replace("status: pending", "status: approved")
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"\n- **Approved At**: {today}\n"

        approved_file = self.approved_dir / f"{lesson_id}.md"
        approved_file.write_text(sanitize_text(content), encoding="utf-8")
        pending_file.unlink(missing_ok=True)
        return True

    def reject_candidate(self, lesson_id: str, reason: str = "User rejected") -> bool:
        """Rejects a pending candidate lesson and moves it to Archived/."""
        pending_file = self.pending_dir / f"{lesson_id}.md"
        if not pending_file.exists():
            return self.reject_run_lesson(lesson_id, reason)

        content = pending_file.read_text(encoding="utf-8")
        content = content.replace("status: pending", "status: rejected")
        content += f"\n\n## Rejection Reason\n- **Date**: {datetime.now().strftime('%Y-%m-%d')}\n- **Reason**: {reason}\n"

        archived_file = self.archived_dir / f"{lesson_id}.md"
        archived_file.write_text(sanitize_text(content), encoding="utf-8")
        pending_file.unlink(missing_ok=True)
        return True

    def archive_lesson(self, lesson_id: str, reason: str = "Archived") -> bool:
        """Moves an approved lesson note to 01_Memory/Archived/ without deleting it."""
        approved_file = self.approved_dir / f"{lesson_id}.md"
        if not approved_file.exists():
            return False
        content = approved_file.read_text(encoding="utf-8")
        content = content.replace("status: approved", "status: archived")
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"\n- **Archived At**: {today}\n- **Archive Reason**: {reason}\n"
        archived_file = self.archived_dir / f"{lesson_id}.md"
        archived_file.write_text(sanitize_text(content), encoding="utf-8")
        approved_file.unlink(missing_ok=True)
        return True

    def restore_lesson(self, lesson_id: str) -> bool:
        """Restores an archived lesson back to 01_Memory/Approved/."""
        archived_file = self.archived_dir / f"{lesson_id}.md"
        if not archived_file.exists():
            return False
        content = archived_file.read_text(encoding="utf-8")
        content = content.replace("status: archived", "status: approved")
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"\n- **Restored At**: {today}\n"
        approved_file = self.approved_dir / f"{lesson_id}.md"
        approved_file.write_text(sanitize_text(content), encoding="utf-8")
        archived_file.unlink(missing_ok=True)
        return True

    def get_storage_report(self) -> Dict[str, Any]:
        """Returns statistics on Obsidian vault memory to verify lean storage."""
        approved_count = len(list(self.approved_dir.glob("*.md")))
        pending_count = len(list(self.pending_dir.glob("*.md")))
        conflicts_count = len(list(self.conflicts_dir.glob("*.md")))
        archived_count = len(list(self.archived_dir.glob("*.md")))

        total_bytes = sum(f.stat().st_size for f in self.vault_path.rglob("*.md") if f.is_file())
        return {
            "approved_notes": approved_count,
            "pending_notes": pending_count,
            "conflicts": conflicts_count,
            "archived_notes": archived_count,
            "total_vault_kb": round(total_bytes / 1024, 2)
        }

    # Backward compatibility methods
    def save_run(self, run_id: str, artifacts: Dict[str, str], run_metadata: Dict[str, Any]) -> Path:
        """Legacy helper: preserves existing run folder writes without failing older test suites."""
        run_folder = self.legacy_runs_dir / run_id
        run_folder.mkdir(parents=True, exist_ok=True)
        for filename, content in artifacts.items():
            (run_folder / filename).write_text(sanitize_text(content), encoding="utf-8")
        (run_folder / "run.json").write_text(sanitize_text(json.dumps(run_metadata, indent=2)), encoding="utf-8")
        return run_folder

    def save_pending_lesson(self, run_id: str, proposed_lessons: List[Dict[str, Any]], project_id: str = "default") -> Path:
        pending_file = self.pending_dir / f"{run_id}.md"
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            "---",
            "status: pending",
            f"project: {project_id}",
            f"source_run_id: {run_id}",
            f"created: {today}",
            "---",
            f"# Proposed Lessons from Run {run_id}",
            ""
        ]
        for i, lesson in enumerate(proposed_lessons, 1):
            lines.append(f"## Lesson {i}: {lesson.get('claim', 'Untitled')}")
            lines.append(f"- **Claim**: {lesson.get('claim', '')}")
            lines.append(f"- **Evidence**: {lesson.get('evidence', '')}")
            lines.append(f"- **Scope**: {lesson.get('scope', project_id)}")
            lines.append(f"- **Kind**: {lesson.get('kind', 'best_practice')}")
            lines.append("")
        pending_file.write_text(sanitize_text("\n".join(lines)), encoding="utf-8")
        return pending_file

    def approve_run_lesson(self, run_id: str, modified_content: Optional[str] = None) -> bool:
        pending_file = self.pending_dir / f"{run_id}.md"
        if not pending_file.exists():
            return False
        content = modified_content if modified_content else pending_file.read_text(encoding="utf-8")
        content = content.replace("status: pending", "status: approved")
        approved_file = self.approved_dir / f"{run_id}.md"
        approved_file.write_text(sanitize_text(content), encoding="utf-8")
        pending_file.unlink(missing_ok=True)
        return True

    def reject_run_lesson(self, run_id: str, reason: str = "User rejected") -> bool:
        pending_file = self.pending_dir / f"{run_id}.md"
        if not pending_file.exists():
            return False
        content = pending_file.read_text(encoding="utf-8")
        content = content.replace("status: pending", "status: rejected")
        content += f"\n\n## Rejection Note\n- **Reason**: {reason}\n"
        rejected_file = self.rejected_dir / f"{run_id}.md"
        rejected_file.write_text(sanitize_text(content), encoding="utf-8")
        pending_file.unlink(missing_ok=True)
        return True

    def save_feedback(self, run_id: str, feedback_text: str) -> Path:
        feedback_file = self.feedback_dir / f"{run_id}.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"# Feedback for Run {run_id}\n\n- **Recorded**: {now}\n- **Feedback**: {feedback_text}\n"
        feedback_file.write_text(sanitize_text(content), encoding="utf-8")
        return feedback_file

    def list_runs(self) -> List[str]:
        if not self.legacy_runs_dir.exists():
            return []
        return sorted([p.name for p in self.legacy_runs_dir.iterdir() if p.is_dir()], reverse=True)
