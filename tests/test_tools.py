import asyncio
import unittest

from copilot.tools import ToolInvocation

from running_coach.tools import COACH_TOOLS


class CoachToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = {tool.name: tool for tool in COACH_TOOLS}

    def test_tools_are_registered_as_local_calculations(self) -> None:
        self.assertEqual(
            set(self.tools),
            {"calculate_running_pace", "estimate_finish_time"},
        )
        self.assertTrue(all(tool.skip_permission for tool in self.tools.values()))
        self.assertTrue(all(tool.parameters for tool in self.tools.values()))

    def test_calculate_running_pace(self) -> None:
        result = asyncio.run(
            self.tools["calculate_running_pace"].handler(
                ToolInvocation(
                    arguments={"distance_km": 5, "duration_minutes": 25},
                )
            )
        )

        self.assertEqual(
            result.text_result_for_llm,
            "Ritmo medio: 5:00 min/km. Velocidad media: 12.00 km/h.",
        )
        self.assertEqual(result.result_type, "success")

    def test_estimate_finish_time(self) -> None:
        result = asyncio.run(
            self.tools["estimate_finish_time"].handler(
                ToolInvocation(
                    arguments={"distance_km": 10, "pace_seconds_per_km": 330},
                )
            )
        )

        self.assertEqual(
            result.text_result_for_llm,
            "Tiempo estimado a 5:30 min/km para 10 km: 00:55:00 "
            "(hh:mm:ss), suponiendo un ritmo constante.",
        )
        self.assertEqual(result.result_type, "success")

    def test_invalid_tool_arguments_are_rejected(self) -> None:
        result = asyncio.run(
            self.tools["calculate_running_pace"].handler(
                ToolInvocation(
                    arguments={"distance_km": 0, "duration_minutes": 25},
                )
            )
        )

        self.assertEqual(result.result_type, "failure")
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
