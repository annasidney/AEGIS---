"""
AEGIS Reasoning Engine
Handles logical deduction, mathematical problem solving, truth evaluation,
uncertainty calibration, and multi-step task decomposition.
"""

import re
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from aegis.core.nlp import ParsedIntent

@dataclass
class ReasoningResult:
    """Represents the outcome of the logical reasoning process."""
    explanation: str
    confidence: float
    is_uncertain: bool = False
    uncertainty_note: Optional[str] = None
    sub_steps: List[Dict[str, Any]] = field(default_factory=list)
    proposed_response: Optional[str] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)


class ReasoningEngine:
    """Logical analysis, mathematical evaluation, and goal planner."""

    def __init__(self, memory_manager=None):
        self.memory = memory_manager

    def reason(self, intent: ParsedIntent, context_facts: Optional[List[Dict[str, Any]]] = None) -> ReasoningResult:
        """
        Executes reasoning over the intent and contextual memories.
        """
        # 1. Handle Misconception Correction
        if intent.has_misconception:
            return ReasoningResult(
                explanation="Detected factual misconception in premise. Generating respectful correction.",
                confidence=0.98,
                is_uncertain=False,
                proposed_response=f"Respectfully correcting the premise: {intent.misconception_correction}"
            )

        # 2. Handle Ambiguity
        if intent.is_ambiguous:
            return ReasoningResult(
                explanation="Request is underspecified or ambiguous. Requesting user clarification.",
                confidence=0.40,
                is_uncertain=False,
                proposed_response=intent.clarification_question or "Could you clarify your request?"
            )

        # 3. Handle Explicit Uncertainty / Unknowable queries
        if intent.requires_uncertainty_report:
            return ReasoningResult(
                explanation="Admitting uncertainty: Information is speculative, unknowable, or private.",
                confidence=0.15,
                is_uncertain=True,
                uncertainty_note="AEGIS cannot predict unknowable future events or access undisclosed private information.",
                proposed_response="I must be honest and admit uncertainty: I do not possess verified data to answer this conclusively, as this involves future speculation or undisclosed details."
            )

        # 4. Handle Math / Computational Reasoning
        if intent.action_type == "math_reasoning":
            return self._solve_math(intent.raw_prompt)

        # 5. Handle Multi-step Workflow Decomposition
        if intent.primary_category.value == "WORKFLOW_AGENT":
            return self._decompose_workflow(intent.raw_prompt)

        # 6. Standard Reasoning & Context Synthesis
        context_summary = ""
        if context_facts:
            context_summary = " Using remembered context: " + ", ".join([f["fact_content"] for f in context_facts[:2]])

        return ReasoningResult(
            explanation=f"Analyzed intent '{intent.action_type}'.{context_summary}",
            confidence=intent.confidence,
            is_uncertain=False
        )

    def _solve_math(self, prompt: str) -> ReasoningResult:
        """Safely evaluates basic to advanced mathematical expressions."""
        # Strip command prefixes
        expr = re.sub(r'^(calculate|compute|solve|what is the value of|what is|math)\s*', '', prompt, flags=re.IGNORECASE).strip()
        expr = expr.rstrip("?= ").strip()

        clean = expr.replace("^", "**").replace("pi", str(math.pi)).replace("e", str(math.e))

        try:
            # Safe evaluation environment with limited built-ins
            allowed_names = {
                "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
                "tan": math.tan, "log": math.log10, "ln": math.log,
                "pi": math.pi, "e": math.e, "pow": math.pow, "abs": abs
            }
            # Remove any dangerous characters
            eval_str = re.sub(r'[^0-9\+\-\*\/\.\(\)\s\_a-z]', '', clean)
            if not eval_str.strip():
                raise ValueError("Empty mathematical expression")

            result = eval(eval_str, {"__builtins__": {}}, allowed_names)
            return ReasoningResult(
                explanation=f"Evaluated mathematical expression: {prompt}",
                confidence=1.0,
                is_uncertain=False,
                proposed_response=f"Calculation Result:\n$$\n{expr} = {result}\n$$",
                structured_data={"expression": expr, "result": result}
            )
        except Exception as e:
            return ReasoningResult(
                explanation=f"Mathematical calculation failed: {e}",
                confidence=0.5,
                is_uncertain=True,
                uncertainty_note="Could not parse expression unambiguously."
            )

    def _decompose_workflow(self, goal: str) -> ReasoningResult:
        """Decomposes a complex objective into sequential sub-tasks."""
        steps = []
        lower = goal.lower()

        if "python" in lower and ("resource" in lower or "learn" in lower):
            steps = [
                {
                    "step_number": 1,
                    "name": "Search Python Learning Resources",
                    "action_type": "web_search",
                    "params": {"query": "Top best Python learning documentation tutorial 2026"},
                    "risk": "SAFE"
                },
                {
                    "step_number": 2,
                    "name": "Synthesize & Curate Guide",
                    "action_type": "reasoning",
                    "params": {"topic": "Python Curriculum"},
                    "risk": "SAFE"
                },
                {
                    "step_number": 3,
                    "name": "Save Curated Guide to Workspace File",
                    "action_type": "file_create",
                    "params": {"filename": "python_learning_guide.md", "content": "# Curated Python Learning Path\n\n1. Official Docs\n2. RealPython\n3. Automate the Boring Stuff"},
                    "risk": "MEDIUM"
                }
            ]
        else:
            steps = [
                {
                    "step_number": 1,
                    "name": "Information Retrieval & Analysis",
                    "action_type": "web_search",
                    "params": {"query": goal},
                    "risk": "SAFE"
                },
                {
                    "step_number": 2,
                    "name": "Workspace File Organization",
                    "action_type": "file_create",
                    "params": {"filename": "task_summary.md", "content": f"# Summary for: {goal}"},
                    "risk": "MEDIUM"
                }
            ]

        return ReasoningResult(
            explanation=f"Decomposed goal '{goal}' into {len(steps)} sequential execution steps.",
            confidence=0.92,
            sub_steps=steps,
            proposed_response=f"I have analyzed your objective and prepared a structured multi-step execution plan with {len(steps)} phases. Each consequential phase will pass through supervision."
        )
