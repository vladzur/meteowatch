"""Modelo de datos para ubicación geográfica."""

from dataclasses import dataclass


@dataclass
class Location:
    """Representa una ubicación geográfica devuelta por la búsqueda de la API."""

    hash: str
    name: str
    description: str
    country_name: str

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        """Construye una instancia de Location desde un diccionario de la API."""
        return cls(
            hash=data.get("hash", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            country_name=data.get("country_name", ""),
        )

    @property
    def display_name(self) -> str:
        """Nombre descriptivo para mostrar en la UI."""
        return f"{self.name}, {self.description} ({self.country_name})"
