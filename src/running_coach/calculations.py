"""Validación y cálculos compartidos para herramientas MCP de running."""

from typing import Annotated

from pydantic import BaseModel, Field

DistanceKm = Annotated[
    float,
    Field(
        gt=0,
        le=500,
        allow_inf_nan=False,
        description="Distancia en kilómetros, mayor que 0 y hasta 500.",
    ),
]
DurationMinutes = Annotated[
    float,
    Field(
        gt=0,
        le=10080,
        allow_inf_nan=False,
        description="Duración en minutos, mayor que 0 y hasta 7 días.",
    ),
]
PaceSecondsPerKm = Annotated[
    int,
    Field(
        gt=0,
        le=3600,
        description="Ritmo en segundos por kilómetro, entre 1 y 3600.",
    ),
]


class RunningPaceParameters(BaseModel):
    distance_km: DistanceKm
    duration_minutes: DurationMinutes


class FinishTimeParameters(BaseModel):
    distance_km: DistanceKm
    pace_seconds_per_km: PaceSecondsPerKm


def calculate_running_pace(distance_km: float, duration_minutes: float) -> str:
    """Calcula ritmo medio en min/km y velocidad en km/h."""
    params = RunningPaceParameters(
        distance_km=distance_km,
        duration_minutes=duration_minutes,
    )
    total_pace_seconds = round(params.duration_minutes * 60 / params.distance_km)
    pace_minutes, pace_seconds = divmod(total_pace_seconds, 60)
    speed_kmh = params.distance_km * 60 / params.duration_minutes
    return (
        f"Ritmo medio: {pace_minutes}:{pace_seconds:02d} min/km. "
        f"Velocidad media: {speed_kmh:.2f} km/h."
    )


def estimate_finish_time(distance_km: float, pace_seconds_per_km: int) -> str:
    """Estima el tiempo total a un ritmo constante."""
    params = FinishTimeParameters(
        distance_km=distance_km,
        pace_seconds_per_km=pace_seconds_per_km,
    )
    total_seconds = round(params.distance_km * params.pace_seconds_per_km)
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)
    return (
        f"Tiempo estimado a {params.pace_seconds_per_km // 60}:"
        f"{params.pace_seconds_per_km % 60:02d} min/km para "
        f"{params.distance_km:g} km: {hours:02d}:{minutes:02d}:{seconds:02d} "
        "(hh:mm:ss), suponiendo un ritmo constante."
    )
