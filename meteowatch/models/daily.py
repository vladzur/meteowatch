"""Modelos de datos para el pronóstico diario (Open-Meteo Forecast API).

La API retorna datos en formato columnar (arrays paralelos) que
se convierten a objetos DayData individuales.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _parse_iso_to_ms(iso_str: str) -> int:
    """Convierte una fecha ISO8601 a timestamp en milisegundos."""
    if not iso_str:
        return 0
    try:
        dt = datetime.fromisoformat(iso_str)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return 0


@dataclass
class DayData:
    """Representa el pronóstico meteorológico de un día individual."""

    start: int
    symbol: int
    temperature_min: float
    temperature_max: float
    wind_speed: int
    wind_gust: int
    wind_direction: int
    precipitation: float
    rain_probability: int
    uv_index_max: float
    sun_in: int
    sun_out: int
    daylight_duration: int
    sunshine_duration: int

    @classmethod
    def from_dict(cls, data: dict) -> "DayData":
        """Construye una instancia de DayData desde un diccionario de la API."""
        return cls(
            start=int(data.get("start", 0)),
            symbol=int(data.get("symbol", 0)),
            temperature_min=float(data.get("temperature_min", 0)),
            temperature_max=float(data.get("temperature_max", 0)),
            wind_speed=int(data.get("wind_speed", 0)),
            wind_gust=int(data.get("wind_gust", 0)),
            wind_direction=int(data.get("wind_direction", 0)),
            precipitation=float(data.get("precipitation", 0)),
            rain_probability=int(data.get("rain_probability", 0)),
            uv_index_max=float(data.get("uv_index_max", 0)),
            sun_in=int(data.get("sun_in", 0)),
            sun_out=int(data.get("sun_out", 0)),
            daylight_duration=int(data.get("daylight_duration", 0)),
            sunshine_duration=int(data.get("sunshine_duration", 0)),
        )

    @classmethod
    def from_openmeteo_daily(cls, row: dict) -> "DayData":
        """Construye desde una fila del bloque daily de Open-Meteo.

        Args:
            row: Diccionario con una fila de datos diarios ya parseados.
        """
        return cls(
            start=row.get("start", 0),
            symbol=row.get("symbol", 0),
            temperature_min=row.get("temperature_min", 0.0),
            temperature_max=row.get("temperature_max", 0.0),
            wind_speed=row.get("wind_speed", 0),
            wind_gust=row.get("wind_gust", 0),
            wind_direction=row.get("wind_direction", 0),
            precipitation=row.get("precipitation", 0.0),
            rain_probability=row.get("rain_probability", 0),
            uv_index_max=row.get("uv_index_max", 0.0),
            sun_in=row.get("sun_in", 0),
            sun_out=row.get("sun_out", 0),
            daylight_duration=row.get("daylight_duration", 0),
            sunshine_duration=row.get("sunshine_duration", 0),
        )


@dataclass
class DailyForecast:
    """Representa la respuesta completa del endpoint de pronóstico diario."""

    latitude: float
    longitude: float
    elevation: float
    timezone: str
    days: list[DayData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "DailyForecast":
        """Construye una instancia de DailyForecast desde un diccionario de la API."""
        days_data = data.get("days", [])
        days = [DayData.from_dict(d) for d in days_data]
        return cls(
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            elevation=data.get("elevation", 0.0),
            timezone=data.get("timezone", "UTC"),
            days=days,
        )

    @classmethod
    def from_openmeteo_daily(cls, data: dict) -> "DailyForecast":
        """Construye desde la respuesta columnar daily de Open-Meteo.

        Args:
            data: Diccionario completo de la respuesta de la API (nivel raíz).
        """
        daily_block = data.get("daily", {})
        times = daily_block.get("time", [])
        num_days = len(times)

        days = []
        for i in range(num_days):
            try:
                start_ms = _parse_iso_to_ms(times[i])
            except (IndexError, TypeError):
                start_ms = 0

            row = {
                "start": start_ms,
                "symbol": int(_safe_get(daily_block, "weather_code", i, 0)),
                "temperature_min": float(_safe_get(daily_block, "temperature_2m_min", i, 0.0)),
                "temperature_max": float(_safe_get(daily_block, "temperature_2m_max", i, 0.0)),
                "wind_speed": int(float(_safe_get(daily_block, "wind_speed_10m_max", i, 0))),
                "wind_gust": int(float(_safe_get(daily_block, "wind_gusts_10m_max", i, 0))),
                "wind_direction": int(float(_safe_get(daily_block, "wind_direction_10m_dominant", i, 0))),
                "precipitation": float(_safe_get(daily_block, "precipitation_sum", i, 0.0)),
                "rain_probability": int(float(_safe_get(daily_block, "precipitation_probability_max", i, 0))),
                "uv_index_max": float(_safe_get(daily_block, "uv_index_max", i, 0.0)),
                "sun_in": _parse_iso_to_ms(_safe_get(daily_block, "sunrise", i, "")),
                "sun_out": _parse_iso_to_ms(_safe_get(daily_block, "sunset", i, "")),
                "daylight_duration": int(float(_safe_get(daily_block, "daylight_duration", i, 0))),
                "sunshine_duration": int(float(_safe_get(daily_block, "sunshine_duration", i, 0))),
            }
            days.append(DayData.from_openmeteo_daily(row))

        return cls(
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            elevation=float(data.get("elevation", 0.0)),
            timezone=data.get("timezone", "UTC"),
            days=days,
        )


def _safe_get(block: dict, key: str, index: int, default):
    """Obtiene un valor de un array columnar de forma segura."""
    arr = block.get(key, [])
    try:
        return arr[index]
    except (IndexError, TypeError):
        return default
