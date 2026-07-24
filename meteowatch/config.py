"""Gestión de configuración de la aplicación.

Almacena y recupera preferencias del usuario desde un archivo JSON
en ~/.config/meteowatch/config.json.
"""

import json
import os
from dataclasses import dataclass

# Usar XDG_CONFIG_HOME si está disponible, fallback a ~/.config
_xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
CONFIG_DIR = os.path.join(_xdg_config, "meteowatch")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class AppConfig:
    """Configuración persistente de la aplicación."""

    latitude: float = 0.0
    longitude: float = 0.0
    location_name: str = ""
    timezone: str = "auto"
    close_to_tray: bool = True

    @classmethod
    def load(cls) -> "AppConfig":
        """Carga la configuración desde el archivo JSON.

        Si el archivo no existe, retorna una configuración vacía.
        """
        if not os.path.exists(CONFIG_FILE):
            return cls()

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Compatibilidad con configuraciones antiguas: ignorar api_key y location_hash
            return cls(
                latitude=float(data.get("latitude", 0.0)),
                longitude=float(data.get("longitude", 0.0)),
                location_name=data.get("location_name", ""),
                timezone=data.get("timezone", "auto"),
                close_to_tray=data.get("close_to_tray", True),
            )
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        """Guarda la configuración actual en el archivo JSON.

        Crea el directorio de configuración si no existe.
        """
        os.makedirs(CONFIG_DIR, exist_ok=True)

        data = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
            "timezone": self.timezone,
            "close_to_tray": self.close_to_tray,
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def set_location(self, latitude: float, longitude: float,
                     location_name: str, timezone: str = "auto") -> None:
        """Actualiza la ubicación seleccionada y persiste los cambios."""
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name
        self.timezone = timezone
        self.save()

    def is_configured(self) -> bool:
        """Verifica si la aplicación tiene coordenadas configuradas."""
        return self.latitude != 0.0 or self.longitude != 0.0
