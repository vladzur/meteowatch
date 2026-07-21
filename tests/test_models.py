"""Tests para los modelos de datos."""

import pytest

from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.models.location import Location


class TestLocation:
    """Pruebas para el modelo Location."""

    def test_from_dict_parses_all_fields(self):
        """Debe parsear correctamente todos los campos de una ubicación."""
        data = {
            "hash": "2f221a18eb86380369570b2ed147d8b4",
            "name": "Madrid",
            "description": "Comunidad de Madrid",
            "country_name": "Spain",
        }
        loc = Location.from_dict(data)
        assert loc.hash == "2f221a18eb86380369570b2ed147d8b4"
        assert loc.name == "Madrid"
        assert loc.description == "Comunidad de Madrid"
        assert loc.country_name == "Spain"

    def test_display_name_formats_correctly(self):
        """Debe formatear el nombre descriptivo correctamente."""
        loc = Location(
            hash="abc",
            name="Barcelona",
            description="Cataluña",
            country_name="Spain",
        )
        assert loc.display_name == "Barcelona, Cataluña (Spain)"

    def test_from_dict_with_missing_fields(self):
        """Debe manejar campos faltantes con valores por defecto."""
        data = {}
        loc = Location.from_dict(data)
        assert loc.hash == ""
        assert loc.name == ""
        assert loc.description == ""
        assert loc.country_name == ""


class TestDayData:
    """Pruebas para el modelo DayData (día individual dentro del array days)."""

    def test_from_dict_parses_all_fields(self):
        """Debe parsear correctamente todos los campos de un día."""
        data = {
            "start": 1701730800000,
            "symbol": 32,
            "temperature_min": 3.32,
            "temperature_max": 16.56,
            "wind_speed": 12,
            "wind_gust": 26,
            "wind_direction": "SE",
            "rain": 0,
            "rain_probability": 20,
            "humidity": 72,
            "pressure": 1019,
            "snowline": 2700,
            "uv_index_max": 1.9,
            "sun_in": 1701759984000,
            "sun_mid": 1701777436000,
            "sun_out": 1701794875000,
            "moon_in": 1701732496000,
            "moon_out": 1701780616000,
            "moon_symbol": 21,
            "moon_illumination": 47.97,
        }
        day = DayData.from_dict(data)
        assert day.symbol == 32
        assert day.temperature_min == 3.32
        assert day.temperature_max == 16.56
        assert day.wind_speed == 12
        assert day.wind_direction == "SE"
        assert day.humidity == 72
        assert day.rain_probability == 20
        assert day.uv_index_max == 1.9

    def test_from_dict_with_missing_fields(self):
        """Debe manejar campos faltantes con valores por defecto."""
        data = {}
        day = DayData.from_dict(data)
        assert day.symbol == 0
        assert day.temperature_max == 0.0
        assert day.temperature_min == 0.0
        assert day.start == 0


class TestDailyForecast:
    """Pruebas para el modelo DailyForecast (respuesta completa)."""

    def test_from_dict_parses_forecast_with_days(self):
        """Debe parsear correctamente la respuesta con array de días."""
        data = {
            "hash": "994007b68e592e9227025715c0c3cb45",
            "name": "Lorca",
            "url": "https://www.theweather.com/lorca-in-spain-c4513.htm",
            "days": [
                {
                    "start": 1701730800000,
                    "symbol": 32,
                    "temperature_min": 3.32,
                    "temperature_max": 16.56,
                    "wind_speed": 12,
                    "wind_gust": 26,
                    "wind_direction": "SE",
                    "rain": 0,
                    "rain_probability": 20,
                    "humidity": 72,
                    "pressure": 1019,
                    "snowline": 2700,
                    "uv_index_max": 1.9,
                    "sun_in": 1701759984000,
                    "sun_mid": 1701777436000,
                    "sun_out": 1701794875000,
                    "moon_in": 1701732496000,
                    "moon_out": 1701780616000,
                    "moon_symbol": 21,
                    "moon_illumination": 47.97,
                },
                {
                    "start": 1701817200000,
                    "symbol": 26,
                    "temperature_min": 5.0,
                    "temperature_max": 18.0,
                    "wind_speed": 8,
                    "wind_gust": 15,
                    "wind_direction": "N",
                    "rain": 0,
                    "rain_probability": 10,
                    "humidity": 65,
                    "pressure": 1020,
                    "snowline": 2800,
                    "uv_index_max": 2.5,
                    "sun_in": 1701846384000,
                    "sun_mid": 1701863836000,
                    "sun_out": 1701881275000,
                    "moon_in": 1701818896000,
                    "moon_out": 1701867016000,
                    "moon_symbol": 22,
                    "moon_illumination": 38.5,
                },
            ],
        }
        forecast = DailyForecast.from_dict(data)
        assert forecast.hash == "994007b68e592e9227025715c0c3cb45"
        assert forecast.name == "Lorca"
        assert forecast.url == "https://www.theweather.com/lorca-in-spain-c4513.htm"
        assert len(forecast.days) == 2
        assert forecast.days[0].symbol == 32
        assert forecast.days[0].temperature_max == 16.56
        assert forecast.days[1].symbol == 26
        assert forecast.days[1].temperature_max == 18.0

    def test_from_dict_with_empty_days(self):
        """Debe manejar un array de días vacío."""
        data = {"hash": "", "name": "", "url": "", "days": []}
        forecast = DailyForecast.from_dict(data)
        assert len(forecast.days) == 0

    def test_from_dict_with_missing_days_key(self):
        """Debe manejar la ausencia de la clave days."""
        data = {"hash": "abc", "name": "Test", "url": ""}
        forecast = DailyForecast.from_dict(data)
        assert forecast.hash == "abc"
        assert forecast.name == "Test"
        assert len(forecast.days) == 0


