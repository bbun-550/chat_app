import os
import shutil
from pathlib import Path
from typing import Any

from app.schemas.agent import RiskLevel
from app.services.agent.tools.base import ToolResult

ALLOWED_PATHS: list[str] = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
]

ACTIONS = {
    "read_file": {"description": "Read contents of a file", "risk": RiskLevel.LOW},
    "list_directory": {"description": "List files in a directory", "risk": RiskLevel.LOW},
    "create_directory": {"description": "Create a new directory", "risk": RiskLevel.MEDIUM},
    "write_file": {"description": "Write content to a file", "risk": RiskLevel.MEDIUM},
    "move_file": {"description": "Move or rename a file", "risk": RiskLevel.MEDIUM},
    "delete_file": {"description": "Delete a file or directory", "risk": RiskLevel.HIGH},
}


class FilesystemTool:
    name = "filesystem"
    description = "Read, write, move, and manage files and directories"

    def _validate_path(self, path_str: str) -> Path:
        resolved = Path(path_str).expanduser().resolve()
        for allowed in ALLOWED_PATHS:
            if str(resolved).startswith(str(Path(allowed).resolve())):
                return resolved
        raise PermissionError(f"Path {resolved} is outside allowed directories")

    def risk_for(self, action: str, args: dict[str, Any]) -> RiskLevel:
        if action not in ACTIONS:
            return RiskLevel.HIGH
        return ACTIONS[action]["risk"]

    def execute(self, action: str, args: dict[str, Any]) -> ToolResult:
        try:
            handler = getattr(self, f"_do_{action}", None)
            if handler is None:
                return ToolResult(success=False, error=f"Unknown action: {action}")
            return handler(args)
        except PermissionError as e:
            return ToolResult(success=False, error=f"Permission denied: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def list_actions(self) -> list[dict[str, str]]:
        return [{"action": k, "description": v["description"]} for k, v in ACTIONS.items()]

    def _do_read_file(self, args: dict) -> ToolResult:
        path = self._validate_path(args["path"])
        content = path.read_text(encoding="utf-8")
        return ToolResult(success=True, output={"content": content, "size": len(content)})

    def _do_list_directory(self, args: dict) -> ToolResult:
        path = self._validate_path(args["path"])
        entries = []
        for item in sorted(path.iterdir()):
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
            })
        return ToolResult(success=True, output={"path": str(path), "entries": entries})

    def _do_create_directory(self, args: dict) -> ToolResult:
        path = self._validate_path(args["path"])
        path.mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, output={"created": str(path)})

    def _do_write_file(self, args: dict) -> ToolResult:
        path = self._validate_path(args["path"])
        path.write_text(args["content"], encoding="utf-8")
        return ToolResult(success=True, output={"written": str(path), "size": len(args["content"])})

    def _do_move_file(self, args: dict) -> ToolResult:
        src = self._validate_path(args["source"])
        dst = self._validate_path(args["destination"])
        shutil.move(str(src), str(dst))
        return ToolResult(success=True, output={"moved": str(src), "to": str(dst)})

    def _do_delete_file(self, args: dict) -> ToolResult:
        path = self._validate_path(args["path"])
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return ToolResult(success=True, output={"deleted": str(path)})
