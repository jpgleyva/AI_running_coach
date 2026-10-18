import unittest

from running_coach.cli import SYSTEM_PROMPT


class SystemPromptTests(unittest.TestCase):
    def test_includes_user_profile_and_safety_boundaries(self) -> None:
        self.assertIn("Corre 2-3 veces por semana", SYSTEM_PROMPT)
        self.assertIn("rodilla derecha", SYSTEM_PROMPT)
        self.assertIn("No diagnostiques lesiones", SYSTEM_PROMPT)
        self.assertIn("No prometas reducción localizada de grasa", SYSTEM_PROMPT)
        self.assertIn("no hay integraciones", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
