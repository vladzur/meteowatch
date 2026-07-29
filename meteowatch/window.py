"""Ventana principal de Meteowatch.

Contiene el Adw.NavigationView que orquesta la navegación entre
las páginas de configuración, pronóstico diario y detalle por hora.

Actúa como ForecastObserver del ForecastService para coordinar
la actualización del icono del tray y la evaluación de alertas
en cada refresco de datos.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from meteowatch.alerts import AlertEngine, send_alerts
from meteowatch.api.client import CurrentWeather, ForecastResult
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.services.forecast import BaseForecastObserver, ForecastService
from meteowatch.status_notifier import StatusNotifierItem
from meteowatch.widgets.daily_card import DailyForecastPage
from meteowatch.widgets.hourly_panel import HourlyForecastPage
from meteowatch.widgets.location_search import LocationSearchPage

logger = logging.getLogger(__name__)


class MeteowatchWindow(Adw.ApplicationWindow, BaseForecastObserver):
    """Ventana principal con navegación entre páginas."""

    def __init__(self, config: AppConfig, forecast_service: ForecastService,
                 enable_tray: bool = True, **kwargs):
        """Inicializa la ventana principal.

        Args:
            config: Configuración de la aplicación.
            forecast_service: Servicio centralizado de datos meteorológicos.
            enable_tray: Si se debe activar el icono de bandeja del sistema.
        """
        super().__init__(**kwargs)
        self._config = config
        self._forecast_service = forecast_service
        self._enable_tray = enable_tray

        # Flag para distinguir cierre real vs minimizar al tray
        self.force_quit: bool = False

        # Motor de alertas climáticas (persiste estado de deduplicación)
        self._alert_engine = AlertEngine()

        # Temporizadores de actualización periódica
        self._current_timer_id: int = 0   # cada 15 min
        self._forecast_timer_id: int = 0  # cada 1 hora

        self.set_title("Meteowatch")
        self.set_default_size(420, 680)
        self.set_size_request(360, 500)

        # Navegación principal
        self._navigation = Adw.NavigationView()
        self.set_content(self._navigation)

        # Conectar señal de cierre para minimizar al tray
        self.connect("close-request", self._on_close_request)

        # Atajo Ctrl+Q para salir de la aplicación
        self._setup_shortcuts()

        # El icono de bandeja se inicializa de forma diferida
        # para evitar bloquear el escritorio durante el arranque.
        self._tray = None
        if self._enable_tray:
            GLib.idle_add(self._init_tray)

        # Suscribirse al ForecastService para recibir actualizaciones
        self._forecast_service.subscribe(self)

        # Determinar página inicial
        if config.is_configured():
            self._show_daily_forecast()
        else:
            self._show_location_search()

    def _init_tray(self) -> None:
        """Inicializa el icono de bandeja de forma diferida."""
        app = self.get_application()
        if app is not None and self._enable_tray:
            self._tray = StatusNotifierItem(app, self)

    def _setup_shortcuts(self) -> None:
        """Registra atajos de teclado de la ventana."""
        controller = Gtk.ShortcutController()
        self.add_controller(controller)

        # Ctrl+Q: salir de la aplicación
        trigger = Gtk.ShortcutTrigger.parse_string("<Control>q")
        action = Gtk.CallbackAction.new(self._on_quit_shortcut)
        controller.add_shortcut(Gtk.Shortcut.new(trigger=trigger, action=action))

    def _on_quit_shortcut(self, widget, arg) -> None:
        """Callback del atajo Ctrl+Q: fuerza el cierre real."""
        logger.debug("Atajo Ctrl+Q activado")
        app = self.get_application()
        if app is not None:
            app.activate_action("quit", None)

    def present(self) -> None:
        """Restaura la ventana desde el tray."""
        super().present()
        logger.debug("Ventana restaurada desde el tray")

    def _show_location_search(self) -> None:
        """Muestra la página de búsqueda de ubicación y configuración."""
        logger.info("Navegando a: búsqueda de ubicación")
        page = LocationSearchPage(
            config=self._config,
            on_location_selected=self._on_location_selected,
        )
        self._navigation.push(page)

    def _show_daily_forecast(self) -> None:
        """Muestra la página de pronóstico diario."""
        logger.info("Navegando a: pronóstico diario (lat=%.4f, lon=%.4f)", self._config.latitude, self._config.longitude)
        page = DailyForecastPage(
            config=self._config,
            forecast_service=self._forecast_service,
            on_day_selected=self._on_day_selected,
            on_change_location=self._on_change_location,
        )
        self._navigation.push(page)
        page.load_forecast()

    def _show_hourly_forecast(self, location_hash: str, day_start: int) -> None:
        """Muestra la página de pronóstico por hora.

        Args:
            location_hash: Hash de la ubicación (no usado, mantenido por compatibilidad).
            day_start: Timestamp del inicio del día (no usado, mantenido por compatibilidad).
        """
        logger.info("Navegando a: pronóstico por hora")
        page = HourlyForecastPage(
            config=self._config,
            forecast_service=self._forecast_service,
            location_hash=location_hash,
            on_change_location=self._on_change_location,
        )
        self._navigation.push(page)

    def _on_location_selected(self, location_hash: str, location_name: str) -> None:
        """Callback cuando el usuario selecciona una ubicación.

        Args:
            location_hash: Hash de la ubicación (no usado, mantenido por compatibilidad).
            location_name: Nombre de la ubicación seleccionada.
        """
        logger.info("Ubicación seleccionada: %s", location_name)
        self._show_daily_forecast()

    def _on_day_selected(self, location_hash: str, day_start: int) -> None:
        """Callback cuando el usuario hace clic en un día.

        Args:
            location_hash: Hash de la ubicación (no usado, mantenido por compatibilidad).
            day_start: Timestamp de inicio del día seleccionado.
        """
        logger.info("Día seleccionado: start=%s", day_start)
        self._show_hourly_forecast(location_hash, day_start)

    def _on_change_location(self) -> None:
        """Callback para cambiar de ubicación (vuelve a búsqueda)."""
        logger.info("Cambiando ubicación...")
        # Limpiar ubicación guardada y volver a búsqueda
        self._config.latitude = 0.0
        self._config.longitude = 0.0
        self._config.location_name = ""
        self._config.save()
        self._show_location_search()

    def _on_close_request(self, window) -> bool:
        """Decide si cerrar la ventana o minimizar a la bandeja."""
        if self.force_quit:
            logger.debug("Cierre forzado: destruyendo ventana")
            return False

        if self._config.close_to_tray and self._tray is not None and self._tray.is_available:
            logger.debug("Minimizando al tray")
            self.hide()
            return True

        return False

    def cleanup_tray(self) -> None:
        """Libera los recursos del system tray al cerrar la aplicación."""
        self._stop_timers()
        self._forecast_service.unsubscribe(self)
        if self._tray is not None:
            self._tray.cleanup()
            self._tray = None

    # ------------------------------------------------------------------
    # Timers de refresco periódico
    # ------------------------------------------------------------------

    def start_timers(self) -> None:
        """Inicia los temporizadores de refresco periódico.

        - current: cada 15 minutos (900s)
        - forecast: cada 1 hora (3600s)
        """
        if not self._config.is_configured():
            return

        if self._current_timer_id == 0:
            self._current_timer_id = GLib.timeout_add_seconds(
                900, self._on_current_timer
            )
            logger.info("Timer de current iniciado (cada 15 min)")

        if self._forecast_timer_id == 0:
            self._forecast_timer_id = GLib.timeout_add_seconds(
                3600, self._on_forecast_timer
            )
            logger.info("Timer de forecast iniciado (cada 1 hora)")

    def _stop_timers(self) -> None:
        """Detiene ambos temporizadores de refresco periódico."""
        if self._current_timer_id != 0:
            GLib.source_remove(self._current_timer_id)
            self._current_timer_id = 0
            logger.debug("Timer de current detenido")
        if self._forecast_timer_id != 0:
            GLib.source_remove(self._forecast_timer_id)
            self._forecast_timer_id = 0
            logger.debug("Timer de forecast detenido")

    def _on_current_timer(self) -> bool:
        """Callback del timer de current (cada 15 min).

        Returns:
            True para mantener el timer activo.
        """
        if self._config.is_configured():
            logger.debug("Timer de current: solicitando refresh...")
            self._forecast_service.refresh_current(
                GLib.idle_add,
                self._config.latitude,
                self._config.longitude,
                self._config.timezone,
            )
        return True  # noqa: S1751 — GLib timeout requiere retornar siempre bool

    def _on_forecast_timer(self) -> bool:
        """Callback del timer de forecast (cada 1 hora).

        Returns:
            True para mantener el timer activo.
        """
        if self._config.is_configured():
            logger.debug("Timer de forecast: solicitando refresh...")
            self._forecast_service.refresh_forecast(
                GLib.idle_add,
                self._config.latitude,
                self._config.longitude,
                self._config.timezone,
            )
        return True  # noqa: S1751 — GLib timeout requiere retornar siempre bool

    # ------------------------------------------------------------------
    # ForecastObserver implementation
    # ------------------------------------------------------------------

    def on_current_updated(self, current: CurrentWeather) -> None:
        """Actualiza el icono del tray con las condiciones actuales.

        Args:
            current: Condiciones actuales actualizadas.
        """
        try:
            symbol = get_weather_symbol(current.symbol)
            if self._tray is not None:
                self._tray.update_icon(symbol.emoji, current.temperature)
            logger.debug(
                "Tray actualizado (current): %s %.1f°C",
                symbol.emoji, current.temperature,
            )
        except Exception:
            logger.exception("Error al actualizar tray en on_current_updated")

    def on_forecast_updated(self, result: ForecastResult) -> None:
        """Actualiza el icono del tray y evalúa alertas climáticas.

        Args:
            result: ForecastResult con daily, hourly y current nuevos.
        """
        # Iniciar timers en el primer forecast exitoso
        self.start_timers()

        # Actualizar tray con las condiciones actuales incluidas en el forecast
        try:
            symbol = get_weather_symbol(result.current.symbol)
            if self._tray is not None:
                self._tray.update_icon(symbol.emoji, result.current.temperature)
            logger.debug(
                "Tray actualizado (forecast): %s %.1f°C",
                symbol.emoji, result.current.temperature,
            )
        except Exception:
            logger.exception("Error al actualizar tray en on_forecast_updated")

        # Evaluar alertas climáticas con los datos completos del forecast
        try:
            alerts = self._alert_engine.evaluate(result.daily, result.hourly)
            if alerts:
                logger.info("Alertas detectadas en refresh: %d", len(alerts))
                send_alerts(alerts)
        except Exception:
            logger.exception("Error al evaluar alertas en on_forecast_updated")

    def on_forecast_error(self, message: str, cached: bool) -> None:
        """Registra el error de forecast (el manejo visual lo hace la UI).

        Args:
            message: Mensaje descriptivo del error.
            cached: True si hay datos en cache como fallback.
        """
        if cached:
            logger.warning("Error de forecast (con cache): %s", message)
        else:
            logger.error("Error de forecast (sin cache): %s", message)
