"""
AEGIS Decision Engine
Resolves the pipeline state given Intent, Reasoning, and Supervision outputs.
Ensures that no action bypasses the Supervision Layer.
"""

from typing import Dict, Any, Optional
from aegis.config import DecisionState, RiskLevel
from aegis.core.nlp import ParsedIntent
from aegis.core.reasoning import ReasoningResult
from aegis.supervision.supervisor import ApprovalDecision

class DecisionEngine:
    """Computes the final system state and coordinates interaction flow."""

    @staticmethod
    def determine_state(intent: ParsedIntent, reasoning: ReasoningResult, supervision: Optional[ApprovalDecision]) -> DecisionState:
        """
        Determines the appropriate DecisionState based on the combined pipeline signals.
        """
        # 1. Hard safety refusal
        if supervision and not supervision.is_safe:
            return DecisionState.REFUSE

        # 2. Ambiguity -> Clarification
        if intent.is_ambiguous:
            return DecisionState.ASK_CLARIFICATION

        # 3. Uncertainty -> Report uncertainty
        if reasoning.is_uncertain and reasoning.confidence < 0.30:
            return DecisionState.REPORT_UNCERTAINTY

        # 4. Misconception correction or pure conversation -> Direct Response
        if intent.has_misconception or intent.action_type in ["conversation", "math_reasoning"]:
            return DecisionState.RESPOND

        # 5. Consequential action requiring user authorization -> Request Permission
        if supervision and supervision.requires_approval:
            return DecisionState.REQUEST_PERMISSION

        # 6. Action safe / pre-approved -> Execute
        if supervision and not supervision.requires_approval:
            return DecisionState.EXECUTE

        # Fallback to direct response
        return DecisionState.RESPOND
