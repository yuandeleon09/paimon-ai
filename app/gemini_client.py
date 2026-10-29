import os
import time
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("gemini_client")

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", max_calls: int = 8, mock_mode: bool = False):
        self.api_key = api_key.strip()
        self.model = model
        self.max_calls = max_calls
        self.mock_mode = mock_mode
        self.call_count = 0
        self._client = None

        if not self.mock_mode and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google-genai Client: {e}")

    def reset_call_count(self) -> None:
        self.call_count = 0

    def generate_json_response(self, prompt: str, system_instruction: Optional[str] = None, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a request to Gemini expecting JSON output.
        Tracks call limits and provides exponential backoff for transient 429/503 errors.
        """
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"PAUSED_QUOTA: Run exceeded maximum API call budget ({self.max_calls}).")

        if self.mock_mode or not self._client:
            self.call_count += 1
            return self._generate_mock_response(prompt, system_instruction, agent_name=agent_name)

        # Live Gemini request with retry logic
        retries = 3
        backoff = 2.0

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System Instruction:\n{system_instruction}\n\nTask:\n{prompt}"

        # Instruction for JSON
        full_prompt += "\n\nCRITICAL: You MUST respond ONLY with a single valid JSON object. Do not include markdown code block markers or any prose outside the JSON."

        for attempt in range(retries):
            try:
                self.call_count += 1
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=full_prompt,
                )
                text = response.text or "{}"
                return self._clean_and_parse_json(text)

            except Exception as e:
                err_str = str(e).lower()
                is_quota_or_rate = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str
                is_transient = "503" in err_str or "overloaded" in err_str

                if (is_quota_or_rate or is_transient) and attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue

                if is_quota_or_rate:
                    raise RuntimeError(f"PAUSED_QUOTA: Gemini free-tier rate limit or quota exceeded: {e}")
                raise RuntimeError(f"Gemini API Error: {e}")

        raise RuntimeError("Failed to receive a valid response after retries.")

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
