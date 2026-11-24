"""
AEGIS Supervision Layer
The central safety, policy, and human-in-the-loop permission gateway.
Evaluates risk levels, enforces user rules, computes blast radius, and issues signed approval tokens.
"""

import uuid
import hmac
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from aegis.config import RiskLevel, SupervisionMode, SECRET_KEY
from aegis.supervision.safety_checker import SafetyChecker
from aegis.supervision.rules import RuleEngine
from aegis.memory.memory_manager import MemoryManager


@dataclass
class ActionProposal:
    """Represents a candidate action proposed by the AEGIS Core Engine."""
    action_id: str
    action_type: str
    category: str
    parameters: Dict[str, Any]
    user_prompt: str
    rationale: str
    suggested_risk: Optional[RiskLevel] = None


@dataclass
class ApprovalDecision:
    """Result of the Supervision Layer evaluation."""
    action_id: str
    requires_approval: bool
    risk_level: RiskLevel
    reason: str
    blast_radius: Dict[str, Any]
    triggered_rules: List[str] = field(default_factory=list)
    is_safe: bool = True
    refusal_reason: Optional[str] = None
    approval_token: Optional[str] = None
    is_reversible: bool = True


class SupervisionLayer:
    """Supervision and Permission Engine ensuring human authority over consequential tasks."""

    # Inherent risk mapping by action type
    INHERENT_RISKS: Dict[str, RiskLevel] = {
        # Safe / Informational
        "system_info": RiskLevel.SAFE,
        "blueprint_gen": RiskLevel.SAFE,
        "chart_gen": RiskLevel.SAFE,
        "web_search": RiskLevel.SAFE,
        "knowledge_read": RiskLevel.SAFE,
        "file_read": RiskLevel.SAFE,
        "file_list": RiskLevel.SAFE,
        "conversation": RiskLevel.SAFE,
        "reasoning": RiskLevel.SAFE,
        "time_query": RiskLevel.SAFE,
        "joke": RiskLevel.SAFE,
        "media_pause": RiskLevel.SAFE,
        "media_resume": RiskLevel.SAFE,
        "media_stop": RiskLevel.SAFE,
        "media_mute": RiskLevel.SAFE,
        "media_vol_up": RiskLevel.SAFE,
        "media_vol_down": RiskLevel.SAFE,

        # Low Risk (Benign App/Web Launches)
        "play_youtube": RiskLevel.LOW,
        "youtube_search": RiskLevel.LOW,
        "google_search": RiskLevel.LOW,
        "open_website": RiskLevel.LOW,
        "app_launch_notepad": RiskLevel.LOW,
        "app_launch_calculator": RiskLevel.LOW,
        "app_launch_explorer": RiskLevel.LOW,
        "app_launch_vscode": RiskLevel.LOW,
        "app_launch_browser": RiskLevel.LOW,
        "open_url": RiskLevel.LOW,

        # Medium Risk
        "file_create": RiskLevel.MEDIUM,
        "file_organize": RiskLevel.MEDIUM,
        "project_create": RiskLevel.MEDIUM,
        "workflow_plan": RiskLevel.MEDIUM,

        # High Risk
        "file_edit": RiskLevel.HIGH,
        "file_overwrite": RiskLevel.HIGH,
        "run_script": RiskLevel.HIGH,
        "app_launch_terminal": RiskLevel.HIGH,
        "batch_file_operation": RiskLevel.HIGH,

        # Critical Risk
        "file_delete": RiskLevel.CRITICAL,
        "folder_delete": RiskLevel.CRITICAL,
        "system_shutdown": RiskLevel.CRITICAL,
        "process_kill": RiskLevel.CRITICAL,
        "clear_memory": RiskLevel.CRITICAL,

        # --- V2 NEW FEATURES ---
        "set_reminder": RiskLevel.SAFE,
        "remember_fact": RiskLevel.SAFE,
        "lan_scan": RiskLevel.SAFE,
        "email_list": RiskLevel.SAFE,
        "email_read": RiskLevel.SAFE,
        "email_search": RiskLevel.SAFE,
        "macro_list": RiskLevel.SAFE,
        "visual_find": RiskLevel.SAFE,
        "visual_highlight": RiskLevel.SAFE,

        "lock_screen": RiskLevel.LOW,
        "sleep_pc": RiskLevel.LOW,
        "wake_on_lan": RiskLevel.LOW,
        "web_archive": RiskLevel.LOW,
        "macro_record": RiskLevel.LOW,
        "macro_stop": RiskLevel.LOW,

        "visual_click": RiskLevel.MEDIUM,
        "macro_play": RiskLevel.MEDIUM,
    }

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory = memory_manager
        self.safety_checker = SafetyChecker()
        self.rule_engine = RuleEngine(memory_manager)
        self._pending_approvals: Dict[str, Tuple[ActionProposal, ApprovalDecision]] = {}

    def generate_token(self, action_id: str, action_type: str, risk_level: str) -> str:
        """Generates a cryptographic signature verifying the action was authorized by the supervisor."""
        payload = f"{action_id}:{action_type}:{risk_level}:{int(time.time() // 3600)}"
        return hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_token(self, action_id: str, action_type: str, risk_level: str, token: str) -> bool:
        """Verifies if an approval token is authentic and valid."""
        expected = self.generate_token(action_id, action_type, risk_level)
        return hmac.compare_digest(expected, token)

    def analyze_blast_radius(self, action_type: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Calculates the blast radius / impact scope of the proposed action.
        Returns: (blast_radius_dict, is_reversible)
        """
        blast = {
            "target": params.get("path") or params.get("target") or params.get("app_id") or params.get("query") or "System",
            "scope": "Local Sandbox" if "workspace" in str(params.get("path", "")) else "System/External",
            "affects_existing_data": False,
            "impact_summary": "Informational / Non-destructive operation."
        }
        reversible = True

        if action_type in ["file_delete", "folder_delete"]:
            blast["affects_existing_data"] = True
            blast["impact_summary"] = f"Permanent deletion of target '{blast['target']}'. Data cannot be restored automatically."
            reversible = False

        elif action_type in ["file_overwrite", "file_edit"]:
            blast["affects_existing_data"] = True
            blast["impact_summary"] = f"Modifies existing content in '{blast['target']}'. Overwrites current version."
            reversible = True

        elif action_type == "file_create":
            blast["impact_summary"] = f"Creates a new file at '{blast['target']}' ({len(params.get('content', ''))} characters)."
            reversible = True

        elif action_type in ["run_script", "app_launch_terminal"]:
            blast["scope"] = "Operating System Process"
            blast["affects_existing_data"] = True
            blast["impact_summary"] = "Executes command/script directly on system environment."
            reversible = False

        elif action_type == "open_url":
            blast["scope"] = "External Network"
            blast["impact_summary"] = f"Opens external browser navigation to {params.get('url')}."
            reversible = True

        return blast, reversible

    def evaluate_proposal(self, proposal: ActionProposal) -> ApprovalDecision:
        """
        Core Supervision Algorithm:
        1. Hard Safety Check
        2. Inherent Risk Level Assignment
        3. User Policy & Custom Rule Evaluation
        4. Blast Radius Assessment
        5. Supervision Mode Threshold Check -> Needs Approval vs Auto-Approved
        """
        # 1. Hard Safety Check
        is_unsafe, unsafe_reason = self.safety_checker.is_inherently_dangerous(
            proposal.user_prompt + " " + str(proposal.parameters)
        )
        if is_unsafe:
            return ApprovalDecision(
                action_id=proposal.action_id,
                requires_approval=False,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Action blocked by hard safety bounds: {unsafe_reason}",
                blast_radius={"scope": "System Blocked", "impact_summary": "Unsafe command rejected."},
                is_safe=False,
                refusal_reason=unsafe_reason
            )

        # 2. Determine base risk level
        action_key = proposal.action_type.lower()
        base_risk = self.INHERENT_RISKS.get(action_key, proposal.suggested_risk or RiskLevel.MEDIUM)

        # Special risk modifiers
        if "delete" in action_key or "remove" in action_key:
            base_risk = RiskLevel.CRITICAL
        elif action_key == "file_create" and proposal.parameters.get("overwrite", False):
            base_risk = RiskLevel.HIGH

        # 3. Dynamic User Rule Evaluation
        rule_override, triggered_rules = self.rule_engine.evaluate_rules(
            proposal.action_type, proposal.parameters, proposal.user_prompt
        )

        risk_order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        final_risk = base_risk
        if rule_override and risk_order.index(rule_override) > risk_order.index(base_risk):
            final_risk = rule_override

        # 4. Compute Blast Radius
        blast_radius, is_reversible = self.analyze_blast_radius(proposal.action_type, proposal.parameters)

        # 5. Check User's Active Supervision Mode
        supervision_mode = SupervisionMode.BALANCED
        if self.memory:
            profile = self.memory.get_user_profile()
            mode_str = profile.get("supervision_mode", "BALANCED")
            if mode_str in [m.value for m in SupervisionMode]:
                supervision_mode = SupervisionMode(mode_str)

        # Determine if human approval is mandatory
        requires_approval = False
        if supervision_mode == SupervisionMode.ZERO_TRUST:
            # Requires approval for anything above SAFE
            requires_approval = final_risk != RiskLevel.SAFE
        elif supervision_mode == SupervisionMode.BALANCED:
            # Default SIH mode: requires approval for MEDIUM, HIGH, CRITICAL
            requires_approval = final_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        elif supervision_mode == SupervisionMode.AUTONOMOUS:
            # Autonomous mode: only HIGH and CRITICAL require approval
            requires_approval = final_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        reason_text = (
            f"Supervision Layer classified action as [{final_risk.value}] risk. "
            f"{'Explicit user authorization required.' if requires_approval else 'Auto-approved under current policy.'}"
        )
        if triggered_rules:
            reason_text += f" Triggered user rules: {', '.join(triggered_rules)}."

        token = self.generate_token(proposal.action_id, proposal.action_type, final_risk.value)

        decision = ApprovalDecision(
            action_id=proposal.action_id,
            requires_approval=requires_approval,
            risk_level=final_risk,
            reason=reason_text,
            blast_radius=blast_radius,
            triggered_rules=triggered_rules,
            is_safe=True,
            approval_token=token if not requires_approval else None,
            is_reversible=is_reversible
        )

        # If approval is needed, stage in pending queue
        if requires_approval:
            self._pending_approvals[proposal.action_id] = (proposal, decision)

        return decision

    def get_pending_proposal(self, action_id: str) -> Optional[Tuple[ActionProposal, ApprovalDecision]]:
        """Retrieves an action awaiting user authorization."""
        return self._pending_approvals.get(action_id)

    def resolve_user_approval(self, action_id: str, approved: bool) -> Optional[ApprovalDecision]:
        """
        Processes human approval or rejection of a staged action proposal.
        """
        if action_id not in self._pending_approvals:
            return None

        proposal, decision = self._pending_approvals.pop(action_id)

        if approved:
            decision.approval_token = self.generate_token(proposal.action_id, proposal.action_type, decision.risk_level.value)
            decision.reason = f"User EXPLICITLY APPROVED [{decision.risk_level.value}] action."
        else:
            decision.approval_token = None
            decision.reason = f"User REJECTED proposed action."

        return decision
