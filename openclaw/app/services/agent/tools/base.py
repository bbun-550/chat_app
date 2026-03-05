from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.agent import RiskLevel


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str

    def risk_for(self, action: str, args: dict[str, Any]) -> RiskLevel: ...

    def execute(self, action: str, args: dict[str, Any]) -> ToolResult: ...

    def list_actions(self) -> list[dict[str, str]]: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def list_all_actions(self) -> list[dict[str, str]]:
        actions = []
        for tool in self._tools.values():
            for action in tool.list_actions():
                actions.append({"tool": tool.name, **action})
        return actions
