"""Cliente HTTP para la API de pronóstico meteorológico de Meteored.

Implementa los tres endpoints disponibles:
- Búsqueda de ubicación por texto
- Pronóstico diario (5 días)
- Pronóstico por hora (hoy)
"""

import json
import logging
import time
from typing import Optional

import requests

from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast
from meteowatch.models.location import Location

logger = logging.getLogger(__name__)

BASE_URL = "https://api.meteored.com"


class MeteoredError(Exception):
    """Excepción base para errores de la API de Meteored."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MeteoredClient:
    """Cliente HTTP para interactuar con la API de Meteored.

    Maneja autenticación vía header x-api-key y rate limiting básico.
    """

    def __init__(self, api_key: str):
        """Inicializa el cliente con la API key proporcionada.

        Args:
            api_key: Clave de API de Meteored para autenticación.
        """
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key": api_key,
            "Accept": "application/json",
        })
        self._session.timeout = 15  # timeout por defecto en segundos
        self._last_request_time: float = 0

    def _respect_rate_limit(self) -> None:
        """Aplica una pausa mínima entre requests para evitar rate limiting."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.monotonic()

    def _request(self, method: str, path: str) -> dict:
        """Realiza una petición HTTP y maneja errores de forma centralizada.

        Args:
            method: Método HTTP (GET, POST, etc.).
            path: Ruta relativa del endpoint (sin BASE_URL).

        Returns:
            Diccionario con la respuesta JSON parseada.

        Raises:
            MeteoredError: Si la API retorna un error o hay un fallo de conexión.
        """
        self._respect_rate_limit()
        url = f"{BASE_URL}{path}"

        logger.debug(">>> %s %s", method, url)

        try:
            response = self._session.request(method, url)
        except requests.RequestException as e:
            logger.exception("Error de conexión con la API")
            raise MeteoredError(f"Error de conexión: {e}") from e

        logger.debug("<<< HTTP %s (%d bytes)", response.status_code, len(response.content))

        # Procesar respuesta
        try:
            data = response.json()
        except ValueError:
            logger.error("Respuesta no es JSON: %s", response.text[:500])
            raise MeteoredError(
                "Respuesta inválida de la API (no es JSON)",
                status_code=response.status_code,
            )

        # Log de la estructura de respuesta (primeros 500 chars)
        logger.debug("Respuesta JSON: ok=%s, data type=%s",
                     data.get("ok"), type(data.get("data")).__name__)

        # Verificar errores de la API
        if not data.get("ok", False):
            error_msg = data.get("info", {}).get("message", "Error desconocido")
            logger.error("API retornó error: %s", error_msg)
            raise MeteoredError(error_msg, status_code=response.status_code)

        if response.status_code >= 400:
            error_msg = data.get("info", {}).get("message", f"HTTP {response.status_code}")
            logger.error("HTTP error %s: %s", response.status_code, error_msg)
            raise MeteoredError(error_msg, status_code=response.status_code)

        return data

    def search_location(self, text: str) -> list[Location]:
        """Busca ubicaciones por nombre de texto.

        Args:
            text: Texto de búsqueda (nombre de ciudad, región, etc.).

        Returns:
            Lista de ubicaciones que coinciden con la búsqueda.
        """
        logger.info("Buscando ubicación: '%s'", text)
        path = f"/api/location/v1/search/txt/{text}"
        data = self._request("GET", path)

        locations_data = data.get("data", {}).get("locations", [])
        logger.info("Encontradas %d ubicaciones para '%s'", len(locations_data), text)
        return [Location.from_dict(loc) for loc in locations_data]

    def get_daily_forecast(self, location_hash: str) -> DailyForecast:
        """Obtiene el pronóstico diario para una ubicación (5 días).

        Args:
            location_hash: Hash de la ubicación obtenido de la búsqueda.

        Returns:
            Objeto DailyForecast con los datos del día actual.
        """
        logger.info("Obteniendo pronóstico diario para hash=%s", location_hash)
        path = f"/api/forecast/v1/daily/{location_hash}"
        data = self._request("GET", path)

        forecast_data = data.get("data", {})

        # Volcar estructura real de la respuesta para diagnóstico
        if isinstance(forecast_data, dict):
            logger.debug("Claves en data: %s", sorted(forecast_data.keys()))
            num_days = len(forecast_data.get("days", []))
            logger.debug("JSON crudo (daily, %d días): %s",
                        num_days,
                        json.dumps(forecast_data, ensure_ascii=False, default=str)[:500])

        return DailyForecast.from_dict(forecast_data)

    def get_hourly_forecast(self, location_hash: str) -> HourlyForecast:
        """Obtiene el pronóstico por hora para una ubicación (hoy).

        Args:
            location_hash: Hash de la ubicación obtenido de la búsqueda.

        Returns:
            Objeto HourlyForecast con los datos hora a hora.
        """
        logger.info("Obteniendo pronóstico por hora para hash=%s", location_hash)
        path = f"/api/forecast/v1/hourly/{location_hash}"
        data = self._request("GET", path)

        forecast_data = data.get("data", {})

        # Volcar estructura real para diagnóstico
        if isinstance(forecast_data, dict):
            logger.debug("Claves en data (hourly): %s", sorted(forecast_data.keys()))
            logger.debug("JSON crudo (hourly, primeros 500 chars): %s",
                        json.dumps(forecast_data, ensure_ascii=False, default=str)[:500])

        num_hours = len(forecast_data.get("hours", [])) if isinstance(forecast_data, dict) else 0
        logger.info("Pronóstico por hora: name=%s, %d horas",
                   forecast_data.get("name") if isinstance(forecast_data, dict) else "?",
                   num_hours)
        return HourlyForecast.from_dict(forecast_data)
