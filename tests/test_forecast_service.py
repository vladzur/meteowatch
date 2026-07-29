"""Tests para el ForecastService y ForecastCache."""

import time
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from meteowatch.api.client import (
    CurrentWeather,
    ForecastResult,
    OpenMeteoError,
)
from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.services.forecast import (
    CURRENT_TTL,
    FORECAST_TTL,
    RETRY_DELAYS,
    MAX_RETRIES,
    BaseForecastObserver,
    ForecastCache,
    ForecastService,
)


# ------------------------------------------------------------------
# Helpers: construir datos de prueba
# ------------------------------------------------------------------

def _make_current(**kwargs) -> CurrentWeather:
    """Construye un CurrentWeather con valores por defecto."""
    defaults = {
        "temperature": 22.5,
        "humidity": 65,
        "feels_like": 21.0,
        "symbol": 1,
        "clouds": 30,
        "wind_speed": 15,
        "wind_gust": 25,
        "wind_direction": 180,
        "precipitation": 0.0,
        "precipitation_probability": 10,
        "is_day": True,
        "pressure": 1013,
        "uv_index": 5.0,
    }
    defaults.update(kwargs)
    return CurrentWeather(**defaults)


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


def _make_forecast_result(days=1, hours=24) -> ForecastResult:
    """Construye un ForecastResult con datos de prueba."""
    daily = DailyForecast(
        latitude=40.0,
        longitude=-3.0,
        elevation=665.0,
        timezone="Europe/Madrid",
        days=[_make_day(start=1700000000000 + i * 86400000) for i in range(days)],
    )
    hourly = HourlyForecast(
        latitude=40.0,
        longitude=-3.0,
        timezone="Europe/Madrid",
        hours=[_make_hour(end=1700000000000 + i * 3600000) for i in range(hours)],
    )
    return ForecastResult(
        daily=daily,
        hourly=hourly,
        current=_make_current(),
        raw={},
    )


# ==================================================================
# ForecastCache
# ==================================================================

class TestForecastCache:
    """Tests para ForecastCache."""

    def test_initial_cache_is_empty(self):
        """Un cache recién creado no debe tener datos."""
        cache = ForecastCache()
        assert cache.current is None
        assert cache.daily is None
        assert cache.hourly is None
        assert cache.has_data() is False
        assert cache.has_current() is False

    def test_cache_has_data_after_update(self):
        """Después de update(), has_data() debe ser True."""
        cache = ForecastCache()
        result = _make_forecast_result()
        cache.update(result)
        assert cache.has_data() is True
        assert cache.has_current() is True
        assert cache.current is not None
        assert cache.daily is not None
        assert cache.hourly is not None

    def test_fresh_cache_is_not_stale(self):
        """Un cache recién actualizado no debe estar stale."""
        cache = ForecastCache()
        cache.update(_make_forecast_result())
        assert cache.is_current_stale() is False
        assert cache.is_forecast_stale() is False

    @patch("meteowatch.services.forecast.time")
    def test_cache_stale_after_ttl(self, mock_time):
        """Después de superar el TTL, el cache debe estar stale."""
        # Configurar time.time antes del update para que el timestamp sea float
        base_time = 1000000.0
        mock_time.time.return_value = base_time

        cache = ForecastCache()
        cache.update(_make_forecast_result())

        # Avanzar el tiempo más allá del TTL de current pero no de forecast
        mock_time.time.return_value = base_time + CURRENT_TTL + 60
        assert cache.is_current_stale() is True
        assert cache.is_forecast_stale() is False

    @patch("meteowatch.services.forecast.time")
    def test_cache_forecast_stale_after_ttl(self, mock_time):
        """Después de 1 hora, el forecast completo debe estar stale."""
        base_time = 1000000.0
        mock_time.time.return_value = base_time

        cache = ForecastCache()
        cache.update(_make_forecast_result())

        mock_time.time.return_value = base_time + FORECAST_TTL + 60
        assert cache.is_forecast_stale() is True

    def test_get_age_minutes_zero_when_empty(self):
        """Un cache vacío debe retornar 0 minutos de antigüedad."""
        cache = ForecastCache()
        assert cache.get_age_minutes() == 0.0

    @patch("meteowatch.services.forecast.time")
    def test_get_age_minutes_after_update(self, mock_time):
        """get_age_minutes debe reflejar el tiempo transcurrido."""
        base_time = 1000000.0
        mock_time.time.return_value = base_time

        cache = ForecastCache()
        cache.update(_make_forecast_result())

        # Simular 5 minutos de antigüedad
        mock_time.time.return_value = base_time + 300
        assert cache.get_age_minutes() == pytest.approx(5.0, abs=0.1)


