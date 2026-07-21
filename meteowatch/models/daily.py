"""Modelos de datos para el pronóstico diario.

La API retorna un objeto con hash, name, url y un array 'days'
con el pronóstico de los próximos 5 días.
"""

from dataclasses import dataclass, field


@dataclass
class DayData:
    """Representa el pronóstico meteorológico de un día individual."""

    start: int
    symbol: int
    temperature_min: float
    temperature_max: float
    wind_speed: int
    wind_gust: int
    wind_direction: str
    rain: float
    rain_probability: int
    humidity: int
    pressure: int
    snowline: int
    uv_index_max: float
    sun_in: int
    sun_mid: int
    sun_out: int
    moon_in: int
    moon_out: int
    moon_symbol: int
    moon_illumination: float

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
            wind_direction=data.get("wind_direction", ""),
            rain=float(data.get("rain", 0)),
            rain_probability=int(data.get("rain_probability", 0)),
            humidity=int(data.get("humidity", 0)),
            pressure=int(data.get("pressure", 0)),
            snowline=int(data.get("snowline", 0)),
            uv_index_max=float(data.get("uv_index_max", 0)),
            sun_in=int(data.get("sun_in", 0)),
            sun_mid=int(data.get("sun_mid", 0)),
            sun_out=int(data.get("sun_out", 0)),
            moon_in=int(data.get("moon_in", 0)),
            moon_out=int(data.get("moon_out", 0)),
            moon_symbol=int(data.get("moon_symbol", 0)),
            moon_illumination=float(data.get("moon_illumination", 0)),
        )


@dataclass
class DailyForecast:
    """Representa la respuesta completa del endpoint de pronóstico diario.

    Contiene metadatos de la ubicación y un array con hasta 5 días.
    """

    hash: str
    name: str
    url: str
    days: list[DayData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "DailyForecast":
        """Construye una instancia de DailyForecast desde un diccionario de la API."""
        days_data = data.get("days", [])
        days = [DayData.from_dict(d) for d in days_data]
        return cls(
            hash=data.get("hash", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            days=days,
        )
