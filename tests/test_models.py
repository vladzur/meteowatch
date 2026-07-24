"""Tests para los modelos de datos (Open-Meteo)."""

import pytest

from meteowatch.models.daily import DailyForecast, DayData, _parse_iso_to_ms, _safe_get
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.models.location import Location


class TestLocation:
    """Pruebas para el modelo Location (geocoding de Open-Meteo)."""

    def test_from_dict_parses_all_fields(self):
        data = {
            "id": 3117735,
            "name": "Madrid",
            "latitude": 40.4165,
            "longitude": -3.70256,
            "country": "España",
            "country_code": "ES",
            "admin1": "Comunidad de Madrid",
            "timezone": "Europe/Madrid",
            "elevation": 665.0,
        }
        loc = Location.from_dict(data)
        assert loc.id == 3117735
        assert loc.name == "Madrid"
        assert loc.latitude == 40.4165
        assert loc.longitude == -3.70256
        assert loc.country == "España"
        assert loc.country_code == "ES"
        assert loc.admin1 == "Comunidad de Madrid"
        assert loc.timezone == "Europe/Madrid"
        assert loc.elevation == 665.0

    def test_display_name_formats_correctly(self):
        loc = Location(
            id=1, name="Barcelona", latitude=41.3874, longitude=2.1686,
            country="España", country_code="ES", admin1="Cataluña",
            timezone="Europe/Madrid", elevation=12.0,
        )
        assert loc.display_name == "Barcelona, Cataluña (España)"

    def test_display_name_without_admin1(self):
        loc = Location(
            id=1, name="Gibraltar", latitude=36.1408, longitude=-5.3536,
            country="Gibraltar", country_code="GI", admin1="",
            timezone="Europe/Gibraltar", elevation=0.0,
        )
        assert loc.display_name == "Gibraltar (Gibraltar)"

    def test_from_dict_with_missing_fields(self):
        loc = Location.from_dict({})
        assert loc.id == 0
        assert loc.name == ""
        assert loc.latitude == 0.0
        assert loc.longitude == 0.0
        assert loc.country == ""
        assert loc.timezone == "UTC"


class TestDayData:
    """Pruebas para el modelo DayData (Open-Meteo)."""

    def test_from_dict_parses_all_fields(self):
        data = {
            "start": 1701730800000, "symbol": 61,
            "temperature_min": 8.5, "temperature_max": 16.2,
            "wind_speed": 18, "wind_gust": 35, "wind_direction": 225,
            "precipitation": 2.3, "rain_probability": 60,
            "uv_index_max": 3.1, "sun_in": 1701759984000,
            "sun_out": 1701794875000, "daylight_duration": 34560,
            "sunshine_duration": 12400,
        }
        day = DayData.from_dict(data)
        assert day.symbol == 61
        assert day.temperature_min == 8.5
        assert day.temperature_max == 16.2
        assert day.wind_speed == 18
        assert day.wind_direction == 225
        assert day.precipitation == 2.3
        assert day.rain_probability == 60
        assert day.uv_index_max == 3.1

    def test_from_dict_with_missing_fields(self):
        day = DayData.from_dict({})
        assert day.symbol == 0
        assert day.temperature_max == 0.0
        assert day.start == 0
        assert day.precipitation == 0.0

    def test_from_openmeteo_daily_parses_row(self):
        row = {
            "start": 1701730800000, "symbol": 3,
            "temperature_min": 10.0, "temperature_max": 20.0,
            "wind_speed": 12, "wind_gust": 25, "wind_direction": 90,
            "precipitation": 0.0, "rain_probability": 5,
            "uv_index_max": 5.0, "sun_in": 1701760000000,
            "sun_out": 1701800000000, "daylight_duration": 40000,
            "sunshine_duration": 25000,
        }
        day = DayData.from_openmeteo_daily(row)
        assert day.symbol == 3
        assert day.temperature_max == 20.0
        assert day.wind_direction == 90
        assert day.uv_index_max == 5.0


