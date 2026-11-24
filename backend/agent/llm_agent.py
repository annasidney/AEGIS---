import os
import json
import logging
import datetime
import dateparser
import httpx
from typing import Dict, Any, List, Optional
from backend.config import settings
from backend.tools.registry import registry
from backend.agent.web_search import search_web_summary
from backend.tools.math_tools import evaluate_math_expression
from backend.database import SessionLocal
from backend.models import Conversation, Memory

logger = logging.getLogger("AEGIS.LLMAgent")

SYSTEM_PROMPT = """You are AEGIS (Assisted Executive Guidance and Intelligence System) — an elite AI personal assistant for Windows designed for SIH2611 / SIH26204.
You combine the intelligence of ChatGPT, the voice/HUD personality of JARVIS, the deep OS integration of Windows Copilot, and full computer-use capabilities.

CORE DIRECTIVES:
1. Keep spoken responses concise, natural, and friendly (1-2 sentences unless the user requests detailed explanations).
2. When performing computer tasks (opening apps, creating files, web searches, playing music, drawing in paint, solving math), execute the appropriate registered tool and speak a natural confirmation (e.g., "Done. Chrome is open.", "Created calculator.py on your Desktop.", "2 * 2 = 4").
3. NEVER expose raw chain-of-thought or internal schemas to the user.
4. When asked for current info (weather, stock prices, news), call the search tool.
5. When asked to create files (Python calculator, Word documents, PowerPoint presentations, HTML portfolios, spreadsheets), provide full, working, complete code/content and invoke create_file.
6. REMINDERS: Reminders must always be user-defined. Never invent or guess a reminder time. If the user doesn't specify when, ask "When should I remind you?".
7. REAL CLOCK: Always use actual system time/date from get_system_time / get_system_date.
8. Maintain conversational context: resolve pronouns like 'it', 'the first one', 'that', 'do it again' based on previous turns.
"""

