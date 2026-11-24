"""
AEGIS App Launcher
Safely launches registered desktop applications and websites on Windows using native ShellExecute.
"""

import os
import subprocess
import webbrowser
from typing import Dict, Any, Tuple
from aegis.config import ALLOWED_APPLICATIONS

class AppLauncher:
    """Controls execution of pre-registered safe desktop applications and websites."""

    @staticmethod
    def launch(app_id: str, extra_args: str = "") -> Tuple[bool, str]:
        """
        Launches an application by registered ID (e.g., 'notepad', 'calculator', 'explorer', 'terminal', 'vscode', 'browser').
        Uses os.startfile() on Windows for foreground execution.
        """
        app_id_clean = app_id.lower().replace("app_launch_", "").strip()

        # Direct URL or browser target
        if app_id_clean.startswith("http://") or app_id_clean.startswith("https://") or "www." in app_id_clean:
            url = app_id_clean if app_id_clean.startswith("http") else f"https://{app_id_clean}"
            if os.name == 'nt' and hasattr(os, 'startfile'):
                os.startfile(url)
            else:
                webbrowser.open(url)
            return True, f"Opened URL in default browser: {url}"

        app_info = ALLOWED_APPLICATIONS.get(app_id_clean)
        if not app_info:
            return False, f"Application '{app_id}' is not in the authorized application registry."

        cmd = app_info["command"]
        try:
            if app_id_clean == "browser":
                target = extra_args if extra_args else "https://google.com"
                if os.name == 'nt' and hasattr(os, 'startfile'):
                    os.startfile(target)
                else:
                    webbrowser.open(target)
                return True, f"Launched web browser for: {target}"

            if os.name == 'nt' and hasattr(os, 'startfile') and not extra_args:
                try:
                    os.startfile(cmd)
                    return True, f"Successfully launched {app_info['name']} (`{cmd}`)."
                except Exception:
                    pass

            # Fallback to subprocess
            full_cmd = f"{cmd} {extra_args}" if extra_args else cmd
            subprocess.Popen(
                full_cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            return True, f"Successfully launched {app_info['name']} (`{cmd}`)."

        except Exception as e:
            return False, f"Failed to launch application {app_info['name']}: {str(e)}"
