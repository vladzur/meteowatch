"""Motor de evaluación de alertas climáticas.

Evalúa los datos del pronóstico (diario y por hora) contra las reglas
definidas en rules.py y genera una lista de Alertas activas.

Incluye deduplicación temporal para evitar notificaciones repetitivas
en ciclos de refresco consecutivos.
"""

import logging
import time

from meteowatch.alerts.rules import (
    Alert,
    WMO_ORANGE_CODES,
    WMO_YELLOW_CODES,
    WMO_CATEGORY_MAP,
    WIND_GUST_YELLOW,
    WIND_GUST_ORANGE,
    FLASH_FLOOD_ORANGE,
    DAILY_RAIN_YELLOW,
    FROST_YELLOW,
    HEAT_YELLOW,
    HOURS_WINDOW,
    FLASH_FLOOD_WINDOW,
    CATEGORY_WIND,
    CATEGORY_FLASH_FLOOD,
    CATEGORY_DAILY_RAIN,
    CATEGORY_FROST,
    CATEGORY_HEAT,
)
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast

logger = logging.getLogger(__name__)

# Ventana de deduplicación: no repetir la misma alerta en este intervalo (segundos)
DEDUP_WINDOW_SECONDS = 3 * 3600  # 3 horas


class AlertEngine:
    """Evalúa datos de pronóstico y genera alertas climáticas.

    Diseñado para instanciarse una vez por ciclo de vida de la ventana
    y reutilizarse en cada refresco periódico, manteniendo el estado
    de deduplicación entre evaluaciones.
    """

    def __init__(self):
        """Inicializa el motor de alertas con estado de deduplicación vacío."""
        # _sent_alerts: dict[(category, level), timestamp]
        self._sent_alerts: dict[tuple[str, str], float] = {}

    def evaluate(self, daily: DailyForecast,
                 hourly: HourlyForecast) -> list[Alert]:
        """Evalúa todas las reglas contra los datos del pronóstico.

        Args:
            daily: Pronóstico diario con precipitation_sum y weather_code.
            hourly: Pronóstico por hora con todas las variables necesarias.

        Returns:
            Lista de alertas activas (ya filtradas por deduplicación).
        """
        if not hourly.hours:
            logger.debug("Sin datos horarios, omitiendo evaluación de alertas")
            return []

        alerts: list[Alert] = []

        alerts.extend(self._check_wmo_codes(hourly))
        alerts.extend(self._check_wind_gusts(hourly))
        alerts.extend(self._check_flash_flood(hourly))
        alerts.extend(self._check_temperature(hourly))

        if daily and daily.days:
            alerts.extend(self._check_daily_rain(daily))

        # Filtrar duplicados
        filtered = self._filter_duplicates(alerts)

        if filtered:
            logger.info(
                "Alertas detectadas: %d (de %d totales, %d duplicadas)",
                len(filtered), len(alerts), len(alerts) - len(filtered),
            )

        return filtered

    # ------------------------------------------------------------------
    # Checks individuales
    # ------------------------------------------------------------------

    def _check_wmo_codes(self, hourly: HourlyForecast) -> list[Alert]:
        """Evalúa códigos WMO en las horas del horizonte de evaluación.

        Busca en las primeras HOURS_WINDOW horas del pronóstico.
        """
        alerts: list[Alert] = []
        check_hours = hourly.hours[:HOURS_WINDOW]

        for hour in check_hours:
            code = hour.symbol

            if code in WMO_ORANGE_CODES:
                alerts.append(Alert(
                    level="orange",
                    category=WMO_CATEGORY_MAP.get(code, "unknown_wmo"),
                    message=WMO_ORANGE_CODES[code],
                    source_code=code,
                    value=None,
                ))
            elif code in WMO_YELLOW_CODES:
                alerts.append(Alert(
                    level="yellow",
                    category=WMO_CATEGORY_MAP.get(code, "unknown_wmo"),
                    message=WMO_YELLOW_CODES[code],
                    source_code=code,
                    value=None,
                ))

        return alerts

    def _check_wind_gusts(self, hourly: HourlyForecast) -> list[Alert]:
        """Evalúa ráfagas de viento contra los umbrales configurados.

        Toma el valor máximo en la ventana de evaluación para determinar
        el nivel de alerta.
        """
        check_hours = hourly.hours[:HOURS_WINDOW]
        if not check_hours:
            return []

        max_gust = max(h.wind_gust for h in check_hours)

        if max_gust > WIND_GUST_ORANGE:
            return [Alert(
                level="orange",
                category=CATEGORY_WIND,
                message=(
                    f"Ráfagas de viento extremas detectadas "
                    f"({max_gust:.0f} km/h). Riesgo de caída de objetos y árboles."
                ),
                source_code=None,
                value=max_gust,
            )]
        elif max_gust > WIND_GUST_YELLOW:
            return [Alert(
                level="yellow",
                category=CATEGORY_WIND,
                message=(
                    f"Ráfagas de viento fuertes previstas "
                    f"({max_gust:.0f} km/h). Precaución en exteriores."
                ),
                source_code=None,
                value=max_gust,
            )]

        return []

    def _check_flash_flood(self, hourly: HourlyForecast) -> list[Alert]:
        """Evalúa riesgo de inundación repentina por lluvia intensa.

        Verifica si alguna de las próximas FLASH_FLOOD_WINDOW horas
        supera el umbral de precipitación.
        """
        check_hours = hourly.hours[:FLASH_FLOOD_WINDOW]

        for hour in check_hours:
            if hour.precipitation > FLASH_FLOOD_ORANGE:
                return [Alert(
                    level="orange",
                    category=CATEGORY_FLASH_FLOOD,
                    message=(
                        f"Lluvia torrencial detectada "
                        f"({hour.precipitation:.1f} mm/h). "
                        f"Riesgo de inundación repentina. Evita zonas bajas."
                    ),
                    source_code=None,
                    value=hour.precipitation,
                )]

        return []

    def _check_daily_rain(self, daily: DailyForecast) -> list[Alert]:
        """Evalúa acumulación diaria de lluvia."""
        if not daily.days:
            return []

        today = daily.days[0]
        if today.precipitation > DAILY_RAIN_YELLOW:
            return [Alert(
                level="yellow",
                category=CATEGORY_DAILY_RAIN,
                message=(
                    f"Acumulación de lluvia elevada hoy "
                    f"({today.precipitation:.1f} mm). "
                    f"Posibles anegamientos en zonas bajas."
                ),
                source_code=None,
                value=today.precipitation,
            )]

        return []

    def _check_temperature(self, hourly: HourlyForecast) -> list[Alert]:
        """Evalúa temperaturas peligrosas (heladas y calor extremo).

        Usa la sensación térmica (apparent_temperature) que incluye
        el efecto del viento y la humedad.
        """
        check_hours = hourly.hours[:HOURS_WINDOW]
        if not check_hours:
            return []

        alerts: list[Alert] = []

        for hour in check_hours:
            feels = hour.temperature_feels_like

            if feels < FROST_YELLOW:
                alerts.append(Alert(
                    level="yellow",
                    category=CATEGORY_FROST,
                    message=(
                        f"Temperatura bajo cero detectada "
                        f"(sensación {feels:.0f}°C). "
                        f"Riesgo de heladas. Precaución en carreteras."
                    ),
                    source_code=None,
                    value=feels,
                ))
                break  # Una alerta por helada es suficiente

        for hour in check_hours:
            feels = hour.temperature_feels_like

            if feels > HEAT_YELLOW:
                alerts.append(Alert(
                    level="yellow",
                    category=CATEGORY_HEAT,
                    message=(
                        f"Temperatura extrema detectada "
                        f"(sensación {feels:.0f}°C). "
                        f"Hidrátate y evita exposición prolongada al sol."
                    ),
                    source_code=None,
                    value=feels,
                ))
                break  # Una alerta por calor es suficiente

        return alerts

    # ------------------------------------------------------------------
    # Deduplicación
    # ------------------------------------------------------------------

    def _filter_duplicates(self, alerts: list[Alert]) -> list[Alert]:
        """Filtra alertas duplicadas dentro de la ventana de deduplicación.

        Una alerta se considera duplicada si ya se envió una del mismo
        category + level en las últimas DEDUP_WINDOW_SECONDS.

        Args:
            alerts: Lista de alertas detectadas en esta evaluación.

        Returns:
            Alertas que no son duplicadas (y actualiza el registro).
        """
        now = time.time()
        filtered: list[Alert] = []

        # Limpiar entradas expiradas del registro
        expired = [
            key for key, ts in self._sent_alerts.items()
            if now - ts > DEDUP_WINDOW_SECONDS
        ]
        for key in expired:
            del self._sent_alerts[key]

        for alert in alerts:
            key = (alert.category, alert.level)
            if key not in self._sent_alerts:
                self._sent_alerts[key] = now
                filtered.append(alert)
            else:
                logger.debug(
                    "Alerta duplicada suprimida: category=%s, level=%s",
                    alert.category, alert.level,
                )

        return filtered
