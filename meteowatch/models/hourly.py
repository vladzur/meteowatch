"""Modelos de datos para el pronóstico por hora."""

from dataclasses import dataclass, field


@dataclass
class HourData:
    """Representa el pronóstico meteorológico de una hora específica."""

    end: int
    rain: float
    night: bool
    clouds: int
    symbol: int
    humidity: int
    pressure: int
    snowline: int
    wind_gust: int
    wind_speed: int
    temperature: float
    uv_index_max: float
    wind_direction: str
    rain_probability: int
    temperature_feels_like: float

    @classmethod
    def from_dict(cls, data: dict) -> "HourData":
        """Construye una instancia de HourData desde un diccionario de la API."""
        return cls(
            end=int(data.get("end", 0)),
            rain=float(data.get("rain", 0)),
            night=bool(data.get("night", False)),
            clouds=int(data.get("clouds", 0)),
            symbol=int(data.get("symbol", 0)),
            humidity=int(data.get("humidity", 0)),
            pressure=int(data.get("pressure", 0)),
            snowline=int(data.get("snowline", 0)),
            wind_gust=int(data.get("wind_gust", 0)),
            wind_speed=int(data.get("wind_speed", 0)),
            temperature=float(data.get("temperature", 0)),
            uv_index_max=float(data.get("uv_index_max", 0)),
            wind_direction=data.get("wind_direction", ""),
            rain_probability=int(data.get("rain_probability", 0)),
            temperature_feels_like=float(data.get("temperature_feels_like", 0)),
        )


@dataclass
class HourlyForecast:
    """Representa el pronóstico por hora de un día completo."""

    url: str
    hash: str
    name: str
    start: int
    hours: list[HourData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "HourlyForecast":
        """Construye una instancia de HourlyForecast desde un diccionario de la API."""
        hours_data = data.get("hours", [])
        hours = [HourData.from_dict(h) for h in hours_data]
        return cls(
            url=data.get("url", ""),
            hash=data.get("hash", ""),
            name=data.get("name", ""),
            start=int(data.get("start", 0)),
            hours=hours,
        )
