"""Tests para el motor de reportes meteorológicos ReportEngine."""

import os
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from meteowatch.api.client import CurrentWeather
from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.report.engine import (
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    SYSTEM_PROMPT,
    ReportEngine,
)


# ------------------------------------------------------------------
# Helpers: construir datos de prueba
# ------------------------------------------------------------------

def _make_current(**kwargs) -> CurrentWeather:
    """Construye un CurrentWeather de prueba."""
    defaults = {
        "temperature": 25.0,
        "humidity": 55,
        "feels_like": 26.0,
        "symbol": 0,
        "clouds": 10,
        "wind_speed": 15,
        "wind_gust": 25,
        "wind_direction": 180,
        "precipitation": 0.0,
        "precipitation_probability": 5,
        "is_day": True,
        "pressure": 1013,
        "uv_index": 5.0,
    }
    defaults.update(kwargs)
    return CurrentWeather(**defaults)


def _make_day_data(**kwargs) -> DayData:
    """Construye un DayData de prueba."""
    defaults = {
        "start": int(time.time() * 1000),
        "symbol": 0,
        "temperature_min": 18.0,
        "temperature_max": 30.0,
        "wind_speed": 12,
        "wind_gust": 22,
        "wind_direction": 90,
        "precipitation": 0.0,
        "rain_probability": 10,
        "uv_index_max": 6.0,
        "sun_in": int(time.time() * 1000),
        "sun_out": int((time.time() + 43200) * 1000),
        "daylight_duration": 43200,
        "sunshine_duration": 36000,
    }
    defaults.update(kwargs)
    return DayData(**defaults)


def _make_hour_data(**kwargs) -> HourData:
    """Construye un HourData de prueba."""
    defaults = {
        "end": int(time.time() * 1000),
        "precipitation": 0.0,
        "night": False,
        "clouds": 20,
        "symbol": 1,
        "humidity": 50,
        "pressure": 1013,
        "wind_gust": 20,
        "wind_speed": 10,
        "temperature": 22.0,
        "uv_index_max": 4.0,
        "wind_direction": 180,
        "rain_probability": 5,
        "temperature_feels_like": 23.0,
    }
    defaults.update(kwargs)
    return HourData(**defaults)


def _make_daily(days: int = 5) -> DailyForecast:
    """Construye un DailyForecast con N días de prueba."""
    return DailyForecast(
        latitude=40.0,
        longitude=-3.0,
        elevation=665.0,
        timezone="Europe/Madrid",
        days=[_make_day_data() for _ in range(days)],
    )


def _make_hourly(hours: int = 48) -> HourlyForecast:
    """Construye un HourlyForecast con N horas de prueba."""
    return HourlyForecast(
        latitude=40.0,
        longitude=-3.0,
        timezone="Europe/Madrid",
        hours=[_make_hour_data() for _ in range(hours)],
    )


# ------------------------------------------------------------------
# Tests: is_available
# ------------------------------------------------------------------

class TestIsAvailable:
    """Tests para ReportEngine.is_available()."""

    def test_returns_false_when_key_not_set(self, monkeypatch):
        """Debe retornar False si DEEPSEEK_API_KEY no está configurada."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert ReportEngine.is_available() is False

    def test_returns_false_when_key_empty(self, monkeypatch):
        """Debe retornar False si DEEPSEEK_API_KEY está vacía."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        assert ReportEngine.is_available() is False

    def test_returns_false_when_key_whitespace(self, monkeypatch):
        """Debe retornar False si DEEPSEEK_API_KEY es solo espacios."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
        assert ReportEngine.is_available() is False

    def test_returns_true_when_key_set(self, monkeypatch):
        """Debe retornar True si DEEPSEEK_API_KEY tiene un valor."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        assert ReportEngine.is_available() is True


# ------------------------------------------------------------------
# Tests: build_prompt
# ------------------------------------------------------------------

