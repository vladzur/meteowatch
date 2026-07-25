"""Ventana principal de Meteowatch.

Contiene el Adw.NavigationView que orquesta la navegación entre
las páginas de configuración, pronóstico diario y detalle por hora.
"""

import logging
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from meteowatch.api.client import OpenMeteoClient, OpenMeteoError
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.status_notifier import StatusNotifierItem
from meteowatch.widgets.daily_card import DailyForecastPage
from meteowatch.widgets.hourly_panel import HourlyForecastPage
from meteowatch.widgets.location_search import LocationSearchPage

logger = logging.getLogger(__name__)


class MeteowatchWindow(Adw.ApplicationWindow):
    """Ventana principal con navegación entre páginas."""

    def __init__(self, config: AppConfig, enable_tray: bool = True, **kwargs):
        """Inicializa la ventana principal.

        Args:
            config: Configuración de la aplicación.
            enable_tray: Si se debe activar el icono de bandeja del sistema.
        """
        super().__init__(**kwargs)
        self._config = config
        self._enable_tray = enable_tray

        # Flag para distinguir cierre real vs minimizar al tray
        self.force_quit: bool = False

        # Temporizador de actualización periódica del icono del tray
        self._refresh_timer_id: int = 0

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
            on_day_selected=self._on_day_selected,
            on_change_location=self._on_change_location,
            on_weather_updated=self._on_weather_updated,
        )
        self._navigation.push(page)
        page.load_forecast()

    def _on_weather_updated(self, symbol_emoji: str, temperature: float | None) -> None:
        """Actualiza el icono del tray y arranca el refresco periódico."""
        if self._tray is not None:
            self._tray.update_icon(symbol_emoji, temperature)
        # Iniciar refresco cada hora tras la primera carga exitosa
        if self._refresh_timer_id == 0 and self._config.is_configured():
            self._start_periodic_refresh()

    def _show_hourly_forecast(self, location_hash: str, day_start: int) -> None:
        """Muestra la página de pronóstico por hora.

        Args:
            location_hash: Hash de la ubicación (no usado, mantenido por compatibilidad).
            day_start: Timestamp del inicio del día (no usado, mantenido por compatibilidad).
        """
        logger.info("Navegando a: pronóstico por hora")
        page = HourlyForecastPage(
            config=self._config,
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
        self._stop_periodic_refresh()
        if self._tray is not None:
            self._tray.cleanup()
            self._tray = None

    # ------------------------------------------------------------------
    # Refresco periódico del icono del tray (cada hora)
    # ------------------------------------------------------------------

    def _start_periodic_refresh(self) -> None:
        """Inicia el temporizador de refresco horario del icono del tray."""
        if self._refresh_timer_id != 0:
            return
        # 3600 segundos = 1 hora
        self._refresh_timer_id = GLib.timeout_add_seconds(
            3600, self._on_periodic_refresh
        )
        logger.info("Refresco periódico del tray iniciado (cada 1 hora)")

    def _stop_periodic_refresh(self) -> None:
        """Detiene el temporizador de refresco periódico."""
        if self._refresh_timer_id != 0:
            GLib.source_remove(self._refresh_timer_id)
            self._refresh_timer_id = 0
            logger.debug("Refresco periódico del tray detenido")

    def _on_periodic_refresh(self) -> bool:
        """Callback del temporizador: actualiza el icono del tray.

        Consulta el endpoint horario de la API en un hilo secundario
        y actualiza el icono con la temperatura y símbolo actuales.

        Returns:
            True para mantener el temporizador activo (GLib.timeout_add).
        """
        if not self._config.is_configured():
            logger.debug("App no configurada, omitiendo refresco periódico")
            return True

        logger.debug("Iniciando refresco periódico del tray...")

        def do_refresh():
            try:
                client = OpenMeteoClient()
                current = client.get_current_weather(
                    self._config.latitude,
                    self._config.longitude,
                    self._config.timezone,
                )
                symbol = get_weather_symbol(current.symbol)
                GLib.idle_add(
                    self._on_weather_updated,
                    symbol.emoji,
                    current.temperature,
                )
                logger.info(
                    "Tray actualizado (periódico): %s %.1f°C",
                        symbol.emoji, current.temperature,
                    )
            except OpenMeteoError as e:
                logger.warning("Error de API en refresco periódico: %s", e)
            except Exception:
                logger.exception("Error inesperado en refresco periódico")

        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()

        # Retornar True para que GLib mantenga el temporizador
        return True