class TestHourData:
    """Pruebas para el modelo HourData."""

    def test_from_dict_parses_all_fields(self):
        """Debe parsear correctamente todos los campos de una hora."""
        data = {
            "end": 1701734400000,
            "rain": 0,
            "night": True,
            "clouds": 46,
            "symbol": 3,
            "humidity": 93,
            "pressure": 1019,
            "snowline": 3100,
            "wind_gust": 16,
            "wind_speed": 7,
            "temperature": 7.78,
            "uv_index_max": 0,
            "wind_direction": "NW",
            "rain_probability": 0,
            "temperature_feels_like": 6.87,
        }
        hour = HourData.from_dict(data)
        assert hour.end == 1701734400000
        assert hour.rain == 0.0
        assert hour.night is True
        assert hour.clouds == 46
        assert hour.symbol == 3
        assert hour.humidity == 93
        assert hour.pressure == 1019
        assert hour.snowline == 3100
        assert hour.wind_gust == 16
        assert hour.wind_speed == 7
        assert hour.temperature == 7.78
        assert hour.uv_index_max == 0.0
        assert hour.wind_direction == "NW"
        assert hour.rain_probability == 0
        assert hour.temperature_feels_like == 6.87

    def test_from_dict_with_missing_fields(self):
        """Debe manejar campos faltantes con valores por defecto."""
        data = {}
        hour = HourData.from_dict(data)
        assert hour.end == 0
        assert hour.temperature == 0.0
        assert hour.night is False


class TestHourlyForecast:
    """Pruebas para el modelo HourlyForecast."""

    def test_from_dict_parses_forecast_with_hours(self):
        """Debe parsear correctamente un pronóstico con array de horas."""
        data = {
            "url": "https://www.theweather.com/lorca-in-spain-c4513.htm",
            "hash": "994007b68e592e9227025715c0c3cb45",
            "name": "Lorca",
            "start": 1701730800000,
            "hours": [
                {
                    "end": 1701734400000,
                    "rain": 0,
                    "night": True,
                    "clouds": 46,
                    "symbol": 3,
                    "humidity": 93,
                    "pressure": 1019,
                    "snowline": 3100,
                    "wind_gust": 16,
                    "wind_speed": 7,
                    "temperature": 7.78,
                    "uv_index_max": 0,
                    "wind_direction": "NW",
                    "rain_probability": 0,
                    "temperature_feels_like": 6.87,
                },
                {
                    "end": 1701738000000,
                    "rain": 0,
                    "night": True,
                    "clouds": 52,
                    "symbol": 4,
                    "humidity": 89,
                    "pressure": 1018,
                    "snowline": 3050,
                    "wind_gust": 14,
                    "wind_speed": 6,
                    "temperature": 8.12,
                    "uv_index_max": 0,
                    "wind_direction": "N",
                    "rain_probability": 5,
                    "temperature_feels_like": 7.45,
                },
            ],
        }
        forecast = HourlyForecast.from_dict(data)
        assert forecast.name == "Lorca"
        assert forecast.start == 1701730800000
        assert len(forecast.hours) == 2
        assert forecast.hours[0].temperature == 7.78
        assert forecast.hours[1].temperature == 8.12

    def test_from_dict_with_empty_hours(self):
        """Debe manejar un array de horas vacío."""
        data = {
            "url": "",
            "hash": "",
            "name": "",
            "start": 0,
            "hours": [],
        }
        forecast = HourlyForecast.from_dict(data)
        assert len(forecast.hours) == 0