class TestDailyForecast:
    """Pruebas para DailyForecast.from_openmeteo_daily (formato columnar)."""

    def test_from_openmeteo_parses_columnar_response(self):
        data = {
            "latitude": 40.4165, "longitude": -3.70256,
            "elevation": 665.0, "timezone": "Europe/Madrid",
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
        }
        forecast = DailyForecast.from_openmeteo_daily(data)
        assert forecast.latitude == 40.4165
        assert forecast.longitude == -3.70256
        assert forecast.elevation == 665.0
        assert forecast.timezone == "Europe/Madrid"
        assert len(forecast.days) == 2

        day0 = forecast.days[0]
        assert day0.symbol == 1
        assert day0.temperature_max == 15.0
        assert day0.temperature_min == 5.0
        assert day0.wind_speed == 20
        assert day0.wind_gust == 35
        assert day0.wind_direction == 180
        assert day0.precipitation == 0.0
        assert day0.rain_probability == 0
        assert day0.uv_index_max == 3.0

        day1 = forecast.days[1]
        assert day1.symbol == 61
        assert day1.temperature_max == 12.5
        assert day1.precipitation == 5.2
        assert day1.rain_probability == 80

    def test_from_openmeteo_with_empty_days(self):
        data = {"latitude": 0.0, "longitude": 0.0, "daily": {"time": []}}
        forecast = DailyForecast.from_openmeteo_daily(data)
        assert len(forecast.days) == 0

    def test_from_openmeteo_with_missing_daily_key(self):
        forecast = DailyForecast.from_openmeteo_daily({"latitude": 0.0, "longitude": 0.0})
        assert len(forecast.days) == 0


class TestHourData:
    """Pruebas para el modelo HourData (Open-Meteo)."""

    def test_from_dict_parses_all_fields(self):
        data = {
            "end": 1701734400000, "precipitation": 0.0, "night": False,
            "clouds": 46, "symbol": 3, "humidity": 72, "pressure": 1019,
            "wind_gust": 16, "wind_speed": 7, "temperature": 12.5,
            "uv_index_max": 2.0, "wind_direction": 315,
            "rain_probability": 10, "temperature_feels_like": 11.0,
        }
        hour = HourData.from_dict(data)
        assert hour.end == 1701734400000
        assert hour.precipitation == 0.0
        assert hour.night is False
        assert hour.symbol == 3
        assert hour.humidity == 72
        assert hour.wind_direction == 315
        assert hour.temperature == 12.5

    def test_from_openmeteo_hourly_derives_night(self):
        row = {"end": 0, "symbol": 0, "night": False, "temperature": 20.0}
        hour = HourData.from_openmeteo_hourly(row)
        assert hour.night is False

        row_night = {"end": 0, "symbol": 0, "night": True, "temperature": 10.0}
        hour2 = HourData.from_openmeteo_hourly(row_night)
        assert hour2.night is True


class TestHourlyForecast:
    """Pruebas para HourlyForecast.from_openmeteo_hourly."""

    def test_from_openmeteo_parses_columnar_response(self):
        data = {
            "latitude": 40.4165, "longitude": -3.70256,
            "timezone": "Europe/Madrid",
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
        }
        forecast = HourlyForecast.from_openmeteo_hourly(data)
        assert forecast.latitude == 40.4165
        assert forecast.longitude == -3.70256
        assert forecast.timezone == "Europe/Madrid"
        assert len(forecast.hours) == 2

        h0 = forecast.hours[0]
        assert h0.temperature == 14.5
        assert h0.humidity == 60
        assert h0.temperature_feels_like == 13.0
        assert h0.precipitation == 0.0
        assert h0.symbol == 2
        assert h0.clouds == 40
        assert h0.pressure == 1020
        assert h0.wind_speed == 8
        assert h0.wind_gust == 15
        assert h0.wind_direction == 270
        assert h0.uv_index_max == 3.0
        assert h0.night is False
        assert h0.rain_probability == 0

    def test_from_openmeteo_with_empty_hours(self):
        data = {"latitude": 0.0, "longitude": 0.0, "hourly": {"time": []}}
        forecast = HourlyForecast.from_openmeteo_hourly(data)
        assert len(forecast.hours) == 0


class TestHelpers:
    """Pruebas para funciones auxiliares de los modelos."""

    def test_parse_iso_to_ms_valid(self):
        result = _parse_iso_to_ms("2024-12-05T12:00")
        assert result > 0
        assert isinstance(result, int)

    def test_parse_iso_to_ms_empty(self):
        assert _parse_iso_to_ms("") == 0
        assert _parse_iso_to_ms("not-a-date") == 0

    def test_safe_get_with_value(self):
        block = {"key": [10, 20, 30]}
        assert _safe_get(block, "key", 1, 0) == 20

    def test_safe_get_missing_key(self):
        assert _safe_get({}, "missing", 0, 99) == 99

    def test_safe_get_out_of_range(self):
        assert _safe_get({"key": [1, 2]}, "key", 5, -1) == -1
