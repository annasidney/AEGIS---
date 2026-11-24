"""
AEGIS SQLite Database Schema and Connection Manager
Handles table initialization, indexing, and connection lifecycle.
"""

import sqlite3
from pathlib import Path
from typing import Optional
from aegis.config import DB_PATH, DEFAULT_USER_RULES, SupervisionMode

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection configured for WAL mode and dictionary rows."""
    target_path = db_path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database(db_path: Optional[Path] = None) -> None:
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    -- User Profile Table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'User',
        role TEXT NOT NULL DEFAULT 'Executive',
        preferred_tone TEXT NOT NULL DEFAULT 'Professional, Crisp, and Supervised',
        supervision_mode TEXT NOT NULL DEFAULT 'BALANCED',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- User Rules & Safety Policy Table
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        rule_text TEXT NOT NULL,
        risk_override TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- General Key-Value Preferences Table
    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pref_key TEXT NOT NULL UNIQUE,
        pref_value TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Knowledge Vault Table (Persistent facts, learned trivia, user info)
    CREATE TABLE IF NOT EXISTS knowledge_vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL DEFAULT 'general',
        topic TEXT NOT NULL,
        fact_content TEXT NOT NULL,
        source TEXT DEFAULT 'user_interaction',
        confidence REAL DEFAULT 1.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Projects & Workspace Table
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        metadata_json TEXT DEFAULT '{}',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Conversation History Table
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        intent TEXT,
        decision_state TEXT,
        metadata_json TEXT DEFAULT '{}',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Action Audit Log Table
    CREATE TABLE IF NOT EXISTS action_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id TEXT NOT NULL UNIQUE,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_prompt TEXT NOT NULL,
        detected_intent TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        supervision_reason TEXT,
        user_approval_status TEXT NOT NULL,
        executed_action TEXT NOT NULL,
        action_params TEXT,
        result_status TEXT NOT NULL,
        result_summary TEXT,
        execution_hash TEXT,
        duration_ms REAL
    );

    -- Indexes for high-speed queries
    CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp ON action_logs(timestamp);
    CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
    CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_vault(topic);
    """)

    # Seed default user if not exists
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
            INSERT INTO users (name, role, preferred_tone, supervision_mode)
            VALUES (?, ?, ?, ?)
        """, ("Ayushmaan", "System Executive", "Professional, Objective, Supervised", SupervisionMode.BALANCED.value))

    # Seed default rules if empty
    cursor.execute("SELECT COUNT(*) as count FROM rules")
    if cursor.fetchone()["count"] == 0:
        for r in DEFAULT_USER_RULES:
            cursor.execute("""
                INSERT OR IGNORE INTO rules (name, rule_text, risk_override, is_active)
                VALUES (?, ?, ?, ?)
            """, (r["name"], r["rule"], r["risk_override"].value, 1 if r["is_active"] else 0))

    # Seed basic preferences
    cursor.execute("SELECT COUNT(*) as count FROM preferences")
    if cursor.fetchone()["count"] == 0:
        default_prefs = [
            ("tts_enabled", "true", "voice"),
            ("tts_rate", "180", "voice"),
            ("tts_volume", "1.0", "voice"),
            ("model_provider", "local", "ai"),
            ("theme", "cyber_dark", "ui"),
            ("supervision_strictness", "BALANCED", "supervision")
        ]
        for key, val, cat in default_prefs:
            cursor.execute("""
                INSERT OR IGNORE INTO preferences (pref_key, pref_value, category)
                VALUES (?, ?, ?)
            """, (key, val, cat))

    conn.commit()
    conn.close()
