import subprocess
from typing import Any

from app.schemas.agent import RiskLevel
from app.services.agent.tools.base import ToolResult

SAFE_COMMANDS = {"ls", "cat", "head", "tail", "wc", "du", "df", "date", "whoami", "pwd", "echo", "find", "grep"}
BLOCKED_COMMANDS = {"rm", "sudo", "chmod", "chown", "mkfs", "dd", "curl", "wget"}
MAX_TIMEOUT = 30


class ShellTool:
    name = "shell"
    description = "Execute shell commands with restrictions"

    def risk_for(self, action: str, args: dict[str, Any]) -> RiskLevel:
        command = args.get("command", "")
        first_word = command.strip().split()[0] if command.strip() else ""
        if first_word in BLOCKED_COMMANDS:
            return RiskLevel.HIGH
        if first_word in SAFE_COMMANDS:
            return RiskLevel.LOW
        return RiskLevel.HIGH

    def execute(self, action: str, args: dict[str, Any]) -> ToolResult:
        command = args.get("command", "")
        timeout = min(args.get("timeout", 10), MAX_TIMEOUT)
        first_word = command.strip().split()[0] if command.strip() else ""
        if first_word in BLOCKED_COMMANDS:
            return ToolResult(success=False, error=f"Command '{first_word}' is blocked")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=args.get("cwd"),
            )
            return ToolResult(
                success=result.returncode == 0,
                output={
                    "stdout": result.stdout[:10000],
                    "stderr": result.stderr[:2000],
                    "returncode": result.returncode,
                },
                error=result.stderr[:500] if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def list_actions(self) -> list[dict[str, str]]:
        return [{"action": "run", "description": "Run a shell command"}]
