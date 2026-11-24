"""
AEGIS Blueprint & Visual Data Generator
Produces structured Mermaid.js diagrams, interactive Chart.js datasets,
and algorithmic blueprints for the Multimodal Visual Canvas.
"""

from typing import Dict, Any

class BlueprintGenerator:
    """Generates visual architecture blueprints, workflow diagrams, and charts."""

    @staticmethod
    def generate_mermaid_blueprint(topic: str) -> Dict[str, Any]:
        """Creates a Mermaid.js diagram definition based on the requested topic."""
        lower = topic.lower()

        # AEGIS Architecture Blueprint
        if any(w in lower for w in ["aegis", "system", "architecture", "overview"]):
            code = """flowchart TD
    User["👤 USER (Voice / Text / Camera)"] --> InputLayer["📥 INPUT LAYER (STT, Parser, Vision)"]
    InputLayer --> CoreEngine["🧠 AEGIS CORE ENGINE<br/>• Intent Understanding<br/>• Reasoning & Truth Check"]

    CoreEngine <--> Memory["💾 MEMORY SYSTEM<br/>• Profiles & Vault<br/>• Custom User Rules"]
    CoreEngine <--> AI["🌐 AI & KNOWLEDGE<br/>• Multi-LLM<br/>• Live Search"]

    CoreEngine --> Supervision["🛡️ SUPERVISION LAYER (Core Differentiator)<br/>• Risk Rating (SAFE ➜ CRITICAL)<br/>• Policy & Rule Verification<br/>• Blast Radius Calculation"]

    Supervision --> RiskDecision{"Supervision Gate"}
    RiskDecision -- "SAFE / Low Risk" --> ActionEngine["⚙️ ACTION ENGINE"]
    RiskDecision -- "Consequential<br/>(Medium / High / Critical)" --> ApprovalGate["⚠️ USER APPROVAL MODAL"]

    ApprovalGate -- "✅ Approved" --> ActionEngine
    ApprovalGate -- "❌ Rejected" --> AbortLog["🛑 ABORT & AUDIT LOG"]

    ActionEngine --> Tools["🧰 TOOLS & SANDBOX<br/>• Apps & Browser<br/>• Workspace Files<br/>• Blueprints & Charts"]
    Tools --> Output["🖥️ EXECUTIVE DASHBOARD & TTS"]
    Output --> AuditLog["📜 PERMANENT AUDIT TRAIL"]
"""
            title = "AEGIS Core System Architecture Blueprint"

        # Supervision Flow Blueprint
        elif any(w in lower for w in ["supervision", "safety", "approval", "permission", "rule"]):
            code = """sequenceDiagram
    autonumber
    actor User as 👤 User
    participant NLP as 📥 Intent Parser
    participant Sup as 🛡️ Supervision Layer
    participant Rule as 📋 Rule Engine
    participant Act as ⚙️ Action Engine
    participant Log as 📜 Audit Logger

    User->>NLP: Issues Command ("Delete temporary files")
    NLP->>Sup: Evaluate Proposed Action (CRITICAL Risk)
    Sup->>Rule: Check Active Policy Constraints
    Rule-->>Sup: Matches "File Deletion Guard"
    Sup->>User: ⚠️ Prompt for Authorization (Blast Radius & Risk)
    alt User Confirms Action
        User->>Sup: Authorize [Approve]
        Sup->>Act: Issue Cryptographic Token & Execute
        Act-->>User: File Deleted Successfully
        Act->>Log: Record [APPROVED_BY_USER]
    else User Declines Action
        User->>Sup: Abort [Reject]
        Sup-->>User: Operation Safely Cancelled
        Sup->>Log: Record [REJECTED_BY_USER]
    end
"""
            title = "Supervised Human-in-the-Loop Sequence Diagram"

        # Python / Developer Learning Roadmap Blueprint
        elif "python" in lower or "roadmap" in lower or "learning" in lower:
            code = """mindmap
  root((🐍 Python Mastery))
    Fundamentals
      Syntax & Types
      Functions & Decorators
      OOP & Classes
    Data & Analytics
      NumPy & Pandas
      Matplotlib & Seaborn
      SQL Databases
    AI & Intelligence
      PyTorch & Transformers
      Agentic AI Systems
      Computer Vision
    Production & Web
      FastAPI & Flask
      Docker & Containerization
      Testing & CI/CD
"""
            title = "Python Intelligent Systems Roadmap Mindmap"

        # Generic Flowchart Blueprint
        else:
            code = f"""flowchart LR
    Start(["Input: {topic}"]) --> Analyze["🔍 Semantic Analysis"]
    Analyze --> Decompose["🧩 Step Decomposition"]
    Decompose --> Supervise["🛡️ Supervision & Policy Gate"]
    Supervise --> Execute["⚙️ Action Dispatch"]
    Execute --> Complete(["✨ Verified Output"])
"""
            title = f"Workflow Blueprint: {topic.title()}"

        return {
            "type": "mermaid",
            "title": title,
            "code": code.strip()
        }

    @staticmethod
    def generate_chart_data(topic: str, chart_type: str = "bar") -> Dict[str, Any]:
        """Generates Chart.js structured dataset for rendering."""
        lower = topic.lower()

        if "risk" in lower or "supervision" in lower or "security" in lower:
            return {
                "type": "chart",
                "chart_type": "doughnut",
                "title": "Supervision Risk Distribution",
                "data": {
                    "labels": ["SAFE (Direct)", "LOW (Apps)", "MEDIUM (Files)", "HIGH (Scripts)", "CRITICAL (Deletions)"],
                    "datasets": [{
                        "label": "Action Proportion",
                        "data": [45, 20, 15, 12, 8],
                        "backgroundColor": ["#10b981", "#06b6d4", "#f59e0b", "#f97316", "#ef4444"],
                        "borderColor": "#1e293b",
                        "borderWidth": 2
                    }]
                }
            }

        # System Performance Chart
        if any(w in lower for w in ["performance", "cpu", "metric", "system"]):
            return {
                "type": "chart",
                "chart_type": "line",
                "title": "Real-time Telemetry Load",
                "data": {
                    "labels": ["-60s", "-45s", "-30s", "-15s", "Now"],
                    "datasets": [
                        {
                            "label": "CPU Utilization (%)",
                            "data": [14, 28, 42, 19, 24],
                            "borderColor": "#00f0ff",
                            "backgroundColor": "rgba(0, 240, 255, 0.15)",
                            "tension": 0.4,
                            "fill": True
                        },
                        {
                            "label": "Memory Load (%)",
                            "data": [48, 49, 51, 50, 52],
                            "borderColor": "#a855f7",
                            "backgroundColor": "rgba(168, 85, 247, 0.15)",
                            "tension": 0.4,
                            "fill": True
                        }
                    ]
                }
            }

        # General Comparison Bar Chart
        return {
            "type": "chart",
            "chart_type": "bar",
            "title": f"Analytics: {topic.title()}",
            "data": {
                "labels": ["Safety", "Speed", "Reasoning", "Memory", "Supervision"],
                "datasets": [{
                    "label": "Confidence & Capability Score (%)",
                    "data": [99, 95, 92, 94, 98],
                    "backgroundColor": ["#00f0ff", "#38bdf8", "#818cf8", "#a78bfa", "#c084fc"],
                    "borderRadius": 6
                }]
            }
        }
