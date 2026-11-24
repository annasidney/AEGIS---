"""
AEGIS File Manager
Executes sandboxed file operations within the dedicated workspace directory.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple
from aegis.config import WORKSPACE_DIR
from aegis.supervision.safety_checker import SafetyChecker

class FileManager:
    """Manages files and directories in a safe, sandboxed workspace."""

    def __init__(self, workspace_path: Path = WORKSPACE_DIR):
        self.workspace = workspace_path
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, filename: str) -> Path:
        """Resolves target path and ensures it does not escape the workspace sandbox."""
        # 1. Check for directory traversal attempts before sanitization
        if ".." in filename:
            resolved_raw = (self.workspace / filename).resolve()
            if not str(resolved_raw).startswith(str(self.workspace.resolve())):
                raise PermissionError(f"Security Alert: Path '{resolved_raw}' attempts to escape sandbox boundary '{self.workspace}'")

        # 2. Sanitize and construct final resolved path
        clean_name = SafetyChecker.sanitize_filename(filename)
        target = (self.workspace / clean_name).resolve()
        if not str(target).startswith(str(self.workspace.resolve())):
            raise PermissionError(f"Security Alert: Path '{target}' attempts to escape sandbox boundary '{self.workspace}'")
        return target

    def create_file(self, filename: str, content: str, overwrite: bool = False) -> Tuple[bool, str]:
        """Creates a file with content in the workspace."""
        try:
            target = self._resolve_safe_path(filename)
            if target.exists() and not overwrite:
                return False, f"File '{target.name}' already exists. Overwrite permission required."

            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return True, f"File '{target.name}' created successfully in workspace ({len(content)} bytes)."
        except Exception as e:
            return False, f"File creation error: {str(e)}"

    def read_file(self, filename: str) -> Tuple[bool, str]:
        """Reads contents of a file in the workspace."""
        try:
            target = self._resolve_safe_path(filename)
            if not target.exists():
                return False, f"File '{filename}' not found in workspace."

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            return True, content
        except Exception as e:
            return False, f"File read error: {str(e)}"

    def delete_file(self, filename: str) -> Tuple[bool, str]:
        """Deletes a file or directory from the workspace (Consequential operation)."""
        try:
            target = self._resolve_safe_path(filename)
            if not target.exists():
                return False, f"Cannot delete '{filename}': Target does not exist."

            if target.is_dir():
                shutil.rmtree(target)
                return True, f"Directory '{target.name}' permanently deleted."
            else:
                target.unlink()
                return True, f"File '{target.name}' permanently deleted."
        except Exception as e:
            return False, f"File deletion error: {str(e)}"

    def list_files(self) -> List[Dict[str, Any]]:
        """Lists all files and directories in the workspace."""
        results = []
        try:
            for item in self.workspace.glob("**/*"):
                if item.is_file():
                    rel_path = item.relative_to(self.workspace)
                    size = item.stat().st_size
                    results.append({
                        "name": item.name,
                        "path": str(rel_path),
                        "size": size,
                        "extension": item.suffix.lower()
                    })
        except Exception as e:
            print(f"[FileManager Error] list_files failed: {e}")
        return results

    def organize_workspace(self) -> Tuple[bool, str]:
        """Organizes miscellaneous workspace files into structured subfolders by type."""
        category_map = {
            "documents": [".txt", ".md", ".pdf", ".docx", ".doc"],
            "code": [".py", ".js", ".html", ".css", ".json", ".sql", ".sh"],
            "data": [".csv", ".tsv", ".xlsx", ".xml"],
            "media": [".png", ".jpg", ".jpeg", ".mp3", ".wav"]
        }
        moved_count = 0
        try:
            for item in list(self.workspace.iterdir()):
                if item.is_file():
                    ext = item.suffix.lower()
                    dest_folder = "misc"
                    for cat, exts in category_map.items():
                        if ext in exts:
                            dest_folder = cat
                            break

                    target_dir = self.workspace / dest_folder
                    target_dir.mkdir(exist_ok=True)
                    shutil.move(str(item), str(target_dir / item.name))
                    moved_count += 1

            return True, f"Organized {moved_count} files into structured workspace folders (documents/, code/, data/, misc/)."
        except Exception as e:
            return False, f"Failed to organize workspace: {str(e)}"
