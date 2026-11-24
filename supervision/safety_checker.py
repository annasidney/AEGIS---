"""
AEGIS Safety Checker
Implements hard safety boundaries, malicious pattern blocking, and command sanitization.
Ensures AEGIS never executes inherently dangerous, malware-like, or destructive actions.
"""

import re
from typing import Tuple, Optional

# Patterns that are fundamentally unsafe and must be REFUSED immediately
DANGEROUS_PATTERNS = [
    # Recursive root/system deletion
    r"rm\s+-(?:rf|fr)\s+[\/\*]",
    r"rmdir\s+(?:[\/\-][sqa]\s*)*[a-zA-Z]:[\\\/]?",
    r"del\s+(?:[\/\-][fsqa]\s*)*[a-zA-Z]:[\\\/]?",
    r"format\s+[a-zA-Z]:",
    # Shell code injection / remote execution pipelines
    r"curl.*\|\s*(bash|sh|powershell|iex)",
    r"wget.*\|\s*(bash|sh|powershell|iex)",
    r"iex\s*\(\s*new-object\s+net\.webclient\s*\)",
    r"invoke-expression.*downloadstring",
    # Fork bomb & OS crashing
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    r"shutdown\s+[\/\-][srf]\s+[\/\-]?t\s+0",
    # Registry destruction
    r"reg\s+delete\s+(hklm|hkcu|hkey_local_machine)",
    # Credential dumping & sensitive paths
    r"(\.ssh[\\\/]id_rsa|\.aws[\\\/]credentials|\/etc\/shadow|sam\.save|system\.save)",
    # System folder modifications
    r"(c:[\\\/]windows[\\\/]system32[\\\/]|c:[\\\/]boot)"
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class SafetyChecker:
    """Evaluates proposed actions against strict safety constraints."""

    @staticmethod
    def is_inherently_dangerous(command_or_text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans a text or command string for dangerous system-level threats.
        Returns: (is_dangerous, reason_description)
        """
        if not command_or_text:
            return False, None

        normalized = command_or_text.strip()

        for pattern in COMPILED_PATTERNS:
            if pattern.search(normalized):
                return True, f"Blocked dangerous system pattern detected: '{pattern.pattern}'"

        # Check for direct recursive root/system deletion variants
        lower = normalized.lower()
        if "rmdir" in lower and ("/s" in lower or "-s" in lower) and ("c:" in lower or "c:\\" in lower):
            return True, "Blocked recursive system drive deletion attempt."

        if "del" in lower and ("/s" in lower or "/f" in lower) and ("c:" in lower or "c:\\" in lower):
            return True, "Blocked recursive system drive deletion attempt."

        # Check for path traversal trying to escape out of workspace
        if "../../../" in normalized or "..\\..\\..\\" in normalized:
            if "workspace" not in normalized.lower():
                return True, "Potential directory traversal attack out of sandbox."

        return False, None

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes user-provided filename to prevent path injection."""
        clean = re.sub(r'[<>:"/\\|?*]', '_', filename)
        clean = clean.replace("..", "_")
        return clean.strip(" .")
