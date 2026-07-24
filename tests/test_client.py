"""Tests para el cliente de Open-Meteo."""

import json
from unittest.mock import Mock, patch

import pytest

from meteowatch.api.client import (
    OpenMeteoClient,
    OpenMeteoError,
    CurrentWeather,
    ForecastResult,
)
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast
from meteowatch.models.location import Location


# ------------------------------------------------------------------
# Fixtures: respuestas simuladas de la API
# ------------------------------------------------------------------

@pytest.fixture
def mock_geocoding_response():
    """Respuesta simulada de la API de geocoding."""
    return {
        "results": [
            {
                "id": 3117735,
                "name": "Madrid",
                "latitude": 40.4165,
                "longitude": -3.70256,
                "country": "España",
                "country_code": "ES",
                "admin1": "Comunidad de Madrid",
                "timezone": "Europe/Madrid",
                "elevation": 665.0,
            },
        ]
    }


@pytest.fixture
def mock_forecast_response():
    """Respuesta simulada de la API de forecast."""
    return {
        "latitude": 40.4165,
        "longitude": -3.70256,
        "elevation": 665.0,
        "timezone": "Europe/Madrid",
        "daily": {
            "time": ["2024-12-05", "2024-12-06"],
            "weather_code": [1, 61],
            "temperature_2m_max": [15.0, 12.5],
            "temperature_2m_min": [5.0, 7.0],
            "wind_speed_10m_max": [20.0, 35.0],
            "wind_gusts_10m_max": [35.0, 55.0],
            "wind_direction_10m_dominant": [180, 225],
            "precipitation_sum": [0.0, 5.2],
            "precipitation_probability_max": [0, 80],
            "uv_index_max": [3.0, 1.5],
            "sunrise": ["2024-12-05T08:30", "2024-12-06T08:31"],
            "sunset": ["2024-12-05T17:49", "2024-12-06T17:48"],
            "daylight_duration": [33564.0, 33420.0],
            "sunshine_duration": [28000.0, 5000.0],
        },
        "hourly": {
            "time": ["2024-12-05T12:00", "2024-12-05T13:00"],
            "temperature_2m": [14.5, 15.2],
            "relative_humidity_2m": [60, 55],
            "apparent_temperature": [13.0, 14.0],
            "precipitation": [0.0, 0.0],
            "precipitation_probability": [0, 5],
            "weather_code": [2, 3],
            "cloud_cover": [40, 60],
            "pressure_msl": [1020.0, 1019.0],
            "wind_speed_10m": [8.0, 10.0],
            "wind_gusts_10m": [15.0, 18.0],
            "wind_direction_10m": [270, 280],
            "uv_index": [3.0, 3.5],
            "is_day": [1, 1],
        },
        "current": {
            "time": "2024-12-05T12:00",
            "interval": 900,
            "temperature_2m": 14.8,
            "relative_humidity_2m": 58,
            "apparent_temperature": 13.5,
            "weather_code": 2,
            "cloud_cover": 45,
            "wind_speed_10m": 7.5,
            "wind_gusts_10m": 14.0,
            "wind_direction_10m": 260,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "is_day": 1,
            "pressure_msl": 1020.0,
            "uv_index": 3.0,
        },
    }


class TestOpenMeteoClientSearchLocation:
    """Pruebas para search_location."""

    def test_returns_parsed_locations(self, mock_geocoding_response):
        """Debe retornar una lista de objetos Location parseados."""
        mock = Mock()
        mock.json.return_value = mock_geocoding_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            locations = client.search_location("Madrid")

        assert len(locations) == 1
        loc = locations[0]
        assert isinstance(loc, Location)
        assert loc.name == "Madrid"
        assert loc.country == "España"
        assert loc.latitude == 40.4165
        assert loc.longitude == -3.70256
        assert loc.timezone == "Europe/Madrid"

    def test_handles_http_error(self):
        """Debe lanzar OpenMeteoError en errores HTTP."""
        mock = Mock()
        mock.json.return_value = {"error": True, "reason": "Bad request"}
        mock.status_code = 400

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            with pytest.raises(OpenMeteoError) as exc:
                client.search_location("x")
            assert "Bad request" in str(exc.value)

    def test_handles_connection_error(self):
        """Debe lanzar OpenMeteoError en errores de conexión."""
        import requests

        with patch("requests.Session.get", side_effect=requests.ConnectionError("timeout")):
            client = OpenMeteoClient()
            with pytest.raises(OpenMeteoError) as exc:
                client.search_location("Madrid")
            assert "conexión" in str(exc.value).lower()


class TestOpenMeteoClientGetForecast:
    """Pruebas para get_forecast."""

    def test_get_forecast_returns_combined_result(self, mock_forecast_response):
        """Debe retornar ForecastResult con daily, hourly y current."""
        mock = Mock()
        mock.json.return_value = mock_forecast_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            result = client.get_forecast(40.4165, -3.70256)

        assert isinstance(result, ForecastResult)
        assert isinstance(result.daily, DailyForecast)
        assert isinstance(result.hourly, HourlyForecast)
        assert isinstance(result.current, CurrentWeather)
        assert len(result.daily.days) == 2
        assert len(result.hourly.hours) == 2

    def test_current_weather_is_parsed(self, mock_forecast_response):
        """Debe parsear correctamente las condiciones actuales."""
        mock = Mock()
        mock.json.return_value = mock_forecast_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            result = client.get_forecast(40.4165, -3.70256)

        current = result.current
        assert current.temperature == 14.8
        assert current.humidity == 58
        assert current.feels_like == 13.5
        assert current.symbol == 2
        assert current.clouds == 45
        assert current.wind_speed == 7
        assert current.wind_gust == 14
        assert current.wind_direction == 260
        assert current.precipitation == 0.0
        assert current.precipitation_probability == 0
        assert current.is_day is True
        assert current.pressure == 1020
        assert current.uv_index == 3.0

    def test_get_daily_forecast_convenience(self, mock_forecast_response):
        """get_daily_forecast debe retornar solo el DailyForecast."""
        mock = Mock()
        mock.json.return_value = mock_forecast_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            daily = client.get_daily_forecast(40.4165, -3.70256)

        assert isinstance(daily, DailyForecast)
        assert len(daily.days) == 2

    def test_get_hourly_forecast_convenience(self, mock_forecast_response):
        """get_hourly_forecast debe retornar solo el HourlyForecast."""
        mock = Mock()
        mock.json.return_value = mock_forecast_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            hourly = client.get_hourly_forecast(40.4165, -3.70256)

        assert isinstance(hourly, HourlyForecast)
        assert len(hourly.hours) == 2

    def test_get_current_weather_convenience(self, mock_forecast_response):
        """get_current_weather debe retornar solo el CurrentWeather."""
        mock = Mock()
        mock.json.return_value = mock_forecast_response
        mock.status_code = 200

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            current = client.get_current_weather(40.4165, -3.70256)

        assert isinstance(current, CurrentWeather)
        assert current.temperature == 14.8

    def test_get_forecast_handles_http_error(self):
        """Debe lanzar OpenMeteoError en errores HTTP."""
        mock = Mock()
        mock.json.return_value = {"error": True, "reason": "Invalid parameter"}
        mock.status_code = 400

        with patch("requests.Session.get", return_value=mock):
            client = OpenMeteoClient()
            with pytest.raises(OpenMeteoError) as exc:
                client.get_forecast(0, 0)
            assert "Invalid parameter" in str(exc.value)

    def test_client_initializes_without_api_key(self):
        """El cliente no debe requerir API key."""
        client = OpenMeteoClient()
        assert client is not None
        assert "x-api-key" not in client._session.headers
