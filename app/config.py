from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv

@dataclass
class SystemConfig:
    project_root: Path
    vault_path: Path
    workspace_path: Optional[Path] = None
    app_data_path: Optional[Path] = None
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    max_model_calls_per_task: int = 8
    max_revisions: int = 1
    max_retrieved_memories: int = 5
    max_memory_context_tokens: int = 700
    memory_min_score: int = 7
    max_memory_words: int = 100
    max_candidate_memories_per_task: int = 2
    max_collaborators: int = 3
    max_ideas_per_agent: int = 2
    max_team_revisions: int = 1
    run_metadata_retention_days: int = 14
    allow_live_tools: bool = False

    # Backward compatibility parameters
    max_review_revisions: Optional[int] = None
    max_api_calls_per_run: Optional[int] = None

    def __post_init__(self):
        if self.workspace_path is None:
            self.workspace_path = self.project_root / "workspace"
        if self.app_data_path is None:
            self.app_data_path = self.project_root / "app_data"
        if self.max_review_revisions is not None:
            self.max_revisions = self.max_review_revisions
        else:
            self.max_review_revisions = self.max_revisions
        if self.max_api_calls_per_run is not None:
            self.max_model_calls_per_task = self.max_api_calls_per_run
        else:
            self.max_api_calls_per_run = self.max_model_calls_per_task

def load_config(root_dir: Path | None = None) -> SystemConfig:
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent

    env_path = root_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key in ("replace_with_your_key_locally", "replace_with_your_api_key"):
        api_key = ""

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    if not model:
        model = "gemini-3.5-flash-lite"

    vault_rel = os.getenv("OBSIDIAN_VAULT", "./Obsidian-Brain").strip()
    vault_path = (root_dir / vault_rel).resolve() if not Path(vault_rel).is_absolute() else Path(vault_rel)
    workspace_path = (root_dir / "workspace").resolve()
    app_data_path = (root_dir / "app_data").resolve()

    max_calls = int(os.getenv("MAX_MODEL_CALLS_PER_TASK", os.getenv("MAX_API_CALLS_PER_RUN", "8")))
    max_revs = int(os.getenv("MAX_REVISIONS", os.getenv("MAX_REVIEW_REVISIONS", "1")))
    max_retrieved = int(os.getenv("MAX_RETRIEVED_MEMORIES", "5"))
    max_tokens = int(os.getenv("MAX_MEMORY_CONTEXT_TOKENS", "700"))
    min_score = int(os.getenv("MEMORY_MIN_SCORE", "7"))
    max_words = int(os.getenv("MAX_MEMORY_WORDS", "100"))
    max_candidates = int(os.getenv("MAX_CANDIDATE_MEMORIES_PER_TASK", "2"))
    max_collabs = int(os.getenv("MAX_COLLABORATORS", "3"))
    max_ideas = int(os.getenv("MAX_IDEAS_PER_AGENT", "2"))
    max_team_revs = int(os.getenv("MAX_TEAM_REVISIONS", "1"))
    retention_days = int(os.getenv("RUN_METADATA_RETENTION_DAYS", "14"))

    allow_live_tools = (
        os.getenv("ENABLE_CODE_EXECUTION", "false").lower() in ("1", "true", "yes") or
        os.getenv("ALLOW_LIVE_TOOLS", "false").lower() in ("1", "true", "yes")
    )

    return SystemConfig(
        project_root=root_dir,
        vault_path=vault_path,
        workspace_path=workspace_path,
        app_data_path=app_data_path,
        gemini_api_key=api_key,
        gemini_model=model,
        max_model_calls_per_task=max_calls,
        max_revisions=max_revs,
        max_retrieved_memories=max_retrieved,
        max_memory_context_tokens=max_tokens,
        memory_min_score=min_score,
        max_memory_words=max_words,
        max_candidate_memories_per_task=max_candidates,
        max_collaborators=max_collabs,
        max_ideas_per_agent=max_ideas,
        max_team_revisions=max_team_revs,
        run_metadata_retention_days=retention_days,
        allow_live_tools=allow_live_tools,
    )
