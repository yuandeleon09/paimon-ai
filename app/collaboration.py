from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import uuid

class AgentIdea(BaseModel):
    idea_id: str = Field(default_factory=lambda: f"idea-{uuid.uuid4().hex[:6]}")
    role: str
    project_id: str = "default"
    goal: str
    proposal: str
    assumptions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    related_tags: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    confidence_label: Literal["high", "medium", "low", "unverified"] = "medium"

class Relationship(BaseModel):
    from_idea_id: str
    to_idea_id: str
    from_role: str = ""
    to_role: str = ""
    rel_type: Literal["supports", "complements", "depends_on", "overlaps", "contradicts", "unrelated"]
    reason: str

class TeamIdea(BaseModel):
    team_idea_id: str = Field(default_factory=lambda: f"team-idea-{uuid.uuid4().hex[:6]}")
    task_id: str
    title: str
    synthesis: str
    relationships: List[Relationship] = Field(default_factory=list)
    contributor_ids: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    conflicts_detected: List[str] = Field(default_factory=list)

def correlate_ideas(ideas: List[AgentIdea]) -> List[Relationship]:
    """
    Deterministically correlates independent agent ideas based on goal, tags,
    dependencies, and keywords to identify relationships without forcing fake consensus.
    """
    relationships: List[Relationship] = []
    if len(ideas) < 2:
        return relationships

    for i in range(len(ideas)):
        for j in range(i + 1, len(ideas)):
            a = ideas[i]
            b = ideas[j]

            # Compare tags and dependencies
            common_tags = set(t.lower() for t in a.related_tags) & set(t.lower() for t in b.related_tags)
            common_deps = set(d.lower() for d in a.dependencies) & set(d.lower() for d in b.dependencies)

            text_a = (a.proposal + " " + " ".join(a.assumptions)).lower()
            text_b = (b.proposal + " " + " ".join(b.assumptions)).lower()

            # Check for direct contradictions (e.g. client-only vs server-only, or opposite assertions)
            is_contradictory = False
            contradiction_pairs = [
                ("client-side only", "server-side"),
                ("no validation", "validate"),
                ("synchronous", "asynchronous"),
                ("client only", "backend only"),
                ("do not sanitize", "sanitize"),
            ]
            for term_x, term_y in contradiction_pairs:
                if (term_x in text_a and term_y in text_b) or (term_y in text_a and term_x in text_b):
                    is_contradictory = True
                    break

            if is_contradictory:
                relationships.append(Relationship(
                    from_idea_id=a.idea_id,
                    to_idea_id=b.idea_id,
                    from_role=a.role,
                    to_role=b.role,
                    rel_type="contradicts",
                    reason=f"{a.role} and {b.role} express contradictory architectural or validation claims."
                ))
                continue

            # Check dependencies
            if any(d in text_b for d in a.dependencies):
                relationships.append(Relationship(
                    from_idea_id=a.idea_id,
                    to_idea_id=b.idea_id,
                    from_role=a.role,
                    to_role=b.role,
                    rel_type="depends_on",
                    reason=f"{a.role} proposal depends on components addressed by {b.role}."
                ))
                continue

            # Check complementary or supporting
            if common_tags or common_deps or any(w in text_b for w in a.related_tags if len(w) > 3):
                relationships.append(Relationship(
                    from_idea_id=a.idea_id,
                    to_idea_id=b.idea_id,
                    from_role=a.role,
                    to_role=b.role,
                    rel_type="complements",
                    reason=f"{a.role} and {b.role} address complementary aspects of {', '.join(common_tags or ['the objective'])}."
                ))
            elif any(w in text_b for w in text_a.split() if len(w) > 5 and w not in ["function", "system", "method", "module"]):
                relationships.append(Relationship(
                    from_idea_id=a.idea_id,
                    to_idea_id=b.idea_id,
                    from_role=a.role,
                    to_role=b.role,
                    rel_type="supports",
                    reason=f"{a.role} proposal supports {b.role} proposal with aligned domain keywords."
                ))
            else:
                relationships.append(Relationship(
                    from_idea_id=a.idea_id,
                    to_idea_id=b.idea_id,
                    from_role=a.role,
                    to_role=b.role,
                    rel_type="unrelated",
                    reason=f"No shared tags or dependencies detected between {a.role} and {b.role}."
                ))

    return relationships

def synthesize_team_idea(
    task: str,
    ideas: List[AgentIdea],
    relationships: List[Relationship],
    gemini_client: Optional[Any] = None
) -> TeamIdea:
    """
    Synthesizes compatible proposals into a unified TeamIdea with contributor attribution,
    tradeoffs, and explicit conflict callouts.
    """
    contributor_ids = [idea.idea_id for idea in ideas]
    conflicts = [r.reason for r in relationships if r.rel_type == "contradicts"]
    unrelated = [r for r in relationships if r.rel_type == "unrelated"]

    compatible_ideas = [
        idea for idea in ideas 
        if not any(r.rel_type == "contradicts" and (r.from_idea_id == idea.idea_id or r.to_idea_id == idea.idea_id) for r in relationships)
    ]

    # Synthesize title and core approach
    title = f"Team Collaboration: {task}"
    synthesis_points = []
    tradeoffs = []
    open_questions = []

    for idea in ideas:
        synthesis_points.append(f"[{idea.role.upper()}]: {idea.proposal}")
        tradeoffs.extend(idea.risks)
        open_questions.extend([f"Assumption by {idea.role}: {a}" for a in idea.assumptions])

    if conflicts:
        synthesis_summary = (
            "The team reached partial agreement with active unresolved contradictions:\n" +
            "\n".join([f"- {sp}" for sp in synthesis_points]) +
            "\n\n**Contradictions / Disagreements to Resolve:**\n" +
            "\n".join([f"- [CONFLICT] {c}" for c in conflicts])
        )
    else:
        synthesis_summary = (
            "Integrated Team Strategy:\n" +
            "\n".join([f"- {sp}" for sp in synthesis_points])
        )

    criteria = [
        "All verified specialist proposals are addressed",
        "Edge cases and race conditions are mitigated",
        "No conflicting assumptions remain unaddressed"
    ]

    return TeamIdea(
        task_id=task[:30],
        title=title,
        synthesis=synthesis_summary,
        relationships=relationships,
        contributor_ids=contributor_ids,
        tradeoffs=list(set(tradeoffs))[:5],
        open_questions=list(set(open_questions))[:5],
        acceptance_criteria=criteria,
        conflicts_detected=conflicts
    )
