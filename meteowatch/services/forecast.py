"""Servicio centralizado de datos meteorológicos.

Proporciona ForecastService como única fuente de verdad para los datos
del pronóstico, con cache en memoria, TTLs diferenciados y patrón observer
para notificar cambios a los componentes interesados (UI, tray, alertas).
"""

import logging
import threading
import time
from typing import Optional, Protocol

from meteowatch.api.client import (
    CurrentWeather,
    ForecastResult,
    OpenMeteoClient,
    OpenMeteoError,
)
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast

logger = logging.getLogger(__name__)

# TTLs de cache (en segundos)
CURRENT_TTL = 900       # 15 minutos
FORECAST_TTL = 3600     # 1 hora

# Reintentos con backoff exponencial
RETRY_DELAYS = [30, 60, 120]  # segundos entre reintentos
MAX_RETRIES = 3


# ------------------------------------------------------------------
# ForecastCache
# ------------------------------------------------------------------

class ForecastCache:
    """Cache en memoria para datos del pronóstico meteorológico.

    Almacena daily, hourly y current con timestamps independientes.
    La API gratuita de Open-Meteo devuelve todo junto, así que cualquier
    fetch actualiza los tres bloques, pero los TTLs se chequean por separado.

    Attributes:
        _current: Condiciones actuales cacheadas (o None).
        _daily: Pronóstico diario cacheado (o None).
        _hourly: Pronóstico por hora cacheado (o None).
        _current_at: Timestamp (time.time()) del último fetch de current.
        _forecast_at: Timestamp (time.time()) del último fetch de forecast.
    """

    def __init__(self):
        """Inicializa el cache vacío."""
        self._current: Optional[CurrentWeather] = None
        self._daily: Optional[DailyForecast] = None
        self._hourly: Optional[HourlyForecast] = None
        self._current_at: float = 0.0
        self._forecast_at: float = 0.0

    # ------------------------------------------------------------------
    # Consulta de staleness
    # ------------------------------------------------------------------

    def is_current_stale(self) -> bool:
        """Indica si los datos de current excedieron su TTL.

        Returns:
            True si el timestamp de current tiene más de CURRENT_TTL segundos.
        """
        if self._current is None or self._current_at <= 0.0:
            return True
        return (time.time() - self._current_at) >= CURRENT_TTL

    def is_forecast_stale(self) -> bool:
        """Indica si los datos de forecast excedieron su TTL.

        Returns:
            True si el timestamp de forecast tiene más de FORECAST_TTL segundos.
        """
        if self._daily is None or self._forecast_at <= 0.0:
            return True
        return (time.time() - self._forecast_at) >= FORECAST_TTL

    # ------------------------------------------------------------------
    # Estado general
    # ------------------------------------------------------------------

    def has_data(self) -> bool:
        """Indica si hay al menos datos de forecast en cache.

        Returns:
            True si hay daily y hourly cacheados.
        """
        return self._daily is not None and self._hourly is not None

    def has_current(self) -> bool:
        """Indica si hay datos de current en cache.

        Returns:
            True si hay current cacheado.
        """
        return self._current is not None

    def get_age_minutes(self) -> float:
        """Retorna la antigüedad del forecast en minutos.

        Returns:
            Minutos transcurridos desde el último fetch de forecast.
            Retorna 0.0 si no hay datos.
        """
        if self._forecast_at <= 0.0:
            return 0.0
        return (time.time() - self._forecast_at) / 60.0

    # ------------------------------------------------------------------
    # Acceso a datos
    # ------------------------------------------------------------------

    @property
    def current(self) -> Optional[CurrentWeather]:
        """Condiciones actuales cacheadas."""
        return self._current

    @property
    def daily(self) -> Optional[DailyForecast]:
        """Pronóstico diario cacheado."""
        return self._daily

    @property
    def hourly(self) -> Optional[HourlyForecast]:
        """Pronóstico por hora cacheado."""
        return self._hourly

    @property
    def forecast_at(self) -> float:
        """Timestamp del último fetch de forecast."""
        return self._forecast_at

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------

    def update(self, result: ForecastResult) -> None:
        """Actualiza el cache completo con datos frescos.

        Args:
            result: Resultado completo de la API (daily, hourly, current).
        """
        now = time.time()
        self._daily = result.daily
        self._hourly = result.hourly
        self._current = result.current
        self._current_at = now
        self._forecast_at = now
        logger.debug(
            "Cache actualizado: daily=%d días, hourly=%d horas, current=%.1f°C",
            len(result.daily.days) if result.daily else 0,
            len(result.hourly.hours) if result.hourly else 0,
            result.current.temperature,
        )


# ------------------------------------------------------------------
# ForecastObserver (protocolo)
# ------------------------------------------------------------------