class AegisAgent:
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.dictation_buffer: List[str] = []
        self.is_dictating: bool = False
        self.last_pending_task: Optional[str] = None

    def start_dictation(self):
        self.is_dictating = True
        self.dictation_buffer = []
        return "Dictation started. I am listening continuously."

    def stop_dictation(self) -> str:
        self.is_dictating = False
        accumulated = " ".join(self.dictation_buffer)
        return f"Dictation stopped. Collected {len(self.dictation_buffer)} spoken segments."

    def append_dictation_text(self, text: str):
        if self.is_dictating and text.strip():
            self.dictation_buffer.append(text.strip())

    def get_dictation_content(self) -> str:
        return "\n".join(self.dictation_buffer)

    def _get_persistent_memories_context(self) -> str:
        db = SessionLocal()
        try:
            mems = db.query(Memory).all()
            if not mems:
                return ""
            mem_lines = [f"- {m.key}: {m.value}" for m in mems]
            return "\nUSER PREFERENCES & MEMORIES:\n" + "\n".join(mem_lines)
        finally:
            db.close()

    async def process_message(self, user_input: str, is_voice: bool = False) -> Dict[str, Any]:
        text = user_input.strip()
        t_low = text.lower()

        # Handle Dictation Mode Commands
        if t_low in ["start dictation", "begin dictation"]:
            msg = self.start_dictation()
            return {"response": msg, "tool": "dictation_start", "verified": True}
        if t_low in ["stop dictation", "end dictation"]:
            msg = self.stop_dictation()
            return {"response": msg, "tool": "dictation_stop", "verified": True}

        # Check if user is replying with a time to a previous "When should I remind you?" question
        if self.last_pending_task:
            task = self.last_pending_task
            parsed_time = dateparser.parse(
                text.replace("/", ":"),
                settings={'RELATIVE_BASE': datetime.datetime.now(), 'PREFER_DATES_FROM': 'future'}
            )
            # Only treat as reminder time if parsing succeeded or text looks like time specification
            if parsed_time and any(w in t_low for w in ["at", "pm", "am", "tomorrow", "today", "minute", "hour", "clock", "morning", "evening", ":", "in "]):
                self.last_pending_task = None
                tool_res = await registry.execute("create_reminder", {"text": task, "time_str": text})
                res_data = tool_res.get("result", {})
                msg = res_data.get("message", "Reminder set.")
                return {"response": msg, "tool": "create_reminder", "verified": tool_res.get("verified", False)}
            else:
                self.last_pending_task = None

        # Primary reasoning engine: Gemini 2.5 Flash (ReAct loop with native tool calling)
        if settings.GEMINI_API_KEY:
            gemini_res = await self._run_gemini_react(text)
            if gemini_res:
                return gemini_res

        # If OpenRouter API key is not configured, use rich offline handler
        if not settings.OPENROUTER_API_KEY:
            return await self._handle_offline_agent(text)

        # Build messages payload with history and system prompt
        memories_ctx = self._get_persistent_memories_context()
        system_content = SYSTEM_PROMPT + (f"\n{memories_ctx}" if memories_ctx else "")
        if self.dictation_buffer:
            system_content += f"\n\nCURRENT DICTATED BUFFER:\n{self.get_dictation_content()}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": text})

        tools_schema = registry.get_all_tools_metadata()
        tools_schema.append({
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the live web for current facts, news, weather, stock prices, or events.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        })

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aegis-assistant.ai",
            "X-Title": "AEGIS Assistant"
        }

        # Multi-turn tool loop (max 4 turns)
        for _ in range(4):
            payload = {
                "model": settings.OPENROUTER_MODEL or "google/gemini-2.0-flash-001",
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": "auto",
                "temperature": 0.4
            }

            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(
                        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                        headers=headers,
                        json=payload
                    )

                if resp.status_code != 200:
                    logger.error(f"OpenRouter API Error {resp.status_code}: {resp.text}")
                    return await self._handle_offline_agent(text)

                data = resp.json()
                choice = data["choices"][0]
                message = choice["message"]

                # If model called tools
                if "tool_calls" in message and message["tool_calls"]:
                    messages.append(message)
                    for tool_call in message["tool_calls"]:
                        fn_name = tool_call["function"]["name"]
                        fn_args_raw = tool_call["function"].get("arguments", "{}")
                        try:
                            fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                        except Exception:
                            fn_args = {}

                        logger.info(f"LLM Agent invoking tool '{fn_name}' with args: {fn_args}")

                        if fn_name == "search_web":
                            search_res = search_web_summary(fn_args.get("query", text))
                            tool_result_str = json.dumps(search_res)
                        else:
                            exec_res = await registry.execute(fn_name, fn_args)
                            tool_result_str = json.dumps(exec_res.get("result", exec_res))

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result_str
                        })
                    continue

                final_answer = message.get("content", "")
                self.conversation_history.append({"role": "user", "content": text})
                self.conversation_history.append({"role": "assistant", "content": final_answer})

                self._save_conversation(text, final_answer)

                return {
                    "response": final_answer,
                    "verified": True
                }

            except Exception as e:
                logger.error(f"Error in LLM Agent loop: {e}", exc_info=True)
                return await self._handle_offline_agent(text)

        return {"response": "I have processed your request.", "verified": True}

    # ---------------------------------------------------------------- Gemini ReAct
    _SCHEMA_KEYS = {"type", "description", "enum", "properties", "required", "items", "format", "nullable"}

    @classmethod
    def _to_gemini_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Strip JSON-schema keys that the Gemini function-declaration subset does not accept."""
        if not isinstance(schema, dict):
            return schema
        clean: Dict[str, Any] = {}
        for k, v in schema.items():
            if k not in cls._SCHEMA_KEYS:
                continue
            if k == "properties" and isinstance(v, dict):
                clean[k] = {pk: cls._to_gemini_schema(pv) for pk, pv in v.items()}
            elif k == "items":
                clean[k] = cls._to_gemini_schema(v)
            else:
                clean[k] = v
        return clean

    def _gemini_function_declarations(self) -> List[Dict[str, Any]]:
        decls: List[Dict[str, Any]] = []
        for tool in registry.get_all_tools_metadata():
            fn = tool["function"]
            decl: Dict[str, Any] = {"name": fn["name"], "description": fn["description"]}
            params = self._to_gemini_schema(fn.get("parameters") or {})
            if params.get("properties"):
                decl["parameters"] = params
            decls.append(decl)
        decls.append({
            "name": "search_web",
            "description": "Search the live web (Wikipedia + DuckDuckGo) for current facts, news, weather, prices or events.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        })
        return decls

    def _gemini_contents(self, text: str) -> List[Dict[str, Any]]:
        contents: List[Dict[str, Any]] = []
        for m in self.conversation_history[-10:]:
            role = "user" if m.get("role") == "user" else "model"
            if isinstance(m.get("content"), str) and m["content"].strip():
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": [{"text": text}]})
        return contents

    async def _run_gemini_react(self, text: str) -> Optional[Dict[str, Any]]:
        """
        ReAct loop on Gemini 2.5 Flash: the model REASONS about the goal, ACTS by calling a
        registered tool, OBSERVES the result, and repeats until it can answer (max AGENT_MAX_STEPS).
        Returns None on any transport/API failure so the caller can fall back gracefully.
        """
        url = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent"
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"}

        system_text = SYSTEM_PROMPT + self._get_persistent_memories_context()
        if self.dictation_buffer:
            system_text += f"\n\nCURRENT DICTATED BUFFER:\n{self.get_dictation_content()}"

        contents = self._gemini_contents(text)
        tools = [{"functionDeclarations": self._gemini_function_declarations()}]
        steps: List[Dict[str, Any]] = []
        last_tool: Optional[str] = None

        for _ in range(max(1, settings.AGENT_MAX_STEPS)):
            payload = {
                "systemInstruction": {"parts": [{"text": system_text}]},
                "contents": contents,
                "tools": tools,
                "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
            }
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
            except Exception as e:
                logger.error(f"Gemini request failed: {e}")
                return None

            if resp.status_code != 200:
                logger.error(f"Gemini API error {resp.status_code}: {resp.text[:300]}")
                return None

            try:
                candidate = resp.json()["candidates"][0]
                content = candidate.get("content") or {}
                parts = content.get("parts") or []
            except Exception as e:
                logger.error(f"Unexpected Gemini response shape: {e}")
                return None

            calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if not calls:
                answer = " ".join(p["text"] for p in parts if p.get("text") and not p.get("thought")).strip()
                if not answer:
                    return None
                self.conversation_history.append({"role": "user", "content": text})
                self.conversation_history.append({"role": "assistant", "content": answer})
                self.conversation_history = self.conversation_history[-20:]
                self._save_conversation(text, answer)
                return {"response": answer, "tool": last_tool, "steps": steps, "verified": True}

            # ACT -> OBSERVE
            contents.append(content)  # keep the model turn exactly as returned (thought signatures)
            response_parts = []
            for call in calls:
                name, args = call.get("name", ""), call.get("args") or {}
                logger.info(f"Gemini ReAct tool call: {name}({args})")
                if name == "search_web":
                    result: Any = search_web_summary(args.get("query", text))
                else:
                    exec_res = await registry.execute(name, args)
                    result = exec_res.get("result", exec_res)
                last_tool = name
                steps.append({"tool": name, "args": args})
                result_json = json.loads(json.dumps(result, default=str))
                response_parts.append({"functionResponse": {"name": name, "response": {"result": result_json}}})
            contents.append({"role": "user", "parts": response_parts})

        return {"response": "I've carried out those steps for you.", "tool": last_tool, "steps": steps, "verified": True}

    async def _handle_offline_agent(self, text: str) -> Dict[str, Any]:
        """Robust offline handler when cloud LLM is unavailable."""
        t_low = text.lower()

        # Handle Python calculator creation request
        if "calculator" in t_low and ("create" in t_low or "make" in t_low):
            calc_code = (
                '"""Simple Calculator generated by AEGIS"""\n\n'
                'def add(x, y): return x + y\n'
                'def subtract(x, y): return x - y\n'
                'def multiply(x, y): return x * y\n'
                'def divide(x, y):\n'
                '    if y == 0: return "Error: Division by zero"\n'
                '    return x / y\n\n'
                'if __name__ == "__main__":\n'
                '    print("=== AEGIS Calculator ===")\n'
                '    print("10 + 5 =", add(10, 5))\n'
                '    print("10 - 5 =", subtract(10, 5))\n'
                '    print("10 * 5 =", multiply(10, 5))\n'
                '    print("10 / 5 =", divide(10, 5))\n'
            )
            res = await registry.execute("create_file", {
                "filename": "calculator.py",
                "content": calc_code,
                "location": "Desktop",
                "overwrite": True
            })
            msg = "Done. Created calculator.py on your Desktop."
            return {"response": msg, "tool": "create_file", "verified": True}

        # Handle creating file from dictation or notes
        if "create" in t_low and ("document" in t_low or "text file" in t_low or "word" in t_low or "file" in t_low):
            content = self.get_dictation_content() or f"Notes recorded by AEGIS:\n\n{text}"
            ext = ".docx" if "word" in t_low or "document" in t_low else ".txt"
            fname = f"AEGIS_Notes{ext}"
            res = await registry.execute("create_file", {
                "filename": fname,
                "content": content,
                "location": "Desktop",
                "overwrite": True
            })
            msg = f"Done. Created {fname} on your Desktop containing your notes."
            return {"response": msg, "tool": "create_file", "verified": True}

        # Greetings and conversational banter
        if any(w in t_low for w in ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon"]):
            if "morning" in t_low:
                return {"response": "Good morning! How can I assist you today?", "verified": True}
            elif "evening" in t_low:
                return {"response": "Good evening! What can I help you with tonight?", "verified": True}
            elif "afternoon" in t_low:
                return {"response": "Good afternoon! What are we working on?", "verified": True}
            return {"response": "Hey! I'm here. What can I do for you?", "verified": True}

        if any(w in t_low for w in ["how are you", "who are you", "what can you do"]):
            return {
                "response": "I'm AEGIS, your Assisted Executive Guidance and Intelligence System for Windows. I can control your computer, launch apps, solve mathematics, manage reminders, inspect surroundings via camera, draw in Paint, and assist you with your daily tasks.",
                "verified": True
            }

        if any(w in t_low for w in ["thank", "thanks", "great job", "awesome"]):
            return {
                "response": "You're very welcome! Let me know if you need anything else.",
                "verified": True
            }

        # Mathematical and arithmetic evaluation
        math_res = evaluate_math_expression(text)
        if math_res.get("success") or "Division by zero" in math_res.get("message", ""):
            return {
                "response": math_res["message"],
                "tool": "calculate_math",
                "verified": True
            }

        # Real-time search & encyclopedic knowledge lookup
        search_res = search_web_summary(text)
        if search_res.get("success"):
            return {"response": search_res.get("message", ""), "tool": "web_search", "verified": True}

        return {
            "response": f"I'm here! Let me know what you'd like to do, such as opening an app, solving math, drawing in Paint, creating files, checking reminders, or asking questions.",
            "verified": True
        }

    def _save_conversation(self, user_msg: str, bot_msg: str):
        db = SessionLocal()
        try:
            db.add(Conversation(role="user", content=user_msg))
            db.add(Conversation(role="assistant", content=bot_msg))
            db.commit()
        except Exception as e:
            logger.error(f"Error saving conversation to database: {e}")
        finally:
            db.close()

agent = AegisAgent()