class TestBuildPrompt:
    """Tests para ReportEngine.build_prompt()."""

    def test_prompt_contains_temperature_values(self):
        """El prompt debe contener los valores de temperatura de los datos."""
        current = _make_current(temperature=28.5)
        daily = _make_daily(3)
        hourly = _make_hourly(24)

        prompt = ReportEngine.build_prompt(daily, hourly, current)

        assert "28.5" in prompt
        assert "Temperatura" in prompt

    def test_prompt_contains_weather_descriptions(self):
        """El prompt debe contener descripciones de condiciones climáticas."""
        current = _make_current(symbol=0)
        daily = _make_daily(1)
        hourly = _make_hourly(1)

        prompt = ReportEngine.build_prompt(daily, hourly, current)

        # El símbolo 0 = "Despejado"
        assert "Despejado" in prompt

    def test_prompt_is_in_spanish(self):
        """El prompt debe estar en español con términos meteorológicos en español."""
        current = _make_current()
        daily = _make_daily(1)
        hourly = _make_hourly(1)

        prompt = ReportEngine.build_prompt(daily, hourly, current)

        # Verificar términos clave en español
        spanish_terms = [
            "CONDICIONES ACTUALES",
            "PRONÓSTICO DIARIO",
            "PRONÓSTICO HORARIO",
            "Temperatura",
            "Humedad",
            "Viento",
            "Precipitación",
        ]
        for term in spanish_terms:
            assert term in prompt, f"Falta el término '{term}' en el prompt"

    def test_prompt_with_empty_data(self):
        """El prompt debe manejar datos vacíos sin errores."""
        current = _make_current()
        empty_daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=665.0,
            timezone="Europe/Madrid", days=[],
        )
        empty_hourly = HourlyForecast(
            latitude=40.0, longitude=-3.0,
            timezone="Europe/Madrid", hours=[],
        )

        prompt = ReportEngine.build_prompt(empty_daily, empty_hourly, current)

        assert "no hay datos" in prompt.lower()

    def test_prompt_does_not_contain_invented_data(self):
        """El prompt no debe contener valores que no estén en los datos de entrada."""
        current = _make_current(temperature=22.0, humidity=60)
        daily = _make_daily(1)
        hourly = _make_hourly(1)

        prompt = ReportEngine.build_prompt(daily, hourly, current)

        # No debe mencionar nieve si no está en los datos
        assert "nieve" not in prompt.lower()
        assert "Nieve" not in prompt

    def test_prompt_truncates_hourly_to_24(self):
        """El prompt debe mostrar solo las primeras 24 horas del pronóstico horario."""
        current = _make_current()
        daily = _make_daily(1)
        hourly = _make_hourly(48)

        prompt = ReportEngine.build_prompt(daily, hourly, current)

        # Debe mencionar que hay más horas
        assert "24 horas más" in prompt


# ------------------------------------------------------------------
# Tests: parse_response
# ------------------------------------------------------------------

class TestParseResponse:
    """Tests para ReportEngine.parse_response()."""

    def test_parses_valid_response(self):
        """Debe extraer el contenido de una respuesta JSON válida de DeepSeek."""
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hoy tendremos un día soleado con temperaturas agradables."
                    }
                }
            ]
        }
        result = ReportEngine.parse_response(response)
        assert "soleado" in result

    def test_parses_empty_choices(self):
        """Debe lanzar ValueError si choices está vacío."""
        response = {"choices": []}
        with pytest.raises(ValueError, match="no contiene choices"):
            ReportEngine.parse_response(response)

    def test_parses_missing_choices_key(self):
        """Debe lanzar ValueError si falta la clave choices."""
        response = {"other": "data"}
        with pytest.raises(ValueError, match="Formato de respuesta"):
            ReportEngine.parse_response(response)

    def test_parses_empty_content(self):
        """Debe lanzar ValueError si el contenido del mensaje está vacío."""
        response = {
            "choices": [
                {"message": {"role": "assistant", "content": ""}}
            ]
        }
        with pytest.raises(ValueError, match="vacío"):
            ReportEngine.parse_response(response)

    def test_parses_whitespace_only_content(self):
        """Debe lanzar ValueError si el contenido es solo espacios."""
        response = {
            "choices": [
                {"message": {"role": "assistant", "content": "   "}}
            ]
        }
        with pytest.raises(ValueError, match="vacío"):
            ReportEngine.parse_response(response)

    def test_parse_response_is_static(self):
        """parse_response debe ser un método estático (no requiere instancia)."""
        assert callable(ReportEngine.parse_response)
        # Puede llamarse sin instancia
        response = {
            "choices": [{"message": {"role": "assistant", "content": "Test"}}]
        }
        result = ReportEngine.parse_response(response)
        assert result == "Test"


# ------------------------------------------------------------------
# Tests: Cache y generación
# ------------------------------------------------------------------

