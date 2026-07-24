"""Modelo de datos para ubicación geográfica (Open-Meteo Geocoding API)."""

from dataclasses import dataclass


@dataclass
class Location:
    """Representa una ubicación geográfica devuelta por la API de geocoding."""

    id: int
    name: str
    latitude: float
    longitude: float
    country: str
    country_code: str
    admin1: str
    timezone: str
    elevation: float

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        """Construye una instancia de Location desde un diccionario de la API de geocoding de Open-Meteo."""
        return cls(
            id=int(data.get("id", 0)),
            name=data.get("name", ""),
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            country=data.get("country", ""),
            country_code=data.get("country_code", ""),
            admin1=data.get("admin1", ""),
            timezone=data.get("timezone", "UTC"),
            elevation=float(data.get("elevation", 0.0)),
        )

    @property
    def display_name(self) -> str:
        """Nombre descriptivo para mostrar en la UI."""
        result = self.name
        if self.admin1:
            result += f", {self.admin1}"
        result += f" ({self.country})"
        return result
