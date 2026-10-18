"""Herramientas deterministas de cálculo para el coach."""

from pydantic import BaseModel, Field

from copilot import define_tool
from copilot.tools import Tool


class RunningPaceParameters(BaseModel):
    distance_km: float = Field(
        gt=0,
        le=500,
        allow_inf_nan=False,
        description="Distancia recorrida en kilómetros, mayor que 0 y hasta 500.",
    )
    duration_minutes: float = Field(
        gt=0,
        le=10080,
        allow_inf_nan=False,
        description="Duración total en minutos, mayor que 0 y hasta 7 días.",
    )


class FinishTimeParameters(BaseModel):
    distance_km: float = Field(
        gt=0,
        le=500,
        allow_inf_nan=False,
        description="Distancia objetivo en kilómetros, mayor que 0 y hasta 500.",
    )
    pace_seconds_per_km: int = Field(
        gt=0,
        le=3600,
        description="Ritmo objetivo en segundos por kilómetro, entre 1 y 3600.",
    )


@define_tool(
    description=(
        "Calcula el ritmo medio por kilómetro y la velocidad a partir de una "
        "distancia en kilómetros y una duración en minutos."
    ),
    skip_permission=True,
)
def calculate_running_pace(params: RunningPaceParameters) -> str:
    """Calcula ritmo medio en min/km y velocidad en km/h."""
    total_pace_seconds = round(params.duration_minutes * 60 / params.distance_km)
    pace_minutes, pace_seconds = divmod(total_pace_seconds, 60)
    speed_kmh = params.distance_km * 60 / params.duration_minutes
    return (
        f"Ritmo medio: {pace_minutes}:{pace_seconds:02d} min/km. "
        f"Velocidad media: {speed_kmh:.2f} km/h."
    )


@define_tool(
    description=(
        "Estima el tiempo total para una distancia en kilómetros manteniendo "
        "un ritmo objetivo en segundos por kilómetro."
    ),
    skip_permission=True,
)
def estimate_finish_time(params: FinishTimeParameters) -> str:
    """Estima el tiempo total a un ritmo constante."""
    total_seconds = round(params.distance_km * params.pace_seconds_per_km)
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)
    return (
        f"Tiempo estimado a {params.pace_seconds_per_km // 60}:"
        f"{params.pace_seconds_per_km % 60:02d} min/km para "
        f"{params.distance_km:g} km: {hours:02d}:{minutes:02d}:{seconds:02d} "
        "(hh:mm:ss), suponiendo un ritmo constante."
    )


COACH_TOOLS: tuple[Tool, ...] = (
    calculate_running_pace,
    estimate_finish_time,
)
