"""
AEGIS Audit Logger
Maintains a verifiable, structured action history for all pipeline operations.
Logs: Timestamp, Request, Intent, Risk Level, Supervision Decision, User Approval, Action, Result, and Duration.
"""

import os
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from aegis.config import DB_PATH, LOGS_PATH, RiskLevel
from aegis.memory.db import get_db_connection

class AuditLogger:
    """Action History and Audit Log Manager for AEGIS."""

    def __init__(self, db_path: Optional[Path] = None, json_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.json_path = json_path or LOGS_PATH

    def _get_conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def generate_execution_hash(self, user_prompt: str, intent: str, action: str, timestamp_str: str) -> str:
        """Computes a SHA-256 cryptographic verification digest of the execution entry."""
        payload = f"{timestamp_str}:{user_prompt}:{intent}:{action}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def log_action(self,
                   execution_id: str,
                   user_prompt: str,
                   detected_intent: str,
                   risk_level: str,
                   supervision_reason: str,
                   user_approval_status: str,
                   executed_action: str,
                   action_params: Dict[str, Any],
                   result_status: str,
                   result_summary: str,
                   duration_ms: float) -> Dict[str, Any]:
        """
        Records an execution event to persistent SQLite and updates backup JSON.
        Uses INSERT OR REPLACE to ensure updates to an existing execution_id update the single record.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        exec_hash = self.generate_execution_hash(user_prompt, detected_intent, executed_action, timestamp)

        log_data = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "user_prompt": user_prompt,
            "detected_intent": detected_intent,
            "risk_level": risk_level,
            "supervision_reason": supervision_reason,
            "user_approval_status": user_approval_status,
            "executed_action": executed_action,
            "action_params": json.dumps(action_params) if isinstance(action_params, dict) else str(action_params),
            "result_status": result_status,
            "result_summary": result_summary,
            "execution_hash": exec_hash,
            "duration_ms": duration_ms
        }

        conn = self._get_conn()
        try:
            # Check if record already exists for this execution_id
            existing = conn.execute("SELECT id FROM action_logs WHERE execution_id = ?", (execution_id,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE action_logs SET
                        timestamp = ?, user_prompt = ?, detected_intent = ?, risk_level = ?,
                        supervision_reason = ?, user_approval_status = ?, executed_action = ?,
                        action_params = ?, result_status = ?, result_summary = ?,
                        execution_hash = ?, duration_ms = ?
                    WHERE execution_id = ?
                """, (
                    timestamp, user_prompt, detected_intent, risk_level,
                    supervision_reason, user_approval_status, executed_action,
                    log_data["action_params"], result_status, result_summary,
                    exec_hash, duration_ms, execution_id
                ))
            else:
                conn.execute("""
                    INSERT INTO action_logs (
                        execution_id, timestamp, user_prompt, detected_intent, risk_level,
                        supervision_reason, user_approval_status, executed_action,
                        action_params, result_status, result_summary, execution_hash, duration_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, timestamp, user_prompt, detected_intent, risk_level,
                    supervision_reason, user_approval_status, executed_action,
                    log_data["action_params"], result_status, result_summary, exec_hash, duration_ms
                ))
            conn.commit()
        finally:
            conn.close()

        # Backup to JSON file asynchronously / defensively
        try:
            self._append_to_json_backup(log_data)
        except Exception as e:
            print(f"[AuditLogger Warning] JSON backup failed: {e}")

        return log_data

    def _append_to_json_backup(self, entry: Dict[str, Any]):
        os.makedirs(self.json_path.parent, exist_ok=True)
        entries = []
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []
        entries.append(entry)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(entries[-200:], f, indent=2)

    def get_recent_logs(self, limit: int = 50, risk_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves recent logs sorted chronologically descending."""
        conn = self._get_conn()
        try:
            if risk_filter:
                query = "SELECT * FROM action_logs WHERE risk_level = ? ORDER BY id DESC LIMIT ?"
                rows = conn.execute(query, (risk_filter, limit)).fetchall()
            else:
                query = "SELECT * FROM action_logs ORDER BY id DESC LIMIT ?"
                rows = conn.execute(query, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Calculates audit metrics for the dashboard."""
        conn = self._get_conn()
        try:
            total_actions = conn.execute("SELECT COUNT(*) as c FROM action_logs").fetchone()["c"]
            approved_count = conn.execute("SELECT COUNT(*) as c FROM action_logs WHERE user_approval_status IN ('APPROVED_BY_USER', 'AUTO_APPROVED')").fetchone()["c"]
            rejected_count = conn.execute("SELECT COUNT(*) as c FROM action_logs WHERE user_approval_status = 'REJECTED_BY_USER'").fetchone()["c"]
            blocked_count = conn.execute("SELECT COUNT(*) as c FROM action_logs WHERE result_status = 'SAFETY_BLOCKED' OR user_approval_status = 'REFUSED_BY_SYSTEM'").fetchone()["c"]

            risk_counts = {}
            for r in [RiskLevel.SAFE.value, RiskLevel.LOW.value, RiskLevel.MEDIUM.value, RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
                count = conn.execute("SELECT COUNT(*) as c FROM action_logs WHERE risk_level = ?", (r,)).fetchone()["c"]
                risk_counts[r] = count

            return {
                "total_actions": total_actions,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "safety_blocked_count": blocked_count,
                "risk_breakdown": risk_counts
            }
        finally:
            conn.close()

    # Aliases for flexible API callers
    get_execution_stats = get_metrics_summary

    def export_as_markdown(self) -> str:
        """Generates a clean Markdown report of the audit history."""
        logs = self.get_recent_logs(limit=100)
        lines = [
            "# AEGIS Action Audit History Report",
            f"*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "| Timestamp | Request | Intent | Risk Level | Decision / Approval | Executed Action | Result |",
            "|---|---|---|---|---|---|---|"
        ]
        for l in logs:
            clean_prompt = l['user_prompt'].replace("|", "\\|")[:40]
            lines.append(f"| {l['timestamp']} | {clean_prompt}... | `{l['detected_intent']}` | **{l['risk_level']}** | {l['user_approval_status']} | `{l['executed_action']}` | {l['result_status']} |")

        return "\n".join(lines)

    export_markdown_report = export_as_markdown
