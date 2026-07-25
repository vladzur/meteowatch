"""Tests para el motor de alertas climáticas."""

import time
from unittest.mock import Mock, patch

import pytest

from meteowatch.alerts.engine import AlertEngine, DEDUP_WINDOW_SECONDS
from meteowatch.alerts.rules import (
    Alert,
    WMO_ORANGE_CODES,
    WMO_YELLOW_CODES,
    WIND_GUST_YELLOW,
    WIND_GUST_ORANGE,
    FLASH_FLOOD_ORANGE,
    DAILY_RAIN_YELLOW,
    FROST_YELLOW,
    HEAT_YELLOW,
    CATEGORY_THUNDERSTORM,
    CATEGORY_FREEZING,
    CATEGORY_HEAVY_RAIN,
    CATEGORY_HEAVY_SNOW,
    CATEGORY_WIND,
    CATEGORY_FLASH_FLOOD,
    CATEGORY_DAILY_RAIN,
    CATEGORY_FROST,
    CATEGORY_HEAT,
)
from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourlyForecast, HourData


# ------------------------------------------------------------------
# Fixtures: datos de pronóstico simulados
# ------------------------------------------------------------------

def _make_hour_data(symbol=0, wind_gust=10.0, precipitation=0.0,
                    feels_like=20.0, end_ms=None):
    """Crea un HourData con valores por defecto para pruebas."""
    return HourData(
        end=end_ms or 1700000000000,
        precipitation=precipitation,
        night=False,
        clouds=0,
        symbol=symbol,
        humidity=50,
        pressure=1013,
        wind_gust=wind_gust,
        wind_speed=5,
        temperature=20.0,
        uv_index_max=3.0,
        wind_direction=180,
        rain_probability=0,
        temperature_feels_like=feels_like,
    )


def _make_day_data(symbol=0, precipitation_sum=0.0):
    """Crea un DayData con valores por defecto para pruebas."""
    return DayData(
        start=1700000000000,
        symbol=symbol,
        temperature_min=10.0,
        temperature_max=25.0,
        wind_speed=10,
        wind_gust=20,
        wind_direction=180,
        precipitation=precipitation_sum,
        rain_probability=0,
        uv_index_max=3.0,
        sun_in=1700020000000,
        sun_out=1700060000000,
        daylight_duration=40000,
        sunshine_duration=20000,
    )


@pytest.fixture
def engine():
    """Motor de alertas nuevo para cada prueba."""
    return AlertEngine()


# ------------------------------------------------------------------
# Tests: alertas por código WMO
# ------------------------------------------------------------------

