"""
AEGIS Memory Manager
Unified interface for reading, writing, and searching persistent user memory, rules, and context.
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional
from aegis.config import DB_PATH, RiskLevel, SupervisionMode
from aegis.memory.db import get_db_connection

class MemoryManager:
    """Provides structured CRUD and retrieval access to AEGIS persistent memory."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH

    def _get_conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    # ------------------ USER PROFILE ------------------ #
    def get_user_profile(self) -> Dict[str, Any]:
        """Retrieves primary user profile and active supervision mode."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1").fetchone()
            if row:
                return dict(row)
            return {
                "name": "User",
                "role": "Executive",
                "preferred_tone": "Professional",
                "supervision_mode": SupervisionMode.BALANCED.value
            }
        finally:
            conn.close()

    def update_user_profile(self, name: Optional[str] = None, role: Optional[str] = None,
                            preferred_tone: Optional[str] = None, supervision_mode: Optional[str] = None) -> bool:
        """Updates user settings."""
        conn = self._get_conn()
        try:
            profile = self.get_user_profile()
            new_name = name if name is not None else profile.get("name", "User")
            new_role = role if role is not None else profile.get("role", "Executive")
            new_tone = preferred_tone if preferred_tone is not None else profile.get("preferred_tone", "Professional")
            new_mode = supervision_mode if supervision_mode is not None else profile.get("supervision_mode", "BALANCED")

            conn.execute("""
                UPDATE users
                SET name = ?, role = ?, preferred_tone = ?, supervision_mode = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (new_name, new_role, new_tone, new_mode))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ RULES ENGINE MEMORY ------------------ #
    def get_rules(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Fetches all system and user-defined rules."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM rules"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY id ASC"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_rule(self, name: str, rule_text: str, risk_override: Optional[str] = "HIGH", is_active: bool = True) -> int:
        """Adds a new custom safety policy rule."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO rules (name, rule_text, risk_override, is_active)
                VALUES (?, ?, ?, ?)
            """, (name, rule_text, risk_override, 1 if is_active else 0))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def toggle_rule(self, rule_id: int, is_active: bool) -> bool:
        """Enables or disables an existing rule."""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE rules SET is_active = ? WHERE id = ?", (1 if is_active else 0, rule_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_rule(self, rule_id: int) -> bool:
        """Deletes a rule."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ KNOWLEDGE VAULT ------------------ #
    def store_knowledge(self, topic: str, fact_content: str, category: str = "general",
                        source: str = "interaction", confidence: float = 1.0) -> int:
        """Stores a persistent fact or note in the knowledge vault."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO knowledge_vault (category, topic, fact_content, source, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (category, topic, fact_content, source, confidence))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_all_knowledge(self) -> List[Dict[str, Any]]:
        """Returns all knowledge items."""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM knowledge_vault ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    get_knowledge_vault = get_all_knowledge
    store_fact = store_knowledge

    def delete_knowledge(self, fact_id: int) -> bool:
        """Deletes a specific knowledge fact."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM knowledge_vault WHERE id = ?", (fact_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def retrieve_relevant_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple keyword/topic relevance search over stored facts."""
        tokens = [t.lower().strip() for t in query.split() if len(t) > 3]
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM knowledge_vault").fetchall()
            all_facts = [dict(r) for r in rows]
        finally:
            conn.close()

        if not tokens:
            return all_facts[:limit]

        scored = []
        for fact in all_facts:
            score = 0
            text = (fact["topic"] + " " + fact["fact_content"] + " " + fact["category"]).lower()
            for token in tokens:
                if token in text:
                    score += 2 if token in fact["topic"].lower() else 1
            if score > 0:
                scored.append((score, fact))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    # ------------------ PROJECTS ------------------ #
    def get_projects(self) -> List[Dict[str, Any]]:
        """Returns list of active projects."""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            projects = []
            for r in rows:
                p = dict(r)
                try:
                    p["metadata"] = json.loads(p.get("metadata_json", "{}"))
                except Exception:
                    p["metadata"] = {}
                projects.append(p)
            return projects
        finally:
            conn.close()

    def add_project(self, title: str, description: str = "", metadata: Optional[Dict] = None) -> int:
        """Creates a new tracked project."""
        meta_str = json.dumps(metadata or {})
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO projects (title, description, metadata_json)
                VALUES (?, ?, ?)
            """, (title, description, meta_str))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_project(self, project_id: int, title: Optional[str] = None,
                       description: Optional[str] = None, status: Optional[str] = None) -> bool:
        """Updates an existing project."""
        conn = self._get_conn()
        try:
            current = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not current:
                return False
            n_title = title if title is not None else current["title"]
            n_desc = description if description is not None else current["description"]
            n_status = status if status is not None else current["status"]

            conn.execute("""
                UPDATE projects
                SET title = ?, description = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (n_title, n_desc, n_status, project_id))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ CONVERSATIONS ------------------ #
    def record_message(self, session_id: str, role: str, content: str,
                       intent: Optional[str] = None, decision_state: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> int:
        """Stores a message in conversation history."""
        meta_str = json.dumps(metadata or {})
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO conversations (session_id, role, content, intent, decision_state, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, role, content, intent, decision_state, meta_str))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent conversation turns for context injection."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (session_id, limit)).fetchall()
            history = [dict(r) for r in reversed(rows)]
            return history
        finally:
            conn.close()

    def clear_history(self, session_id: Optional[str] = None) -> bool:
        """Clears conversation history."""
        conn = self._get_conn()
        try:
            if session_id:
                conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            else:
                conn.execute("DELETE FROM conversations")
            conn.commit()
            return True
        finally:
            conn.close()
