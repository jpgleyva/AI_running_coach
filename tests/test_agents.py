import unittest

from running_coach.agents import build_custom_agents
from running_coach.mcp_config import ZEPP_TOOL_NAMES
from running_coach.mcp_server import MCP_TOOL_NAMES


class CustomAgentTests(unittest.TestCase):
    def test_specialists_are_available_for_model_inference(self) -> None:
        agents = build_custom_agents()

        self.assertEqual(
            [agent["name"] for agent in agents],
            [
                "running_training_specialist",
                "nutrition_specialist",
                "recovery_safety_specialist",
            ],
        )
        self.assertTrue(all(agent["infer"] for agent in agents))
        for agent in agents:
            self.assertIn("sin diagnosticar lesiones", agent["prompt"])
            self.assertIn("corre 2-3 veces por semana", agent["prompt"])

    def test_mcp_tools_are_limited_to_each_specialist_domain(self) -> None:
        servers = {
            "running-coach": {
                "type": "stdio",
                "command": "python",
                "args": ["-m", "running_coach.mcp_server"],
                "tools": list(MCP_TOOL_NAMES),
            },
            "zepp": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "zepp-mcp"],
                "tools": list(ZEPP_TOOL_NAMES),
            },
        }

        agents = {agent["name"]: agent for agent in build_custom_agents(servers)}

        self.assertEqual(
            set(
                agents["running_training_specialist"]["mcp_servers"][
                    "running-coach"
                ]["tools"]
            ),
            set(MCP_TOOL_NAMES),
        )
        self.assertEqual(
            set(
                agents["running_training_specialist"]["mcp_servers"]["zepp"][
                    "tools"
                ]
            ),
            {
                "zepp_daily_summary",
                "zepp_list_workouts",
                "zepp_training_thresholds",
            },
        )
        self.assertNotIn(
            "running-coach",
            agents["recovery_safety_specialist"]["mcp_servers"],
        )
        self.assertEqual(
            set(
                agents["recovery_safety_specialist"]["mcp_servers"]["zepp"][
                    "tools"
                ]
            ),
            {
                "zepp_daily_summary",
                "zepp_sleep",
                "zepp_heart_rate",
                "zepp_list_workouts",
            },
        )
        self.assertEqual(
            set(
                agents["nutrition_specialist"]["mcp_servers"]["zepp"]["tools"]
            ),
            {"zepp_body_composition"},
        )

    def test_zepp_specialists_keep_working_without_zepp_configuration(self) -> None:
        agents = build_custom_agents(
            {
                "running-coach": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "running_coach.mcp_server"],
                    "tools": list(MCP_TOOL_NAMES),
                }
            }
        )

        for agent in agents:
            self.assertNotIn("zepp", agent.get("mcp_servers", {}))


if __name__ == "__main__":
    unittest.main()
