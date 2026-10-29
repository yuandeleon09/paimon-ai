from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class BaseAgentOutput(BaseModel):
    agent: str
    summary: str
    result: str
    evidence: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    next_action: str

class PlannerOutput(BaseAgentOutput):
    agent: Literal["planner"] = "planner"
    steps: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    needs_research: bool = False
    needs_testing: bool = True

class MemoryItem(BaseModel):
    note_path: str
    trust_status: Literal["approved", "pending", "rejected", "project_baseline"]
    scope: str = "default"
    excerpt: str

class MemoryManagerOutput(BaseAgentOutput):
    agent: Literal["memory_manager"] = "memory_manager"
    retrieved_notes: List[MemoryItem] = Field(default_factory=list)
    contradictions_or_stale: List[str] = Field(default_factory=list)

class ResearchSource(BaseModel):
    source_url: str
    retrieved_date: str
    finding: str

class ResearcherOutput(BaseAgentOutput):
    agent: Literal["researcher"] = "researcher"
    sources: List[ResearchSource] = Field(default_factory=list)

class DeveloperOutput(BaseAgentOutput):
    agent: Literal["developer"] = "developer"
    implementation_notes: str = ""
    assumptions: List[str] = Field(default_factory=list)

class TestCase(BaseModel):
    name: str
    test_command: str
    executed: bool = False
    exit_code: Optional[int] = None
    output: str = "NOT RUN"

class TesterOutput(BaseAgentOutput):
    agent: Literal["tester"] = "tester"
    test_cases: List[TestCase] = Field(default_factory=list)
    overall_status: Literal["PASSED", "FAILED", "NOT_RUN", "BLOCKED"] = "NOT_RUN"

class ReviewIssue(BaseModel):
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    description: str
    remediation: str

class ReviewerOutput(BaseAgentOutput):
    agent: Literal["reviewer"] = "reviewer"
    verdict: Literal["PASS", "REVISE", "BLOCKED"]
    issues: List[ReviewIssue] = Field(default_factory=list)

class ProposedLesson(BaseModel):
    claim: str
    evidence: str
    scope: str = "default"
    reason: str
    kind: Literal["user_correction", "best_practice", "pitfall_avoidance"] = "best_practice"

class LearnerOutput(BaseAgentOutput):
    agent: Literal["learner"] = "learner"
    proposed_lessons: List[ProposedLesson] = Field(default_factory=list)
