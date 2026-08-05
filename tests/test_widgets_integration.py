"""Tests de integración para las páginas de pronóstico.

Verifica que los widgets tengan los métodos requeridos por el
patrón observer y que las funciones de comparación funcionen.
"""

import pytest

from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.widgets.daily_card import DailyForecastPage, _degrees_to_cardinal
from meteowatch.widgets.hourly_panel import HourlyForecastPage


# ==================================================================
# Helpers
# ==================================================================

def _make_day(**kwargs) -> DayData:
    """Construye un DayData con valores por defecto."""
    defaults = {
        "start": 1700000000000,
        "symbol": 1,
        "temperature_min": 12.0,
        "temperature_max": 25.0,
        "wind_speed": 15,
        "wind_gust": 30,
        "wind_direction": 180,
        "precipitation": 0.0,
        "rain_probability": 5,
        "uv_index_max": 6.0,
        "sun_in": 1700020000000,
        "sun_out": 1700060000000,
        "daylight_duration": 40000,
        "sunshine_duration": 36000,
    }
    defaults.update(kwargs)
    return DayData(**defaults)


def _make_hour(**kwargs) -> HourData:
    """Construye un HourData con valores por defecto."""
    defaults = {
        "end": 1700003600000,
        "precipitation": 0.0,
        "night": False,
        "clouds": 20,
        "symbol": 1,
        "humidity": 60,
        "pressure": 1013,
        "wind_gust": 20,
        "wind_speed": 10,
        "temperature": 20.0,
        "uv_index_max": 3.0,
        "wind_direction": 180,
        "rain_probability": 5,
        "temperature_feels_like": 19.0,
    }
    defaults.update(kwargs)
    return HourData(**defaults)


def _make_daily_forecast(days=3) -> DailyForecast:
    """Construye un DailyForecast con datos de prueba."""
    return DailyForecast(
        latitude=40.0,
        longitude=-3.0,
        elevation=665.0,
        timezone="Europe/Madrid",
        days=[_make_day(start=1700000000000 + i * 86400000) for i in range(days)],
    )


def _make_hourly_forecast(hours=48) -> HourlyForecast:
    """Construye un HourlyForecast con datos de prueba."""
    return HourlyForecast(
        latitude=40.0,
        longitude=-3.0,
        timezone="Europe/Madrid",
        hours=[_make_hour(end=1700000000000 + i * 3600000) for i in range(hours)],
    )


# ==================================================================
# DailyForecastPage — métodos requeridos
# ==================================================================

class TestDailyForecastPageMethods:
    """Verifica que la clase tenga los métodos esperados por el observer."""

    def test_has_on_forecast_updated(self):
        """Debe tener el método on_forecast_updated del protocolo observer."""
        assert hasattr(DailyForecastPage, "on_forecast_updated")
        assert callable(getattr(DailyForecastPage, "on_forecast_updated"))

    def test_has_on_current_updated(self):
        """Debe tener el método on_current_updated del protocolo observer."""
        assert hasattr(DailyForecastPage, "on_current_updated")
        assert callable(getattr(DailyForecastPage, "on_current_updated"))

    def test_has_on_forecast_error(self):
        """Debe tener el método on_forecast_error del protocolo observer."""
        assert hasattr(DailyForecastPage, "on_forecast_error")
        assert callable(getattr(DailyForecastPage, "on_forecast_error"))

    def test_has_load_forecast(self):
        """Debe tener el método load_forecast."""
        assert hasattr(DailyForecastPage, "load_forecast")

    def test_has_on_24h_clicked(self):
        """Debe tener el método _on_24h_clicked (regresión detectada)."""
        assert hasattr(DailyForecastPage, "_on_24h_clicked")
        assert callable(getattr(DailyForecastPage, "_on_24h_clicked"))

    def test_has_freshness_methods(self):
        """Debe tener los métodos del indicador de frescura."""
        assert hasattr(DailyForecastPage, "_start_freshness_timer")
        assert hasattr(DailyForecastPage, "_stop_freshness_timer")
        assert hasattr(DailyForecastPage, "_update_freshness_label")
        assert hasattr(DailyForecastPage, "_set_offline_freshness")
        assert hasattr(DailyForecastPage, "_set_normal_freshness")

    def test_has_forecast_changed_method(self):
        """Debe tener el método de comparación de forecasts."""
        assert hasattr(DailyForecastPage, "_has_forecast_changed")

    def test_inherits_from_base_observer(self):
        """Debe heredar de BaseForecastObserver."""
        from meteowatch.services.forecast import BaseForecastObserver
        assert issubclass(DailyForecastPage, BaseForecastObserver)


