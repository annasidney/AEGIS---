"""
AEGIS Action Engine
The central execution layer.
CRITICAL RULE: Guarantees that no consequential action executes without a verified Supervision Token.
Includes native desktop execution, media keys (Play/Pause, Stop, Mute), os.startfile foreground browser/app triggers, pyjokes, and direct YouTube video resolution.
"""

import os
import re
import urllib.parse
import datetime
import threading
import webbrowser
import pyjokes
from typing import Dict, Any, Tuple, Optional
from aegis.config import RiskLevel
from aegis.actions.app_launcher import AppLauncher
from aegis.actions.file_manager import FileManager
from aegis.actions.web_search import WebSearchEngine, get_youtube_video_url
from aegis.actions.system_ops import SystemInspector
from aegis.actions.blueprint_gen import BlueprintGenerator
from aegis.actions.workflow_agent import WorkflowAgent
from aegis.actions.visual_clicker import VisualClicker
from aegis.actions.email_reader import OutlookReader
from aegis.actions.web_archiver import WebArchiver
from aegis.actions.sandbox import PythonSandbox
from aegis.actions.macro_engine import MacroEngine
from aegis.actions.network_tools import LANScanner, WakeOnLAN
from aegis.supervision.supervisor import SupervisionLayer

PHONE_NUMBERS = {
    "ankur": "+918709883914",
    "ayush": "+918709883914",
    "ayushmaan": "+918709883914",
    "someone": "+91XXXXXXXXXX"
}

KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "chatgpt": "https://chat.openai.com",
    "gmail": "https://mail.google.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "wikipedia": "https://www.wikipedia.org"
}

