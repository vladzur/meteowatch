"""Módulo de acceso a la API de Open-Meteo."""

from meteowatch.api.client import OpenMeteoClient, OpenMeteoError

__all__ = ["OpenMeteoClient", "OpenMeteoError"]