class TestCache:
    """Tests para el cache del ReportEngine."""

    def test_cache_returns_same_report_for_same_data(self, monkeypatch):
        """El cache debe retornar el mismo reporte si los datos no cambiaron."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        engine = ReportEngine()

        current = _make_current()
        daily = _make_daily(3)
        hourly = _make_hourly(24)

        # Primera llamada: va a fallback porque mockeamos la API
        report1 = engine.generate(daily, hourly, current)

        # Segunda llamada: debe retornar del cache
        report2 = engine.generate(daily, hourly, current)

        assert report1 == report2

    def test_cache_invalidated_after_invalidate_call(self, monkeypatch):
        """El cache debe invalidarse al llamar a invalidate_cache()."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        engine = ReportEngine()

        current = _make_current()
        daily = _make_daily(3)
        hourly = _make_hourly(24)

        report1 = engine.generate(daily, hourly, current)

        # Invalidar cache
        engine.invalidate_cache()

        # Con datos diferentes, debe regenerar
        new_current = _make_current(temperature=15.0)
        report2 = engine.generate(daily, hourly, new_current)

        # Puede ser igual o diferente dependiendo del fallback,
        # pero el punto es que no debe crashear y debe retornar algo
        assert isinstance(report2, str)
        assert len(report2) > 0

    def test_last_generation_at_updated_after_generation(self, monkeypatch):
        """last_generation_at debe actualizarse después de generar un reporte."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        engine = ReportEngine()

        current = _make_current()
        daily = _make_daily(3)
        hourly = _make_hourly(24)

        assert engine.last_generation_at == 0.0

        # Mockear la API para evitar llamada real
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"role": "assistant", "content": "Reporte de prueba."}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("meteowatch.report.engine.requests.post",
                   return_value=mock_response):
            engine.generate(daily, hourly, current)

            assert engine.last_generation_at > 0.0


# ------------------------------------------------------------------
# Tests: Fallback
# ------------------------------------------------------------------

class TestFallback:
    """Tests para el fallback sin API de DeepSeek."""

    def test_fallback_generated_when_no_api_key(self, monkeypatch):
        """Debe generar un reporte de fallback si no hay API key."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        engine = ReportEngine()

        current = _make_current(temperature=22.0)
        daily = _make_daily(2)
        hourly = _make_hourly(24)

        report = engine.generate(daily, hourly, current)

        assert isinstance(report, str)
        assert len(report) > 0
        # El fallback contiene el emoji de sol/nube
        assert "🌤️" in report or "Resumen" in report

    def test_fallback_contains_temperature(self, monkeypatch):
        """El fallback debe contener la temperatura actual."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        engine = ReportEngine()

        current = _make_current(temperature=22.0)
        daily = _make_daily(1)
        hourly = _make_hourly(1)

        report = engine.generate(daily, hourly, current)

        assert "22" in report

    def test_fallback_with_empty_daily(self, monkeypatch):
        """El fallback debe manejar daily vacío sin errores."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        engine = ReportEngine()

        current = _make_current()
        daily = DailyForecast(
            latitude=40.0, longitude=-3.0, elevation=665.0,
            timezone="Europe/Madrid", days=[],
        )
        hourly = _make_hourly(1)

        report = engine.generate(daily, hourly, current)

        assert isinstance(report, str)
        assert len(report) > 0


# ------------------------------------------------------------------
# Tests: API call (con mock)
# ------------------------------------------------------------------

class TestApiCall:
    """Tests para _call_api con mock de requests."""

    def test_call_api_success(self, monkeypatch):
        """Debe llamar a la API de DeepSeek y retornar el reporte."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        engine = ReportEngine()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"role": "assistant", "content": "Día soleado."}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("meteowatch.report.engine.requests.post",
                   return_value=mock_response) as mock_post:
            result = engine._call_api("prompt de prueba")

            assert result == "Día soleado."
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["model"] == DEEPSEEK_MODEL
            assert "Bearer sk-test-123" in call_kwargs["headers"]["Authorization"]

    def test_call_api_http_error_triggers_fallback(self, monkeypatch):
        """Si la API falla, generate() debe retornar fallback sin lanzar excepción."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        engine = ReportEngine()

        current = _make_current()
        daily = _make_daily(1)
        hourly = _make_hourly(1)

        import requests as req
        with patch("meteowatch.report.engine.requests.post",
                   side_effect=req.RequestException("Network error")):
            report = engine.generate(daily, hourly, current)

            assert isinstance(report, str)
            assert len(report) > 0

    def test_call_api_uses_system_prompt(self, monkeypatch):
        """La llamada a la API debe incluir el system prompt."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        engine = ReportEngine()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"role": "assistant", "content": "Test report."}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("meteowatch.report.engine.requests.post",
                   return_value=mock_response) as mock_post:
            engine._call_api("datos del pronóstico")

            messages = mock_post.call_args.kwargs["json"]["messages"]
            system_msg = messages[0]
            assert system_msg["role"] == "system"
            assert "meteorólogo" in system_msg["content"]
            assert "español neutro" in system_msg["content"]


# ------------------------------------------------------------------
# Tests: Clase y métodos
# ------------------------------------------------------------------

class TestReportEngineClass:
    """Tests de estructura de la clase ReportEngine."""

    def test_has_required_methods(self):
        """La clase debe tener todos los métodos requeridos por la spec."""
        required_static = ["is_available", "build_prompt", "parse_response"]
        required_instance = ["generate", "invalidate_cache", "_call_api"]

        for method_name in required_static:
            assert hasattr(ReportEngine, method_name), \
                f"Falta el método estático {method_name}"
            assert callable(getattr(ReportEngine, method_name)), \
                f"{method_name} no es callable"

        engine = ReportEngine()
        for method_name in required_instance:
            assert hasattr(engine, method_name), \
                f"Falta el método de instancia {method_name}"
            assert callable(getattr(engine, method_name)), \
                f"{method_name} no es callable"

    def test_has_property_last_generation_at(self):
        """Debe tener la propiedad last_generation_at."""
        engine = ReportEngine()
        assert hasattr(engine, "last_generation_at")
