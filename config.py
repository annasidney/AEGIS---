"""
AEGIS Configuration and Constants
Defines risk levels, decision states, supervision modes, paths, and system policies.
"""

import os
from pathlib import Path
from enum import Enum
from typing import Dict, Any, List

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORKSPACE_DIR = DATA_DIR / "workspace"
DB_PATH = DATA_DIR / "aegis_memory.db"
LOGS_PATH = DATA_DIR / "action_logs.json"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


class RiskLevel(str, Enum):
    """Risk tiers for system operations evaluated by the Supervision Layer."""
    SAFE = "SAFE"           # Informational, reading public data, pure reasoning, rendering diagrams
    LOW = "LOW"             # Launching safe local apps (calculator, notepad), web searches
    MEDIUM = "MEDIUM"       # Creating new files, navigating to external URLs, workspace non-destructive ops
    HIGH = "HIGH"           # Modifying existing files, executing scripts, batch operations
    CRITICAL = "CRITICAL"   # Deleting files, system config modification, process termination, shell execution


class SupervisionMode(str, Enum):
    """Operating philosophy modes for the Supervision Layer."""
    ZERO_TRUST = "ZERO_TRUST"       # Strict: Requires explicit user approval for any action >= LOW
    BALANCED = "BALANCED"           # Standard SIH Mode: Auto-approves SAFE & LOW, requires approval for MEDIUM+
    AUTONOMOUS = "AUTONOMOUS"       # Permissive: Auto-approves SAFE, LOW, MEDIUM; requires approval for HIGH+


class DecisionState(str, Enum):
    """States returned by the Decision Engine."""
    RESPOND = "RESPOND"                         # Safe to respond directly to user with text/visuals
    ASK_CLARIFICATION = "ASK_CLARIFICATION"     # Ambiguous or underspecified prompt
    REPORT_UNCERTAINTY = "REPORT_UNCERTAINTY"   # Insufficient knowledge / facts uncertain
    REQUEST_PERMISSION = "REQUEST_PERMISSION"   # Action proposed, awaiting user verification
    EXECUTE = "EXECUTE"                         # Action pre-approved or authorized
    REFUSE = "REFUSE"                           # Action violates hard safety boundaries or ethics


class ActionCategory(str, Enum):
    """Functional action domains supported by the Action Engine."""
    CONVERSATION = "CONVERSATION"
    REASONING = "REASONING"
    APP_LAUNCH = "APP_LAUNCH"
    FILE_OPERATION = "FILE_OPERATION"
    WEB_SEARCH = "WEB_SEARCH"
    SYSTEM_OPERATION = "SYSTEM_OPERATION"
    BLUEPRINT_GENERATION = "BLUEPRINT_GENERATION"
    WORKFLOW_AGENT = "WORKFLOW_AGENT"
    VISION_ANALYSIS = "VISION_ANALYSIS"


# Default App Registry for safe desktop launches
ALLOWED_APPLICATIONS: Dict[str, Dict[str, Any]] = {
    "notepad": {
        "name": "Notepad",
        "command": "notepad.exe",
        "risk": RiskLevel.LOW,
        "description": "Windows text editor"
    },
    "calculator": {
        "name": "Calculator",
        "command": "calc.exe",
        "risk": RiskLevel.LOW,
        "description": "Windows Calculator"
    },
    "explorer": {
        "name": "File Explorer",
        "command": "explorer.exe",
        "risk": RiskLevel.LOW,
        "description": "Windows File Explorer"
    },
    "terminal": {
        "name": "Windows Terminal / PowerShell",
        "command": "powershell.exe",
        "risk": RiskLevel.MEDIUM,
        "description": "Windows PowerShell Command Console"
    },
    "vscode": {
        "name": "Visual Studio Code",
        "command": "code",
        "risk": RiskLevel.LOW,
        "description": "Source code editor"
    },
    "browser": {
        "name": "Web Browser",
        "command": "start",
        "risk": RiskLevel.LOW,
        "description": "Default Internet Browser"
    }
}

# Core AEGIS Identity & Philosophy
SYSTEM_PHILOSOPHY = """AEGIS (Assisted Executive Guidance and Intelligence System)
PHILOSOPHY: 'AI assists, AI reasons, AI recommends, the user decides.'
CORE PRINCIPLES:
1. USER FIRST - User is the ultimate authority.
2. SUPERVISED INTELLIGENCE - Consequential actions require user supervision.
3. USER APPROVAL - Consequential actions must obtain explicit user authorization.
4. SAFETY - Never execute destructive or harmful commands without verification.
5. CORRECTION OVER BLIND AGREEMENT - Respectfully correct user misconceptions.
6. UNCERTAINTY - Admit lack of knowledge openly without hallucinating.
7. CLARIFICATION - Ask clarifying questions when requests are ambiguous.
8. EXPLAINABILITY - Provide transparent rationale and blast radius for proposed actions.
9. AUDITABILITY - Log every step from input through reasoning and execution.
"""

DEFAULT_USER_RULES = [
    {
        "name": "File Deletion Guard",
        "rule": "Always require explicit confirmation before deleting any file or folder.",
        "risk_override": RiskLevel.CRITICAL,
        "is_active": True
    },
    {
        "name": "File Overwrite Guard",
        "rule": "Prompt for confirmation before overwriting or modifying existing project documents.",
        "risk_override": RiskLevel.HIGH,
        "is_active": True
    },
    {
        "name": "Script Execution Guard",
        "rule": "Never run automated scripts or terminal commands without displaying code and receiving approval.",
        "risk_override": RiskLevel.HIGH,
        "is_active": True
    },
    {
        "name": "Sandbox Boundary Guard",
        "rule": "Keep automatic file creations sandboxed inside the AEGIS workspace directory.",
        "risk_override": RiskLevel.MEDIUM,
        "is_active": True
    }
]

# Web Server Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SECRET_KEY = os.environ.get("AEGIS_SECRET_KEY", "aegis_secure_executive_supervision_key_2026")
