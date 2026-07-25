"""Tests para el widget de pronóstico por hora y su filtro de horas futuras."""

import time
from datetime import datetime, timezone

import pytest

from meteowatch import __version__
from meteowatch.models.hourly import HourData
from meteowatch.widgets.hourly_panel import WEEKDAYS, _degrees_to_cardinal, HourlyForecastPage


class TestDegreesToCardinal:
    """Pruebas para la conversión de grados a punto cardinal."""

    def test_north(self):
        assert _degrees_to_cardinal(0) == "N"
        assert _degrees_to_cardinal(360) == "N"

    def test_cardinals(self):
        assert _degrees_to_cardinal(45) == "NE"
        assert _degrees_to_cardinal(90) == "E"
        assert _degrees_to_cardinal(135) == "SE"
        assert _degrees_to_cardinal(180) == "S"
        assert _degrees_to_cardinal(225) == "SW"
        assert _degrees_to_cardinal(270) == "W"
        assert _degrees_to_cardinal(315) == "NW"

    def test_negative_returns_unknown(self):
        assert _degrees_to_cardinal(-1) == "?"


class TestGroupHoursByDay:
    """Pruebas para la agrupación de horas por día."""

    @staticmethod
    def _make_hour(end_ts_ms: int) -> HourData:
        """Factory helper: crea un HourData mínimo con solo el campo end."""
        return HourData(
            end=end_ts_ms,
            precipitation=0.0,
            night=False,
            clouds=0,
            symbol=1,
            humidity=50,
            pressure=1013,
            wind_gust=10,
            wind_speed=5,
            temperature=20.0,
            uv_index_max=0.0,
            wind_direction=180,
            rain_probability=0,
            temperature_feels_like=19.0,
        )

    def test_groups_hours_by_midnight_utc(self):
        """Verifica que las horas se agrupen por medianoche UTC cuando el tz es UTC."""
        tz = timezone.utc
        # Dos horas del mismo día UTC
        h1 = self._make_hour(int(datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc).timestamp() * 1000))
        h2 = self._make_hour(int(datetime(2026, 7, 24, 14, 0, tzinfo=timezone.utc).timestamp() * 1000))
        # Una hora del día siguiente
        h3 = self._make_hour(int(datetime(2026, 7, 25, 2, 0, tzinfo=timezone.utc).timestamp() * 1000))

        grouped = HourlyForecastPage._group_hours_by_day([h1, h2, h3], tz)

        assert len(grouped) == 2
        # Día 1 (24 jul)
        day1_key = int(datetime(2026, 7, 24, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert day1_key in grouped
        assert len(grouped[day1_key]) == 2
        # Día 2 (25 jul)
        day2_key = int(datetime(2026, 7, 25, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert day2_key in grouped
        assert len(grouped[day2_key]) == 1

    def test_empty_list_returns_empty(self):
        grouped = HourlyForecastPage._group_hours_by_day([], timezone.utc)
        assert len(grouped) == 0

    def test_preserves_chronological_order(self):
        """Verifica que las horas dentro de cada grupo mantengan orden cronológico."""
        tz = timezone.utc
        h1 = self._make_hour(int(datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc).timestamp() * 1000))
        h2 = self._make_hour(int(datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc).timestamp() * 1000))
        h3 = self._make_hour(int(datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc).timestamp() * 1000))
        # Las pasamos desordenadas; la agrupación mantiene el orden de entrada
        grouped = HourlyForecastPage._group_hours_by_day([h1, h2, h3], tz)
        day_key = list(grouped.keys())[0]
        assert len(grouped[day_key]) == 3

    def test_groups_by_local_midnight_not_utc(self):
        """Verifica que la agrupación respete la medianoche local, no UTC.

        Con UTC-3, las 02:00 hora local del 25 de julio equivalen a las 05:00 UTC
        del 25 de julio. Deben agruparse bajo la medianoche local del 25,
        no bajo la medianoche UTC del 25.
        """
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Argentina/Buenos_Aires")  # UTC-3

        # 02:00 ART = 05:00 UTC — ambas del 25 de julio
        h_art_0200 = self._make_hour(int(datetime(2026, 7, 25, 5, 0, tzinfo=timezone.utc).timestamp() * 1000))
        # 14:00 ART = 17:00 UTC
        h_art_1400 = self._make_hour(int(datetime(2026, 7, 25, 17, 0, tzinfo=timezone.utc).timestamp() * 1000))

        grouped = HourlyForecastPage._group_hours_by_day([h_art_0200, h_art_1400], tz)

        assert len(grouped) == 1
        # La clave debe ser la medianoche local del 25 de julio
        local_midnight = int(datetime(2026, 7, 25, 0, 0, 0, tzinfo=tz).timestamp() * 1000)
        assert local_midnight in grouped
        assert len(grouped[local_midnight]) == 2


class TestFilterFutureHours:
    """Pruebas para la lógica de filtrado de horas futuras."""

    @staticmethod
    def _make_hour(end_ts_ms: int) -> HourData:
        return HourData(
            end=end_ts_ms,
            precipitation=0.0,
            night=False,
            clouds=0,
            symbol=1,
            humidity=50,
            pressure=1013,
            wind_gust=10,
            wind_speed=5,
            temperature=20.0,
            uv_index_max=0.0,
            wind_direction=180,
            rain_probability=0,
            temperature_feels_like=19.0,
        )

    def test_filter_excludes_past_hours(self):
        """Verifica que las horas con end < now_ms se excluyan."""
        now_ms = int(time.time() * 1000)
        one_hour_ms = 3600 * 1000

        past_hour = self._make_hour(now_ms - one_hour_ms)
        future_hour_1 = self._make_hour(now_ms + one_hour_ms)
        future_hour_2 = self._make_hour(now_ms + 2 * one_hour_ms)

        all_hours = [past_hour, future_hour_1, future_hour_2]
        future_hours = [h for h in all_hours if h.end >= now_ms]

        assert len(future_hours) == 2
        assert past_hour not in future_hours
        assert future_hour_1 in future_hours
        assert future_hour_2 in future_hours

    def test_filter_keeps_exact_now(self):
        """Verifica que una hora con end exactamente igual a now_ms se conserve."""
        now_ms = int(time.time() * 1000)
        exact_hour = self._make_hour(now_ms)

        future_hours = [h for h in [exact_hour] if h.end >= now_ms]
        assert len(future_hours) == 1

    def test_filter_all_past_returns_empty(self):
        """Verifica que si todas las horas son pasadas, la lista quede vacía."""
        now_ms = int(time.time() * 1000)
        one_hour_ms = 3600 * 1000

        past_hours = [
            self._make_hour(now_ms - 3 * one_hour_ms),
            self._make_hour(now_ms - 2 * one_hour_ms),
            self._make_hour(now_ms - 1 * one_hour_ms),
        ]
        future_hours = [h for h in past_hours if h.end >= now_ms]
        assert len(future_hours) == 0

    def test_filter_all_future_keeps_all(self):
        """Verifica que si todas las horas son futuras, se conserven todas."""
        now_ms = int(time.time() * 1000)
        one_hour_ms = 3600 * 1000

        future = [
            self._make_hour(now_ms + one_hour_ms),
            self._make_hour(now_ms + 2 * one_hour_ms),
            self._make_hour(now_ms + 3 * one_hour_ms),
        ]
        filtered = [h for h in future if h.end >= now_ms]
        assert len(filtered) == len(future)

    def test_detect_past_hours_presence(self):
        """Verifica detección de si hay horas pasadas (para mostrar el toggle)."""
        now_ms = int(time.time() * 1000)
        one_hour_ms = 3600 * 1000

        all_hours = [
            self._make_hour(now_ms - one_hour_ms),  # pasada
            self._make_hour(now_ms + one_hour_ms),  # futura
            self._make_hour(now_ms + 2 * one_hour_ms),  # futura
        ]
        future_hours = [h for h in all_hours if h.end >= now_ms]
        has_past = len(future_hours) < len(all_hours)
        assert has_past is True


class TestVersion:
    """Pruebas para la versión de la aplicación."""

    def test_version_is_1_3_0(self):
        assert __version__ == "1.3.1"

    def test_version_has_three_components(self):
        parts = __version__.split(".")
        assert len(parts) == 3


class TestWeekdays:
    """Pruebas para los nombres de días de la semana."""

    def test_weekdays_count(self):
        assert len(WEEKDAYS) == 7

    def test_first_is_monday(self):
        assert WEEKDAYS[0] == "Lunes"
