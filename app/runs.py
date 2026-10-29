import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class RunStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    project_id TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    agent_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    project_id TEXT,
                    task TEXT,
                    status TEXT,
                    verdict TEXT,
                    api_calls INTEGER,
                    final_result TEXT,
                    team_idea_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    rating INTEGER,
                    correction TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    project_id TEXT DEFAULT 'default',
                    task_text TEXT,
                    status TEXT DEFAULT 'queued',
                    current_stage TEXT,
                    work_type TEXT,
                    budget_limit INTEGER DEFAULT 8,
                    used_attempts INTEGER DEFAULT 0,
                    result TEXT,
                    partial_result TEXT,
                    last_error TEXT,
                    idempotency_key TEXT UNIQUE,
                    checkpoint_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    step_key TEXT,
                    agent_role TEXT,
                    status TEXT,
                    result_json TEXT,
                    input_fingerprint TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    step_key TEXT,
                    agent_role TEXT,
                    model TEXT,
                    outcome TEXT,
                    http_status INTEGER,
                    error_code TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_task ON task_steps(task_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_task ON api_attempts(task_id);")
            conn.commit()

    def create_conversation(self, conv_id: str, title: str, project_id: str = "default") -> None:
        with self._get_connection() as conn:
            conn.cursor().execute(
                "INSERT OR REPLACE INTO conversations (id, title, project_id, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (conv_id, title, project_id)
            )
            conn.commit()

    def list_conversations(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute("SELECT * FROM conversations WHERE project_id = ? ORDER BY updated_at DESC", (project_id,))
            else:
                cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def add_message(self, conv_id: str, role: str, content: str, agent_name: Optional[str] = None) -> None:
        with self._get_connection() as conn:
            conn.cursor().execute(
                "INSERT INTO messages (conversation_id, role, content, agent_name) VALUES (?, ?, ?, ?)",
                (conv_id, role, content, agent_name)
            )
            conn.cursor().execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conv_id,)
            )
            conn.commit()

    def get_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conv_id,))
            return [dict(r) for r in cursor.fetchall()]

    def record_run(
        self,
        run_id: str,
        task: str,
        project_id: str,
        status: str,
        verdict: str,
        api_calls: int,
        final_result: str,
        conversation_id: Optional[str] = None,
        team_idea: Optional[Dict[str, Any]] = None
    ) -> None:
        team_json = json.dumps(team_idea) if team_idea else None
        with self._get_connection() as conn:
            conn.cursor().execute(
                """INSERT OR REPLACE INTO runs 
                   (run_id, conversation_id, project_id, task, status, verdict, api_calls, final_result, team_idea_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, conversation_id, project_id, task, status, verdict, api_calls, final_result, team_json)
            )
            conn.commit()

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def record_feedback(self, run_id: str, rating: Optional[int], correction: str) -> None:
        with self._get_connection() as conn:
            conn.cursor().execute(
                "INSERT INTO feedback (run_id, rating, correction) VALUES (?, ?, ?)",
                (run_id, rating, correction)
            )
            conn.commit()

    def clean_old_runs(self, retention_days: int = 14) -> int:
        """Deletes raw diagnostic run metadata older than retention days from SQLite. Never deletes Obsidian user notes."""
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM runs WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    # ==========================================
    # Phase 1: Durable Task Queue & Checkpoints
    # ==========================================

    def create_task(
        self,
        task_id: str,
        task_text: str,
        project_id: str = "default",
        conversation_id: Optional[str] = None,
        budget_limit: int = 8,
        idempotency_key: Optional[str] = None,
        work_type: Optional[str] = None,
        status: str = "queued",
        current_stage: str = "initialized"
    ) -> Dict[str, Any]:
        with self._get_connection() as conn:
            conn.cursor().execute("""
                INSERT OR REPLACE INTO tasks (
                    id, conversation_id, project_id, task_text, status, current_stage,
                    work_type, budget_limit, used_attempts, idempotency_key, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
            """, (task_id, conversation_id, project_id, task_text, status, current_stage, work_type, budget_limit, idempotency_key))
            conn.commit()
        return self.get_task(task_id) or {}

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_task_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE idempotency_key = ?", (idempotency_key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_task_state(
        self,
        task_id: str,
        status: Optional[str] = None,
        current_stage: Optional[str] = None,
        result: Optional[str] = None,
        partial_result: Optional[str] = None,
        last_error: Optional[str] = None,
        used_attempts: Optional[int] = None,
        checkpoint_json: Optional[str] = None
    ) -> None:
        updates = ["updated_at = CURRENT_TIMESTAMP"]
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if current_stage is not None:
            updates.append("current_stage = ?")
            params.append(current_stage)
        if result is not None:
            updates.append("result = ?")
            params.append(result)
        if partial_result is not None:
            updates.append("partial_result = ?")
            params.append(partial_result)
        if last_error is not None:
            updates.append("last_error = ?")
            params.append(last_error)
        if used_attempts is not None:
            updates.append("used_attempts = ?")
            params.append(used_attempts)
        if checkpoint_json is not None:
            updates.append("checkpoint_json = ?")
            params.append(checkpoint_json)

        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        with self._get_connection() as conn:
            conn.cursor().execute(query, tuple(params))
            conn.commit()

    def save_step_checkpoint(
        self,
        task_id: str,
        step_key: str,
        agent_role: str,
        status: str,
        result_data: Any,
        input_fingerprint: str = ""
    ) -> None:
        result_str = json.dumps(result_data) if isinstance(result_data, (dict, list)) else str(result_data)
        with self._get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO task_steps (task_id, step_key, agent_role, status, result_json, input_fingerprint, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (task_id, step_key, agent_role, status, result_str, input_fingerprint))
            conn.commit()

    def get_step_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM task_steps WHERE task_id = ? ORDER BY id ASC", (task_id,))
            return [dict(r) for r in cursor.fetchall()]

    def record_api_attempt(
        self,
        task_id: str,
        step_key: str,
        agent_role: str,
        model: str,
        outcome: str,
        http_status: Optional[int] = None,
        error_code: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None
    ) -> None:
        with self._get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO api_attempts (
                    task_id, step_key, agent_role, model, outcome,
                    http_status, error_code, input_tokens, output_tokens, total_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, step_key, agent_role, model, outcome, http_status, error_code, input_tokens, output_tokens, total_tokens))
            conn.commit()

    def get_local_usage(self, time_window_hours: int = 24) -> Dict[str, Any]:
        cutoff = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_attempts WHERE created_at >= ? ORDER BY id DESC", (cutoff,))
            records = [dict(r) for r in cursor.fetchall()]

        total_requests = len(records)
        successful = sum(1 for r in records if r["outcome"] == "success")
        rate_limited = sum(1 for r in records if "rate_limit" in r["outcome"] or r["http_status"] == 429)
        quota_exceeded = sum(1 for r in records if "quota" in r["outcome"])
        transient_failures = sum(1 for r in records if "transient" in r["outcome"] or r["http_status"] in (500, 503))

        total_in = sum(r["input_tokens"] or 0 for r in records)
        total_out = sum(r["output_tokens"] or 0 for r in records)

        by_role: Dict[str, int] = {}
        for r in records:
            role = r["agent_role"] or "unknown"
            by_role[role] = by_role.get(role, 0) + 1

        return {
            "scope": "local_observed_ledger",
            "time_window_hours": time_window_hours,
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
            "google_account_quota_status": "Not available — check Google AI Studio",
            "provider_quota": {
                "status": "Not available — check Google AI Studio",
                "source": "https://aistudio.google.com/usage"
            }
        }

    def reconcile_startup_tasks(self) -> List[str]:
        """
        Reconciles interrupted/crashed tasks upon system reboot.
        Transitions any lingering 'running' or 'queued' state into 'interrupted',
        safely retaining previously verified checkpoint data without blind re-execution.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tasks WHERE status IN ('running', 'queued')")
            task_ids = [row[0] for row in cursor.fetchall()]
            if task_ids:
                placeholders = ",".join("?" * len(task_ids))
                cursor.execute(f"""
                    UPDATE tasks 
                    SET status = 'interrupted', 
                        last_error = 'Process restarted or interrupted before completion. Click Resume to continue.',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """, task_ids)
                conn.commit()
            return task_ids

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a task, preventing future model calls while preserving partial results."""
        task = self.get_task(task_id)
        if not task:
            return False
        with self._get_connection() as conn:
            conn.cursor().execute("""
                UPDATE tasks
                SET status = 'cancelled',
                    last_error = 'Task was cancelled by user.',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (task_id,))
            conn.commit()
        return True

    def resume_task_record(self, task_id: str, extra_budget: int = 0) -> Optional[Dict[str, Any]]:
        """
        Validates whether a task can be resumed.
        If extra budget is provided (e.g. user raises budget limit), updates the limit.
        """
        task = self.get_task(task_id)
        if not task:
            return None
        resumable_states = {"paused_budget", "paused_rate_limit", "paused_quota", "paused_transient", "interrupted"}
        if task["status"] not in resumable_states:
            return None

        new_budget = task["budget_limit"] + max(0, extra_budget)
        with self._get_connection() as conn:
            conn.cursor().execute("""
                UPDATE tasks
                SET status = 'queued',
                    budget_limit = ?,
                    last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_budget, task_id))
            conn.commit()
        return self.get_task(task_id)

