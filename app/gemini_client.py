import os
import time
import json
import random
import logging
from typing import Optional, Dict, Any

from app.budget_manager import TaskBudget, UsageLedger, ApiAttemptRecord

logger = logging.getLogger("gemini_client")


class GeminiError(RuntimeError):
    """Base exception for Gemini client failures."""
    pass


class GeminiQuotaExhaustedError(GeminiError):
    """Raised when the local task budget or daily provider quota is exhausted."""
    pass


class GeminiRateLimitError(GeminiError):
    """Raised when temporary RPM/TPM rate limits are hit and retries are exhausted."""
    pass


class GeminiTransientError(GeminiError):
    """Raised when 503 or temporary network failures persist after backoff."""
    pass


class GeminiConfigurationError(GeminiError):
    """Raised for 400/401/403/invalid model/key errors where retry would be useless."""
    pass


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite", max_calls: int = 8, mock_mode: bool = False, run_store: Optional[Any] = None):
        self.api_key = api_key.strip()
        self.model = model
        self.max_calls = max_calls
        self.mock_mode = mock_mode
        self.call_count = 0
        self.ledger = UsageLedger()
        self.run_store = run_store
        self._client = None

        if not self.mock_mode and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google-genai Client: {e}")

    def reset_call_count(self) -> None:
        self.call_count = 0

    def _record_attempt(
        self,
        task_id: str,
        step_key: str,
        agent_role: str,
        outcome: str,
        http_status: Optional[int] = None,
        error_code: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        rec = ApiAttemptRecord(
            task_id=task_id,
            step_key=step_key,
            agent_role=agent_role,
            model=self.model,
            outcome=outcome,
            http_status=http_status,
            error_code=error_code,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
        self.ledger.record(rec)
        if self.run_store:
            try:
                self.run_store.record_api_attempt(
                    task_id=task_id,
                    step_key=step_key,
                    agent_role=agent_role,
                    model=self.model,
                    outcome=outcome,
                    http_status=http_status,
                    error_code=error_code,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )
            except Exception:
                pass

    def generate_json_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        agent_name: Optional[str] = None,
        task_budget: Optional[TaskBudget] = None,
        task_id: str = "default",
        step_key: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Sends a request to Gemini expecting JSON output.
        Tracks call limits, records attempt telemetry, and provides jittered backoff.
        """
        role = agent_name or "unknown"

        # Safe admission checks
        if task_budget and not task_budget.can_call():
            raise GeminiQuotaExhaustedError(f"PAUSED_QUOTA: Run exceeded maximum API call budget ({task_budget.max_attempts}).")

        if self.call_count >= self.max_calls:
            raise GeminiQuotaExhaustedError(f"PAUSED_QUOTA: Run exceeded maximum API call budget ({self.max_calls}).")

        if self.mock_mode or not self._client:
            self.call_count += 1
            if task_budget:
                task_budget.consume_attempt(tokens_in=60, tokens_out=120)
            self._record_attempt(
                task_id=task_id,
                step_key=step_key,
                agent_role=role,
                outcome="success",
                http_status=200,
                input_tokens=60,
                output_tokens=120
            )
            return self._generate_mock_response(prompt, system_instruction, agent_name=agent_name)

        # Live Gemini request with bounded retry and jittered backoff
        retries = 3
        base_backoff = 1.0

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System Instruction:\n{system_instruction}\n\nTask:\n{prompt}"

        full_prompt += "\n\nCRITICAL: You MUST respond ONLY with a single valid JSON object. Do not include markdown code block markers or any prose outside the JSON."

        for attempt in range(retries):
            try:
                self.call_count += 1
                if task_budget:
                    task_budget.consume_attempt()

                response = self._client.models.generate_content(
                    model=self.model,
                    contents=full_prompt,
                )

                # Capture token metadata when available
                in_tokens = 0
                out_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    in_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    out_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                self._record_attempt(
                    task_id=task_id,
                    step_key=step_key,
                    agent_role=role,
                    outcome="success",
                    http_status=200,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens
                )

                text = response.text or "{}"
                return self._clean_and_parse_json(text)

            except Exception as e:
                err_str = str(e).lower()

                # 1. Configuration / Authentication Errors (Do NOT retry)
                is_auth_error = any(w in err_str for w in ["401", "403", "invalid_api_key", "permission_denied", "api key not valid", "not found", "404"])
                if is_auth_error:
                    self._record_attempt(
                        task_id=task_id,
                        step_key=step_key,
                        agent_role=role,
                        outcome="configuration_error",
                        http_status=401 if "401" in err_str else (403 if "403" in err_str else 400),
                        error_code="CONFIGURATION_ERROR"
                    )
                    raise GeminiConfigurationError(f"CONFIGURATION_ERROR: Invalid API key or model permissions. Check your .env setup: {e}")

                # 2. Daily / Project Quota Exhaustion (Do NOT retry rapidly)
                is_daily_quota = any(w in err_str for w in ["daily quota", "daily limit", "free_tier_quota_exhausted", "quota limit exceeded for the day", "resource exhausted"]) and ("minute" not in err_str and "rpm" not in err_str)
                if is_daily_quota and "429" in err_str:
                    self._record_attempt(
                        task_id=task_id,
                        step_key=step_key,
                        agent_role=role,
                        outcome="quota_exceeded",
                        http_status=429,
                        error_code="DAILY_QUOTA_EXHAUSTED"
                    )
                    raise GeminiQuotaExhaustedError(f"PAUSED_QUOTA: Daily Gemini free-tier quota may be exhausted. Check Google AI Studio: {e}")

                # 3. Temporary 429 / Rate Limit
                is_rate_limit = "429" in err_str or "rate_limit" in err_str or "resource_exhausted" in err_str
                # 4. Transient 503 / 500 / Overloaded
                is_transient = any(w in err_str for w in ["503", "500", "overloaded", "timeout", "timed out", "connection reset"])

                if (is_rate_limit or is_transient) and attempt < retries - 1:
                    jitter = random.uniform(0.1, 0.6)
                    sleep_time = (base_backoff * (2 ** attempt)) + jitter
                    logger.info(f"Temporary Gemini API throttling ({err_str[:60]}). Backing off for {sleep_time:.2f}s (Attempt {attempt+1}/{retries})")
                    time.sleep(sleep_time)
                    continue

                if is_rate_limit:
                    self._record_attempt(
                        task_id=task_id,
                        step_key=step_key,
                        agent_role=role,
                        outcome="rate_limit_429",
                        http_status=429,
                        error_code="RATE_LIMIT_PAUSED"
                    )
                    raise GeminiRateLimitError(f"PAUSED_RATE_LIMIT: Gemini per-minute rate limit hit after retries. Pausing task safely: {e}")

                if is_transient:
                    self._record_attempt(
                        task_id=task_id,
                        step_key=step_key,
                        agent_role=role,
                        outcome="transient_503",
                        http_status=503 if "503" in err_str else 500,
                        error_code="TRANSIENT_PAUSED"
                    )
                    raise GeminiTransientError(f"PAUSED_TRANSIENT: Transient Gemini service error. Pausing task safely: {e}")

                raise GeminiError(f"Gemini API Error: {e}")

        raise GeminiTransientError("Failed to receive a valid response after retries.")

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback search for first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
            raise ValueError(f"Could not parse valid JSON from output:\n{raw_text}")

    def _generate_mock_response(self, prompt: str, system_instruction: Optional[str], agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Provides simulated structural outputs for offline testing and verification."""
        target_role = (agent_name or "").lower()
        if not target_role:
            sys_lower = (system_instruction or "").lower()
            p_lower = prompt.lower()
            for r in ["planner", "memory_manager", "researcher", "developer", "tester", "reviewer", "learner"]:
                if f"agent: {r}" in sys_lower or f"{r} agent" in sys_lower or r in sys_lower or r in p_lower:
                    target_role = r
                    break

        p_lower = prompt.lower()
        if "agentidea" in p_lower or "idea card" in p_lower:
            role_name = target_role or "developer"
            return {
                "idea_id": f"idea-{role_name[:4]}",
                "role": role_name,
                "project_id": "default",
                "goal": "Solve task securely and effectively",
                "proposal": f"{role_name.capitalize()} proposal for robust architecture.",
                "assumptions": ["Standard execution environment"],
                "evidence_refs": ["Approved memory guidelines"],
                "dependencies": ["validation"],
                "related_tags": ["validation", "security"],
                "risks": ["Edge case inputs"],
                "confidence_label": "high"
            }

        if target_role == "planner":
            return {
                "agent": "planner",
                "summary": "Plan formulated based on task constraints",
                "result": "Structured execution plan and acceptance criteria",
                "steps": [
                    "1. Define components and data schema",
                    "2. Implement core functionality",
                    "3. Validate against edge cases"
                ],
                "acceptance_criteria": [
                    "Input is validated against format specifications",
                    "Invalid inputs produce clear error messages",
                    "All test cases pass without regressions"
                ],
                "needs_research": False,
                "needs_testing": True,
                "evidence": ["Derived from user requirements and project baseline"],
                "uncertainties": [],
                "next_action": "developer"
            }

        if target_role == "memory_manager":
            return {
                "agent": "memory_manager",
                "summary": "Retrieved approved context from vault",
                "result": "Applied shared memory guidelines and approved rules",
                "retrieved_notes": [
                    {
                        "note_path": "01_Memory/shared_memory.md",
                        "trust_status": "project_baseline",
                        "scope": "default",
                        "excerpt": "Zero-cost free-tier architecture; human-in-the-loop memory approval."
                    }
                ],
                "contradictions_or_stale": [],
                "evidence": ["01_Memory/shared_memory.md"],
                "uncertainties": [],
                "next_action": "planner"
            }

        if target_role == "researcher":
            return {
                "agent": "researcher",
                "summary": "Local documentation checked",
                "result": "Verified reference documentation in project workspace",
                "sources": [
                    {
                        "source_url": "local:docs/project.md",
                        "retrieved_date": "2026-10-29",
                        "finding": "Standard conventions and constraints confirmed"
                    }
                ],
                "evidence": ["Local workspace notes"],
                "uncertainties": [],
                "next_action": "developer"
            }

        if target_role == "developer":
            return {
                "agent": "developer",
                "summary": "Implementation developed according to plan",
                "result": "def validate_email(email: str) -> bool:\n    import re\n    if not email or not isinstance(email, str):\n        return False\n    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'\n    return bool(re.match(pattern, email.strip()))\n",
                "implementation_notes": "Implemented robust regex and handled non-string/empty edge cases.",
                "assumptions": ["Standard email RFC format regex suffices."],
                "evidence": ["Matches acceptance criteria."],
                "uncertainties": [],
                "next_action": "tester"
            }

        if target_role == "tester":
            return {
                "agent": "tester",
                "summary": "Test cases defined and verified",
                "result": "Generated unit tests covering normal and edge cases.",
                "test_cases": [
                    {
                        "name": "Test valid email",
                        "test_command": "pytest test_email.py",
                        "executed": False,
                        "exit_code": None,
                        "output": "NOT RUN / Execution tool not enabled"
                    },
                    {
                        "name": "Test empty email",
                        "test_command": "pytest test_email.py",
                        "executed": False,
                        "exit_code": None,
                        "output": "NOT RUN / Execution tool not enabled"
                    }
                ],
                "overall_status": "NOT_RUN",
                "evidence": ["Tests formulated based on acceptance criteria"],
                "uncertainties": ["Runtime execution not authorized"],
                "next_action": "reviewer"
            }

        if target_role == "reviewer":
            return {
                "agent": "reviewer",
                "summary": "Deliverable evaluated against criteria",
                "result": "Code correctly handles specifications and edge cases.",
                "verdict": "PASS",
                "issues": [],
                "evidence": ["Code matches all acceptance criteria."],
                "uncertainties": [],
                "next_action": "learner"
            }

        if target_role == "learner":
            return {
                "agent": "learner",
                "summary": "Extracted key takeaways for future runs",
                "result": "Identified input validation best practice",
                "proposed_lessons": [
                    {
                        "claim": "Always validate empty and non-string inputs at function entry.",
                        "evidence": "Observed input validation requirements in task.",
                        "scope": "default",
                        "reason": "Prevents runtime AttributeError or UnboundLocalError.",
                        "kind": "best_practice"
                    }
                ],
                "evidence": ["Implementation edge cases"],
                "uncertainties": [],
                "next_action": "complete"
            }

        return {
            "agent": "unknown",
            "summary": "Generic response",
            "result": "OK",
            "evidence": [],
            "uncertainties": [],
            "next_action": "complete"
        }
