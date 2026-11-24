"""
AEGIS Memory Module
Provides persistent SQLite storage, user knowledge vault, custom rules, and audit logging.
"""

from aegis.memory.db import init_database, get_db_connection
from aegis.memory.memory_manager import MemoryManager
from aegis.memory.audit_logger import AuditLogger

__all__ = ["init_database", "get_db_connection", "MemoryManager", "AuditLogger"]