def trigger_media_key(key_code: int) -> None:
    """Sends native hardware media key events using pyautogui."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        key_map = {
            0xB3: 'playpause',
            0xB2: 'stop',
            0xAD: 'volumemute',
            0xAF: 'volumeup',
            0xAE: 'volumedown'
        }
        if key_code in key_map:
            pyautogui.press(key_map[key_code])
    except Exception as e:
        print(f"[Media Key Error]: {e}")

def open_url_foreground(url: str):
    """Opens a URL in the default browser in the active foreground window."""
    try:
        if os.name == "nt":
            import subprocess
            subprocess.run(["cmd", "/c", "start", "", url], shell=True, check=False)
        else:
            import webbrowser
            webbrowser.open(url, new=2, autoraise=True)
    except Exception as e:
        print(f"[ActionEngine Open Error]: {e}")
        try:
            import webbrowser
            webbrowser.open(url, new=2, autoraise=True)
        except Exception:
            pass
        webbrowser.open(url)


class ActionEngine:
    """Dispatches authorized tool operations and validates supervision authorization tokens."""

    def __init__(self, supervision_layer: SupervisionLayer, file_manager: Optional[FileManager] = None):
        self.supervision = supervision_layer
        self.file_manager = file_manager or FileManager()
        self.app_launcher = AppLauncher()
        self.web_search = WebSearchEngine()
        self.system_inspector = SystemInspector()
        self.blueprint_gen = BlueprintGenerator()
        self.workflow_agent = WorkflowAgent(self.file_manager, self.web_search)
        self.visual_clicker = VisualClicker()
        self.web_archiver = WebArchiver()
        self.email_reader = OutlookReader()
        self.sandbox = PythonSandbox()
        self.macro_engine = MacroEngine()
        self.lan_scanner = LANScanner()
        self.wol = WakeOnLAN()

    def execute_action(self,
                       action_id: str,
                       action_type: str,
                       risk_level: str,
                       params: Dict[str, Any],
                       approval_token: Optional[str]) -> Dict[str, Any]:
        """
        Executes the action ONLY if the authorization token is valid and signed by SupervisionLayer.
        """
        # 1. Verify token unless action is inherently SAFE
        if risk_level != RiskLevel.SAFE.value:
            if not approval_token or not self.supervision.verify_token(action_id, action_type, risk_level, approval_token):
                return {
                    "status": "UNAUTHORIZED_BLOCKED",
                    "success": False,
                    "message": "Security Error: Action blocked. Valid Supervision Layer approval token is required.",
                    "data": None
                }

        # 2. Dispatch to dedicated sub-handler
        try:
            # --- MEDIA CONTROLS (Pause, Resume, Stop, Mute, Volume) ---
            if action_type in ["media_pause", "media_resume"]:
                trigger_media_key(0xB3) # VK_MEDIA_PLAY_PAUSE
                is_pause = (action_type == "media_pause")
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "⏸️ Paused media playback." if is_pause else "▶️ Resumed media playback.",
                    "data": {"media_command": "pause" if is_pause else "resume"}
                }

            elif action_type == "media_stop":
                trigger_media_key(0xB2) # VK_MEDIA_STOP
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "⏹️ Stopped media playback.",
                    "data": {"media_command": "stop"}
                }

            elif action_type == "media_mute":
                trigger_media_key(0xAD) # VK_VOLUME_MUTE
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "🔇 Toggled audio mute.",
                    "data": {"media_command": "mute"}
                }

            elif action_type == "media_vol_up":
                for _ in range(3):
                    trigger_media_key(0xAF) # VK_VOLUME_UP
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "🔊 Volume increased.",
                    "data": {"media_command": "vol_up"}
                }

            elif action_type == "media_vol_down":
                for _ in range(3):
                    trigger_media_key(0xAE) # VK_VOLUME_DOWN
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "🔉 Volume decreased.",
                    "data": {"media_command": "vol_down"}
                }

            # --- Time Query ---
            elif action_type == "time_query":
                cur_time = datetime.datetime.now().strftime("%I:%M %p")
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"The current time is **{cur_time}**.",
                    "data": {"time": cur_time}
                }

            # --- Joke (pyjokes) ---
            elif action_type == "joke":
                joke_text = pyjokes.get_joke()
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"😄 **Here's a joke**:\n\n\"{joke_text}\"",
                    "data": {"joke": joke_text}
                }

            # --- Play YouTube Song (Foreground Direct Playback) ---
            elif action_type == "play_youtube":
                raw_song = params.get("song", "music").strip()
                clean_song, watch_url, video_id = get_youtube_video_url(raw_song)
                embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1" if video_id else ""

                # Launch immediately in foreground browser window
                open_url_foreground(watch_url)

                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"🎵 **Opening YouTube & Playing**: *{clean_song.title()}*\n\n[▶️ Watch on YouTube]({watch_url})",
                    "data": {
                        "song": clean_song,
                        "url": watch_url,
                        "target_url": watch_url,
                        "video_id": video_id,
                        "embed_url": embed_url,
                        "visual_type": "youtube_player"
                    },
                    "visual_type": "youtube_player"
                }

            # --- YouTube Search ---
            elif action_type == "youtube_search":
                q = params.get("query", "trending").strip()
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
                open_url_foreground(url)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"📺 **Searching YouTube for**: *{q}*\n\n[▶️ Open YouTube Results]({url})",
                    "data": {"query": q, "url": url, "target_url": url}
                }

            # --- Google Search ---
            elif action_type == "google_search":
                q = params.get("query", "").strip()
                google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
                open_url_foreground(google_url)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"🔍 **Searching Google for**: *{q}*\n\n[Open Search Results]({google_url})",
                    "data": {"query": q, "url": google_url, "target_url": google_url}
                }

            # --- Reminders ---
            elif action_type == "set_reminder":
                task_text = params.get("task", "")
                delay_sec = 60 # default 1 min
                if "second" in task_text:
                    match = re.search(r'(\d+)\s*second', task_text)
                    if match: delay_sec = int(match.group(1))
                elif "minute" in task_text:
                    match = re.search(r'(\d+)\s*minute', task_text)
                    if match: delay_sec = int(match.group(1)) * 60
                elif "hour" in task_text:
                    match = re.search(r'(\d+)\s*hour', task_text)
                    if match: delay_sec = int(match.group(1)) * 3600

                def reminder_worker(task, delay):
                    time.sleep(delay)
                    try:
                        import winsound
                        winsound.Beep(1500, 500)
                        winsound.Beep(1500, 500)
                        
                        command = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('Sir, you have a reminder: {task}')"
                        import subprocess
                        subprocess.Popen(["powershell", "-NoProfile", "-Command", command], creationflags=subprocess.CREATE_NO_WINDOW)
                    except:
                        pass
                
                threading.Thread(target=reminder_worker, args=(task_text, delay_sec), daemon=True).start()
                
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"⏰ **Reminder Set**\n\nI will remind you about this in {delay_sec} seconds.",
                    "data": {"delay": delay_sec, "task": task_text}
                }

            # --- Remember Fact ---
            elif action_type == "remember_fact":
                fact_text = params.get("fact", "")
                clean_fact = re.sub(r'(?i)^(remember that|add memory|addmemory|keep in mind|save fact)\s*(that\s+)?', '', fact_text)
                
                try:
                    self.supervision.memory.store_knowledge(
                        topic="User Memory",
                        fact_content=clean_fact,
                        category="user_added",
                        source="chat"
                    )
                except Exception as e:
                    print(f"[Memory Save Error]: {e}")

                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"🧠 **Memory Saved**\n\nI have securely added this to your Knowledge Vault:\n> *{clean_fact}*",
                    "data": {"fact": clean_fact}
                }

            # --- Open Website / App ---
            elif action_type == "open_website":
                site = params.get("site", "google").strip().lower()
                
                # Check for desktop apps
                if site in ["notepad", "calculator", "calc", "explorer", "cmd", "terminal", "code", "vscode"]:
                    success, msg = self.app_launcher.launch(site)
                    return {
                        "status": "SUCCESS" if success else "FAILED",
                        "success": success,
                        "message": f"🖥️ {msg}",
                        "data": {"app": site}
                    }

                if site in KNOWN_SITES:
                    target_url = KNOWN_SITES[site]
                elif "." in site and not site.endswith("."):
                    target_url = f"https://{site}" if not site.startswith("http") else site
                else:
                    target_url = f"https://www.{site.replace(' ', '')}.com"

                open_url_foreground(target_url)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"🌐 **Opening Website**: [{site}]({target_url})",
                    "data": {"site": site, "url": target_url, "target_url": target_url}
                }

            # --- WhatsApp Message ---
            elif action_type == "whatsapp_message":
                recipient = params.get("recipient", "ankur").strip().lower()
                msg_body = params.get("message", "Hello from AEGIS")
                phone = PHONE_NUMBERS.get(recipient, "+918709883914")

                wa_web_url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg_body)}"
                open_url_foreground(wa_web_url)
                res_msg = f"💬 Opened WhatsApp Web to message **{recipient.title()}** ({phone})."

                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": res_msg,
                    "data": {"recipient": recipient, "phone": phone}
                }

            # --- System Telemetry ---
            elif action_type == "system_info":
                metrics = self.system_inspector.get_system_metrics()
                top_procs = self.system_inspector.get_top_processes(limit=5)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "Retrieved system telemetry successfully.",
                    "data": {"metrics": metrics, "top_processes": top_procs},
                    "visual_type": "system_telemetry"
                }

            # --- Visual Blueprints & Diagrams ---
            elif action_type == "blueprint_gen":
                topic = params.get("topic", "System Architecture")
                bp = self.blueprint_gen.generate_mermaid_blueprint(topic)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"Generated architectural blueprint for '{topic}'.",
                    "data": bp,
                    "visual_type": "mermaid"
                }

            # --- Chart Visualizations ---
            elif action_type == "chart_gen":
                topic = params.get("topic", "Data Analytics")
                chart_type = params.get("chart_type", "bar")
                chart_data = self.blueprint_gen.generate_chart_data(topic, chart_type)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"Generated interactive chart visualization for '{topic}'.",
                    "data": chart_data,
                    "visual_type": "chart"
                }

            # --- Live Web Search & Factual Q&A ---
            elif action_type == "web_search":
                query = params.get("query", "")
                search_res = self.web_search.search(query)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": search_res.get("summary") or f"Web search completed for '{query}'.",
                    "data": search_res,
                    "visual_type": "web_results"
                }

            # --- Web Page Archiving & Markdown Conversion ---
            elif action_type in ["web_archive", "archive_page"]:
                target_url = params.get("url", "").strip()
                archive_res = self.web_archiver.archive(target_url)
                if archive_res.get("success"):
                    return {
                        "status": "SUCCESS",
                        "success": True,
                        "message": f"Successfully archived **{archive_res.get('title', target_url)}** to `{archive_res.get('saved_path')}` ({archive_res.get('word_count')} words).",
                        "data": archive_res,
                        "visual_type": "archive_card"
                    }
                else:
                    return {
                        "status": "FAILED",
                        "success": False,
                        "message": f"Failed to archive '{target_url}': {archive_res.get('error', 'Unknown error')}",
                        "data": archive_res
                    }

            # --- Application Launch ---
            elif action_type.startswith("app_launch"):
                app_id = params.get("app_id") or action_type.replace("app_launch_", "")
                extra = params.get("args", "")
                success, msg = self.app_launcher.launch(app_id, extra)
                return {
                    "status": "SUCCESS" if success else "FAILED",
                    "success": success,
                    "message": msg,
                    "data": {"app_id": app_id}
                }

            # --- File Operations ---
            elif action_type == "file_create":
                filename = params.get("filename", "note.txt")
                content = params.get("content", "")
                overwrite = params.get("overwrite", False)
                success, msg = self.file_manager.create_file(filename, content, overwrite=overwrite)
                return {
                    "status": "SUCCESS" if success else "FAILED",
                    "success": success,
                    "message": msg,
                    "data": {"filename": filename}
                }

            elif action_type == "file_read":
                filename = params.get("filename", "")
                success, content = self.file_manager.read_file(filename)
                return {
                    "status": "SUCCESS" if success else "FAILED",
                    "success": success,
                    "message": f"Read file '{filename}'" if success else content,
                    "data": {"filename": filename, "content": content if success else ""}
                }

            elif action_type == "file_delete":
                filename = params.get("filename", "")
                success, msg = self.file_manager.delete_file(filename)
                return {
                    "status": "SUCCESS" if success else "FAILED",
                    "success": success,
                    "message": msg,
                    "data": {"filename": filename}
                }

            elif action_type == "file_list":
                files = self.file_manager.list_files()
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"Found {len(files)} files in workspace.",
                    "data": {"files": files},
                    "visual_type": "file_tree"
                }

            elif action_type == "file_organize":
                success, msg = self.file_manager.organize_workspace()
                return {
                    "status": "SUCCESS" if success else "FAILED",
                    "success": success,
                    "message": msg,
                    "data": {}
                }

            # --- Multi-Step Workflow ---
            elif action_type == "workflow_plan":
                goal = params.get("goal", "Python")
                wf_res = self.workflow_agent.execute_python_resource_workflow(goal)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": wf_res["summary"],
                    "data": wf_res,
                    "visual_type": "workflow_card"
                }

            # --- Visual GUI Automation (VisualClicker) ---
            elif action_type == "visual_click":
                template_path = params.get("template_path", "")
                confidence = float(params.get("confidence", 0.8))
                clicks = int(params.get("clicks", 1))
                button = str(params.get("button", "left"))
                res = self.visual_clicker.find_and_click(template_path=template_path, confidence=confidence, clicks=clicks, button=button)
                return {
                    "status": "SUCCESS" if res.get("success") else "FAILED",
                    "success": res.get("success", False),
                    "message": res.get("message", ""),
                    "data": res,
                    "visual_type": "visual_action"
                }

            elif action_type == "visual_find":
                template_path = params.get("template_path", "")
                confidence = float(params.get("confidence", 0.8))
                res = self.visual_clicker.find_on_screen(template_path=template_path, confidence=confidence)
                return {
                    "status": "SUCCESS" if res.get("found") else "FAILED",
                    "success": res.get("found", False),
                    "message": res.get("message", ""),
                    "data": res,
                    "visual_type": "visual_action"
                }

            elif action_type == "visual_highlight":
                template_path = params.get("template_path", "")
                confidence = float(params.get("confidence", 0.8))
                out_path = params.get("output_path")
                res = self.visual_clicker.highlight_match(template_path=template_path, confidence=confidence, output_path=out_path)
                return {
                    "status": "SUCCESS" if res.get("found") else "FAILED",
                    "success": res.get("found", False),
                    "message": res.get("message", ""),
                    "data": res,
                    "visual_type": "visual_action"
                }

            elif action_type in ["email_list", "email_read", "email_recent"]:
                count = int(params.get("count", 10))
                emails = self.email_reader.get_recent_emails(count=count)
                if isinstance(emails, dict) and not emails.get("success", True):
                    return {
                        "status": "FAILED",
                        "success": False,
                        "message": emails.get("error", "Failed to retrieve Outlook emails."),
                        "data": emails
                    }
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"Retrieved {len(emails)} recent email(s) from Outlook.",
                    "data": {"emails": emails, "count": len(emails)},
                    "visual_type": "email_list"
                }

            elif action_type == "email_search":
                query = params.get("query", "")
                count = int(params.get("count", 10))
                emails = self.email_reader.search_emails(query=query, count=count)
                if isinstance(emails, dict) and not emails.get("success", True):
                    return {
                        "status": "FAILED",
                        "success": False,
                        "message": emails.get("error", f"Failed to search emails for '{query}'."),
                        "data": emails
                    }
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"Found {len(emails)} email(s) matching '{query}'.",
                    "data": {"emails": emails, "query": query, "count": len(emails)},
                    "visual_type": "email_list"
                }

            # --- Lock Screen ---
            elif action_type == "lock_screen":
                result = self.system_inspector.lock_screen()
                return {
                    "status": "SUCCESS" if result["success"] else "FAILED",
                    "success": result["success"],
                    "message": f"🔒 {result['message']}",
                    "data": result
                }

            # --- Sleep PC ---
            elif action_type == "sleep_pc":
                result = self.system_inspector.sleep_pc()
                return {
                    "status": "SUCCESS" if result["success"] else "FAILED",
                    "success": result["success"],
                    "message": f"😴 {result['message']}",
                    "data": result
                }

            # --- System Shutdown ---
            elif action_type == "system_shutdown":
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "30"], check=False)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": "⚠️ **System shutdown initiated.** The PC will shut down in 30 seconds. Run `shutdown /a` to cancel.",
                    "data": {}
                }

            # --- Process Kill ---
            elif action_type == "process_kill":
                import psutil
                target = params.get("process_name", "")
                killed = []
                for p in psutil.process_iter(['pid', 'name']):
                    try:
                        if target.lower() in p.info['name'].lower():
                            p.kill()
                            killed.append(p.info['name'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                return {
                    "status": "SUCCESS" if killed else "FAILED",
                    "success": bool(killed),
                    "message": f"Killed {len(killed)} process(es): {', '.join(killed)}" if killed else f"No processes matching '{target}' found.",
                    "data": {"killed": killed}
                }

            # --- Clear Memory ---
            elif action_type == "clear_memory":
                try:
                    self.supervision.memory.clear_history()
                    return {
                        "status": "SUCCESS",
                        "success": True,
                        "message": "🧹 **Conversation history cleared** from memory.",
                        "data": {}
                    }
                except Exception as e:
                    return {
                        "status": "FAILED",
                        "success": False,
                        "message": f"Failed to clear memory: {e}",
                        "data": {}
                    }

            # --- Python Sandbox ---
            elif action_type == "run_script":
                code = params.get("code", "")
                result = self.sandbox.execute_safe(code, timeout=10)
                return {
                    "status": "SUCCESS" if result["success"] else "FAILED",
                    "success": result["success"],
                    "message": f"🐍 **Python Sandbox Output:**\n```\n{result.get('stdout', result.get('stderr', ''))}\n```" if result["success"] else f"⚠️ **Sandbox Error:**\n{result.get('stderr', result.get('issues', ''))}",
                    "data": result
                }

            # --- LAN Scanner ---
            elif action_type == "lan_scan":
                devices = self.lan_scanner.scan_network()
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"📡 **Network Scan Complete** — Found {len(devices)} device(s) on your LAN.",
                    "data": {"devices": devices, "count": len(devices)},
                    "visual_type": "network_scan"
                }

            # --- Wake-on-LAN ---
            elif action_type == "wake_on_lan":
                mac = params.get("mac_address", "")
                result = self.wol.wake(mac)
                return {
                    "status": "SUCCESS" if result.get("success") else "FAILED",
                    "success": result.get("success", False),
                    "message": f"🔌 {result.get('message', '')}",
                    "data": result
                }

            # --- Macro Record ---
            elif action_type == "macro_record":
                name = params.get("name", "untitled")
                self.macro_engine.start_recording(name)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"🔴 **Recording Macro:** `{name}` — I am now recording your mouse and keyboard. Say 'stop recording' when done.",
                    "data": {"macro_name": name}
                }

            elif action_type == "macro_stop":
                result = self.macro_engine.stop_recording()
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"⏹️ **Macro Saved:** `{result.get('name', 'untitled')}` with {len(result.get('events', []))} events.",
                    "data": result
                }

            elif action_type == "macro_play":
                name = params.get("name", "")
                self.macro_engine.play_macro(name)
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"▶️ **Playing Macro:** `{name}`",
                    "data": {"macro_name": name}
                }

            elif action_type == "macro_list":
                macros = self.macro_engine.list_macros()
                return {
                    "status": "SUCCESS",
                    "success": True,
                    "message": f"📋 **Available Macros ({len(macros)}):**\n" + "\n".join(f"- `{m}`" for m in macros) if macros else "No macros recorded yet.",
                    "data": {"macros": macros}
                }

            else:
                return {
                    "status": "UNKNOWN_ACTION",
                    "success": False,
                    "message": f"Unrecognized action type: '{action_type}'",
                    "data": None
                }

        except Exception as e:
            return {
                "status": "EXECUTION_EXCEPTION",
                "success": False,
                "message": f"Action execution error: {str(e)}",
                "data": None
            }