# ==================================================================
# DailyForecastPage._has_forecast_changed — lógica pura
# ==================================================================

class TestHasForecastChanged:
    """Tests para la comparación de forecasts (refresco transparente)."""

    def test_none_forecast_means_changed(self):
        """Si no hay forecast previo, siempre hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = None
        assert page._has_forecast_changed(_make_daily_forecast()) is True

    def test_different_day_count_is_changed(self):
        """Si cambia la cantidad de días, hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = _make_daily_forecast(days=3)
        assert page._has_forecast_changed(_make_daily_forecast(days=5)) is True

    def test_same_data_is_not_changed(self):
        """Si los datos son idénticos, no hay cambios."""
        forecast = _make_daily_forecast(days=3)
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = forecast
        assert page._has_forecast_changed(forecast) is False

    def test_different_temperature_is_changed(self):
        """Si cambia la temperatura máxima, hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = _make_daily_forecast(days=3)

        new_forecast = _make_daily_forecast(days=3)
        # Modificar primer día
        new_forecast.days[0] = _make_day(
            start=1700000000000, temperature_max=30.0
        )
        assert page._has_forecast_changed(new_forecast) is True

    def test_different_symbol_is_changed(self):
        """Si cambia el código WMO, hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = _make_daily_forecast(days=3)

        new_forecast = _make_daily_forecast(days=3)
        new_forecast.days[1] = _make_day(
            start=1700000000000 + 86400000, symbol=61
        )
        assert page._has_forecast_changed(new_forecast) is True

    def test_different_precipitation_is_changed(self):
        """Si cambia la precipitación, hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = _make_daily_forecast(days=3)

        new_forecast = _make_daily_forecast(days=3)
        new_forecast.days[0] = _make_day(
            start=1700000000000, precipitation=5.0
        )
        assert page._has_forecast_changed(new_forecast) is True

    def test_different_wind_is_changed(self):
        """Si cambia el viento, hay cambios."""
        page = DailyForecastPage.__new__(DailyForecastPage)
        page._forecast = _make_daily_forecast(days=3)

        new_forecast = _make_daily_forecast(days=3)
        new_forecast.days[0] = _make_day(
            start=1700000000000, wind_speed=50, wind_gust=80
        )
        assert page._has_forecast_changed(new_forecast) is True


# ==================================================================
# HourlyForecastPage — métodos requeridos
# ==================================================================

class TestHourlyForecastPageMethods:
    """Verifica que la clase tenga los métodos esperados por el observer."""

    def test_has_on_forecast_updated(self):
        """Debe tener el método on_forecast_updated del protocolo observer."""
        assert hasattr(HourlyForecastPage, "on_forecast_updated")
        assert callable(getattr(HourlyForecastPage, "on_forecast_updated"))

    def test_has_on_forecast_error(self):
        """Debe tener el método on_forecast_error del protocolo observer."""
        assert hasattr(HourlyForecastPage, "on_forecast_error")
        assert callable(getattr(HourlyForecastPage, "on_forecast_error"))

    def test_has_hourly_changed_method(self):
        """Debe tener el método de comparación de forecasts horarios."""
        assert hasattr(HourlyForecastPage, "_has_hourly_changed")

    def test_inherits_from_base_observer(self):
        """Debe heredar de BaseForecastObserver."""
        from meteowatch.services.forecast import BaseForecastObserver
        assert issubclass(HourlyForecastPage, BaseForecastObserver)


# ==================================================================
# HourlyForecastPage._has_hourly_changed — lógica pura
# ==================================================================

class TestHasHourlyChanged:
    """Tests para la comparación de forecasts horarios."""

    def test_none_forecast_means_changed(self):
        """Si no hay forecast previo, siempre hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = None
        assert page._has_hourly_changed(_make_hourly_forecast()) is True

    def test_different_hour_count_is_changed(self):
        """Si cambia la cantidad de horas, hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = _make_hourly_forecast(hours=24)
        assert page._has_hourly_changed(_make_hourly_forecast(hours=48)) is True

    def test_same_data_is_not_changed(self):
        """Si los datos son idénticos, no hay cambios."""
        forecast = _make_hourly_forecast(hours=24)
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = forecast
        assert page._has_hourly_changed(forecast) is False

    def test_different_temperature_is_changed(self):
        """Si cambia la temperatura, hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = _make_hourly_forecast(hours=24)

        new_forecast = _make_hourly_forecast(hours=24)
        new_forecast.hours[0] = _make_hour(
            end=1700000000000, temperature=30.0
        )
        assert page._has_hourly_changed(new_forecast) is True

    def test_different_precipitation_is_changed(self):
        """Si cambia la precipitación, hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = _make_hourly_forecast(hours=24)

        new_forecast = _make_hourly_forecast(hours=24)
        new_forecast.hours[0] = _make_hour(
            end=1700000000000, precipitation=10.0
        )
        assert page._has_hourly_changed(new_forecast) is True

    def test_different_wind_is_changed(self):
        """Si cambia la velocidad del viento, hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = _make_hourly_forecast(hours=24)

        new_forecast = _make_hourly_forecast(hours=24)
        new_forecast.hours[0] = _make_hour(
            end=1700000000000, wind_speed=50
        )
        assert page._has_hourly_changed(new_forecast) is True

    def test_different_rain_probability_is_changed(self):
        """Si cambia la probabilidad de lluvia, hay cambios."""
        page = HourlyForecastPage.__new__(HourlyForecastPage)
        page._forecast = _make_hourly_forecast(hours=24)

        new_forecast = _make_hourly_forecast(hours=24)
        new_forecast.hours[0] = _make_hour(
            end=1700000000000, rain_probability=90
        )
        assert page._has_hourly_changed(new_forecast) is True