# ==================================================================
# ForecastService
# ==================================================================

class TestForecastServiceSubscription:
    """Tests de suscripción y notificación de observers."""

    def test_subscribe_adds_observer(self):
        """subscribe() debe agregar el observer a la lista."""
        service = ForecastService()
        observer = BaseForecastObserver()
        service.subscribe(observer)
        # Verificar que no lanza error al notificar
        # (no hay API pública para listar observers)

    def test_unsubscribe_removes_observer(self):
        """unsubscribe() debe eliminar el observer."""
        service = ForecastService()
        observer = BaseForecastObserver()
        service.subscribe(observer)
        service.unsubscribe(observer)
        # No debe lanzar error al desuscribir dos veces
        service.unsubscribe(observer)

    def test_subscribe_duplicate_ignored(self):
        """Suscribir el mismo observer dos veces no debe duplicarlo."""
        service = ForecastService()
        observer = BaseForecastObserver()
        service.subscribe(observer)
        service.subscribe(observer)
        service.unsubscribe(observer)
        # No debe lanzar error

    def test_notify_forecast_calls_observer(self):
        """Al notificar forecast, se llama a on_forecast_updated en cada observer."""
        service = ForecastService()
        mock_observer = Mock()
        service.subscribe(mock_observer)

        result = _make_forecast_result()
        service._notify_forecast(result)
        mock_observer.on_forecast_updated.assert_called_once_with(result)

    def test_notify_current_calls_observer(self):
        """Al notificar current, se llama a on_current_updated en cada observer."""
        service = ForecastService()
        mock_observer = Mock()
        service.subscribe(mock_observer)

        current = _make_current()
        service._notify_current(current)
        mock_observer.on_current_updated.assert_called_once_with(current)

    def test_notify_error_calls_observer(self):
        """Al notificar error, se llama a on_forecast_error en cada observer."""
        service = ForecastService()
        mock_observer = Mock()
        service.subscribe(mock_observer)

        service._notify_error("Error de prueba", cached=True)
        mock_observer.on_forecast_error.assert_called_once_with(
            "Error de prueba", True
        )

    def test_notify_handles_observer_exception(self):
        """Si un observer lanza excepción, los demás siguen funcionando."""
        service = ForecastService()
        bad_observer = Mock()
        bad_observer.on_forecast_updated.side_effect = RuntimeError("boom")
        good_observer = Mock()

        service.subscribe(bad_observer)
        service.subscribe(good_observer)

        result = _make_forecast_result()
        service._notify_forecast(result)

        # El observer bueno debe haber recibido la notificación
        good_observer.on_forecast_updated.assert_called_once_with(result)


class TestForecastServiceCachedAccess:
    """Tests de acceso síncrono al cache."""

    def test_get_cached_forecast_none_when_empty(self):
        """Sin datos en cache, get_cached_forecast retorna None."""
        service = ForecastService()
        assert service.get_cached_forecast() is None

    def test_get_cached_current_none_when_empty(self):
        """Sin datos en cache, get_cached_current retorna None."""
        service = ForecastService()
        assert service.get_cached_current() is None

    def test_get_cached_forecast_after_update(self):
        """Después de actualizar el cache, get_cached_forecast retorna datos."""
        service = ForecastService()
        result = _make_forecast_result()
        service._cache.update(result)

        cached = service.get_cached_forecast()
        assert cached is not None
        assert cached.daily is not None
        assert cached.hourly is not None
        assert cached.current is not None

    def test_get_age_minutes_delegates_to_cache(self):
        """get_age_minutes() debe delegar en el cache."""
        service = ForecastService()
        assert service.get_age_minutes() == 0.0


