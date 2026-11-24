"""
AEGIS Rule Engine
Evaluates active user-configured safety policies, overrides, and constraints against proposed actions.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from aegis.config import RiskLevel

class RuleEngine:
    """Evaluates rules stored in memory against incoming requests and action parameters."""

    def __init__(self, memory_manager=None):
        self.memory = memory_manager

    def evaluate_rules(self, action_type: str, action_params: Dict[str, Any], prompt: str) -> Tuple[Optional[RiskLevel], List[str]]:
        """
        Evaluates active rules against the proposed action and prompt.
        Returns: (highest_risk_override, list_of_triggered_rule_names)
        """
        if not self.memory:
            return None, []

        active_rules = self.memory.get_rules(active_only=True)
        triggered_rules = []
        highest_risk = None

        risk_order = {
            RiskLevel.SAFE.value: 0,
            RiskLevel.LOW.value: 1,
            RiskLevel.MEDIUM.value: 2,
            RiskLevel.HIGH.value: 3,
            RiskLevel.CRITICAL.value: 4
        }

        lower_prompt = prompt.lower()
        action_clean = action_type.lower()

        for rule in active_rules:
            rule_text = rule["rule_text"].lower()
            name = rule["name"]
            override_str = rule.get("risk_override") or RiskLevel.HIGH.value

            matched = False

            # Rule match: Deletions
            if "delet" in rule_text or "remove" in rule_text:
                if action_clean in ["file_delete", "folder_delete"] or any(k in lower_prompt for k in ["delete", "remove", "erase", "wipe", "clean up"]):
                    matched = True

            # Rule match: Overwriting / Modifying
            elif "overwrite" in rule_text or "modify" in rule_text:
                if action_clean in ["file_write", "file_edit"] and action_params.get("overwrite", False):
                    matched = True

            # Rule match: Scripts / Terminal execution
            elif "script" in rule_text or "terminal" in rule_text or "command" in rule_text:
                if action_clean in ["run_script", "terminal_command"] or action_params.get("app_id") in ["terminal", "powershell", "cmd"]:
                    matched = True

            # Rule match: External web browsing / navigation
            elif "external" in rule_text or "url" in rule_text:
                if action_clean in ["open_url", "web_navigate"]:
                    matched = True

            if matched:
                triggered_rules.append(name)
                override_level = RiskLevel(override_str) if override_str in risk_order else RiskLevel.HIGH
                if highest_risk is None or risk_order[override_level.value] > risk_order[highest_risk.value]:
                    highest_risk = override_level

        return highest_risk, triggered_rules