class TestWMOAlerts:
    """Pruebas para alertas basadas en códigos WMO."""

    @pytest.mark.parametrize("code,expected_category", [
        (95, CATEGORY_THUNDERSTORM),
        (96, CATEGORY_THUNDERSTORM),
        (99, CATEGORY_THUNDERSTORM),
        (66, CATEGORY_FREEZING),
        (67, CATEGORY_FREEZING),
        (77, CATEGORY_FREEZING),
    ])
    def test_wmo_orange_codes_trigger_alert(self, engine, code, expected_category):
        """Los códigos WMO naranja deben disparar alerta naranja."""
        hours = [_make_hour_data(symbol=code)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        assert len(alerts) >= 1
        found = [a for a in alerts if a.source_code == code]
        assert len(found) == 1
        assert found[0].level == "orange"
        assert found[0].category == expected_category
        assert code in WMO_ORANGE_CODES
        assert found[0].message == WMO_ORANGE_CODES[code]

    @pytest.mark.parametrize("code,expected_category", [
        (65, CATEGORY_HEAVY_RAIN),
        (75, CATEGORY_HEAVY_SNOW),
    ])
    def test_wmo_yellow_codes_trigger_alert(self, engine, code, expected_category):
        """Los códigos WMO amarillos deben disparar alerta amarilla."""
        hours = [_make_hour_data(symbol=code)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        found = [a for a in alerts if a.source_code == code]
        assert len(found) == 1
        assert found[0].level == "yellow"
        assert found[0].category == expected_category
        assert code in WMO_YELLOW_CODES
        assert found[0].message == WMO_YELLOW_CODES[code]

    def test_wmo_benign_codes_no_alert(self, engine):
        """Códigos WMO benignos (0=despejado) no deben generar alertas."""
        hours = [_make_hour_data(symbol=0)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wmo_alerts = [a for a in alerts if a.source_code is not None]
        assert len(wmo_alerts) == 0

    def test_multiple_wmo_codes_in_window(self, engine):
        """Varios códigos WMO en la ventana de evaluación deben generar múltiples alertas."""
        hours = [
            _make_hour_data(symbol=95),  # tormenta naranja
            _make_hour_data(symbol=65),  # lluvia fuerte amarilla
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wmo_alerts = [a for a in alerts if a.source_code is not None]
        assert len(wmo_alerts) == 2
        levels = {a.level for a in wmo_alerts}
        assert "orange" in levels
        assert "yellow" in levels


# ------------------------------------------------------------------
# Tests: alertas por ráfagas de viento
# ------------------------------------------------------------------

class TestWindGustAlerts:
    """Pruebas para alertas de ráfagas de viento."""

    def test_no_alert_below_threshold(self, engine):
        """Viento por debajo del umbral no debe generar alerta."""
        hours = [_make_hour_data(wind_gust=WIND_GUST_YELLOW - 1)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wind_alerts = [a for a in alerts if a.category == CATEGORY_WIND]
        assert len(wind_alerts) == 0

    def test_yellow_alert_at_threshold(self, engine):
        """Ráfagas > 50 km/h deben generar alerta amarilla."""
        gust = WIND_GUST_YELLOW + 1
        hours = [_make_hour_data(wind_gust=gust)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wind_alerts = [a for a in alerts if a.category == CATEGORY_WIND]
        assert len(wind_alerts) == 1
        assert wind_alerts[0].level == "yellow"
        assert wind_alerts[0].value == gust

    def test_orange_alert_at_high_threshold(self, engine):
        """Ráfagas > 90 km/h deben generar alerta naranja."""
        gust = WIND_GUST_ORANGE + 5
        hours = [_make_hour_data(wind_gust=gust)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wind_alerts = [a for a in alerts if a.category == CATEGORY_WIND]
        assert len(wind_alerts) == 1
        assert wind_alerts[0].level == "orange"
        assert wind_alerts[0].value == gust

    def test_max_gust_across_hours(self, engine):
        """Debe usar el valor máximo de ráfaga en la ventana de horas."""
        hours = [
            _make_hour_data(wind_gust=30),
            _make_hour_data(wind_gust=WIND_GUST_YELLOW + 10),  # este dispara
            _make_hour_data(wind_gust=40),
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        wind_alerts = [a for a in alerts if a.category == CATEGORY_WIND]
        assert len(wind_alerts) == 1
        assert wind_alerts[0].level == "yellow"


# ------------------------------------------------------------------
# Tests: alertas por inundación repentina
# ------------------------------------------------------------------

class TestFlashFloodAlerts:
    """Pruebas para alertas de inundación repentina."""

    def test_no_alert_below_threshold(self, engine):
        """Precipitación por debajo del umbral no debe generar alerta."""
        hours = [_make_hour_data(precipitation=FLASH_FLOOD_ORANGE - 1)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        flood_alerts = [a for a in alerts if a.category == CATEGORY_FLASH_FLOOD]
        assert len(flood_alerts) == 0

    def test_orange_alert_above_threshold(self, engine):
        """Precipitación > 15 mm/h debe generar alerta naranja."""
        precip = FLASH_FLOOD_ORANGE + 5
        hours = [_make_hour_data(precipitation=precip)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        flood_alerts = [a for a in alerts if a.category == CATEGORY_FLASH_FLOOD]
        assert len(flood_alerts) == 1
        assert flood_alerts[0].level == "orange"
        assert flood_alerts[0].value == precip

    def test_checks_only_flash_flood_window(self, engine):
        """Solo debe verificar las primeras FLASH_FLOOD_WINDOW horas."""
        hours = [
            _make_hour_data(precipitation=0),               # hora 0
            _make_hour_data(precipitation=0),               # hora 1
            _make_hour_data(precipitation=FLASH_FLOOD_ORANGE + 10),  # hora 2 (dentro de ventana)
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        flood_alerts = [a for a in alerts if a.category == CATEGORY_FLASH_FLOOD]
        assert len(flood_alerts) == 1  # La hora 2 está dentro de la ventana


# ------------------------------------------------------------------
# Tests: alertas por lluvia diaria acumulada
# ------------------------------------------------------------------

class TestDailyRainAlerts:
    """Pruebas para alertas de acumulación diaria de lluvia."""

    def test_no_alert_below_threshold(self, engine):
        """Precipitación diaria por debajo del umbral no debe generar alerta."""
        hours = [_make_hour_data()]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data(precipitation_sum=DAILY_RAIN_YELLOW - 1)],
        )

        alerts = engine.evaluate(daily, hourly)

        rain_alerts = [a for a in alerts if a.category == CATEGORY_DAILY_RAIN]
        assert len(rain_alerts) == 0

    def test_yellow_alert_above_threshold(self, engine):
        """Precipitación diaria > 40 mm debe generar alerta amarilla."""
        daily_sum = DAILY_RAIN_YELLOW + 15
        hours = [_make_hour_data()]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data(precipitation_sum=daily_sum)],
        )

        alerts = engine.evaluate(daily, hourly)

        rain_alerts = [a for a in alerts if a.category == CATEGORY_DAILY_RAIN]
        assert len(rain_alerts) == 1
        assert rain_alerts[0].level == "yellow"
        assert rain_alerts[0].value == daily_sum

    def test_empty_daily_no_alert(self, engine):
        """Sin datos diarios no debe generar alerta de lluvia diaria."""
        hours = [_make_hour_data()]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[],
        )

        alerts = engine.evaluate(daily, hourly)

        rain_alerts = [a for a in alerts if a.category == CATEGORY_DAILY_RAIN]
        assert len(rain_alerts) == 0


# ------------------------------------------------------------------
# Tests: alertas por temperatura
# ------------------------------------------------------------------

class TestTemperatureAlerts:
    """Pruebas para alertas de temperatura peligrosa."""

    def test_frost_alert_below_zero(self, engine):
        """Sensación térmica < 0°C debe generar alerta amarilla por helada."""
        hours = [_make_hour_data(feels_like=-2.0)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        frost_alerts = [a for a in alerts if a.category == CATEGORY_FROST]
        assert len(frost_alerts) == 1
        assert frost_alerts[0].level == "yellow"
        assert frost_alerts[0].value == -2.0

    def test_heat_alert_above_35(self, engine):
        """Sensación térmica > 35°C debe generar alerta amarilla por calor."""
        hours = [_make_hour_data(feels_like=38.0)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        heat_alerts = [a for a in alerts if a.category == CATEGORY_HEAT]
        assert len(heat_alerts) == 1
        assert heat_alerts[0].level == "yellow"
        assert heat_alerts[0].value == 38.0

    def test_no_alert_in_normal_range(self, engine):
        """Temperatura en rango normal no debe generar alertas."""
        hours = [_make_hour_data(feels_like=22.0)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        temp_alerts = [a for a in alerts
                       if a.category in (CATEGORY_FROST, CATEGORY_HEAT)]
        assert len(temp_alerts) == 0

    def test_only_one_frost_alert_even_with_multiple_hours(self, engine):
        """Solo debe emitir una alerta de helada, no una por hora."""
        hours = [
            _make_hour_data(feels_like=-1.0),
            _make_hour_data(feels_like=-2.0),
            _make_hour_data(feels_like=-3.0),
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        frost_alerts = [a for a in alerts if a.category == CATEGORY_FROST]
        assert len(frost_alerts) == 1


# ------------------------------------------------------------------
# Tests: deduplicación
# ------------------------------------------------------------------

class TestDeduplication:
    """Pruebas para la deduplicación de alertas."""

    def test_duplicate_alert_suppressed(self, engine):
        """La misma alerta (category + level) no debe repetirse."""
        hours = [_make_hour_data(symbol=95)]  # tormenta naranja
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        # Primera evaluación: debe retornar la alerta
        alerts1 = engine.evaluate(daily, hourly)
        thunder1 = [a for a in alerts1 if a.category == CATEGORY_THUNDERSTORM]
        assert len(thunder1) == 1

        # Segunda evaluación inmediata: no debe retornar la misma alerta
        alerts2 = engine.evaluate(daily, hourly)
        thunder2 = [a for a in alerts2 if a.category == CATEGORY_THUNDERSTORM]
        assert len(thunder2) == 0

    def test_different_categories_not_duplicates(self, engine):
        """Alertas de distintas categorías no se consideran duplicadas."""
        hours = [_make_hour_data(symbol=95, wind_gust=WIND_GUST_YELLOW + 10)]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        alerts = engine.evaluate(daily, hourly)

        categories = {a.category for a in alerts}
        assert CATEGORY_THUNDERSTORM in categories
        assert CATEGORY_WIND in categories

    def test_alert_reappears_after_dedup_window(self, engine):
        """Una alerta debe reaparecer después de la ventana de deduplicación."""
        hours = [_make_hour_data(symbol=99)]  # tormenta severa
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data()],
        )

        # Primera evaluación
        alerts1 = engine.evaluate(daily, hourly)
        assert len([a for a in alerts1 if a.category == CATEGORY_THUNDERSTORM]) == 1

        # Simular que pasó la ventana de deduplicación
        engine._sent_alerts = {
            (CATEGORY_THUNDERSTORM, "orange"):
                time.time() - DEDUP_WINDOW_SECONDS - 60,
        }

        # Segunda evaluación: debe reaparecer
        alerts2 = engine.evaluate(daily, hourly)
        thunder2 = [a for a in alerts2 if a.category == CATEGORY_THUNDERSTORM]
        assert len(thunder2) == 1


# ------------------------------------------------------------------
# Tests: integración (evaluación completa)
# ------------------------------------------------------------------

class TestEvaluateIntegration:
    """Pruebas de integración para evaluar múltiples tipos de alertas."""

    def test_no_alerts_with_calm_weather(self, engine):
        """Clima tranquilo no debe generar ninguna alerta."""
        hours = [
            _make_hour_data(symbol=1, wind_gust=10, precipitation=0, feels_like=20)
            for _ in range(6)
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data(precipitation_sum=2.0)],
        )

        alerts = engine.evaluate(daily, hourly)
        assert len(alerts) == 0

    def test_multiple_alert_types_detected(self, engine):
        """Debe detectar múltiples tipos de alerta simultáneamente."""
        hours = [
            _make_hour_data(
                symbol=65,           # lluvia fuerte (amarillo WMO)
                wind_gust=WIND_GUST_ORANGE + 5,  # viento naranja
                precipitation=FLASH_FLOOD_ORANGE + 8,  # inundación naranja
                feels_like=-3.0,     # helada amarilla
            ),
        ]
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=hours,
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC",
            days=[_make_day_data(precipitation_sum=DAILY_RAIN_YELLOW + 10)],
        )

        alerts = engine.evaluate(daily, hourly)

        categories = {a.category for a in alerts}
        assert CATEGORY_HEAVY_RAIN in categories    # WMO 65
        assert CATEGORY_WIND in categories           # wind gusts > 90
        assert CATEGORY_FLASH_FLOOD in categories    # precipitation > 15mm/h
        assert CATEGORY_FROST in categories          # feels_like < 0
        assert CATEGORY_DAILY_RAIN in categories     # daily > 40mm

        levels = {a.level for a in alerts}
        assert "orange" in levels
        assert "yellow" in levels

    def test_empty_hourly_no_alerts(self, engine):
        """Sin datos horarios no debe generar alertas."""
        hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0, timezone="UTC", hours=[],
        )
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=0.0,
            timezone="UTC", days=[_make_day_data(precipitation_sum=100.0)],
        )

        alerts = engine.evaluate(daily, hourly)
        assert len(alerts) == 0


# ------------------------------------------------------------------
# Tests: reglas y definiciones
# ------------------------------------------------------------------

class TestAlertRules:
    """Pruebas para las definiciones de reglas en rules.py."""

    def test_wmo_orange_codes_have_expected_keys(self):
        """WMO_ORANGE_CODES debe contener los códigos esperados."""
        expected = [95, 96, 99, 66, 67, 77]
        for code in expected:
            assert code in WMO_ORANGE_CODES, f"Falta código WMO naranja {code}"

    def test_wmo_yellow_codes_have_expected_keys(self):
        """WMO_YELLOW_CODES debe contener los códigos esperados."""
        expected = [65, 75]
        for code in expected:
            assert code in WMO_YELLOW_CODES, f"Falta código WMO amarillo {code}"

    def test_alert_is_named_tuple(self):
        """Alert debe ser una NamedTuple con los atributos esperados."""
        alert = Alert(
            level="orange", category="test", message="Test message",
            source_code=95, value=None,
        )
        assert alert.level == "orange"
        assert alert.category == "test"
        assert alert.message == "Test message"
        assert alert.source_code == 95
        assert alert.value is None

    def test_thresholds_are_positive(self):
        """Todos los umbrales deben ser valores positivos."""
        assert WIND_GUST_YELLOW > 0
        assert WIND_GUST_ORANGE > 0
        assert WIND_GUST_ORANGE > WIND_GUST_YELLOW
        assert FLASH_FLOOD_ORANGE > 0
        assert DAILY_RAIN_YELLOW > 0
        assert HEAT_YELLOW > 0
        # FROST_YELLOW es 0 por diseño, no se verifica > 0
