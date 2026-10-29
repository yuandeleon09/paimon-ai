from typing import Dict, Any, Optional
from app.gemini_client import GeminiClient
from app.memory_store import MemoryStore
from app.validators import (
    PlannerOutput,
    MemoryManagerOutput,
    ResearcherOutput,
    DeveloperOutput,
    TesterOutput,
    ReviewerOutput,
    LearnerOutput,
    BaseAgentOutput
)

class AgentRunner:
    def __init__(self, gemini_client: GeminiClient, memory_store: MemoryStore):
        self.client = gemini_client
        self.memory = memory_store

    def run_agent(self, agent_name: str, task: str, context_data: Dict[str, Any]) -> BaseAgentOutput:
        """Loads prompt, builds context, calls Gemini, and validates structured response."""
        system_instruction = self.memory.get_agent_prompt(agent_name)

        prompt_parts = [
            f"User Task: {task}\n",
            "Context Information:",
        ]

        for k, v in context_data.items():
            if isinstance(v, (dict, list)):
                import json
                def json_serializer(obj):
                    if hasattr(obj, "model_dump"):
                        return obj.model_dump()
                    if hasattr(obj, "__dict__"):
                        return obj.__dict__
                    return str(obj)
                prompt_parts.append(f"--- {k} ---\n{json.dumps(v, indent=2, default=json_serializer)}")
            else:
                prompt_parts.append(f"--- {k} ---\n{str(v)}")

        full_prompt = "\n\n".join(prompt_parts)

        raw_json = self.client.generate_json_response(
            full_prompt,
            system_instruction=system_instruction,
            agent_name=agent_name
        )

        # Validate with specific pydantic models
        if agent_name == "planner":
            return PlannerOutput.model_validate(raw_json)
        elif agent_name == "memory_manager":
            return MemoryManagerOutput.model_validate(raw_json)
        elif agent_name == "researcher":
            return ResearcherOutput.model_validate(raw_json)
        elif agent_name == "developer":
            return DeveloperOutput.model_validate(raw_json)
        elif agent_name == "tester":
            return TesterOutput.model_validate(raw_json)
        elif agent_name == "reviewer":
            return ReviewerOutput.model_validate(raw_json)
        elif agent_name == "learner":
            return LearnerOutput.model_validate(raw_json)
        else:
            return BaseAgentOutput.model_validate(raw_json)