class ForecastObserver(Protocol):
    """Protocolo que deben implementar los suscriptores del ForecastService.

    Cada método es opcional; la clase base BaseForecastObserver proporciona
    implementaciones no-op para que los suscriptores solo sobrescriban
    los que necesitan.
    """

    def on_forecast_updated(self, result: ForecastResult) -> None:
        """Notifica que el forecast completo fue actualizado.

        Args:
            result: ForecastResult con daily, hourly y current nuevos.
        """
        ...

    def on_current_updated(self, current: CurrentWeather) -> None:
        """Notifica que solo las condiciones actuales fueron actualizadas.

        Args:
            current: CurrentWeather con temperatura, icono, etc.
        """
        ...

    def on_forecast_error(self, message: str, cached: bool) -> None:
        """Notifica que ocurrió un error al obtener el forecast.

        Args:
            message: Mensaje descriptivo del error.
            cached: True si hay datos en cache que pueden usarse como fallback.
        """
        ...


class BaseForecastObserver:
    """Implementación base no-op de ForecastObserver.

    Los suscriptores heredan de esta clase y sobrescriben solo
    los métodos que necesitan.
    """

    def on_forecast_updated(self, result: ForecastResult) -> None:
        """No-op: el suscriptor puede sobrescribir."""

    def on_current_updated(self, current: CurrentWeather) -> None:
        """No-op: el suscriptor puede sobrescribir."""

    def on_forecast_error(self, message: str, cached: bool) -> None:
        """No-op: el suscriptor puede sobrescribir."""


# ------------------------------------------------------------------
# ForecastService
# ------------------------------------------------------------------

