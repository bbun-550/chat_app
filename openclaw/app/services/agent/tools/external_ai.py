import subprocess
from typing import Any

from app.schemas.agent import RiskLevel
from app.services.agent.tools.base import ToolResult

ALLOWED_CLIS = {"claude", "codex"}
MAX_TIMEOUT = 120


class ExternalAITool:
    name = "external_ai"
    description = "Call external AI CLI tools (claude, codex)"

    def risk_for(self, action: str, args: dict[str, Any]) -> RiskLevel:
        return RiskLevel.MEDIUM

    def execute(self, action: str, args: dict[str, Any]) -> ToolResult:
        cli = args.get("cli", "")
        if cli not in ALLOWED_CLIS:
            return ToolResult(success=False, error=f"CLI '{cli}' not allowed. Allowed: {ALLOWED_CLIS}")
        prompt = args.get("prompt", "")
        try:
            cmd = [cli, prompt] if cli == "claude" else [cli, "--prompt", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_TIMEOUT)
            return ToolResult(
                success=result.returncode == 0,
                output={"response": result.stdout[:20000]},
                error=result.stderr[:500] if result.returncode != 0 else None,
            )
        except FileNotFoundError:
            return ToolResult(success=False, error=f"CLI '{cli}' not found on system")
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"CLI call timed out after {MAX_TIMEOUT}s")

    def list_actions(self) -> list[dict[str, str]]:
        return [{"action": "call", "description": "Call an external AI CLI with a prompt"}]
