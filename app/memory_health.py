from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import json
import re

from app.safety import SECRET_PATTERNS
from app.memory_store import MemoryStore

class HealthFinding(BaseModel):
    finding_id: str
    finding_type: Literal[
        "duplicate", "contradiction", "outdated", "weak_evidence",
        "never_used", "oversized", "sensitive_content", "missing_metadata", "broken_link"
    ]
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    affected_note_ids: List[str]
    reason: str
    proposed_diff: str = ""
    suggested_action: Literal[
        "merge", "resolve_conflict", "review_date", "redact", "archive", "condense", "repair_metadata"
    ] = "merge"
    status: Literal["pending_review", "applied", "rejected"] = "pending_review"

class HealthReport(BaseModel):
    timestamp: str
    approved_notes_count: int
    pending_notes_count: int
    conflicts_count: int
    archived_notes_count: int
    total_approved_bytes: int
    findings: List[HealthFinding] = Field(default_factory=list)

class MemoryHealthService:
    def __init__(self, vault_path: Path, app_data_path: Path):
        self.vault_path = Path(vault_path)
        self.app_data_path = Path(app_data_path)
        self.versioning_dir = self.app_data_path / "versioning"
        self.versioning_dir.mkdir(parents=True, exist_ok=True)
        self.store = MemoryStore(self.vault_path)
        self._last_report: Optional[HealthReport] = None

    def scan(self, scope: Optional[str] = None) -> HealthReport:
        """
        Conducts a strictly READ-ONLY audit scan of the Obsidian vault.
        Identifies duplicates, contradictions, sensitive content, oversized notes,
        weak evidence, and stale facts.
        """
        approved_dir = self.store.approved_dir
        pending_dir = self.store.pending_dir
        conflicts_dir = self.store.conflicts_dir
        archived_dir = self.store.archived_dir

        approved_files = list(approved_dir.glob("*.md")) if approved_dir.exists() else []
        pending_files = list(pending_dir.glob("*.md")) if pending_dir.exists() else []
        conflict_files = list(conflicts_dir.glob("*.md")) if conflicts_dir.exists() else []
        archived_files = list(archived_dir.glob("*.md")) if archived_dir.exists() else []

        total_bytes = sum(f.stat().st_size for f in approved_files)
        findings: List[HealthFinding] = []
        finding_counter = 1

        approved_data: List[Dict[str, Any]] = []
        today_str = datetime.now().strftime("%Y-%m-%d")

        for f in approved_files:
            try:
                text = f.read_text(encoding="utf-8")
                approved_data.append({
                    "id": f.stem,
                    "filename": f.name,
                    "path": f,
                    "text": text,
                    "words": len(text.split()),
                    "bytes": f.stat().st_size
                })
            except Exception:
                continue

        # 1. Audit: Sensitive content check (High Risk)
        for note in approved_data:
            has_secret = any(pat.search(note["text"]) for pat in SECRET_PATTERNS)
            if has_secret:
                findings.append(HealthFinding(
                    finding_id=f"FIND-{finding_counter:03d}",
                    finding_type="sensitive_content",
                    risk_level="HIGH",
                    affected_note_ids=[note["id"]],
                    reason=f"Potential API key, password, or sensitive token pattern detected in `{note['filename']}`.",
                    proposed_diff=f"- Content contains sensitive pattern.\n+ [REDACTED_SECRET]",
                    suggested_action="redact"
                ))
                finding_counter += 1

        # 2. Audit: Oversized notes check (> 150 words in approved rule)
        for note in approved_data:
            if note["words"] > 150:
                findings.append(HealthFinding(
                    finding_id=f"FIND-{finding_counter:03d}",
                    finding_type="oversized",
                    risk_level="MEDIUM",
                    affected_note_ids=[note["id"]],
                    reason=f"Note `{note['filename']}` contains {note['words']} words (target <= 100 words). May include raw transcript.",
                    proposed_diff=f"Condense to atomic rule: Situation, Rule, Evidence, Limitations.",
                    suggested_action="condense"
                ))
                finding_counter += 1

        # 3. Audit: Missing metadata
        for note in approved_data:
            text_lower = note["text"].lower()
            if "status:" not in text_lower or "project:" not in text_lower:
                findings.append(HealthFinding(
                    finding_id=f"FIND-{finding_counter:03d}",
                    finding_type="missing_metadata",
                    risk_level="LOW",
                    affected_note_ids=[note["id"]],
                    reason=f"Note `{note['filename']}` is missing frontmatter metadata (status or project).",
                    proposed_diff=f"+ ---\n+ status: approved\n+ project: default\n+ ---",
                    suggested_action="repair_metadata"
                ))
                finding_counter += 1

        # 4. Audit: Weak evidence (claims verified: true without test or user proof)
        for note in approved_data:
            text_lower = note["text"].lower()
            if ("verified: true" in text_lower or "verified_approved" in text_lower) and \
               ("test" not in text_lower and "user" not in text_lower and "feedback" not in text_lower and "run-" not in text_lower):
                findings.append(HealthFinding(
                    finding_id=f"FIND-{finding_counter:03d}",
                    finding_type="weak_evidence",
                    risk_level="MEDIUM",
                    affected_note_ids=[note["id"]],
                    reason=f"Note `{note['filename']}` marked verified without traceable test or human feedback evidence.",
                    proposed_diff=f"- verified: true\n+ verified: false (pending human verification)",
                    suggested_action="archive"
                ))
                finding_counter += 1

        # 5. Audit: Outdated notes (review_after date passed)
        for note in approved_data:
            match = re.search(r"review_after:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", note["text"])
            if match:
                rev_date = match.group(1)
                if rev_date < today_str:
                    findings.append(HealthFinding(
                        finding_id=f"FIND-{finding_counter:03d}",
                        finding_type="outdated",
                        risk_level="LOW",
                        affected_note_ids=[note["id"]],
                        reason=f"Note `{note['filename']}` review date `{rev_date}` has elapsed.",
                        proposed_diff=f"Update review_after date after confirming rule validity.",
                        suggested_action="review_date"
                    ))
                    finding_counter += 1

        # 6. Audit: Duplicate detection & Merging proposals
        for i in range(len(approved_data)):
            for j in range(i + 1, len(approved_data)):
                n1 = approved_data[i]
                n2 = approved_data[j]
                words1 = set(w.lower() for w in n1["text"].split() if len(w) > 4)
                words2 = set(w.lower() for w in n2["text"].split() if len(w) > 4)
                shared = words1 & words2
                if len(shared) >= 4:
                    findings.append(HealthFinding(
                        finding_id=f"FIND-{finding_counter:03d}",
                        finding_type="duplicate",
                        risk_level="MEDIUM",
                        affected_note_ids=[n1["id"], n2["id"]],
                        reason=f"High semantic overlap between `{n1['filename']}` and `{n2['filename']}` (shared concepts: {', '.join(list(shared)[:4])}).",
                        proposed_diff=f"Propose merging `{n2['filename']}` into canonical `{n1['filename']}`.",
                        suggested_action="merge"
                    ))
                    finding_counter += 1

        # 7. Audit: Contradictions check
        contradiction_pairs = [
            ("client-side only", "server-side"),
            ("server-side", "client-side only"),
            ("do not validate", "always validate"),
            ("no test", "test required"),
        ]
        for i in range(len(approved_data)):
            for j in range(i + 1, len(approved_data)):
                n1 = approved_data[i]
                n2 = approved_data[j]
                t1 = n1["text"].lower()
                t2 = n2["text"].lower()
                for c1, c2 in contradiction_pairs:
                    if c1 in t1 and c2 in t2:
                        findings.append(HealthFinding(
                            finding_id=f"FIND-{finding_counter:03d}",
                            finding_type="contradiction",
                            risk_level="HIGH",
                            affected_note_ids=[n1["id"], n2["id"]],
                            reason=f"Direct policy contradiction between `{n1['filename']}` ('{c1}') and `{n2['filename']}` ('{c2}').",
                            proposed_diff=f"Requires human resolution. Flagged for review; neither note silently overwritten.",
                            suggested_action="resolve_conflict"
                        ))
                        finding_counter += 1
                        break

        report = HealthReport(
            timestamp=datetime.now().isoformat(),
            approved_notes_count=len(approved_files),
            pending_notes_count=len(pending_files),
            conflicts_count=len(conflict_files),
            archived_notes_count=len(archived_files),
            total_approved_bytes=total_bytes,
            findings=findings
        )
        self._last_report = report
        return report

    def apply_approved_fix(self, finding_id: str) -> Dict[str, Any]:
        """
        Applies a user-approved health recommendation with safety backup and rollback versioning.
        """
        if not self._last_report:
            self.scan()

        finding = next((f for f in self._last_report.findings if f.finding_id == finding_id), None)
        if not finding:
            return {"success": False, "message": f"Finding {finding_id} not found."}

        backup_id = f"backup_{finding_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_folder = self.versioning_dir / backup_id
        backup_folder.mkdir(parents=True, exist_ok=True)

        # Back up affected notes first
        for note_id in finding.affected_note_ids:
            note_file = self.store.approved_dir / f"{note_id}.md"
            if note_file.exists():
                (backup_folder / f"{note_id}.md").write_text(note_file.read_text(encoding="utf-8"), encoding="utf-8")

        # Execute approved action
        if finding.suggested_action == "merge" and len(finding.affected_note_ids) >= 2:
            canonical_id = finding.affected_note_ids[0]
            redundant_id = finding.affected_note_ids[1]

            canonical_file = self.store.approved_dir / f"{canonical_id}.md"
            redundant_file = self.store.approved_dir / f"{redundant_id}.md"

            if canonical_file.exists() and redundant_file.exists():
                addition = f"\n\n## Merged Guideline (from {redundant_id})\n" + redundant_file.read_text(encoding="utf-8")
                canonical_file.write_text(canonical_file.read_text(encoding="utf-8") + addition, encoding="utf-8")
                # Archive redundant note, never hard delete
                self.store.archive_lesson(redundant_id, reason=f"Merged into canonical {canonical_id}")
                finding.status = "applied"
                return {"success": True, "message": f"Merged {redundant_id} into {canonical_id}. Redundant note archived.", "backup_id": backup_id}

        elif finding.suggested_action == "archive":
            for note_id in finding.affected_note_ids:
                self.store.archive_lesson(note_id, reason=f"Archived per health check {finding_id}")
            finding.status = "applied"
            return {"success": True, "message": f"Archived notes: {finding.affected_note_ids}", "backup_id": backup_id}

        elif finding.suggested_action == "redact":
            for note_id in finding.affected_note_ids:
                note_file = self.store.approved_dir / f"{note_id}.md"
                if note_file.exists():
                    clean_text = note_file.read_text(encoding="utf-8")
                    for pat in SECRET_PATTERNS:
                        clean_text = pat.sub("[REDACTED_SECRET]", clean_text)
                    note_file.write_text(clean_text, encoding="utf-8")
            finding.status = "applied"
            return {"success": True, "message": f"Redacted secrets in {finding.affected_note_ids}", "backup_id": backup_id}

        return {"success": False, "message": f"Action {finding.suggested_action} requires manual resolution."}

    def restore_backup(self, backup_id: str) -> bool:
        """Restores notes from versioned backup folder."""
        backup_folder = self.versioning_dir / backup_id
        if not backup_folder.exists():
            return False

        for f in backup_folder.glob("*.md"):
            dest = self.store.approved_dir / f.name
            dest.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        return True
