import asyncio
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import AsyncMock

from running_coach.cli import close_session, handle_memory_command
from running_coach.memory import SessionMemory, build_user_prompt


class SessionMemoryTests(unittest.TestCase):
    def test_remembered_profile_is_validated_and_rendered(self) -> None:
        memory = SessionMemory()
        memory.remember(" objetivo ", "  correr 10 km  ")

        self.assertEqual(memory.values, {"objetivo": "correr 10 km"})
        self.assertIn(
            '"objetivo": "correr 10 km"',
            build_user_prompt("Sugiere una sesión", memory),
        )

    def test_invalid_fields_and_sensitive_values_are_rejected(self) -> None:
        memory = SessionMemory()

        with self.assertRaisesRegex(ValueError, "Campo desconocido"):
            memory.remember("historial médico", "dolor")
        with self.assertRaisesRegex(ValueError, "credenciales"):
            memory.remember("preferencias", "mi correo es runner@example.com")
        with self.assertRaisesRegex(ValueError, "credenciales"):
            memory.remember("preferencias", "mi Zepp password es secreto")
        with self.assertRaisesRegex(ValueError, "160 caracteres"):
            memory.remember("objetivo", "x" * 161)

    def test_empty_snapshot_clears_previous_profile_context(self) -> None:
        memory = SessionMemory()
        memory.remember("objetivo", "correr 10 km")
        memory.forget("objetivo")

        prompt = build_user_prompt("¿Qué recomiendas?", memory)

        self.assertIn("sustituye cualquier perfil temporal anterior", prompt)
        self.assertIn("{}", prompt)
        self.assertNotIn("correr 10 km", prompt)

    def test_memory_command_saves_only_after_confirmation(self) -> None:
        memory = SessionMemory()
        output = io.StringIO()

        with redirect_stdout(output):
            handled = handle_memory_command(
                "/recordar unidades=km",
                memory,
                input_fn=lambda _: "s",
            )

        self.assertTrue(handled)
        self.assertEqual(memory.values, {"unidades": "km"})
        self.assertIn("Guardado temporalmente", output.getvalue())

    def test_memory_command_does_not_save_without_confirmation(self) -> None:
        memory = SessionMemory()
        output = io.StringIO()

        with redirect_stdout(output):
            handle_memory_command(
                "/recordar objetivo=correr 10 km",
                memory,
                input_fn=lambda _: "n",
            )

        self.assertEqual(memory.values, {})
        self.assertIn("No se guardó", output.getvalue())

    def test_forget_requires_confirmation_and_clear_removes_profile(self) -> None:
        memory = SessionMemory()
        memory.remember("objetivo", "correr 10 km")
        memory.remember("unidades", "km")

        with redirect_stdout(io.StringIO()):
            handle_memory_command(
                "/olvidar objetivo",
                memory,
                input_fn=lambda _: "s",
            )
            handle_memory_command(
                "/olvidar-todo",
                memory,
                input_fn=lambda _: "s",
            )

        self.assertEqual(memory.values, {})


class SessionCleanupTests(unittest.TestCase):
    def test_close_deletes_copilot_session_after_disconnect(self) -> None:
        session = type("Session", (), {"session_id": "session-1"})()
        session.disconnect = AsyncMock()
        client = type("Client", (), {})()
        client.delete_session = AsyncMock()

        asyncio.run(close_session(client, session))

        session.disconnect.assert_awaited_once()
        client.delete_session.assert_awaited_once_with("session-1")


if __name__ == "__main__":
    unittest.main()
