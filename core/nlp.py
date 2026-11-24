"""
AEGIS NLP & Intent Understanding Module
Processes natural language, extracts entities/parameters, detects ambiguities,
identifies factual misconceptions, and supports rich media controls (play, pause, resume, mute).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from aegis.config import ActionCategory

@dataclass
class ParsedIntent:
    """Represents the structured interpretation of the user's input."""
    raw_prompt: str
    primary_category: ActionCategory
    action_type: str
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_ambiguous: bool = False
    clarification_question: Optional[str] = None
    has_misconception: bool = False
    misconception_correction: Optional[str] = None
    requires_uncertainty_report: bool = False


# Known misconceptions database for Principle 5: Correction Over Blind Agreement
KNOWN_MISCONCEPTIONS = [
    {
        "pattern": r"(capital of australia.*sydney|sydney.*capital of australia)",
        "correction": "Actually, the capital of Australia is Canberra, not Sydney (which is Australia's largest city)."
    },
    {
        "pattern": r"(sun revolves around.*earth|sun orbits.*earth)",
        "correction": "In fact, the Earth and other planets orbit the Sun (heliocentrism), not the other way around."
    },
    {
        "pattern": r"(great wall.*visible from.*moon|wall of china.*from the moon)",
        "correction": "That is a common myth. The Great Wall of China is generally not visible from low Earth orbit without magnification, and impossible to see from the Moon with the naked eye."
    },
    {
        "pattern": r"(python is purely compiled.*machine code)",
        "correction": "Python is primarily an interpreted language that compiles source code to bytecode (.pyc), which is then executed by the Python Virtual Machine (PVM)."
    },
    {
        "pattern": r"(humans only use 10% of their brain|use 10 percent of our brain)",
        "correction": "That is a popular myth. Neuroimaging shows that humans utilize virtually every part of the brain, and most of the brain is active almost all the time."
    },
    {
        "pattern": r"(bats are blind)",
        "correction": "Bats are not blind; in fact, all bat species have eyes and can see. Many use echolocation to navigate in total darkness, but their vision is functional."
    }
]

# Patterns representing ambiguous / underspecified requests for Principle 7: Clarification
AMBIGUOUS_PATTERNS = [
    (r"^(do it|fix it|run that|clean it|start now|organize my stuff|delete that|do that thing|do that|handle it)$",
     "Could you please specify which file, application, or task you would like me to process?"),
    (r"^(open the file|delete the file|edit the file)$",
     "Which specific file would you like to target? Please provide the filename or path."),
    (r"^(send it|email it)$",
     "Could you clarify the recipient and the content you want to send?"),
]


