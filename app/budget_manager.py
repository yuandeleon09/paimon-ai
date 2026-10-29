from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


class TaskWorkType(str, Enum):
    SIMPLE_DIRECT = "simple_direct"
    DOCUMENT_SUMMARY = "document_summary"
    CODING_RESEARCH = "coding_research"
    COMPLEX_COLLABORATIVE = "complex_collaborative"


class TaskClassifier:
    """
    Classifies tasks deterministically based on complexity, attachments, and collaboration needs.
    Enforces that simple tasks use minimal agent calls rather than calling all agents.
    """
    COLLAB_KEYWORDS = {"collaborate", "team", "design", "reservation", "checkout", "architecture", "tradeoff", "contradiction"}
    CODE_KEYWORDS = {
        "code", "function", "script", "class", "test", "build", "develop",
        "refactor", "bug", "fix", "program", "sql", "database", "api",
        "endpoint", "review", "revision", "revise", "email", "validator"
    }
    RESEARCH_KEYWORDS = {"research", "investigate", "literature", "find sources", "deep dive"}

    @classmethod
    def classify(
        cls,
        task: str,
        has_attachments: bool = False,
        collaborative: bool = False
    ) -> Tuple[TaskWorkType, List[str]]:
        task_lower = task.lower().strip()
        words = set(task_lower.split())

        # 1. Complex Collaborative Work
        if collaborative or any(kw in task_lower for kw in cls.COLLAB_KEYWORDS):
            route = ["memory_manager", "planner", "team_room", "developer", "tester", "reviewer", "learning_agent"]
            return TaskWorkType.COMPLEX_COLLABORATIVE, route

        # 2. Document Summary / File Reading
        if has_attachments:
            # If prompt has coding/architecture requests with files, classify as coding_research
            if any(kw in task_lower for kw in cls.CODE_KEYWORDS):
                route = ["attachment_analyst", "memory_manager", "planner", "developer", "tester", "reviewer", "learning_agent"]
                return TaskWorkType.CODING_RESEARCH, route
            route = ["attachment_analyst", "developer"]
            return TaskWorkType.DOCUMENT_SUMMARY, route

        # 3. Coding & Technical Research
        if any(kw in task_lower for kw in cls.CODE_KEYWORDS) or any(kw in task_lower for kw in cls.RESEARCH_KEYWORDS) or len(task_lower.split()) > 25:
            route = ["memory_manager", "planner", "developer", "tester", "reviewer", "learning_agent"]
            return TaskWorkType.CODING_RESEARCH, route

        # 4. Simple Explanation / Formatting / Direct Q&A (Target: 1 model call)
        route = ["developer"]
        return TaskWorkType.SIMPLE_DIRECT, route


@dataclass
class TaskBudget:
    """
    Manages local task logical attempt budget.
    Explicitly labeled as Paimon's application safety cap, NOT Google's live account quota.
    """
    max_attempts: int = 8
    used_attempts: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def can_call(self) -> bool:
        return self.used_attempts < self.max_attempts

    def consume_attempt(self, tokens_in: Optional[int] = None, tokens_out: Optional[int] = None) -> None:
        self.used_attempts += 1
        if tokens_in:
            self.total_input_tokens += tokens_in
        if tokens_out:
            self.total_output_tokens += tokens_out

    def raise_budget(self, additional_attempts: int) -> None:
        if additional_attempts > 0:
            self.max_attempts += additional_attempts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "used_known_attempts": self.used_attempts,
            "limit": self.max_attempts,
            "remaining": max(0, self.max_attempts - self.used_attempts),
            "is_depleted": self.used_attempts >= self.max_attempts,
            "tokens": {
                "input_tokens_known": self.total_input_tokens,
                "output_tokens_known": self.total_output_tokens,
                "total_tokens_known": self.total_input_tokens + self.total_output_tokens
            },
            "note": "Paimon local task attempt safety cap. Does not reflect Google AI Studio account quota."
        }


@dataclass
class ApiAttemptRecord:
    task_id: str
    step_key: str
    agent_role: str
    model: str
    outcome: str  # success, rate_limit_429, quota_exceeded, transient_503, configuration_error, etc.
    http_status: Optional[int] = None
    error_code: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class UsageLedger:
    """
    In-memory and persisted tracker for local provider usage.
    Tracks observed requests and tokens across tasks and specialist roles.
    """
    def __init__(self):
        self._attempts: List[ApiAttemptRecord] = []

    def record(self, attempt: ApiAttemptRecord) -> None:
        self._attempts.append(attempt)

    def get_summary(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        records = [a for a in self._attempts if task_id is None or a.task_id == task_id]
        total_requests = len(records)
        successful = sum(1 for a in records if a.outcome == "success")
        rate_limited = sum(1 for a in records if "rate_limit" in a.outcome or a.http_status == 429)
        quota_exceeded = sum(1 for a in records if "quota" in a.outcome)
        transient_failures = sum(1 for a in records if "transient" in a.outcome or a.http_status in (500, 503))

        total_in = sum(a.input_tokens or 0 for a in records)
        total_out = sum(a.output_tokens or 0 for a in records)

        by_role: Dict[str, int] = {}
        for a in records:
            by_role[a.agent_role] = by_role.get(a.agent_role, 0) + 1

        return {
            "scope": "local_observed_ledger",
            "note": "Observed local requests/tokens. Provider-wide quota is not known.",
            "total_requests": total_requests,
            "successful_requests": successful,
            "rate_limited_requests": rate_limited,
            "quota_exceeded_requests": quota_exceeded,
            "transient_failures": transient_failures,
            "tokens": {
                "input_tokens_known": total_in,
                "output_tokens_known": total_out,
                "total_tokens_known": total_in + total_out
            },
            "by_role": by_role,
            "provider_quota": {
                "status": "Not available — check Google AI Studio",
                "source": "https://aistudio.google.com/usage"
            }
        }
