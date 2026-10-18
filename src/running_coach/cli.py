"""CLI conversacional del agente de running."""

import asyncio

from copilot import CopilotClient
from copilot.generated.session_events import AssistantMessageData
from copilot.session import (
    PermissionRequest,
    PermissionRequestResult,
    SystemMessageAppendConfig,
)

SYSTEM_PROMPT = """\
Eres un coach conversacional de running y recomposición corporal. Responde en
español, con empatía, claridad y recomendaciones prácticas y graduales.

Contexto del usuario:
- Corre 2-3 veces por semana.
- Busca reducir grasa visceral y conseguir mayor definición abdominal.
- Tiene historial de molestias en la rodilla derecha.

Límites y seguridad:
- No diagnostiques lesiones ni sustituyas la atención de un profesional de salud.
- Si describe dolor agudo o creciente, inflamación, inestabilidad o dificultad para
  apoyar la pierna, recomiéndale detener la actividad y buscar atención médica.
- Ante molestias recurrentes, sugiere valoración por un profesional antes de
  aumentar la carga. No le animes a correr con dolor.
- No prometas reducción localizada de grasa ni resultados físicos garantizados.
- Evita dietas extremas y cambios de entrenamiento bruscos; prioriza hábitos
  sostenibles y recuperación.
- No afirmes tener acceso a datos de Garmin, Amazfit/Zepp o Google Calendar: aún
  no hay integraciones. Si falta información importante, pregunta antes de
  personalizar una recomendación.
"""


def reject_tool_permission(
    _request: PermissionRequest,
    _invocation: dict[str, str],
) -> PermissionRequestResult:
    """Rechaza cualquier solicitud de permiso para ejecutar herramientas."""
    return PermissionRequestResult(kind="reject")


async def run_chat() -> None:
    system_message: SystemMessageAppendConfig = {
        "mode": "append",
        "content": SYSTEM_PROMPT,
    }
    async with CopilotClient() as client:
        async with await client.create_session(
            on_permission_request=reject_tool_permission,
            model="auto",
            available_tools=[],
            system_message=system_message,
        ) as session:
            print("AI Running Coach — escribe /salir para terminar.")
            while True:
                try:
                    message = input("\nTú: ").strip()
                except EOFError:
                    print("\nHasta luego.")
                    return

                if message.lower() in {"/salir", "/exit", "/quit"}:
                    print("Hasta luego.")
                    return
                if not message:
                    continue

                response = await session.send_and_wait(message)
                if response is None:
                    print("Copilot no devolvió una respuesta. Inténtalo de nuevo.")
                    continue
                match response.data:
                    case AssistantMessageData() as data:
                        print(f"\nCoach: {data.content}")
                    case _:
                        raise RuntimeError(
                            "Copilot devolvió un evento inesperado en lugar de una respuesta."
                        )


def main() -> None:
    """Inicia la CLI y deja que los errores de conexión sean visibles."""
    try:
        asyncio.run(run_chat())
    except KeyboardInterrupt:
        print("\nHasta luego.")


if __name__ == "__main__":
    main()