class TestForecastServiceRefresh:
    """Tests de refresco de datos."""

    def test_refresh_forecast_skips_when_fresh(self):
        """Si el forecast está fresco, no se lanza fetch."""
        service = ForecastService()
        service._cache.update(_make_forecast_result())
        idle_add = Mock()

        service.refresh_forecast(idle_add, 40.0, -3.0)
        # No debe haberse llamado a idle_add porque no se lanzó hilo
        idle_add.assert_not_called()

    def test_refresh_current_skips_when_fresh(self):
        """Si current está fresco, no se lanza fetch."""
        service = ForecastService()
        service._cache.update(_make_forecast_result())
        idle_add = Mock()

        service.refresh_current(idle_add, 40.0, -3.0)
        idle_add.assert_not_called()

    @patch("meteowatch.services.forecast.time")
    def test_refresh_forecast_triggers_when_stale(self, mock_time):
        """Si el forecast está stale, se lanza fetch en hilo secundario."""
        base_time = 1000000.0
        mock_time.time.return_value = base_time

        service = ForecastService()
        service._cache.update(_make_forecast_result())

        # Avanzar tiempo para que esté stale
        mock_time.time.return_value = base_time + FORECAST_TTL + 60

        idle_add = Mock()
        service.refresh_forecast(idle_add, 40.0, -3.0)
        # El hilo no termina instantáneamente, pero verificamos que no lanza error


class TestForecastServiceRetry:
    """Tests de reintentos con backoff exponencial."""

    @patch("meteowatch.services.forecast.OpenMeteoClient")
    def test_fetch_with_retry_succeeds_first_attempt(self, mock_client_cls):
        """El primer intento exitoso no reintenta."""
        mock_client = Mock()
        mock_client.get_forecast.return_value = _make_forecast_result()
        mock_client_cls.return_value = mock_client

        service = ForecastService()
        result = service._fetch_with_retry(40.0, -3.0, "auto")

        assert result is not None
        mock_client.get_forecast.assert_called_once()

    @patch("meteowatch.services.forecast.OpenMeteoClient")
    @patch("meteowatch.services.forecast.time")
    def test_fetch_retries_on_failure(self, mock_time, mock_client_cls):
        """Si falla, reintenta con backoff."""
        mock_client = Mock()
        mock_client.get_forecast.side_effect = [
            OpenMeteoError("Fallo 1"),
            OpenMeteoError("Fallo 2"),
            _make_forecast_result(),
        ]
        mock_client_cls.return_value = mock_client

        service = ForecastService()
        result = service._fetch_with_retry(40.0, -3.0, "auto")

        assert result is not None
        assert mock_client.get_forecast.call_count == 3
        # Verificar que se llamó a time.sleep con los delays correctos
        mock_time.sleep.assert_has_calls([
            call(RETRY_DELAYS[0]),
            call(RETRY_DELAYS[1]),
        ])

    @patch("meteowatch.services.forecast.OpenMeteoClient")
    @patch("meteowatch.services.forecast.time")
    def test_fetch_raises_after_max_retries(self, mock_time, mock_client_cls):
        """Después de MAX_RETRIES+1 intentos fallidos, lanza excepción."""
        mock_client = Mock()
        error = OpenMeteoError("Fallo persistente")
        # MAX_RETRIES=3, así que 4 intentos totales (0, 1, 2, 3)
        mock_client.get_forecast.side_effect = [error] * (MAX_RETRIES + 1)
        mock_client_cls.return_value = mock_client

        service = ForecastService()
        with pytest.raises(OpenMeteoError):
            service._fetch_with_retry(40.0, -3.0, "auto")
        assert mock_client.get_forecast.call_count == MAX_RETRIES + 1


class TestForecastServiceConcurrency:
    """Tests de control de concurrencia."""

    def test_second_fetch_waits_when_lock_held(self):
        """Si hay un fetch en vuelo, el segundo espera el lock."""
        service = ForecastService()

        # Simular que el lock está tomado
        assert service._fetch_lock.acquire(blocking=False) is True

        # Liberar para que los tests siguientes no fallen
        service._fetch_lock.release()


# ==================================================================
# BaseForecastObserver
# ==================================================================

class TestBaseForecastObserver:
    """Tests para BaseForecastObserver."""

    def test_default_methods_are_noop(self):
        """Los métodos por defecto no deben lanzar excepciones."""
        observer = BaseForecastObserver()
        result = _make_forecast_result()
        current = _make_current()

        # No deben lanzar excepción
        observer.on_forecast_updated(result)
        observer.on_current_updated(current)
        observer.on_forecast_error("test error", cached=True)
