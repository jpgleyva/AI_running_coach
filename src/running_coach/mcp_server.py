"""Servidor MCP local que expone los cálculos de running."""

from mcp.server.fastmcp import FastMCP

from running_coach.calculations import (
    DistanceKm,
    DurationMinutes,
    PaceSecondsPerKm,
    calculate_running_pace,
    estimate_finish_time,
)

MCP_TOOL_NAMES = ("calculate_running_pace", "estimate_finish_time")

mcp = FastMCP("running-coach")


@mcp.tool(name="calculate_running_pace")
def calculate_running_pace_tool(
    distance_km: DistanceKm,
    duration_minutes: DurationMinutes,
) -> str:
    """Calcula ritmo medio por kilómetro y velocidad desde distancia y duración."""
    return calculate_running_pace(distance_km, duration_minutes)


@mcp.tool(name="estimate_finish_time")
def estimate_finish_time_tool(
    distance_km: DistanceKm,
    pace_seconds_per_km: PaceSecondsPerKm,
) -> str:
    """Estima el tiempo de llegada para una distancia y ritmo constantes."""
    return estimate_finish_time(distance_km, pace_seconds_per_km)


if __name__ == "__main__":
    mcp.run(transport="stdio")
