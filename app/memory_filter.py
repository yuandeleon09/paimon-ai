from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from pathlib import Path
import re

class MemoryCandidate(BaseModel):
    lesson_id: str
    title: str
    body: str
    project_id: str = "default"
    scope: str = "project"
    evidence: str
    status: str = "pending"
    source_run_ids: List[str] = Field(default_factory=list)
    novelty: int = 0
    impact: int = 0
    durability: int = 0
    reuse_score: int = 0
    evidence_score: int = 0
    total_score: int = 0
    target_canonical_note: Optional[str] = None
    is_merge: bool = False
    is_conflict: bool = False
    conflict_details: str = ""

class MemoryFilterResult(BaseModel):
    should_store: bool
    score: int
    rationale: str
    candidates: List[MemoryCandidate] = Field(default_factory=list)

def evaluate_memory_value(
    task: str,
    outcome_result: str,
    feedback: Optional[str] = None,
    test_verified: bool = False,
    existing_approved_notes: Optional[List[Dict[str, Any]]] = None,
    min_score: int = 7,
    max_words: int = 100,
    max_candidates: int = 2
) -> MemoryFilterResult:
    """
    Evaluates whether a task generated durable, high-value, reusable lessons worthy
    of being stored as Pending notes in Obsidian, versus routine/transient tasks.
    """
    existing_approved = existing_approved_notes or []
    task_lower = task.lower()
    outcome_lower = outcome_result.lower()

    # Rule 1: Immediate disqualifiers for trivial/one-off tasks
    trivial_patterns = [
        r"^(what is|calculate|solve|convert|how much|explain briefly)\b",
        r"\b(2\s*\+\s*2|weather|capital of|synonym|joke|label)\b",
    ]
    if any(re.search(pat, task_lower) for pat in trivial_patterns) and not feedback and not test_verified:
        return MemoryFilterResult(
            should_store=False,
            score=2,
            rationale="Trivial query or general knowledge. Discarded per V2 Smart Memory Policy."
        )

    # Dimension 1: Durability (0-2)
    # Does it describe a permanent architecture decision, persistent constraint, or reusable pattern?
    durability = 0
    if any(w in outcome_lower for w in ["always", "ensure", "invariant", "schema", "architecture", "standard", "never", "pattern", "retry", "backoff", "transaction"]):
        durability = 2
    elif any(w in task_lower for w in ["function", "class", "validate", "api", "database", "security", "rules"]):
        durability = 1

    # Dimension 2: Future Reuse (0-2)
    # Is this applicable across tasks in the project?
    future_reuse = 0
    if any(w in task_lower for w in ["validate", "auth", "login", "payment", "transaction", "model", "config", "test", "rules"]):
        future_reuse = 2
    elif len(task.split()) > 2:
        future_reuse = 1

    # Dimension 3: Novelty vs Existing Approved Notes (0-2)
    novelty = 2
    potential_merge_target = None
    is_conflict = False
    conflict_reason = ""

    for note in existing_approved:
        note_text = (note.get("excerpt", "") + " " + note.get("note_path", "")).lower()
        
        # Check if this conflicts with approved note
        if ("do not" in outcome_lower and "always" in note_text) or \
           ("client-side" in outcome_lower and "server-side" in note_text) or \
           ("server-side" in outcome_lower and "client-side" in note_text):
            is_conflict = True
            conflict_reason = f"Candidate contradicts rule in approved note: {note.get('note_path')}"
            novelty = 2
            break

        # Check for duplication or overlap
        shared_keywords = [w for w in task_lower.split() if (len(w) > 4 and w in note_text) or (w in ["auth", "rule", "rules", "test", "flow"] and w in note_text)]
        if len(shared_keywords) >= 2 or ("payment" in task_lower and "payment" in note_text):
            novelty = 1
            potential_merge_target = note.get("note_path")

    # Dimension 4: Impact on Quality / Safety (0-2)
    impact = 0
    if any(w in outcome_lower for w in ["security", "error", "exception", "race condition", "idempotent", "vulnerability", "leak", "retry", "backoff"]):
        impact = 2
    elif any(w in outcome_lower for w in ["validation", "unittest", "typeerror", "valueerror", "robust", "rules"]):
        impact = 1

    # Dimension 5: Evidence / Confirmation (0-2)
    evidence_score = 0
    evidence_desc = "Observed from model synthesis"
    if feedback:
        evidence_score = 2
        evidence_desc = f"Direct human correction/feedback: '{feedback[:60]}'"
    elif test_verified:
        evidence_score = 2
        evidence_desc = "Verified by passing executed unit/integration test"
    elif "test" in outcome_lower or "def test_" in outcome_result:
        evidence_score = 1
        evidence_desc = "Unit tests formulated in code artifact"

    total = durability + future_reuse + novelty + impact + evidence_score

    if total < min_score:
        return MemoryFilterResult(
            should_store=False,
            score=total,
            rationale=f"Task score {total}/{10} below threshold {min_score}. Routine outcome; no Obsidian note created."
        )

    # Build concise candidate (<= 100 words body)
    words = outcome_result.split()
    concise_claim = f"Ensure verified handling for: {task.strip()}"
    if feedback:
        concise_claim = f"User preference/fix: {feedback.strip()}"
    elif "def " in outcome_result:
        concise_claim = f"Robust implementation standard for {task.strip()}"

    body_lines = [
        f"**Rule:** {concise_claim}",
        f"**Scope:** Project-level guideline.",
        f"**Evidence:** {evidence_desc}.",
        f"**Quality Score:** {total}/10 (Durability: {durability}, Reuse: {future_reuse}, Novelty: {novelty}, Impact: {impact}, Evidence: {evidence_score})."
    ]
    concise_body = "\n".join(body_lines)
    # Ensure <= max_words
    body_word_count = len(concise_body.split())
    if body_word_count > max_words:
        concise_body = " ".join(concise_body.split()[:max_words])

    candidate = MemoryCandidate(
        lesson_id=f"MEM-{abs(hash(task)) % 10000:04d}",
        title=f"Lesson: {task[:40]}",
        body=concise_body,
        project_id="default",
        scope="project",
        evidence=evidence_desc,
        status="pending",
        novelty=novelty,
        impact=impact,
        durability=durability,
        reuse_score=future_reuse,
        evidence_score=evidence_score,
        total_score=total,
        target_canonical_note=potential_merge_target,
        is_merge=(potential_merge_target is not None and not is_conflict),
        is_conflict=is_conflict,
        conflict_details=conflict_reason
    )

    return MemoryFilterResult(
        should_store=True,
        score=total,
        rationale=f"High-value verified lesson identified (Score {total}/10). Created Pending proposal.",
        candidates=[candidate][:max_candidates]
    )
