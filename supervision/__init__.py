"""
AEGIS Supervision Layer Module
The primary differentiator of AEGIS. Guarantees safety, evaluates policies,
and enforces human-in-the-loop authorization for consequential operations.
"""

from aegis.supervision.safety_checker import SafetyChecker
from aegis.supervision.rules import RuleEngine
from aegis.supervision.supervisor import SupervisionLayer, ActionProposal, ApprovalDecision

__all__ = ["SafetyChecker", "RuleEngine", "SupervisionLayer", "ActionProposal", "ApprovalDecision"]