# ==================================================================
# WeatherReportCard — integración
# ==================================================================

class TestWeatherReportCardIntegration:
    """Verifica que el WeatherReportCard se integre correctamente."""

    def test_module_imports_cleanly(self):
        """El módulo report_card debe importarse sin errores circulares."""
        import meteowatch.widgets.report_card  # noqa: F401

    def test_class_exists(self):
        """La clase WeatherReportCard debe existir."""
        from meteowatch.widgets.report_card import WeatherReportCard
        assert WeatherReportCard is not None

    def test_has_required_methods(self):
        """Debe tener los métodos requeridos por la spec."""
        from meteowatch.widgets.report_card import WeatherReportCard

        required = [
            "set_forecast_data",
            "_build_ui",
            "_on_generate_clicked",
            "_set_loading_state",
            "_do_generate",
            "_on_report_ready",
            "_enable_generate_button",
        ]
        for method in required:
            assert hasattr(WeatherReportCard, method), \
                f"Falta el método {method}"
            assert callable(getattr(WeatherReportCard, method)), \
                f"{method} no es callable"

    def test_cooldown_constant(self):
        """COOLDOWN_SECONDS debe ser positivo."""
        from meteowatch.widgets.report_card import COOLDOWN_SECONDS
        assert COOLDOWN_SECONDS > 0

    def test_report_engine_integration(self, monkeypatch):
        """ReportEngine.is_available debe funcionar correctamente."""
        from meteowatch.report.engine import ReportEngine

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert ReportEngine.is_available() is False

        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        assert ReportEngine.is_available() is True


class TestDailyForecastReportIntegration:
    """Verifica que DailyForecastPage acepte el parámetro report_engine."""

    def test_init_accepts_report_engine(self):
        """El constructor de DailyForecastPage debe aceptar report_engine."""
        import inspect
        sig = inspect.signature(DailyForecastPage.__init__)
        params = list(sig.parameters.keys())
        assert "report_engine" in params
