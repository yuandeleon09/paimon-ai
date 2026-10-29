import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List
from app.safety import validate_safe_path

# Allowlist of safe command prefixes
ALLOWED_COMMAND_PREFIXES = [
    "pytest",
    "python -m pytest",
    "python -m unittest",
    "python -m py_compile",
    "py -m pytest",
    "py -m unittest",
    "py -m py_compile",
]

def run_bounded_test(
    command: str,
    workspace_dir: Path,
    enabled: bool = False,
    timeout_seconds: int = 15
) -> Dict[str, Any]:
    """
    Executes a bounded, allowlisted test command inside the authorized workspace directory.
    If testing is disabled or command is not allowlisted, returns NOT RUN without executing.
    """
    if not enabled:
        return {
            "executed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "NOT RUN: Tool execution not authorized by configuration.",
            "status": "NOT_RUN"
        }

    cmd_stripped = command.strip()
    is_allowed = any(cmd_stripped.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES)
    if not is_allowed:
        return {
            "executed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"BLOCKED: Command '{cmd_stripped}' is not in the permitted allowlist.",
            "status": "BLOCKED"
        }

    if not validate_safe_path(workspace_dir, workspace_dir.parent):
        return {
            "executed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "BLOCKED: Invalid workspace directory.",
            "status": "BLOCKED"
        }

    workspace_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Use virtual environment python if available
        venv_py = sys.executable
        resolved_cmd = cmd_stripped
        if resolved_cmd.startswith("python "):
            resolved_cmd = f'"{venv_py}" ' + resolved_cmd[len("python "):]
        elif resolved_cmd.startswith("pytest"):
            resolved_cmd = f'"{venv_py}" -m pytest' + resolved_cmd[len("pytest"):]

        proc = subprocess.run(
            resolved_cmd,
            cwd=str(workspace_dir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )

        status = "PASSED" if proc.returncode == 0 else "FAILED"
        return {
            "executed": True,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:2000],  # bounded output
            "stderr": proc.stderr[:2000],
            "status": status
        }
    except subprocess.TimeoutExpired:
        return {
            "executed": True,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"TIMEOUT: Command exceeded maximum allowed duration of {timeout_seconds}s.",
            "status": "FAILED"
        }
    except Exception as e:
        return {
            "executed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"ERROR: Execution failure: {str(e)}",
            "status": "BLOCKED"
        }
