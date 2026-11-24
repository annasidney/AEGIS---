"""
AEGIS Python Sandbox
Provides isolated, AST-validated execution of Python code within the workspace sandbox.
"""

import os
import sys
import ast
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from aegis.config import WORKSPACE_DIR
except ImportError:
    # Fallback to relative workspace path if running standalone
    WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "workspace"


class _SandboxASTValidator(ast.NodeVisitor):
    """AST visitor to inspect code for forbidden modules, calls, and attributes."""

    def __init__(self) -> None:
        self.issues: List[str] = []
        self.imported_modules: Dict[str, str] = {}

        # Modules completely forbidden from being imported
        self.forbidden_modules = {
            "subprocess",
            "socket",
            "pty",
            "commands",
            "ctypes",
            "multiprocessing",
        }

        # Dangerous builtins / function calls forbidden from execution
        self.forbidden_calls = {
            "eval",
            "exec",
            "compile",
            "__import__",
        }

        # Specific functions forbidden when imported from modules
        self.forbidden_from_imports = {
            "os": {
                "system", "popen", "spawn", "spawnl", "spawnle", "spawnlp",
                "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
                "execl", "execle", "execlp", "execlpe", "execv", "execve",
                "execvp", "execvpe", "fork"
            },
            "shutil": {"rmtree"},
        }

        # Specific module.attribute calls that are forbidden
        self.forbidden_attributes = {
            ("os", "system"),
            ("os", "popen"),
            ("os", "spawnl"),
            ("os", "spawnle"),
            ("os", "spawnlp"),
            ("os", "spawnlpe"),
            ("os", "spawnv"),
            ("os", "spawnve"),
            ("os", "spawnvp"),
            ("os", "spawnvpe"),
            ("os", "execl"),
            ("os", "execle"),
            ("os", "execlp"),
            ("os", "execlpe"),
            ("os", "execv"),
            ("os", "execve"),
            ("os", "execvp"),
            ("os", "execvpe"),
            ("os", "fork"),
            ("shutil", "rmtree"),
        }

    def _add_issue(self, message: str) -> None:
        if message not in self.issues:
            self.issues.append(message)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            alias_name = alias.asname if alias.asname else alias.name
            self.imported_modules[alias_name] = alias.name

            if base_module in self.forbidden_modules:
                self._add_issue(f"Forbidden module import: '{alias.name}' (line {node.lineno})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        base_module = module.split(".")[0]

        if base_module in self.forbidden_modules:
            self._add_issue(f"Forbidden module import: '{module}' (line {node.lineno})")

        if base_module in self.forbidden_from_imports:
            forbidden_funcs = self.forbidden_from_imports[base_module]
            for alias in node.names:
                if alias.name in forbidden_funcs or alias.name == "*":
                    self._add_issue(f"Forbidden import: from '{module}' import '{alias.name}' (line {node.lineno})")

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct calls like eval() or exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_calls:
                self._add_issue(f"Forbidden function call: '{node.func.id}()' (line {node.lineno})")

        # Check attribute calls like os.system() or shutil.rmtree()
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                actual_mod = self.imported_modules.get(obj_name, obj_name).split(".")[0]
                attr = node.func.attr

                if (actual_mod, attr) in self.forbidden_attributes:
                    self._add_issue(f"Forbidden method call: '{actual_mod}.{attr}()' (line {node.lineno})")
                elif actual_mod in self.forbidden_modules:
                    self._add_issue(f"Forbidden module call: '{actual_mod}.{attr}()' (line {node.lineno})")

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in ("eval", "exec"):
            self._add_issue(f"Forbidden builtin reference: '{node.id}' (line {node.lineno})")
        self.generic_visit(node)


class PythonSandbox:
    """Executes Python code in an isolated subprocess with AST safety validation."""

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace = Path(workspace_path) if workspace_path else WORKSPACE_DIR
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[PythonSandbox Error] Failed to create workspace directory: {e}")

    def validate(self, code: str) -> Dict[str, Any]:
        """
        Parses and validates Python code using AST to detect dangerous imports and calls.

        Returns:
            Dict containing 'safe' (bool) and 'issues' (List[str]).
        """
        if not isinstance(code, str):
            return {
                "safe": False,
                "issues": ["Invalid input: code must be a string"]
            }

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "safe": False,
                "issues": [f"Syntax error on line {e.lineno}: {e.msg}"]
            }
        except Exception as e:
            print(f"[PythonSandbox Error] AST parse failure: {e}")
            return {
                "safe": False,
                "issues": [f"AST parsing error: {str(e)}"]
            }

        validator = _SandboxASTValidator()
        try:
            validator.visit(tree)
        except Exception as e:
            print(f"[PythonSandbox Error] AST traversal failure: {e}")
            return {
                "safe": False,
                "issues": [f"Validation error: {str(e)}"]
            }

        return {
            "safe": len(validator.issues) == 0,
            "issues": validator.issues
        }

    def execute(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Executes Python code string in a separate subprocess within the workspace sandbox.

        Steps:
        1. Write code to data/workspace/sandbox_tmp.py
        2. Execute via subprocess.run with timeout
        3. Clean up the temp file
        4. Return execution result dictionary

        Returns:
            Dict with 'success', 'stdout', 'stderr', 'return_code', and 'execution_time'.
        """
        if not isinstance(code, str):
            return {
                "success": False,
                "stdout": "",
                "stderr": "Invalid input: code must be a string",
                "return_code": -1,
                "execution_time": 0.0
            }

        temp_file = self.workspace / "sandbox_tmp.py"
        start_time = time.time()

        try:
            # 1. Write code to temp file
            self.workspace.mkdir(parents=True, exist_ok=True)
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(code)

            # 2. Execute via subprocess
            python_bin = sys.executable if sys.executable else "python"
            result = subprocess.run(
                [python_bin, str(temp_file)],
                capture_output=True,
                timeout=timeout,
                text=True,
                cwd=str(self.workspace)
            )

            execution_time = round(time.time() - start_time, 4)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": execution_time
            }

        except subprocess.TimeoutExpired as e:
            execution_time = round(time.time() - start_time, 4)
            print(f"[PythonSandbox Error] Execution timed out after {timeout} seconds")
            stdout_str = e.stdout if isinstance(e.stdout, str) and e.stdout else ""
            return {
                "success": False,
                "stdout": stdout_str,
                "stderr": f"Execution timed out after {timeout} seconds.",
                "return_code": -1,
                "execution_time": execution_time
            }
        except Exception as e:
            execution_time = round(time.time() - start_time, 4) if 'start_time' in locals() else 0.0
            print(f"[PythonSandbox Error] Execution error: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time
            }
        finally:
            # 3. Clean up temp file
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as cleanup_err:
                    print(f"[PythonSandbox Error] Cleanup error for '{temp_file}': {cleanup_err}")

    def execute_safe(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Validates code safety via AST analysis, then executes only if safe.

        Returns:
            Dict containing execution results and validation state.
        """
        validation = self.validate(code)
        if not validation.get("safe", False):
            issues = validation.get("issues", [])
            issues_str = "; ".join(issues)
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Safety validation failed: {issues_str}",
                "return_code": -1,
                "execution_time": 0.0,
                "issues": issues,
                "validation": validation
            }

        return self.execute(code, timeout=timeout)


