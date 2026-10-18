import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from copilot.generated.session_events import PermissionRequestKind
from copilot.session import PermissionRequest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from running_coach.mcp_config import (
    MCP_SERVERS,
    ZEPP_TOOL_NAMES,
    build_mcp_servers,
    reject_unapproved_tool_permission,
)
from running_coach.mcp_server import MCP_TOOL_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def call_server_tools() -> tuple[list[str], str, str, bool]:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "running_coach.mcp_server"],
        env=os.environ.copy(),
        cwd=PROJECT_ROOT,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed_tools = await session.list_tools()
            pace = await session.call_tool(
                "calculate_running_pace",
                {"distance_km": 5, "duration_minutes": 25},
            )
            finish = await session.call_tool(
                "estimate_finish_time",
                {"distance_km": 10, "pace_seconds_per_km": 330},
            )
            invalid = await session.call_tool(
                "calculate_running_pace",
                {"distance_km": 0, "duration_minutes": 25},
            )
            return (
                [tool.name for tool in listed_tools.tools],
                pace.content[0].text,
                finish.content[0].text,
                invalid.isError,
            )


class MCPToolsTests(unittest.TestCase):
    def test_tools_work_over_stdio_and_reject_invalid_arguments(self) -> None:
        tools, pace, finish, invalid_is_error = asyncio.run(call_server_tools())

        self.assertEqual(set(tools), set(MCP_TOOL_NAMES))
        self.assertIn("Ritmo medio: 5:00 min/km", pace)
        self.assertIn("Velocidad media: 12.00 km/h", pace)
        self.assertIn("00:55:00", finish)
        self.assertTrue(invalid_is_error)

    def test_copilot_only_connects_to_the_local_calculation_server(self) -> None:
        config = MCP_SERVERS["running-coach"]

        self.assertEqual(config["command"], sys.executable)
        self.assertEqual(config["args"], ["-m", "running_coach.mcp_server"])
        self.assertEqual(set(config["tools"]), set(MCP_TOOL_NAMES))

    def test_mcp_permissions_are_limited_to_our_calculation_tools(self) -> None:
        allowed = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="running-coach",
            tool_name="calculate_running_pace",
        )
        allowed_zepp = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="zepp",
            tool_name="zepp_body_composition",
        )
        unknown_tool = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="running-coach",
            tool_name="other_tool",
        )
        other_server = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="other-server",
            tool_name="calculate_running_pace",
        )
        raw_zepp_request = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="zepp",
            tool_name="zepp_raw_request",
        )
        gps_workout_detail = PermissionRequest(
            kind=PermissionRequestKind.MCP,
            server_name="zepp",
            tool_name="zepp_workout_detail",
        )
        shell_request = PermissionRequest(kind=PermissionRequestKind.SHELL)

        self.assertEqual(reject_unapproved_tool_permission(allowed, {}).kind, "approve-once")
        self.assertEqual(
            reject_unapproved_tool_permission(allowed_zepp, {}).kind,
            "approve-once",
        )
        self.assertEqual(
            reject_unapproved_tool_permission(unknown_tool, {}).kind,
            "reject",
        )
        self.assertEqual(
            reject_unapproved_tool_permission(other_server, {}).kind,
            "reject",
        )
        self.assertEqual(
            reject_unapproved_tool_permission(raw_zepp_request, {}).kind,
            "reject",
        )
        self.assertEqual(
            reject_unapproved_tool_permission(gps_workout_detail, {}).kind,
            "reject",
        )
        self.assertEqual(
            reject_unapproved_tool_permission(shell_request, {}).kind,
            "reject",
        )

    def test_zepp_checkout_uses_its_own_locked_uv_environment_and_tool_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as checkout:
            Path(checkout, "pyproject.toml").touch()
            expected_root = Path(checkout).resolve()
            with patch.dict(
                os.environ,
                {"PATH": "safe-path", "GH_TOKEN": "must-not-be-forwarded"},
                clear=True,
            ):
                servers = build_mcp_servers(checkout, uv_executable="uv")

        zepp_config = servers["zepp"]
        self.assertEqual(zepp_config["command"], "uv")
        self.assertEqual(
            zepp_config["args"],
            [
                "run",
                "--locked",
                "--directory",
                str(expected_root),
                "zepp-mcp",
            ],
        )
        self.assertEqual(set(zepp_config["tools"]), set(ZEPP_TOOL_NAMES))
        self.assertEqual(zepp_config["env"], {"PATH": "safe-path"})
        self.assertNotIn("zepp_raw_request", ZEPP_TOOL_NAMES)
        self.assertNotIn("zepp_workout_detail", ZEPP_TOOL_NAMES)

    def test_invalid_zepp_checkout_path_is_reported(self) -> None:
        with self.assertRaisesRegex(ValueError, "ZEPP_MCP_PATH"):
            build_mcp_servers("missing-zepp-checkout", uv_executable="uv")


if __name__ == "__main__":
    unittest.main()
