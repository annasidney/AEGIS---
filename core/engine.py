"""
AEGIS Core Engine
The master orchestrator coordinating Input, NLP, Reasoning, Memory,
Supervision, Action Execution, Output Interface, and Audit Logging.
"""

import time
import uuid
from typing import Dict, Any, List, Optional

from aegis.config import RiskLevel, DecisionState, ActionCategory
from aegis.memory.db import init_database
from aegis.memory.memory_manager import MemoryManager
from aegis.memory.audit_logger import AuditLogger
from aegis.supervision.supervisor import SupervisionLayer, ActionProposal, ApprovalDecision
from aegis.core.nlp import NLPProcessor, ParsedIntent
from aegis.core.reasoning import ReasoningEngine, ReasoningResult
from aegis.core.decision import DecisionEngine
from aegis.actions.action_engine import ActionEngine
from aegis.ai.model_provider import ModelProvider
from aegis.ai.vision_analyzer import VisionAnalyzer
from aegis.speech.tts import TTSEngine

class AegisEngine:
    """The central intelligence and execution coordinator of AEGIS."""

    def __init__(self, db_path=None):
        # 1. Initialize SQLite Database
        init_database(db_path)

        # 2. Subsystem Initializations
        self.memory = MemoryManager(db_path)
        self.audit_logger = AuditLogger(db_path)
        self.supervision = SupervisionLayer(self.memory)
        self.nlp = NLPProcessor()
        self.reasoning = ReasoningEngine(self.memory)
        self.action_engine = ActionEngine(self.supervision)
        self.model_provider = ModelProvider(self.memory)
        self.vision_analyzer = VisionAnalyzer(self.model_provider)
        self.tts = TTSEngine()

    def process_input(self, prompt: str, session_id: str = "default_session",
                      image_data: Optional[str] = None,
                      detected_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executes the full AEGIS pipeline:
        INPUT -> UNDERSTAND -> CONTEXT -> REASON -> SUPERVISE -> DECIDE -> (EXECUTE) -> LOG
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())[:8]

        # ------------------ STAGE 1: VISION PRE-PROCESSING ------------------ #
        vision_result = None
        if image_data or detected_objects:
            vision_result = self.vision_analyzer.analyze_image(
                image_data or "",
                user_question=prompt,
                detected_objects=detected_objects
            )
            if not prompt.strip():
                prompt = "Inspect the visual field and identify objects."

        # ------------------ STAGE 2: INTENT UNDERSTANDING ------------------ #
        intent: ParsedIntent = self.nlp.parse(prompt)

        # ------------------ STAGE 3: CONTEXT & MEMORY RETRIEVAL ------------------ #
        user_profile = self.memory.get_user_profile()
        relevant_memories = self.memory.retrieve_relevant_knowledge(prompt, limit=3)
        history = self.memory.get_conversation_history(session_id, limit=6)

        # Record incoming user turn in conversation memory AFTER retrieving history
        self.memory.record_message(session_id, "user", prompt, intent=intent.action_type)

        # ------------------ STAGE 4: REASONING & TRUTH CHECK ------------------ #
        reasoning_res: ReasoningResult = self.reasoning.reason(intent, relevant_memories)

        # ------------------ STAGE 5: SUPERVISION LAYER EVALUATION ------------------ #
        proposal = ActionProposal(
            action_id=execution_id,
            action_type=intent.action_type,
            category=intent.primary_category.value,
            parameters=intent.parameters,
            user_prompt=prompt,
            rationale=reasoning_res.explanation
        )

        supervision_decision: ApprovalDecision = self.supervision.evaluate_proposal(proposal)

        # ------------------ STAGE 6: DECISION RESOLUTION ------------------ #
        decision_state = DecisionEngine.determine_state(intent, reasoning_res, supervision_decision)

        # Output payload initialization
        output_response = ""
        action_result = None
        approval_status = "NOT_REQUIRED"
        result_status = "SUCCESS"

        # ------------------ STAGE 7: STATE-BASED DISPATCH ------------------ #

        # State A: Refused by Hard Safety
        if decision_state == DecisionState.REFUSE:
            output_response = (
                f"🛑 **Safety Boundary Enforcement**\n\n"
                f"AEGIS refused execution: {supervision_decision.refusal_reason}\n\n"
                f"*Action violates core safety protocols and has been aborted.*"
            )
            approval_status = "REFUSED_BY_SYSTEM"
            result_status = "SAFETY_BLOCKED"

        # State B: Ambiguity / Request Clarification
        elif decision_state == DecisionState.ASK_CLARIFICATION:
            output_response = reasoning_res.proposed_response or "Could you please clarify your request?"
            approval_status = "NOT_REQUIRED"
            result_status = "SUCCESS"

        # State C: Report Uncertainty
        elif decision_state == DecisionState.REPORT_UNCERTAINTY:
            output_response = reasoning_res.proposed_response or "I do not have sufficient information to answer with certainty."
            approval_status = "NOT_REQUIRED"
            result_status = "SUCCESS"

        # State D: Request Permission (Consequential Action Staged)
        elif decision_state == DecisionState.REQUEST_PERMISSION:
            output_response = (
                f"⚠️ **Executive Authorization Required**\n\n"
                f"AEGIS has prepared the proposed action: **`{intent.action_type}`** (Risk: **{supervision_decision.risk_level.value}**).\n\n"
                f"- **Rationale**: {reasoning_res.explanation}\n"
                f"- **Blast Radius**: {supervision_decision.blast_radius.get('impact_summary')}\n\n"
                f"*Please review and authorize via the Supervision Gate below.*"
            )
            approval_status = "AWAITING_USER_APPROVAL"
            result_status = "PENDING_APPROVAL"

        # State E: Direct Execution (Safe or Pre-approved)
        elif decision_state == DecisionState.EXECUTE:
            approval_status = "AUTO_APPROVED"
            action_result = self.action_engine.execute_action(
                action_id=execution_id,
                action_type=intent.action_type,
                risk_level=supervision_decision.risk_level.value,
                params=intent.parameters,
                approval_token=supervision_decision.approval_token
            )
            result_status = "SUCCESS" if action_result.get("success") else "FAILED"

            if action_result.get("visual_type") == "mermaid":
                output_response = f"**Architectural Blueprint Rendered:**\n\n```mermaid\n{action_result['data']['code']}\n```"
            elif action_result.get("visual_type") == "chart":
                output_response = f"**Interactive Visual Chart Generated:** {action_result['message']}"
            elif action_result.get("visual_type") == "web_results":
                output_response = action_result["data"].get("summary") or action_result.get("message")
            elif action_result.get("visual_type") == "system_telemetry":
                m = action_result["data"]["metrics"]
                output_response = (
                    f"### 🖥️ AEGIS System Telemetry\n\n"
                    f"- **OS**: `{m['os']}` | **Uptime**: `{m['uptime_hours']} hrs`\n"
                    f"- **CPU Usage**: `{m['cpu_percent']}%` ({m['cpu_cores']} cores)\n"
                    f"- **RAM Load**: `{m['memory_percent']}%` ({m['memory_used_gb']} GB / {m['memory_total_gb']} GB)\n"
                    f"- **Disk Storage**: `{m['disk_percent']}%` ({m['disk_used_gb']} GB / {m['disk_total_gb']} GB)\n"
                    f"- **Battery**: `{m['battery_percent']}%` ({'Charging' if m['power_plugged'] else 'Battery'})"
                )
            elif action_result.get("visual_type") == "workflow_card":
                output_response = (
                    f"### 📋 Multi-Step Workflow Plan\n\n"
                    f"{action_result['data']['summary']}\n\n"
                    f"**Proposed Output Document**: `{action_result['data']['proposed_file']['filename']}`\n\n"
                    f"```markdown\n{action_result['data']['proposed_file']['content']}\n```"
                )
            else:
                output_response = action_result.get("message", "Action executed successfully.")

        # State F: Standard Conversational Response / Misconception Correction / Knowledge Response
        elif decision_state == DecisionState.RESPOND:
            approval_status = "NOT_REQUIRED"
            result_status = "SUCCESS"
            if reasoning_res.proposed_response:
                output_response = reasoning_res.proposed_response
            elif vision_result:
                if prompt.strip().lower() == "what do you see in the camera view right now?":
                    output_response = "" # Silent update for the UI button
                else:
                    output_response = vision_result["analysis"]
            else:
                output_response = self.model_provider.generate_response(
                    prompt=prompt,
                    conversation_history=history
                )

        duration_ms = (time.time() - start_time) * 1000

        # ------------------ STAGE 8: AUDIT LOGGING ------------------ #
        audit_entry = self.audit_logger.log_action(
            execution_id=execution_id,
            user_prompt=prompt,
            detected_intent=intent.action_type,
            risk_level=supervision_decision.risk_level.value,
            supervision_reason=supervision_decision.reason,
            user_approval_status=approval_status,
            executed_action=intent.action_type if decision_state == DecisionState.EXECUTE else "NONE",
            action_params=intent.parameters,
            result_status=result_status,
            result_summary=output_response[:120],
            duration_ms=duration_ms
        )

        # Record assistant reply in memory if it exists
        if output_response:
            self.memory.record_message(
                session_id, "assistant", output_response,
                intent=intent.action_type, decision_state=decision_state.value
            )

        # Assemble full pipeline response bundle
        return {
            "execution_id": execution_id,
            "session_id": session_id,
            "decision_state": decision_state.value,
            "user_prompt": prompt,
            "intent": {
                "category": intent.primary_category.value,
                "action_type": intent.action_type,
                "confidence": intent.confidence,
                "parameters": intent.parameters,
                "has_misconception": intent.has_misconception
            },
            "reasoning": {
                "explanation": reasoning_res.explanation,
                "confidence": reasoning_res.confidence,
                "is_uncertain": reasoning_res.is_uncertain,
                "sub_steps": reasoning_res.sub_steps
            },
            "supervision": {
                "risk_level": supervision_decision.risk_level.value,
                "requires_approval": supervision_decision.requires_approval,
                "reason": supervision_decision.reason,
                "blast_radius": supervision_decision.blast_radius,
                "triggered_rules": supervision_decision.triggered_rules,
                "is_safe": supervision_decision.is_safe,
                "is_reversible": supervision_decision.is_reversible
            },
            "action_result": action_result,
            "vision_result": vision_result,
            "output_text": output_response,
            "audit_hash": audit_entry.get("execution_hash"),
            "duration_ms": round(duration_ms, 2)
        }

    def handle_user_approval(self, action_id: str, approved: bool,
                             session_id: str = "default_session") -> Dict[str, Any]:
        """
        Executes or aborts a staged action upon explicit human decision.
        """
        start_time = time.time()
        pending = self.supervision.get_pending_proposal(action_id)

        if not pending:
            return {
                "success": False,
                "message": f"No pending action found with ID '{action_id}' (may have already been resolved or expired)."
            }

        proposal, initial_decision = pending
        resolved_decision = self.supervision.resolve_user_approval(action_id, approved)

        if not approved:
            # Action cancelled by user
            output_msg = f"❌ **Action Cancelled by User**\n\nThe proposed action `{proposal.action_type}` was declined. No changes were made to system or workspace."

            self.audit_logger.log_action(
                execution_id=action_id,
                user_prompt=proposal.user_prompt,
                detected_intent=proposal.action_type,
                risk_level=initial_decision.risk_level.value,
                supervision_reason="User clicked REJECT.",
                user_approval_status="REJECTED_BY_USER",
                executed_action="CANCELLED",
                action_params=proposal.parameters,
                result_status="CANCELLED",
                result_summary="Cancelled by user.",
                duration_ms=(time.time() - start_time) * 1000
            )

            self.memory.record_message(session_id, "assistant", output_msg, intent=proposal.action_type, decision_state="CANCELLED")

            return {
                "success": True,
                "approved": False,
                "message": output_msg,
                "action_id": action_id
            }

        # Action explicitly authorized by user
        action_result = self.action_engine.execute_action(
            action_id=action_id,
            action_type=proposal.action_type,
            risk_level=resolved_decision.risk_level.value,
            params=proposal.parameters,
            approval_token=resolved_decision.approval_token
        )

        result_status = "SUCCESS" if action_result.get("success") else "FAILED"
        output_msg = f"✅ **Authorized Action Executed**\n\n{action_result.get('message', 'Completed successfully.')}"

        self.audit_logger.log_action(
            execution_id=action_id,
            user_prompt=proposal.user_prompt,
            detected_intent=proposal.action_type,
            risk_level=resolved_decision.risk_level.value,
            supervision_reason="Explicit user authorization granted via Supervision Gate.",
            user_approval_status="APPROVED_BY_USER",
            executed_action=proposal.action_type,
            action_params=proposal.parameters,
            result_status=result_status,
            result_summary=action_result.get("message", "")[:120],
            duration_ms=(time.time() - start_time) * 1000
        )

        self.memory.record_message(session_id, "assistant", output_msg, intent=proposal.action_type, decision_state="EXECUTED")

        return {
            "success": action_result.get("success", False),
            "approved": True,
            "message": output_msg,
            "action_id": action_id,
            "action_result": action_result
        }
