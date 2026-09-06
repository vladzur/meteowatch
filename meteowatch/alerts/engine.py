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
    CATEGORY_DAILY_RAIN,
    CATEGORY_FLASH_FLOOD,
    DAILY_RAIN_YELLOW,
    FLASH_FLOOD_WINDOW,
    HOURS_WINDOW,
    get_hour_alerts,
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

        # Alertas horarias en ventana general (excluye inundación)
        alerts.extend(self._check_hourly(hourly, HOURS_WINDOW, False))
        # Inundación repentina en su ventana propia
        alerts.extend(self._check_hourly(hourly, FLASH_FLOOD_WINDOW, True))

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

    def _check_hourly(self, hourly: HourlyForecast, window: int,
                      include_flash_flood: bool) -> list[Alert]:
        """Recoge alertas horarias de la fuente unificada en una ventana.

        Args:
            hourly: Pronóstico por hora.
            window: Cantidad de horas a evaluar desde el inicio.
            include_flash_flood: Si True, solo incluye alertas de inundación;
                si False, las excluye.

        Returns:
            Alertas horarias detectadas dentro de la ventana.
        """
        alerts: list[Alert] = []
        for hour in hourly.hours[:window]:
            for alert in get_hour_alerts(hour):
                is_flash_flood = alert.category == CATEGORY_FLASH_FLOOD
                if is_flash_flood == include_flash_flood:
                    alerts.append(alert)
        return alerts

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
