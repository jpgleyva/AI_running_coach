"""Configuración y permisos de los servidores MCP del coach."""

import os
import shutil
import sys
from pathlib import Path

from copilot.generated.session_events import PermissionRequestKind
from copilot.session import (
    MCPServerConfig,
    PermissionRequest,
    PermissionRequestResult,
)

from running_coach.mcp_server import MCP_TOOL_NAMES

ZEPP_SERVER_NAME = "zepp"
ZEPP_TOOL_NAMES = (
    "zepp_daily_summary",
    "zepp_sleep",
    "zepp_heart_rate",
    "zepp_list_workouts",
    "zepp_training_thresholds",
    "zepp_body_composition",
)
_ZEPP_ENV_ALLOWLIST = (
    "PATH",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
)

MCP_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "running-coach": frozenset(MCP_TOOL_NAMES),
    ZEPP_SERVER_NAME: frozenset(ZEPP_TOOL_NAMES),
}


def build_mcp_servers(
    zepp_mcp_path: str | None = None,
    uv_executable: str | None = None,
) -> dict[str, MCPServerConfig]:
    """Configure local calculators and, optionally, an isolated Zepp MCP checkout."""
    servers: dict[str, MCPServerConfig] = {
        "running-coach": {
            "type": "stdio",
            "command": sys.executable,
            "args": ["-m", "running_coach.mcp_server"],
            "tools": list(MCP_TOOL_NAMES),
            "timeout": 30000,
        }
    }
    if not zepp_mcp_path:
        return servers

    zepp_root = Path(zepp_mcp_path).expanduser().resolve()
    if not zepp_root.is_dir() or not (zepp_root / "pyproject.toml").is_file():
        raise ValueError(
            "ZEPP_MCP_PATH debe apuntar a un checkout local de zepp-mcp "
            "que contenga pyproject.toml."
        )

    uv = uv_executable or shutil.which("uv")
    if not uv:
        raise RuntimeError(
            "ZEPP_MCP_PATH está configurado, pero no se encontró uv en PATH."
        )

    servers[ZEPP_SERVER_NAME] = {
        "type": "stdio",
        "command": uv,
        "args": [
            "run",
            "--locked",
            "--directory",
            str(zepp_root),
            "zepp-mcp",
        ],
        "env": {
            name: os.environ[name]
            for name in _ZEPP_ENV_ALLOWLIST
            if name in os.environ
        },
        "tools": list(ZEPP_TOOL_NAMES),
        "timeout": 60000,
    }
    return servers


def reject_unapproved_tool_permission(
    request: PermissionRequest,
    _invocation: dict[str, str],
) -> PermissionRequestResult:
    """Approve only named tools on the explicitly configured local MCP servers."""
    allowed_tools = MCP_TOOL_ALLOWLIST.get(request.server_name or "")
    if (
        request.kind is PermissionRequestKind.MCP
        and allowed_tools is not None
        and request.tool_name in allowed_tools
    ):
        return PermissionRequestResult(kind="approve-once")
    return PermissionRequestResult(kind="reject")


MCP_SERVERS = build_mcp_servers(os.environ.get("ZEPP_MCP_PATH"))
