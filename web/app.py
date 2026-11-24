"""
AEGIS Web Application & API Server
Flask RESTful backend serving the high-tech executive command center dashboard.
"""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response
from aegis.config import SECRET_KEY, RiskLevel, SupervisionMode
from aegis.core.engine import AegisEngine
from aegis.speech.tts import TTSEngine

def create_app(db_path=None) -> Flask:
    """Application factory for AEGIS."""
    template_dir = Path(__file__).resolve().parent / "templates"
    static_dir = Path(__file__).resolve().parent / "static"

    app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["JSON_SORT_KEYS"] = False

    # Initialize master AEGIS engine
    engine = AegisEngine(db_path=db_path)

    # ------------------ ROOT UI ROUTE ------------------ #
    @app.route("/")
    def index():
        profile = engine.memory.get_user_profile()
        return render_template("index.html", user_profile=profile)

    # ------------------ CORE INTERACTION APIS ------------------ #
    @app.route("/api/chat", methods=["POST"])
    def chat_endpoint():
        """Handles incoming text, voice transcript, camera query, and neural object tags."""
        data = request.get_json() or {}
        prompt = data.get("prompt", "").strip()
        session_id = data.get("session_id", "default_session")
        image_data = data.get("image_data")  # base64 string
        detected_objects = data.get("detected_objects")  # list of objects from COCO-SSD

        if not prompt and not image_data and not detected_objects:
            return jsonify({"error": "Empty prompt and no visual data provided."}), 400

        try:
            result = engine.process_input(
                prompt,
                session_id=session_id,
                image_data=image_data,
                detected_objects=detected_objects
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": f"Internal pipeline error: {str(e)}"}), 500

    @app.route("/api/voice/stop", methods=["POST"])
    def stop_voice_endpoint():
        """Immediately halts active TTS speech synthesis (Barge-in / Kill feature)."""
        try:
            engine.tts.stop()
            engine.tts = TTSEngine()
            return jsonify({"success": True, "message": "Speech synthesis killed successfully."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/approve", methods=["POST"])
    def approve_endpoint():
        """Processes user authorization or rejection for a staged action."""
        data = request.get_json() or {}
        action_id = data.get("action_id")
        approved = data.get("approved", False)
        session_id = data.get("session_id", "default_session")

        if not action_id:
            return jsonify({"error": "Missing action_id parameter."}), 400

        try:
            res = engine.handle_user_approval(action_id, approved, session_id=session_id)
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": f"Error handling approval: {str(e)}"}), 500

    # ------------------ RULES ENGINE APIS ------------------ #
    @app.route("/api/rules", methods=["GET", "POST"])
    def rules_endpoint():
        if request.method == "POST":
            data = request.get_json() or {}
            name = data.get("name", "Custom Rule")
            rule_text = data.get("rule_text", "")
            risk_override = data.get("risk_override", "HIGH")
            if not rule_text:
                return jsonify({"error": "Rule text cannot be empty."}), 400
            rule_id = engine.memory.add_rule(name, rule_text, risk_override=risk_override)
            return jsonify({"success": True, "rule_id": rule_id, "message": f"Rule '{name}' added successfully."})

        rules = engine.memory.get_rules()
        return jsonify({"rules": rules})

    @app.route("/api/rules/<int:rule_id>/toggle", methods=["POST"])
    def toggle_rule_endpoint(rule_id):
        data = request.get_json() or {}
        is_active = data.get("is_active", True)
        engine.memory.toggle_rule(rule_id, is_active)
        return jsonify({"success": True, "message": f"Rule {rule_id} status updated."})

    @app.route("/api/rules/<int:rule_id>", methods=["DELETE"])
    def delete_rule_endpoint(rule_id):
        engine.memory.delete_rule(rule_id)
        return jsonify({"success": True, "message": f"Rule {rule_id} deleted."})

    # ------------------ MEMORY & PROFILE APIS ------------------ #
    @app.route("/api/profile", methods=["GET", "POST"])
    def profile_endpoint():
        if request.method == "POST":
            data = request.get_json() or {}
            engine.memory.update_user_profile(
                name=data.get("name"),
                role=data.get("role"),
                preferred_tone=data.get("preferred_tone"),
                supervision_mode=data.get("supervision_mode")
            )
            return jsonify({"success": True, "message": "Profile updated."})

        profile = engine.memory.get_user_profile()
        return jsonify({"profile": profile})

    @app.route("/api/knowledge", methods=["GET", "POST"])
    def knowledge_endpoint():
        if request.method == "POST":
            data = request.get_json() or {}
            key = data.get("key", "")
            value = data.get("value", "")
            category = data.get("category", "general")
            if not key or not value:
                return jsonify({"error": "Key and value required."}), 400
            doc_id = engine.memory.store_fact(key, value, category=category)
            return jsonify({"success": True, "id": doc_id, "message": "Fact stored in Knowledge Vault."})

        vault = engine.memory.get_knowledge_vault()
        return jsonify({"knowledge": vault})

    @app.route("/api/projects", methods=["GET", "POST"])
    def projects_endpoint():
        if request.method == "POST":
            data = request.get_json() or {}
            name = data.get("name", "New Project")
            desc = data.get("description", "")
            ws_path = data.get("workspace_path")
            pid = engine.memory.add_project(name, desc, {"workspace_path": ws_path} if ws_path else None)
            return jsonify({"success": True, "project_id": pid, "message": f"Project '{name}' initialized."})

        projects = engine.memory.get_projects()
        return jsonify({"projects": projects})

    # ------------------ SETTINGS APIS ------------------ #
    @app.route("/api/settings/apikey", methods=["POST"])
    def apikey_endpoint():
        data = request.get_json() or {}
        provider = data.get("provider", "gemini")
        key = data.get("key", "")
        if not key:
            return jsonify({"error": "API key cannot be empty."}), 400
        engine.model_provider.set_api_key(provider, key)
        return jsonify({"success": True, "message": f"API key for {provider} updated."})

    # ------------------ AUDIT & TELEMETRY APIS ------------------ #
    @app.route("/api/audit-logs", methods=["GET"])
    def audit_logs_endpoint():
        limit = request.args.get("limit", 50, type=int)
        risk_filter = request.args.get("risk")
        logs = engine.audit_logger.get_recent_logs(limit=limit, risk_filter=risk_filter)
        stats = engine.audit_logger.get_execution_stats()
        return jsonify({"logs": logs, "stats": stats, "metrics": stats})

    @app.route("/api/audit-logs/export", methods=["GET"])
    def export_audit_endpoint():
        md_content = engine.audit_logger.export_markdown_report()
        return Response(
            md_content,
            mimetype="text/markdown",
            headers={"Content-Disposition": "attachment;filename=aegis_audit_report.md"}
        )

    @app.route("/api/system-telemetry", methods=["GET"])
    def telemetry_endpoint():
        metrics = engine.action_engine.system_inspector.get_system_metrics()
        top_procs = engine.action_engine.system_inspector.get_top_processes(limit=5)
        return jsonify({"metrics": metrics, "top_processes": top_procs})

    @app.route("/api/files", methods=["GET"])
    def files_endpoint():
        files = engine.action_engine.file_manager.list_files()
        return jsonify({"files": files})

    @app.route("/api/media/control", methods=["POST"])
    def media_control_endpoint():
        from aegis.actions.action_engine import trigger_media_key
        data = request.get_json() or {}
        command = data.get("command", "pause").lower()
        if command in ["pause", "resume", "play", "playpause"]:
            trigger_media_key(0xB3)
            msg = "Toggled Play/Pause"
        elif command == "stop":
            trigger_media_key(0xB2)
            msg = "Stopped"
        elif command == "mute":
            trigger_media_key(0xAD)
            msg = "Toggled Mute"
        elif command == "vol_up":
            for _ in range(3): trigger_media_key(0xAF)
            msg = "Volume Increased"
        elif command == "vol_down":
            for _ in range(3): trigger_media_key(0xAE)
            msg = "Volume Decreased"
        else:
            trigger_media_key(0xB3)
            msg = "Play/Pause"

        return jsonify({"success": True, "command": command, "message": f"{msg} playback."})

    return app
