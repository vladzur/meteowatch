"""Modelos de datos para el pronóstico por hora (Open-Meteo Forecast API).

La API retorna datos en formato columnar (arrays paralelos) que
se convierten a objetos HourData individuales.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


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
class HourData:
    """Representa el pronóstico meteorológico de una hora específica."""

    end: int
    precipitation: float
    night: bool
    clouds: int
    symbol: int
    humidity: int
    pressure: int
    wind_gust: int
    wind_speed: int
    temperature: float
    uv_index_max: float
    wind_direction: int
    rain_probability: int
    temperature_feels_like: float

    @classmethod
    def from_dict(cls, data: dict) -> "HourData":
        """Construye una instancia de HourData desde un diccionario de la API."""
        return cls(
            end=int(data.get("end", 0)),
            precipitation=float(data.get("precipitation", 0)),
            night=bool(data.get("night", False)),
            clouds=int(data.get("clouds", 0)),
            symbol=int(data.get("symbol", 0)),
            humidity=int(data.get("humidity", 0)),
            pressure=int(data.get("pressure", 0)),
            wind_gust=int(data.get("wind_gust", 0)),
            wind_speed=int(data.get("wind_speed", 0)),
            temperature=float(data.get("temperature", 0)),
            uv_index_max=float(data.get("uv_index_max", 0)),
            wind_direction=int(data.get("wind_direction", 0)),
            rain_probability=int(data.get("rain_probability", 0)),
            temperature_feels_like=float(data.get("temperature_feels_like", 0)),
        )

    @classmethod
    def from_openmeteo_hourly(cls, row: dict) -> "HourData":
        """Construye desde una fila del bloque hourly de Open-Meteo.

        Args:
            row: Diccionario con una fila de datos horarios ya parseados.
        """
        return cls(
            end=row.get("end", 0),
            precipitation=row.get("precipitation", 0.0),
            night=row.get("night", False),
            clouds=row.get("clouds", 0),
            symbol=row.get("symbol", 0),
            humidity=row.get("humidity", 0),
            pressure=row.get("pressure", 0),
            wind_gust=row.get("wind_gust", 0),
            wind_speed=row.get("wind_speed", 0),
            temperature=row.get("temperature", 0.0),
            uv_index_max=row.get("uv_index_max", 0.0),
            wind_direction=row.get("wind_direction", 0),
            rain_probability=row.get("rain_probability", 0),
            temperature_feels_like=row.get("temperature_feels_like", 0.0),
        )


@dataclass
class HourlyForecast:
    """Representa el pronóstico por hora de un día completo."""

    latitude: float
    longitude: float
    timezone: str
    hours: list[HourData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "HourlyForecast":
        """Construye una instancia de HourlyForecast desde un diccionario de la API."""
        hours_data = data.get("hours", [])
        hours = [HourData.from_dict(h) for h in hours_data]
        return cls(
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            timezone=data.get("timezone", "UTC"),
            hours=hours,
        )

    @classmethod
    def from_openmeteo_hourly(cls, data: dict) -> "HourlyForecast":
        """Construye desde la respuesta columnar hourly de Open-Meteo.

        Args:
            data: Diccionario completo de la respuesta de la API (nivel raíz).
        """
        hourly_block = data.get("hourly", {})
        times = hourly_block.get("time", [])
        num_hours = len(times)

        hours = []
        for i in range(num_hours):
            try:
                end_ms = _parse_iso_to_ms(times[i])
            except (IndexError, TypeError):
                end_ms = 0

            is_day_val = int(float(_safe_get(hourly_block, "is_day", i, 1)))

            row = {
                "end": end_ms,
                "precipitation": float(_safe_get(hourly_block, "precipitation", i, 0.0)),
                "night": is_day_val == 0,
                "clouds": int(float(_safe_get(hourly_block, "cloud_cover", i, 0))),
                "symbol": int(float(_safe_get(hourly_block, "weather_code", i, 0))),
                "humidity": int(float(_safe_get(hourly_block, "relative_humidity_2m", i, 0))),
                "pressure": int(float(_safe_get(hourly_block, "pressure_msl", i, 0))),
                "wind_gust": int(float(_safe_get(hourly_block, "wind_gusts_10m", i, 0))),
                "wind_speed": int(float(_safe_get(hourly_block, "wind_speed_10m", i, 0))),
                "temperature": float(_safe_get(hourly_block, "temperature_2m", i, 0.0)),
                "uv_index_max": float(_safe_get(hourly_block, "uv_index", i, 0.0)),
                "wind_direction": int(float(_safe_get(hourly_block, "wind_direction_10m", i, 0))),
                "rain_probability": int(float(_safe_get(hourly_block, "precipitation_probability", i, 0))),
                "temperature_feels_like": float(_safe_get(hourly_block, "apparent_temperature", i, 0.0)),
            }
            hours.append(HourData.from_openmeteo_hourly(row))

        return cls(
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            timezone=data.get("timezone", "UTC"),
            hours=hours,
        )


def _safe_get(block: dict, key: str, index: int, default):
    """Obtiene un valor de un array columnar de forma segura."""
    arr = block.get(key, [])
    try:
        return arr[index]
    except (IndexError, TypeError):
        return default
