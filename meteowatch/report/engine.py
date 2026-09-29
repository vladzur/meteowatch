"""Motor de generación de reportes meteorológicos con DeepSeek.

Construye un prompt estructurado a partir de los datos del ForecastService
(daily + hourly + current), llama a la API de DeepSeek y retorna un informe
narrativo en español neutro, profesional y dirigido directamente al usuario.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from meteowatch.api.client import CurrentWeather
from meteowatch.icons import get_weather_symbol
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
REQUEST_TIMEOUT = 30  # segundos para timeout HTTP

# Prompt del sistema: instrucciones para DeepSeek
SYSTEM_PROMPT = (
    "Eres un meteorólogo profesional que redacta informes del tiempo "
    "precisos y útiles. Tu tarea es analizar los datos del pronóstico "
    "meteorológico proporcionados y elaborar un informe claro, "
    "informativo y dirigido directamente al usuario.\n\n"
    "Reglas obligatorias:\n"
    "- Dirígete SIEMPRE al usuario en segunda persona (\"tú\"), con un "
    "registro formal y respetuoso.\n"
    "- Escribe SIEMPRE en español neutro (sin regionalismos de ningún país).\n"
    "- Sé preciso y conciso; usa un lenguaje claro y profesional, e "
    "incluye magnitudes concretas (temperaturas, viento, precipitación, "
    "humedad, índice UV).\n"
    "- NO inventes datos ni condiciones meteorológicas que no aparezcan "
    "explícitamente en los datos proporcionados.\n"
    "- Si no hay datos suficientes para una afirmación, no la hagas.\n"
    "- Mantén un tono serio y profesional en todo momento.\n\n"
    "Estructura del informe:\n"
    "1. Un párrafo introductorio que resuma la situación general y lo "
    "más relevante para el usuario.\n"
    "2. Un análisis día por día con detalles concretos: temperaturas "
    "máximas y mínimas, condiciones del cielo, precipitación y su "
    "probabilidad, viento y ráfagas, salida y puesta del sol, horas de "
    "sol e índice UV cuando corresponda.\n"
    "3. Recomendaciones prácticas y específicas para cada jornada "
    "(abrigo, paraguas, protección solar, precaución con el viento).\n\n"
    "Extensión máxima: 350 palabras."
)


# ------------------------------------------------------------------
# ReportEngine
# ------------------------------------------------------------------


def _degrees_to_cardinal(degrees: int) -> str:
    """Convierte una dirección en grados (0-360) a punto cardinal.

    Args:
        degrees: Ángulo en grados (0=N, 90=E, 180=S, 270=W).

    Returns:
        Abreviatura del punto cardinal (N, NE, E, SE, S, SW, W, NW).
    """
    if degrees < 0:
        return "?"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[round(degrees / 45) % 8]


class ReportEngine:
    """Motor de generación de reportes meteorológicos narrativos.

    Construye un prompt con los datos del pronóstico, consulta la API
    de DeepSeek y retorna un informe textual en español neutro.

    Attributes:
        _api_key: Clave de API de DeepSeek (desde DEEPSEEK_API_KEY).
        _cached_report: Último reporte generado (None si no hay).
        _cached_forecast_at: Timestamp del forecast usado para el cache.
        _last_generation_at: Timestamp de la última generación (para enfriamiento).
    """

    def __init__(self, api_key: str = ""):
        """Inicializa el motor de reportes.

        La API key se obtiene del argumento o, si está vacío, de la
        variable de entorno DEEPSEEK_API_KEY. Si no hay llave configurada,
        is_available() retorna False.

        Args:
            api_key: Llave de API de DeepSeek desde la configuración.
        """
        self._api_key = (api_key or os.environ.get("DEEPSEEK_API_KEY", "")).strip()
        self._cached_report: Optional[str] = None
        self._cached_forecast_at: float = 0.0
        self._last_generation_at: float = 0.0

    # ------------------------------------------------------------------
    # Disponibilidad
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Verifica si el motor de reportes está disponible.

        Retorna True si hay una API key configurada (desde la configuración
        o la variable de entorno) con un valor no vacío.

        Returns:
            True si hay una API key configurada y el motor puede operar.
        """
        return bool(self._api_key)

    def set_api_key(self, api_key: str) -> None:
        """Actualiza la API key y limpia el cache del reporte.

        Args:
            api_key: Nueva llave de API de DeepSeek.
        """
        self._api_key = (api_key or os.environ.get("DEEPSEEK_API_KEY", "")).strip()
        self.invalidate_cache()
        logger.debug("API key de DeepSeek actualizada")

    # ------------------------------------------------------------------
    # Construcción del prompt
    # ------------------------------------------------------------------

    @staticmethod
    def build_prompt(
        daily: DailyForecast,
        hourly: HourlyForecast,
        current: CurrentWeather,
    ) -> str:
        """Construye el prompt para DeepSeek con los datos del pronóstico.

        Formatea los datos diarios, horarios y actuales en un texto
        estructurado que la IA puede interpretar fácilmente.

        Args:
            daily: Pronóstico diario con la lista de días.
            hourly: Pronóstico por hora con la lista de horas.
            current: Condiciones meteorológicas actuales.

        Returns:
            String con el prompt completo listo para enviar a la API.
        """
        parts: list[str] = []

        # --- Condiciones actuales ---
        parts.append("=== CONDICIONES ACTUALES ===")
        current_desc = get_weather_symbol(current.symbol)
        parts.append(f"Temperatura: {current.temperature:.1f}°C")
        parts.append(f"Sensación térmica: {current.feels_like:.1f}°C")
        parts.append(f"Humedad: {current.humidity}%")
        parts.append(f"Estado del cielo: {current_desc.description}")
        parts.append(f"Nubosidad: {current.clouds}%")
        parts.append(f"Viento: {current.wind_speed} km/h "
                     f"con ráfagas de {current.wind_gust} km/h")
        parts.append(f"Presión: {current.pressure} hPa")
        if current.precipitation > 0:
            parts.append(f"Precipitación actual: {current.precipitation:.1f} mm")
        if current.precipitation_probability > 0:
            parts.append(
                f"Probabilidad de precipitación: {current.precipitation_probability}%"
            )
        parts.append("")

        # --- Pronóstico diario ---
        parts.append("=== PRONÓSTICO DIARIO ===")
        if daily and daily.days:
            # Zona horaria para formatear salida/puesta del sol
            try:
                tz = ZoneInfo(daily.timezone)
            except Exception:
                tz = None

            for i, day in enumerate(daily.days):
                symbol = get_weather_symbol(day.symbol)
                parts.append(f"Día {i + 1}:")
                parts.append(f"  Temperatura: mín {day.temperature_min:.1f}°C / "
                             f"máx {day.temperature_max:.1f}°C")
                parts.append(f"  Condición: {symbol.description}")
                parts.append(f"  Precipitación: {day.precipitation:.1f} mm "
                             f"(probabilidad: {day.rain_probability}%)")
                parts.append(
                    f"  Viento: {day.wind_speed} km/h "
                    f"({_degrees_to_cardinal(day.wind_direction)}) "
                    f"con ráfagas de {day.wind_gust} km/h"
                )
                parts.append(f"  Índice UV máximo: {day.uv_index_max:.1f}")
                if day.sunshine_duration > 0:
                    hours_sun = day.sunshine_duration / 3600.0
                    parts.append(f"  Horas de sol: {hours_sun:.1f}h")
                if tz is not None and day.sun_in > 0 and day.sun_out > 0:
                    sun_in = datetime.fromtimestamp(
                        day.sun_in / 1000, tz=tz
                    ).strftime("%H:%M")
                    sun_out = datetime.fromtimestamp(
                        day.sun_out / 1000, tz=tz
                    ).strftime("%H:%M")
                    parts.append(
                        f"  Salida del sol: {sun_in} · Puesta del sol: {sun_out}"
                    )
                parts.append("")
        else:
            parts.append("(No hay datos de pronóstico diario disponibles)")
            parts.append("")

        # --- Pronóstico horario (primeras 24 horas) ---
        parts.append("=== PRONÓSTICO HORARIO (próximas 24 horas) ===")
        if hourly and hourly.hours:
            max_hours = min(24, len(hourly.hours))
            for i in range(max_hours):
                hour = hourly.hours[i]
                symbol = get_weather_symbol(hour.symbol)
                parts.append(
                    f"Hora {i}: {hour.temperature:.1f}°C, "
                    f"{symbol.description}, "
                    f"humedad {hour.humidity}%, "
                    f"viento {hour.wind_speed} km/h, "
                    f"precipitación {hour.precipitation:.1f} mm "
                    f"(prob: {hour.rain_probability}%)"
                )
            if len(hourly.hours) > 24:
                parts.append(f"(...y {len(hourly.hours) - 24} horas más)")
        else:
            parts.append("(No hay datos de pronóstico horario disponibles)")
        parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Llamada a la API de DeepSeek
    # ------------------------------------------------------------------

    def _call_api(self, prompt: str) -> str:
        """Llama a la API de DeepSeek para generar el reporte.

        Args:
            prompt: Prompt con los datos meteorológicos estructurados.

        Returns:
            Texto del reporte generado por DeepSeek.

        Raises:
            requests.RequestException: Si hay error de red o HTTP.
            ValueError: Si la respuesta no tiene el formato esperado.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 900,
            "stream": False,
        }

        logger.info("Llamando a la API de DeepSeek...")
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        return self.parse_response(data)

    # ------------------------------------------------------------------
    # Parseo de respuesta
    # ------------------------------------------------------------------

    @staticmethod
    def parse_response(api_json: dict) -> str:
        """Extrae el texto del reporte de la respuesta JSON de DeepSeek.

        Args:
            api_json: Diccionario con la respuesta completa de la API.

        Returns:
            Texto del reporte desde choices[0].message.content.

        Raises:
            ValueError: Si la respuesta no tiene la estructura esperada.
        """
        try:
            choices = api_json["choices"]
            if not choices:
                raise ValueError("La respuesta no contiene choices")
            message = choices[0]["message"]
            content = message["content"]
            if not content or not content.strip():
                raise ValueError("El contenido del reporte está vacío")
            return content.strip()
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(
                f"Formato de respuesta inesperado de DeepSeek: {e}"
            ) from e

    # ------------------------------------------------------------------
    # Fallback sin API
    # ------------------------------------------------------------------

    @staticmethod
    def _build_fallback(
        daily: DailyForecast,
        current: CurrentWeather,
    ) -> str:
        """Construye un reporte de fallback simple basado en los datos.

        Se usa cuando la API de DeepSeek no está disponible o falla.

        Args:
            daily: Pronóstico diario.
            current: Condiciones actuales.

        Returns:
            Texto del reporte de fallback en español.
        """
        parts: list[str] = []
        parts.append("🌤️ **Resumen del tiempo**\n")

        current_sym = get_weather_symbol(current.symbol)
        parts.append(
            f"Actualmente tenemos {current.temperature:.0f}°C con "
            f"{current_sym.description.lower()}. "
            f"La sensación térmica es de {current.feels_like:.0f}°C "
            f"y la humedad es del {current.humidity}%.\n"
        )

        if daily and daily.days:
            parts.append("**Próximos días:**\n")
            for i, day in enumerate(daily.days[:3]):
                sym = get_weather_symbol(day.symbol)
                parts.append(
                    f"- Día {i + 1}: {sym.description}, "
                    f"mín {day.temperature_min:.0f}°C / "
                    f"máx {day.temperature_max:.0f}°C, "
                    f"precipitación: {day.precipitation:.1f} mm "
                    f"({day.rain_probability}% prob.)"
                )
            parts.append("")

        parts.append(
            "ℹ️ *Este es un resumen automático generado sin IA. "
            "Para obtener un reporte detallado, configura una API key "
            "de DeepSeek.*"
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Control de cache
    # ------------------------------------------------------------------

    def invalidate_cache(self) -> None:
        """Invalida el cache del reporte para forzar una regeneración.

        Debe llamarse cuando el ForecastService notifica que hay datos
        nuevos del pronóstico.
        """
        self._cached_report = None
        self._cached_forecast_at = 0.0
        logger.debug("Cache del reporte invalidado")

    # ------------------------------------------------------------------
    # Generación del reporte
    # ------------------------------------------------------------------

    def generate(
        self,
        daily: DailyForecast,
        hourly: HourlyForecast,
        current: CurrentWeather,
    ) -> str:
        """Genera un reporte meteorológico narrativo.

        Si los datos no cambiaron desde la última generación, retorna
        el reporte cacheado. Si cambiaron, construye un nuevo prompt
        y consulta a DeepSeek.

        Args:
            daily: Pronóstico diario.
            hourly: Pronóstico por hora.
            current: Condiciones actuales.

        Returns:
            Texto del reporte meteorológico en español neutro.
        """
        now = time.time()

        # Verificar si podemos usar el cache
        if self._cached_report is not None:
            logger.debug("Usando reporte cacheado")
            return self._cached_report

        # Construir el prompt
        prompt = self.build_prompt(daily, hourly, current)

        # Intentar llamar a la API de DeepSeek
        try:
            if self._api_key:
                report = self._call_api(prompt)
                self._cached_report = report
                self._cached_forecast_at = now
                self._last_generation_at = now
                logger.info("Reporte generado exitosamente con DeepSeek")
                return report
            else:
                logger.info("API key no configurada, usando fallback")
                return self._build_fallback(daily, current)
        except (requests.RequestException, ValueError) as e:
            logger.warning("Error al generar reporte con DeepSeek: %s", e)
            return self._build_fallback(daily, current)

    # ------------------------------------------------------------------
    # Período de enfriamiento
    # ------------------------------------------------------------------

    @property
    def last_generation_at(self) -> float:
        """Timestamp de la última generación exitosa (para UI)."""
        return self._last_generation_at
