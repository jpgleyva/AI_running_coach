"""Local A2A server that exposes the coach without exposing MCP tools."""

import argparse
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
    TaskState,
)
from starlette.applications import Starlette

from copilot import CopilotClient
from copilot.generated.session_events import AssistantMessageData
from copilot.session import SystemMessageAppendConfig
from running_coach.agents import build_custom_agents
from running_coach.cli import build_system_prompt, close_session
from running_coach.mcp_config import reject_unapproved_tool_permission
from running_coach.memory import SessionMemory, build_user_prompt

logger = logging.getLogger(__name__)

A2A_HOST = "127.0.0.1"
A2A_PORT = 8765
MAX_QUERY_LENGTH = 4000
COACH_TIMEOUT_SECONDS = 180
A2A_SYSTEM_PROMPT = (
    f"{build_system_prompt(zepp_enabled=False)}\n"
    "En este endpoint A2A, responde únicamente sobre running, hábitos sostenibles "
    "de recomposición corporal y recuperación. Si la consulta no pertenece a "
    "esos temas, explica brevemente el alcance del servicio."
)


async def generate_coach_response(query: str) -> str:
    """Run one ephemeral Copilot session without any MCP server connections."""
    system_message: SystemMessageAppendConfig = {
        "mode": "append",
        "content": A2A_SYSTEM_PROMPT,
    }
    async with CopilotClient() as client:
        session = await client.create_session(
            on_permission_request=reject_unapproved_tool_permission,
            model="auto",
            available_tools=[],
            custom_agents=build_custom_agents(servers={}),
            enable_config_discovery=False,
            system_message=system_message,
        )
        try:
            response = await session.send_and_wait(
                build_user_prompt(query, SessionMemory()),
                timeout=COACH_TIMEOUT_SECONDS,
            )
            if response is None:
                raise RuntimeError("Copilot no devolvió una respuesta.")
            if not isinstance(response.data, AssistantMessageData):
                raise RuntimeError(
                    "Copilot devolvió un evento inesperado en lugar de una respuesta."
                )
            return response.data.content
        finally:
            await close_session(client, session)


class RunningCoachExecutor(AgentExecutor):
    """Translate A2A text tasks into one-off coach conversations."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        if message is None or message.role != Role.ROLE_USER:
            raise ValueError("La solicitud A2A debe incluir un mensaje de usuario.")
        if not message.parts or any(
            not part.HasField("text") for part in message.parts
        ):
            raise ValueError("Solo se admiten mensajes A2A de texto.")

        query = get_message_text(message).strip()
        if not query:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"El mensaje no puede superar {MAX_QUERY_LENGTH} caracteres."
            )

        task = context.current_task or new_task_from_user_message(message)
        await event_queue.enqueue_event(task)
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(TaskState.TASK_STATE_WORKING)

        try:
            result = await generate_coach_response(query)
        except Exception:
            logger.exception("Falló el procesamiento de la tarea A2A %s.", task.id)
            await updater.update_status(
                TaskState.TASK_STATE_FAILED,
                message=new_text_message(
                    "No se pudo completar la consulta. Inténtalo de nuevo más tarde."
                ),
            )
            return

        await updater.add_artifact(
            parts=[new_text_part(result)],
            name="coach_response",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            raise ValueError("No se encontró la tarea A2A que se debe cancelar.")
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(TaskState.TASK_STATE_CANCELED)


def build_agent_card(port: int = A2A_PORT) -> AgentCard:
    """Return the public card for this localhost-only A2A service."""
    skill = AgentSkill(
        id="running_coaching",
        name="Coaching de running y recomposición corporal",
        description=(
            "Responde consultas conversacionales sobre entrenamiento de running, "
            "hábitos sostenibles de recomposición corporal y recuperación."
        ),
        tags=["running", "nutrición", "recuperación"],
        examples=[
            "Sugiere una semana de entrenamiento gradual.",
            "¿Cómo puedo mejorar mis hábitos de alimentación?",
            "Tengo molestias en la rodilla después de correr, ¿qué hago?",
        ],
        input_modes=["text/plain"],
        output_modes=["text/plain"],
    )
    return AgentCard(
        name="AI Running Coach",
        description=(
            "Coach conversacional en español para running, recomposición corporal "
            "y recuperación segura."
        ),
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=f"http://{A2A_HOST}:{port}",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[skill],
    )


def build_app(port: int = A2A_PORT) -> Starlette:
    """Create the A2A 1.0 JSON-RPC app with an ephemeral in-memory task store."""
    card = build_agent_card(port)
    handler = DefaultRequestHandler(
        agent_executor=RunningCoachExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
        validate_input_modes=True,
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        yield
        await handler.aclose()

    app = Starlette(
        routes=[
            *create_agent_card_routes(card),
            *create_jsonrpc_routes(handler, rpc_url="/"),
        ],
        lifespan=lifespan,
    )
    app.state.request_handler = handler
    return app


def _port_argument(value: str) -> int:
    """Parse a valid TCP port for the local A2A listener."""
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "El puerto debe ser un número entero."
        ) from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("El puerto debe estar entre 1 y 65535.")
    return port


def main() -> None:
    """Start the A2A service bound exclusively to the local loopback interface."""
    parser = argparse.ArgumentParser(
        description="Servidor A2A local de AI Running Coach."
    )
    parser.add_argument(
        "--port",
        type=_port_argument,
        default=A2A_PORT,
        help=f"Puerto TCP local (predeterminado: {A2A_PORT}).",
    )
    port = parser.parse_args().port
    uvicorn.run(
        build_app(port),
        host=A2A_HOST,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