if __name__ == "__main__":
    print("--- Testing PythonSandbox ---")
    sandbox = PythonSandbox()

    # 1. Test execute with print(2+2)
    print("\n[Test 1] Executing: print(2+2)")
    result = sandbox.execute("print(2+2)")
    print(f"Success: {result['success']}")
    print(f"Stdout: {result['stdout'].strip()}")
    print(f"Execution Time: {result['execution_time']}s")
    assert result["success"] is True
    assert result["stdout"].strip() == "4"

    # 2. Test safe execution
    print("\n[Test 2] Safe Execution: print('AEGIS Sandbox Active')")
    safe_result = sandbox.execute_safe("print('AEGIS Sandbox Active')")
    print(f"Safe Execution Success: {safe_result['success']}")
    print(f"Stdout: {safe_result['stdout'].strip()}")
    assert safe_result["success"] is True

    # 3. Test validation blocking dangerous code
    print("\n[Test 3] Validating dangerous imports and calls")
    dangerous_code_samples = [
        "import os\nos.system('dir')",
        "import subprocess\nsubprocess.run(['cmd'])",
        "from shutil import rmtree\nrmtree('data')",
        "eval('2 + 2')",
        "exec('print(123)')"
    ]
    for code_sample in dangerous_code_samples:
        val = sandbox.validate(code_sample)
        print(f"Code: {repr(code_sample)} -> Safe: {val['safe']}, Issues: {val['issues']}")
        assert val["safe"] is False

    # 4. Test execute_safe refusal on dangerous code
    print("\n[Test 4] execute_safe refusing dangerous code")
    blocked_result = sandbox.execute_safe("import os\nos.system('calc')")
    print(f"Blocked Success: {blocked_result['success']}")
    print(f"Stderr: {blocked_result['stderr']}")
    assert blocked_result["success"] is False

    print("\nAll PythonSandbox tests passed successfully!")
