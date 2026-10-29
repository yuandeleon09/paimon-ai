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