class NLPProcessor:
    """Natural Language Understanding Engine for AEGIS."""

    def __init__(self):
        pass

    def parse(self, prompt: str) -> ParsedIntent:
        """Parses raw text into a structured intent with entity extraction and sanity checks."""
        clean_text = prompt.strip()
        lower = clean_text.lower()

        # 1. Check for known misconceptions (Principle 5: Correction over blind agreement)
        for item in KNOWN_MISCONCEPTIONS:
            if re.search(item["pattern"], lower):
                return ParsedIntent(
                    raw_prompt=clean_text,
                    primary_category=ActionCategory.CONVERSATION,
                    action_type="misconception_correction",
                    confidence=0.95,
                    parameters={},
                    has_misconception=True,
                    misconception_correction=item["correction"]
                )

        # 2. Check for extreme ambiguity (Principle 7: Clarification)
        for pattern, q in AMBIGUOUS_PATTERNS:
            if re.search(pattern, lower):
                return ParsedIntent(
                    raw_prompt=clean_text,
                    primary_category=ActionCategory.CONVERSATION,
                    action_type="request_clarification",
                    confidence=0.40,
                    parameters={},
                    is_ambiguous=True,
                    clarification_question=q
                )

        # 3. Check for requests requiring Uncertainty admission (Principle 6: Uncertainty)
        if any(re.search(p, lower) for p in [
            r"who will win the next\b",
            r"predict exactly when\b",
            r"what am i thinking\b",
            r"what is my secret password\b"
        ]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.CONVERSATION,
                action_type="report_uncertainty",
                confidence=0.90,
                requires_uncertainty_report=True,
                parameters={"query": clean_text}
            )

        # 3b. Identity, Greetings & Self Description (Principle 1 & Philosophy)
        if any(re.search(r'\b' + re.escape(w) + r'\b', lower) for w in [
            "who are you", "what is your name", "what is your purpose", "introduce yourself",
            "what can you do", "who created you", "who made you", "how are you", "hello", "hi", "hey"
        ]) and not any(kw in lower for kw in ["blueprint", "diagram", "chart", "architecture", "flowchart", "youtube"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.CONVERSATION,
                action_type="conversation",
                confidence=0.98,
                parameters={"text": clean_text}
            )

        # 4. MEDIA CONTROLS (Pause, Resume, Stop, Mute, Volume)
        if any(lower.startswith(w) or lower == w for w in [
            "pause the song", "pause song", "pause music", "pause video", "pause the video", "pause", "hold music", "hold song"
        ]) or ("pause" in lower and any(m in lower for m in ["song", "music", "video", "track", "playback"])):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_pause",
                confidence=0.98,
                parameters={}
            )

        if any(lower.startswith(w) or lower == w for w in [
            "resume the song", "resume song", "resume music", "resume video", "unpause", "continue song", "continue music", "resume"
        ]) or ("resume" in lower and any(m in lower for m in ["song", "music", "video", "track"])):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_resume",
                confidence=0.98,
                parameters={}
            )

        if any(lower.startswith(w) or lower == w for w in [
            "stop the song", "stop song", "stop music", "stop video", "stop audio"
        ]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_stop",
                confidence=0.98,
                parameters={}
            )

        if any(lower.startswith(w) or lower == w for w in [
            "mute", "mute volume", "mute audio", "mute sound", "unmute"
        ]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_mute",
                confidence=0.98,
                parameters={}
            )

        if any(lower.startswith(w) or lower == w for w in [
            "volume up", "increase volume", "louder", "boost volume"
        ]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_vol_up",
                confidence=0.98,
                parameters={}
            )

        if any(lower.startswith(w) or lower == w for w in [
            "volume down", "decrease volume", "lower volume", "softer"
        ]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="media_vol_down",
                confidence=0.98,
                parameters={}
            )

        # 5. TIME INTENT
        if any(word in lower for word in ["time", "clock", "current time", "what time", "tell me the time", "know the time"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="time_query",
                confidence=0.95,
                parameters={}
            )

        # 6. JOKE INTENT (pyjokes)
        if any(word in lower for word in ["joke", "make me laugh", "something funny", "say something funny", "tell me something funny"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.CONVERSATION,
                action_type="joke",
                confidence=0.95,
                parameters={}
            )

        # 7. PLAY MUSIC / YOUTUBE (pywhatkit.playonyt)
        if any(word in lower for word in ["play song", "play music", "put on", "listen to"]) or (lower.startswith("play ") and "blueprint" not in lower and "game" not in lower):
            song = lower
            for word in ["play", "song", "music", "put on", "listen to"]:
                song = song.replace(word, "")
            # Clean "in youtube", "on youtube", quotes
            song = re.sub(r'\s*(in youtube|on youtube|from youtube|video|song|track|lyrics)\s*$', '', song, flags=re.IGNORECASE)
            song = song.strip(" '\"`")
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.APP_LAUNCH,
                action_type="play_youtube",
                confidence=0.95,
                parameters={"song": song or clean_text}
            )

        # 8. YOUTUBE SEARCH
        if "youtube" in lower:
            search_query = lower.replace("youtube", "").replace("search", "").strip()
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.APP_LAUNCH,
                action_type="youtube_search",
                confidence=0.95,
                parameters={"query": search_query or "popular videos"}
            )

        # 9. GOOGLE SEARCH (pywhatkit.search)
        if any(lower.startswith(word) for word in ["google", "search the web", "search online", "search for"]):
            search_query = lower
            for word in ["google", "search the web", "search online", "search for", "search"]:
                search_query = search_query.replace(word, "")
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.WEB_SEARCH,
                action_type="google_search",
                confidence=0.92,
                parameters={"query": search_query.strip() or clean_text}
            )

        # 9a. REMINDER INTENT
        if any(w in lower for w in ["remind me", "set a reminder", "set reminder"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="set_reminder",
                confidence=0.95,
                parameters={"task": clean_text}
            )

        # 9b. REMEMBER FACT INTENT
        if any(w in lower for w in ["remember that", "add memory", "addmemory", "keep in mind", "save fact"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="remember_fact",
                confidence=0.95,
                parameters={"fact": clean_text}
            )

        # 10. WHATSAPP MESSAGE
        if any(word in lower for word in ["whatsapp", "send a message", "send message", "message someone"]):
            recipient = "ankur"
            for name in ["ankur", "ayush", "someone"]:
                if name in lower:
                    recipient = name
                    break
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="whatsapp_message",
                confidence=0.92,
                parameters={"recipient": recipient, "message": clean_text}
            )

        # 11. OPEN WEBSITE / APP
        if any(word in lower for word in ["open website", "open site", "go to website", "visit website"]) or (lower.startswith("open ") and any(ext in lower for ext in [".com", ".org", ".net", ".io", "google", "github", "reddit", "youtube", "calc", "notepad", "code"])):
            site = lower
            for word in ["open website", "open site", "go to website", "visit website", "open"]:
                site = site.replace(word, "")
            site = site.strip()
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.APP_LAUNCH,
                action_type="open_website",
                confidence=0.95,
                parameters={"site": site}
            )

        # 12. Multi-step Workflow Intent (SIH demo: "Find 3 Python resources and organize them in a file")
        if (("find" in lower or "search" in lower) and ("organize" in lower or "save" in lower or "create" in lower)) or \
           ("step by step" in lower or "workflow" in lower or "research and summarize" in lower):
            return self._extract_workflow_intent(clean_text)

        # 13. Blueprints & Diagrams Intent
        if any(w in lower for w in ["blueprint", "architecture", "diagram", "flowchart", "mermaid", "mindmap", "system sketch"]):
            return self._extract_blueprint_intent(clean_text)

        # 14. Charts & Visual Data Analytics Intent
        if any(w in lower for w in ["chart", "graph", "plot", "pie chart", "bar chart", "visualize data"]):
            return self._extract_chart_intent(clean_text)

        # 15. File Operations Intent (Delete, Create, List, Read)
        if any(w in lower for w in ["file", "folder", "directory", "note", "script", "document"]) or \
           any(w in lower for w in ["create", "write", "delete", "remove", "save", "list files", "read file"]):
            file_intent = self._extract_file_intent(clean_text)
            if file_intent:
                return file_intent

        # 16. Standard App Launcher Intent
        if any(w in lower for w in ["open", "launch", "start", "run"]) and \
           any(app in lower for app in ["notepad", "calculator", "calc", "explorer", "terminal", "powershell", "code", "vscode", "browser"]):
            return self._extract_app_intent(clean_text)

        # 17. System Telemetry / Info Intent
        if any(w in lower for w in ["system status", "battery", "cpu", "ram", "memory usage", "disk space", "specs", "system info", "os info"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="system_info",
                confidence=0.95,
                parameters={}
            )

        # 18. Information / Knowledge & Question Answering Intent
        QUESTION_PREFIXES = [
            "who is", "who was", "who were", "who invented", "who discovered", "who built",
            "what is", "what are", "what was", "what were", "what causes", "what happens",
            "why is", "why are", "why does", "why do", "why did",
            "how do", "how does", "how is", "how are", "how can", "how to",
            "where is", "where are", "where was",
            "when did", "when was", "when were",
            "tell me about", "explain", "information about", "details on", "define", "meaning of",
            "search wikipedia", "search info on", "brief me on", "summarize"
        ]
        
        is_camera_query = any(w in lower for w in ["what do you see", "camera view", "in the camera", "on my screen", "look at"])
        
        if not is_camera_query and (
           any(lower.startswith(w) for w in QUESTION_PREFIXES) or \
           lower in ["pok", "sih", "isro", "drdo", "dna", "photosynthesis", "gravity"] or \
           (lower.endswith("?") and not any(k in lower for k in ["delete", "create", "launch", "open", "rule", "setting", "clear"]))
        ):
            return self._extract_search_intent(clean_text)

        # 19. Mathematical / Reasoning Intent
        if re.search(r"(\bcalculate\b|\bcompute\b|\bsolve\b|\bmath\b|[\d\.\(\)]+\s*[\+\-\*\/\^]\s*[\d\.\(\)]+)", lower):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.REASONING,
                action_type="math_reasoning",
                confidence=0.92,
                parameters={"expression": clean_text}
            )

        # 20. LOCK SCREEN
        if any(w in lower for w in ["lock screen", "lock my pc", "lock my computer", "lock workstation"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="lock_screen",
                confidence=0.95,
                parameters={}
            )

        # 21. SLEEP PC
        if any(w in lower for w in ["sleep mode", "put pc to sleep", "put computer to sleep", "go to sleep", "hibernate"]) and "go to sleep" != lower.strip():
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="sleep_pc",
                confidence=0.95,
                parameters={}
            )

        # 22. MACRO AUTOMATION
        if any(w in lower for w in ["record macro", "start recording macro", "start recording"]):
            name = re.sub(r'(?i)(record|start|macro|recording)\s*', '', lower).strip() or "untitled"
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="macro_record",
                confidence=0.95,
                parameters={"name": name}
            )

        if any(w in lower for w in ["stop recording", "stop macro"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="macro_stop",
                confidence=0.95,
                parameters={}
            )

        if any(w in lower for w in ["play macro", "replay macro", "run macro"]):
            name = re.sub(r'(?i)(play|replay|run|macro)\s*', '', lower).strip()
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="macro_play",
                confidence=0.95,
                parameters={"name": name}
            )

        if any(w in lower for w in ["list macros", "show macros", "my macros"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="macro_list",
                confidence=0.95,
                parameters={}
            )

        # 23. PYTHON SANDBOX
        if any(w in lower for w in ["run this python", "execute python", "run script", "execute code", "python code", "run code"]):
            code = re.sub(r'(?i)(run this python|execute python|run script|execute code|python code|run code)\s*:?\s*', '', clean_text).strip()
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="run_script",
                confidence=0.92,
                parameters={"code": code}
            )

        # 24. LAN SCAN
        if any(w in lower for w in ["scan network", "scan lan", "find devices", "network scan", "iot devices", "connected devices"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="lan_scan",
                confidence=0.95,
                parameters={}
            )

        # 25. WAKE-ON-LAN
        if any(w in lower for w in ["wake on lan", "wake up device", "wake device", "send magic packet"]):
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', clean_text)
            mac = mac_match.group(0) if mac_match else ""
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="wake_on_lan",
                confidence=0.92,
                parameters={"mac_address": mac}
            )

        # 26. WEB ARCHIVER
        if any(w in lower for w in ["archive website", "save webpage", "download page", "archive page", "save website"]):
            url_match = re.search(r'https?://\S+', clean_text)
            url = url_match.group(0) if url_match else ""
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="web_archive",
                confidence=0.92,
                parameters={"url": url}
            )

        # 27. EMAIL READER
        if any(w in lower for w in ["read my emails", "check outlook", "recent emails", "check email", "inbox", "read emails"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="email_list",
                confidence=0.95,
                parameters={"count": 10}
            )

        # 28. SYSTEM SHUTDOWN
        if any(w in lower for w in ["shutdown computer", "shut down pc", "shutdown pc", "turn off computer"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="system_shutdown",
                confidence=0.95,
                parameters={}
            )

        # 29. CLEAR MEMORY
        if any(w in lower for w in ["clear memory", "clear history", "forget everything", "wipe memory"]):
            return ParsedIntent(
                raw_prompt=clean_text,
                primary_category=ActionCategory.SYSTEM_OPERATION,
                action_type="clear_memory",
                confidence=0.95,
                parameters={}
            )

        # 30. Default to Conversational Intent
        return ParsedIntent(
            raw_prompt=clean_text,
            primary_category=ActionCategory.CONVERSATION,
            action_type="conversation",
            confidence=0.85,
            parameters={"text": clean_text}
        )

    def _extract_app_intent(self, text: str) -> ParsedIntent:
        lower = text.lower()
        target_app = "notepad"
        if "calc" in lower:
            target_app = "calculator"
        elif "explorer" in lower or "folder" in lower:
            target_app = "explorer"
        elif "terminal" in lower or "powershell" in lower or "cmd" in lower:
            target_app = "terminal"
        elif "code" in lower or "vscode" in lower:
            target_app = "vscode"
        elif "browser" in lower or "chrome" in lower or "edge" in lower:
            target_app = "browser"

        return ParsedIntent(
            raw_prompt=text,
            primary_category=ActionCategory.APP_LAUNCH,
            action_type=f"app_launch_{target_app}",
            confidence=0.95,
            parameters={"app_id": target_app}
        )

    def _extract_file_intent(self, text: str) -> Optional[ParsedIntent]:
        lower = text.lower()

        # Delete File / Folder
        if "delete" in lower or "remove" in lower or "erase" in lower:
            filename_match = re.search(r'(?:file|folder|document)?\s*([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+|[a-zA-Z0-9_\-]+)', lower.split("delete")[-1])
            target = filename_match.group(1).strip() if filename_match else "unspecified_file"
            return ParsedIntent(
                raw_prompt=text,
                primary_category=ActionCategory.FILE_OPERATION,
                action_type="file_delete",
                confidence=0.90,
                parameters={"filename": target, "path": target}
            )

        # List files
        if "list" in lower or "show files" in lower or "dir" in lower:
            return ParsedIntent(
                raw_prompt=text,
                primary_category=ActionCategory.FILE_OPERATION,
                action_type="file_list",
                confidence=0.95,
                parameters={}
            )

        # Create / Save File
        if "create" in lower or "save" in lower or "write" in lower:
            filename_match = re.search(r'([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)', text)
            target = filename_match.group(1).strip() if filename_match else "note.txt"
            content = text
            if "with content" in lower:
                content = text.split("with content", 1)[1].strip()
            elif "containing" in lower:
                content = text.split("containing", 1)[1].strip()

            return ParsedIntent(
                raw_prompt=text,
                primary_category=ActionCategory.FILE_OPERATION,
                action_type="file_create",
                confidence=0.90,
                parameters={"filename": target, "content": content, "overwrite": False}
            )

        # Read File
        if "read" in lower or "view" in lower or "show content" in lower:
            filename_match = re.search(r'([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)', text)
            target = filename_match.group(1).strip() if filename_match else "note.txt"
            return ParsedIntent(
                raw_prompt=text,
                primary_category=ActionCategory.FILE_OPERATION,
                action_type="file_read",
                confidence=0.90,
                parameters={"filename": target}
            )

        return None

    def _extract_blueprint_intent(self, text: str) -> ParsedIntent:
        lower = text.lower()
        topic = "System Architecture"
        for kw in ["of", "about", "for"]:
            if f"blueprint {kw}" in lower:
                topic = text[lower.find(f"blueprint {kw}") + len(f"blueprint {kw}"):].strip()
                break
            elif f"diagram {kw}" in lower:
                topic = text[lower.find(f"diagram {kw}") + len(f"diagram {kw}"):].strip()
                break
            elif f"architecture {kw}" in lower:
                topic = text[lower.find(f"architecture {kw}") + len(f"architecture {kw}"):].strip()
                break

        return ParsedIntent(
            raw_prompt=text,
            primary_category=ActionCategory.BLUEPRINT_GENERATION,
            action_type="blueprint_gen",
            confidence=0.95,
            parameters={"topic": topic.strip(" .")}
        )

    def _extract_chart_intent(self, text: str) -> ParsedIntent:
        lower = text.lower()
        chart_type = "bar"
        if "pie" in lower:
            chart_type = "pie"
        elif "line" in lower:
            chart_type = "line"
        elif "radar" in lower:
            chart_type = "radar"

        return ParsedIntent(
            raw_prompt=text,
            primary_category=ActionCategory.BLUEPRINT_GENERATION,
            action_type="chart_gen",
            confidence=0.92,
            parameters={"chart_type": chart_type, "topic": text}
        )

    def _extract_workflow_intent(self, text: str) -> ParsedIntent:
        return ParsedIntent(
            raw_prompt=text,
            primary_category=ActionCategory.WORKFLOW_AGENT,
            action_type="workflow_plan",
            confidence=0.90,
            parameters={"goal": text}
        )

    def _extract_search_intent(self, text: str) -> ParsedIntent:
        clean_q = re.sub(
            r'^(search for|search wikipedia for|search wikipedia|search|lookup|look up|google|who is|who was|who were|what is|what are|what was|what were|what causes|why is|why are|why does|why do|why did|how do|how does|how is|how can|how to|where is|where are|when did|when was|tell me about|explain|information about|details on|define|meaning of)\s*',
            '',
            text,
            flags=re.IGNORECASE
        ).strip(" ?.")
        return ParsedIntent(
            raw_prompt=text,
            primary_category=ActionCategory.WEB_SEARCH,
            action_type="web_search",
            confidence=0.95,
            parameters={"query": clean_q or text}
        )
