"""
AEGIS Action Engine Module
Executes authorized tools, system utilities, file operations, blueprints, and multi-step workflows.
"""

from aegis.actions.app_launcher import AppLauncher
from aegis.actions.file_manager import FileManager
from aegis.actions.web_search import WebSearchEngine
from aegis.actions.system_ops import SystemInspector
from aegis.actions.blueprint_gen import BlueprintGenerator
from aegis.actions.workflow_agent import WorkflowAgent
from aegis.actions.visual_clicker import VisualClicker
from aegis.actions.email_reader import OutlookReader
from aegis.actions.sandbox import PythonSandbox
from aegis.actions.web_archiver import WebArchiver
from aegis.actions.network_tools import LANScanner, WakeOnLAN
from aegis.actions.macro_engine import MacroEngine
from aegis.actions.action_engine import ActionEngine

__all__ = [
    "AppLauncher", "FileManager", "WebSearchEngine",
    "SystemInspector", "BlueprintGenerator", "WorkflowAgent",
    "VisualClicker", "OutlookReader", "PythonSandbox", "WebArchiver",
    "LANScanner", "WakeOnLAN", "MacroEngine", "ActionEngine"
]
