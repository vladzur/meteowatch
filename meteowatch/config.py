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

    api_key: str = ""
    location_hash: str = ""
    location_name: str = ""

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
            return cls(
                api_key=data.get("api_key", ""),
                location_hash=data.get("location_hash", ""),
                location_name=data.get("location_name", ""),
            )
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        """Guarda la configuración actual en el archivo JSON.

        Crea el directorio de configuración si no existe.
        """
        os.makedirs(CONFIG_DIR, exist_ok=True)

        data = {
            "api_key": self.api_key,
            "location_hash": self.location_hash,
            "location_name": self.location_name,
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_api_key(self) -> str:
        """Retorna la API key configurada."""
        return self.api_key

    def set_location(self, location_hash: str, location_name: str) -> None:
        """Actualiza la ubicación seleccionada y persiste los cambios."""
        self.location_hash = location_hash
        self.location_name = location_name
        self.save()

    def is_configured(self) -> bool:
        """Verifica si la aplicación tiene API key y ubicación configuradas."""
        return bool(self.api_key and self.location_hash)
