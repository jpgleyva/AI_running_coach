import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from a2a.helpers import new_text_message
from a2a.types import AgentInterface, AgentSkill, Role, TaskState
from copilot.generated.session_events import AssistantMessageData
from starlette.applications import Starlette

from running_coach.a2a_server import (
    A2A_HOST,
    A2A_PORT,
    A2A_SYSTEM_PROMPT,
    MAX_QUERY_LENGTH,
    RunningCoachExecutor,
    build_agent_card,
    build_app,
    generate_coach_response,
)
from running_coach.agents import build_custom_agents


async def send_http_request(
    app: Starlette,
    path: str,
    payload: dict[str, object] | None = None,
) -> httpx.Response:
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            if payload is None:
                return await client.get(path)
            return await client.post(
                path,
                json=payload,
                headers={"A2A-Version": "1.0"},
            )


class A2AServerTests(unittest.TestCase):
    def test_agent_card_is_discoverable_and_exposes_only_coaching_skill(self) -> None:
        response = asyncio.run(
            send_http_request(build_app(), "/.well-known/agent-card.json")
        )

        self.assertEqual(response.status_code, 200)
        card = response.json()
        self.assertEqual(card["name"], "AI Running Coach")
        self.assertEqual(
            card["supportedInterfaces"],
            [
                {
                    "protocolBinding": "JSONRPC",
                    "url": f"http://{A2A_HOST}:{A2A_PORT}",
                    "protocolVersion": "1.0",
                }
            ],
        )
        self.assertEqual(
            [skill["id"] for skill in card["skills"]],
            ["running_coaching"],
        )
        self.assertNotIn("Zepp", str(card))

    def test_json_rpc_endpoint_completes_a_conversation_task(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": "request-1",
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "message-1",
                    "role": "ROLE_USER",
                    "parts": [{"text": "¿Cómo empiezo a correr?"}],
                }
            },
        }
        with patch(
            "running_coach.a2a_server.generate_coach_response",
            new=AsyncMock(return_value="Empieza con intervalos suaves."),
        ) as generate:
            response = asyncio.run(send_http_request(build_app(), "/", payload))

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]["task"]
        self.assertEqual(result["status"]["state"], "TASK_STATE_COMPLETED")
        self.assertEqual(
            result["artifacts"][0]["parts"][0]["text"],
            "Empieza con intervalos suaves.",
        )
        generate.assert_awaited_once_with("¿Cómo empiezo a correr?")

    def test_agent_card_supports_a_custom_port(self) -> None:
        card = build_agent_card(8766)

        self.assertEqual(
            card.supported_interfaces[0].url,
            f"http://{A2A_HOST}:8766",
        )
        self.assertIsInstance(card.supported_interfaces[0], AgentInterface)
        self.assertIsInstance(card.skills[0], AgentSkill)

    def test_a2a_specialists_are_created_without_mcp_tools(self) -> None:
        agents = build_custom_agents(servers={})

        self.assertEqual(len(agents), 3)
        self.assertTrue(all(not agent.get("mcp_servers") for agent in agents))
        self.assertIn("únicamente sobre running", A2A_SYSTEM_PROMPT)
        self.assertNotIn("Datos de Zepp", A2A_SYSTEM_PROMPT)

    def test_copilot_session_has_no_mcp_connections_or_tools(self) -> None:
        session = SimpleNamespace(
            session_id="a2a-session",
            disconnect=AsyncMock(),
            send_and_wait=AsyncMock(
                return_value=SimpleNamespace(
                    data=AssistantMessageData(
                        content="Respuesta de coaching",
                        message_id="assistant-message",
                    )
                )
            ),
        )

        class FakeClient:
            def __init__(self) -> None:
                self.create_session = AsyncMock(return_value=session)
                self.delete_session = AsyncMock()

            async def __aenter__(self) -> "FakeClient":
                return self

            async def __aexit__(self, *_args: object) -> None:
                return None

        client = FakeClient()
        with patch("running_coach.a2a_server.CopilotClient", return_value=client):
            answer = asyncio.run(generate_coach_response("Sugiere un rodaje suave"))

        self.assertEqual(answer, "Respuesta de coaching")
        session_config = client.create_session.await_args.kwargs
        self.assertEqual(session_config["available_tools"], [])
        self.assertNotIn("mcp_servers", session_config)
        self.assertTrue(
            all(
                not agent.get("mcp_servers")
                for agent in session_config["custom_agents"]
            )
        )
        session.disconnect.assert_awaited_once()
        client.delete_session.assert_awaited_once_with("a2a-session")

    def test_executor_completes_a_text_task_with_one_coach_response(self) -> None:
        message = new_text_message("Sugiere una sesión de running", role=Role.ROLE_USER)
        context = SimpleNamespace(message=message, current_task=None)
        events: list[object] = []

        class EventCollector:
            async def enqueue_event(self, event: object) -> None:
                events.append(event)

        with patch(
            "running_coach.a2a_server.generate_coach_response",
            new=AsyncMock(return_value="Alterna carrera suave y descanso."),
        ) as generate:
            asyncio.run(RunningCoachExecutor().execute(context, EventCollector()))

        generate.assert_awaited_once_with("Sugiere una sesión de running")
        self.assertEqual(len(events), 4)
        self.assertEqual(events[1].status.state, TaskState.TASK_STATE_WORKING)
        self.assertEqual(events[2].artifact.name, "coach_response")
        self.assertEqual(
            events[2].artifact.parts[0].text,
            "Alterna carrera suave y descanso.",
        )
        self.assertEqual(events[3].status.state, TaskState.TASK_STATE_COMPLETED)

    def test_executor_rejects_non_text_and_oversized_queries(self) -> None:
        executor = RunningCoachExecutor()
        queue = SimpleNamespace(enqueue_event=AsyncMock())
        with patch("running_coach.a2a_server.generate_coach_response") as generate:
            with self.assertRaisesRegex(ValueError, "texto"):
                asyncio.run(
                    executor.execute(
                        SimpleNamespace(
                            message=SimpleNamespace(
                                role=Role.ROLE_USER,
                                parts=[SimpleNamespace(HasField=lambda _: False)],
                            ),
                            current_task=None,
                        ),
                        queue,
                    )
                )

            with self.assertRaisesRegex(ValueError, "4000 caracteres"):
                asyncio.run(
                    executor.execute(
                        SimpleNamespace(
                            message=new_text_message(
                                "x" * (MAX_QUERY_LENGTH + 1),
                                role=Role.ROLE_USER,
                            ),
                            current_task=None,
                        ),
                        queue,
                    )
                )

        generate.assert_not_called()
        queue.enqueue_event.assert_not_awaited()

    def test_executor_marks_copilot_failure_as_failed_and_logs_it(self) -> None:
        message = new_text_message("¿Qué rutina hago?", role=Role.ROLE_USER)
        context = SimpleNamespace(message=message, current_task=None)
        events: list[object] = []

        class EventCollector:
            async def enqueue_event(self, event: object) -> None:
                events.append(event)

        with self.assertLogs("running_coach.a2a_server", level="ERROR") as logs:
            with patch(
                "running_coach.a2a_server.generate_coach_response",
                new=AsyncMock(side_effect=RuntimeError("Copilot connection failed")),
            ):
                asyncio.run(RunningCoachExecutor().execute(context, EventCollector()))

        self.assertIn("Copilot connection failed", "\n".join(logs.output))
        self.assertEqual(events[-1].status.state, TaskState.TASK_STATE_FAILED)


if __name__ == "__main__":
    unittest.main()