class ForecastService:
    """Servicio centralizado de datos meteorológicos.

    Única fuente de verdad para el pronóstico. Mantiene un ForecastCache
    en memoria y notifica a los observers suscritos cuando los datos cambian.

    El fetching se hace en hilos secundarios (daemon). Las notificaciones
    a los observers se despachan por GLib.idle_add() para seguridad de hilos
    con GTK. El caller es responsable de pasar las funciones GLib adecuadas.

    Uso:
        service = ForecastService()
        service.subscribe(mi_observer)
        service.refresh_forecast(idle_add=GLib.idle_add)
        service.refresh_current(idle_add=GLib.idle_add)
    """

    def __init__(self):
        """Inicializa el servicio con cache vacío y sin observers."""
        self._cache = ForecastCache()
        self._observers: list[ForecastObserver] = []
        self._fetch_lock = threading.Lock()
        self._client = OpenMeteoClient()
        logger.info("ForecastService inicializado")

    # ------------------------------------------------------------------
    # Gestión de observers
    # ------------------------------------------------------------------

    def subscribe(self, observer: ForecastObserver) -> None:
        """Registra un observer para recibir notificaciones.

        Args:
            observer: Instancia que implementa ForecastObserver.
        """
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug("Observer suscrito: %s", type(observer).__name__)

    def unsubscribe(self, observer: ForecastObserver) -> None:
        """Elimina un observer de la lista de suscriptores.

        Args:
            observer: Instancia previamente suscrita.
        """
        if observer in self._observers:
            self._observers.remove(observer)
            logger.debug("Observer eliminado: %s", type(observer).__name__)

    # ------------------------------------------------------------------
    # Refresco de datos
    # ------------------------------------------------------------------

    def refresh_forecast(self, idle_add, latitude: float, longitude: float,
                         timezone: str = "auto") -> None:
        """Solicita un refresco del forecast completo si está stale.

        Si el forecast está fresco, no hace nada. Si está stale, lanza
        un hilo secundario para fetchear y notificar.

        Args:
            idle_add: Función GLib.idle_add (o equivalente para testing).
            latitude: Latitud de la ubicación configurada.
            longitude: Longitud de la ubicación configurada.
            timezone: Zona horaria IANA.
        """
        if not self._cache.is_forecast_stale():
            logger.debug("Forecast fresco (%.0f min), omitiendo refresh",
                         self._cache.get_age_minutes())
            return

        logger.info("Forecast stale (%.0f min), iniciando refresh...",
                    self._cache.get_age_minutes())
        thread = threading.Thread(
            target=self._do_fetch,
            args=(idle_add, latitude, longitude, timezone, "forecast"),
            daemon=True,
        )
        thread.start()

    def refresh_current(self, idle_add, latitude: float, longitude: float,
                        timezone: str = "auto") -> None:
        """Solicita un refresco de condiciones actuales si está stale.

        Si current está fresco, no hace nada. Si está stale, lanza
        un hilo secundario para fetchear (la API devuelve todo junto,
        pero solo se notifica el evento 'current').

        Args:
            idle_add: Función GLib.idle_add (o equivalente para testing).
            latitude: Latitud de la ubicación configurada.
            longitude: Longitud de la ubicación configurada.
            timezone: Zona horaria IANA.
        """
        if not self._cache.is_current_stale():
            logger.debug("Current fresco (%.0f min), omitiendo refresh",
                         self._cache.get_age_minutes())
            return

        logger.info("Current stale, iniciando refresh...")
        thread = threading.Thread(
            target=self._do_fetch,
            args=(idle_add, latitude, longitude, timezone, "current"),
            daemon=True,
        )
        thread.start()

    # ------------------------------------------------------------------
    # Acceso síncrono al cache
    # ------------------------------------------------------------------

    def get_cached_forecast(self) -> Optional[ForecastResult]:
        """Retorna el forecast cacheado como ForecastResult, o None.

        Returns:
            ForecastResult con daily, hourly y current, o None si no hay datos.
        """
        if not self._cache.has_data():
            return None
        return ForecastResult(
            daily=self._cache.daily,     # type: ignore[arg-type]
            hourly=self._cache.hourly,   # type: ignore[arg-type]
            current=self._cache.current,  # type: ignore[arg-type]
            raw={},
        )

    def get_cached_current(self) -> Optional[CurrentWeather]:
        """Retorna las condiciones actuales cacheadas, o None.

        Returns:
            CurrentWeather o None si no hay datos.
        """
        return self._cache.current

    def get_age_minutes(self) -> float:
        """Retorna la antigüedad del forecast en minutos.

        Returns:
            Minutos desde el último fetch exitoso.
        """
        return self._cache.get_age_minutes()

    # ------------------------------------------------------------------
    # Fetch interno (hilo secundario)
    # ------------------------------------------------------------------

    def _do_fetch(self, idle_add, latitude: float, longitude: float,
                  timezone: str, event_type: str) -> None:
        """Ejecuta el fetch en un hilo secundario con reintentos.

        Args:
            idle_add: Función para despachar callbacks al hilo principal.
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA.
            event_type: 'forecast' o 'current' (determina qué notificar).
        """
        # Control de concurrencia: solo un fetch a la vez
        if not self._fetch_lock.acquire(blocking=False):
            logger.debug("Fetch ya en vuelo, esperando...")
            with self._fetch_lock:
                # Al obtener el lock, verificar si el fetch anterior
                # ya actualizó los datos que necesitamos
                if event_type == "current" and not self._cache.is_current_stale():
                    logger.debug("Current ya fue actualizado por otro fetch")
                    return
                if event_type == "forecast" and not self._cache.is_forecast_stale():
                    logger.debug("Forecast ya fue actualizado por otro fetch")
                    return
                # Si aún está stale, continuar con el fetch
        else:
            # Adquirimos el lock, lo liberaremos al final
            pass

        try:
            result = self._fetch_with_retry(latitude, longitude, timezone)
        except OpenMeteoError as e:
            logger.warning("Error de API en refresh (%s): %s", event_type, e)
            cached = self._cache.has_data()
            idle_add(self._notify_error, str(e), cached)
            return
        except Exception:
            logger.exception("Error inesperado en refresh (%s)", event_type)
            cached = self._cache.has_data()
            idle_add(self._notify_error, "Error inesperado al obtener el pronóstico", cached)
            return
        finally:
            # Liberar el lock si lo tenemos
            try:
                self._fetch_lock.release()
            except RuntimeError:
                pass  # Lock ya liberado o no adquirido

        # Éxito: actualizar cache y notificar
        self._cache.update(result)

        if event_type == "forecast":
            idle_add(self._notify_forecast, result)
        else:
            idle_add(self._notify_current, result.current)

    def _fetch_with_retry(self, latitude: float, longitude: float,
                          timezone: str) -> ForecastResult:
        """Ejecuta el fetch con reintentos y backoff exponencial.

        Args:
            latitude: Latitud de la ubicación.
            longitude: Longitud de la ubicación.
            timezone: Zona horaria IANA.

        Returns:
            ForecastResult con los datos obtenidos.

        Raises:
            OpenMeteoError: Si todos los reintentos fallan.
        """
        last_error: Optional[OpenMeteoError] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    delay = RETRY_DELAYS[attempt - 1]
                    logger.debug("Reintento %d/%d en %ds...",
                                 attempt, MAX_RETRIES, delay)
                    time.sleep(delay)
                return self._client.get_forecast(latitude, longitude, timezone)
            except OpenMeteoError as e:
                last_error = e
                logger.warning("Intento %d/%d fallido: %s",
                               attempt + 1, MAX_RETRIES + 1, e)

        raise last_error  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Notificación a observers (ejecutado en hilo principal vía idle_add)
    # ------------------------------------------------------------------

    def _notify_forecast(self, result: ForecastResult) -> None:
        """Notifica a todos los observers que el forecast fue actualizado.

        Args:
            result: ForecastResult con los datos nuevos.
        """
        for observer in self._observers:
            try:
                observer.on_forecast_updated(result)
            except Exception:
                logger.exception(
                    "Error en observer %s.on_forecast_updated",
                    type(observer).__name__,
                )

    def _notify_current(self, current: CurrentWeather) -> None:
        """Notifica a todos los observers que current fue actualizado.

        Args:
            current: CurrentWeather con los datos nuevos.
        """
        for observer in self._observers:
            try:
                observer.on_current_updated(current)
            except Exception:
                logger.exception(
                    "Error en observer %s.on_current_updated",
                    type(observer).__name__,
                )

    def _notify_error(self, message: str, cached: bool) -> None:
        """Notifica a todos los observers que ocurrió un error.

        Args:
            message: Mensaje descriptivo del error.
            cached: True si hay datos en cache como fallback.
        """
        for observer in self._observers:
            try:
                observer.on_forecast_error(message, cached)
            except Exception:
                logger.exception(
                    "Error en observer %s.on_forecast_error",
                    type(observer).__name__,
                )
