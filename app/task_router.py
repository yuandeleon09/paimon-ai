from typing import List, Dict, Any

class TaskRouter:
    @staticmethod
    def determine_route(task_description: str, needs_research: bool = False, needs_testing: bool = True) -> List[str]:
        """
        Selects the minimal sequence of agents necessary to complete the task,
        optimizing for free-tier token conservation.
        """
        task_lower = task_description.lower()

        # Always starts with memory retrieval & planning
        route = ["memory_manager", "planner"]

        # Check if research is explicitly required
        if needs_research or any(w in task_lower for w in ["research", "investigate", "find sources", "literature"]):
            route.append("researcher")

        # Developer builds deliverable
        route.append("developer")

        # Determine if QA testing is needed (coding/logic vs purely explanatory text)
        is_code = any(w in task_lower for w in ["code", "function", "script", "class", "test", "build", "develop", "refactor", "bug", "fix", "program"])
        if needs_testing or is_code:
            route.append("tester")

        # Reviewer checks deliverable
        route.append("reviewer")

        # Learning agent records lessons
        route.append("learner")

        return route
