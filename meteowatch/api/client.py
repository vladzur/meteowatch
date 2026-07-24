"""Cliente HTTP para la API de pronóstico meteorológico de Open-Meteo.

Implementa los endpoints necesarios:
- Geocoding: búsqueda de ubicación por texto
- Forecast: pronóstico diario, por hora y condiciones actuales (todo en una llamada)

Open-Meteo es gratuito para uso no comercial (hasta 10,000 requests/día)
y no requiere autenticación.
"""

import logging
from typing import Optional, NamedTuple

import requests

from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast
from meteowatch.models.location import Location

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Variables diarias que solicitamos a la API
DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "weather_code",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "sunrise",
    "sunset",
    "daylight_duration",
    "sunshine_duration",
    "uv_index_max",
]

# Variables horarias que solicitamos a la API
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "uv_index",
    "is_day",
]

# Variables de condiciones actuales
CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "precipitation",
    "precipitation_probability",
    "is_day",
    "pressure_msl",
    "uv_index",
]


class OpenMeteoError(Exception):
    """Excepción base para errores de la API de Open-Meteo."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CurrentWeather(NamedTuple):
    """Condiciones meteorológicas actuales."""

    temperature: float
    humidity: int
    feels_like: float
    symbol: int
    clouds: int
    wind_speed: int
    wind_gust: int
    wind_direction: int
    precipitation: float
    precipitation_probability: int
    is_day: bool
    pressure: int
    uv_index: float


class ForecastResult(NamedTuple):
    """Resultado combinado de una llamada a la API de forecast."""

    daily: DailyForecast
    hourly: HourlyForecast
    current: CurrentWeather
    raw: dict


class OpenMeteoClient:
    """Cliente HTTP para interactuar con la API de Open-Meteo.

    No requiere autenticación. La API gratuita permite hasta 10,000
    requests diarios sin clave.
    """

    def __init__(self):
        """Inicializa el cliente HTTP."""
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
        })
        self._session.timeout = 15

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    def search_location(self, text: str, count: int = 10,
                        language: str = "es") -> list[Location]:
        """Busca ubicaciones por nombre de texto.

        Args:
            text: Texto de búsqueda (nombre de ciudad, región, etc.).
            count: Número máximo de resultados.
            language: Idioma para los nombres de ubicación.

        Returns:
            Lista de ubicaciones que coinciden con la búsqueda.
        """
        logger.info("Buscando ubicación: '%s'", text)
        params = {
            "name": text,
            "count": count,
            "language": language,
            "format": "json",
        }

        try:
            response = self._session.get(GEOCODING_URL, params=params)
        except requests.RequestException as e:
            logger.exception("Error de conexión con la API de geocoding")
            raise OpenMeteoError(f"Error de conexión: {e}") from e

        if response.status_code >= 400:
            try:
                error_data = response.json()
                reason = error_data.get("reason", f"HTTP {response.status_code}")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            logger.error("Geocoding error: %s", reason)
            raise OpenMeteoError(reason, status_code=response.status_code)

        try:
            data = response.json()
        except ValueError:
            logger.error("Respuesta no es JSON: %s", response.text[:500])
            raise OpenMeteoError("Respuesta inválida de la API (no es JSON)")

        results = data.get("results", [])
        logger.info("Encontradas %d ubicaciones para '%s'", len(results), text)
        return [Location.from_dict(loc) for loc in results]

    # ------------------------------------------------------------------
    # Forecast (daily + hourly + current en una sola llamada)
    # ------------------------------------------------------------------

    def get_forecast(self, latitude: float, longitude: float,
                     timezone: str = "auto",
                     forecast_days: int = 7) -> ForecastResult:
        """Obtiene pronóstico diario, por hora y condiciones actuales.

        Realiza una única llamada HTTP que incluye daily, hourly y current.

        Args:
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA o "auto" para detección automática.
            forecast_days: Número de días de pronóstico (máx. 16).

        Returns:
            ForecastResult con daily, hourly y current.
        """
        logger.info(
            "Obteniendo forecast: lat=%.4f, lon=%.4f, tz=%s, days=%d",
            latitude, longitude, timezone, forecast_days,
        )

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "forecast_days": forecast_days,
            "daily": ",".join(DAILY_VARIABLES),
            "hourly": ",".join(HOURLY_VARIABLES),
            "current": ",".join(CURRENT_VARIABLES),
        }

        try:
            response = self._session.get(FORECAST_URL, params=params)
        except requests.RequestException as e:
            logger.exception("Error de conexión con la API de forecast")
            raise OpenMeteoError(f"Error de conexión: {e}") from e

        if response.status_code >= 400:
            try:
                error_data = response.json()
                reason = error_data.get("reason", f"HTTP {response.status_code}")
            except ValueError:
                reason = f"HTTP {response.status_code}"
            logger.error("Forecast error: %s", reason)
            raise OpenMeteoError(reason, status_code=response.status_code)

        try:
            data = response.json()
        except ValueError:
            logger.error("Respuesta no es JSON: %s", response.text[:500])
            raise OpenMeteoError("Respuesta inválida de la API (no es JSON)")

        logger.debug(
            "Forecast recibido: daily=%d días, hourly=%d horas, current=%s",
            len(data.get("daily", {}).get("time", [])),
            len(data.get("hourly", {}).get("time", [])),
            "present" if data.get("current") else "absent",
        )

        # Parsear cada bloque
        daily = DailyForecast.from_openmeteo_daily(data)
        hourly = HourlyForecast.from_openmeteo_hourly(data)
        current = self._parse_current(data)

        return ForecastResult(
            daily=daily,
            hourly=hourly,
            current=current,
            raw=data,
        )

    def get_daily_forecast(self, latitude: float, longitude: float,
                           timezone: str = "auto",
                           forecast_days: int = 7) -> DailyForecast:
        """Obtiene solo el pronóstico diario.

        Args:
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA.
            forecast_days: Número de días.

        Returns:
            DailyForecast con los días de pronóstico.
        """
        result = self.get_forecast(latitude, longitude, timezone, forecast_days)
        return result.daily

    def get_hourly_forecast(self, latitude: float, longitude: float,
                            timezone: str = "auto",
                            forecast_days: int = 7) -> HourlyForecast:
        """Obtiene solo el pronóstico por hora.

        Args:
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA.
            forecast_days: Número de días.

        Returns:
            HourlyForecast con las horas de pronóstico.
        """
        result = self.get_forecast(latitude, longitude, timezone, forecast_days)
        return result.hourly

    def get_current_weather(self, latitude: float, longitude: float,
                            timezone: str = "auto") -> CurrentWeather:
        """Obtiene solo las condiciones actuales.

        Args:
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA.

        Returns:
            CurrentWeather con las condiciones actuales.
        """
        result = self.get_forecast(latitude, longitude, timezone, forecast_days=1)
        return result.current

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_current(data: dict) -> CurrentWeather:
        """Parsea el bloque 'current' de la respuesta de Open-Meteo.

        Args:
            data: Diccionario completo de la respuesta de la API.

        Returns:
            CurrentWeather con los valores parseados.
        """
        current = data.get("current", {})
        is_day_val = int(current.get("is_day", 1))

        return CurrentWeather(
            temperature=float(current.get("temperature_2m", 0.0)),
            humidity=int(float(current.get("relative_humidity_2m", 0))),
            feels_like=float(current.get("apparent_temperature", 0.0)),
            symbol=int(current.get("weather_code", 0)),
            clouds=int(float(current.get("cloud_cover", 0))),
            wind_speed=int(float(current.get("wind_speed_10m", 0))),
            wind_gust=int(float(current.get("wind_gusts_10m", 0))),
            wind_direction=int(float(current.get("wind_direction_10m", 0))),
            precipitation=float(current.get("precipitation", 0.0)),
            precipitation_probability=int(
                float(current.get("precipitation_probability", 0))
            ),
            is_day=is_day_val == 1,
            pressure=int(float(current.get("pressure_msl", 0))),
            uv_index=float(current.get("uv_index", 0.0)),
        )
