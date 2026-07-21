"""Ventana principal de Meteowatch.

Contiene el Adw.NavigationView que orquesta la navegación entre
las páginas de configuración, pronóstico diario y detalle por hora.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from meteowatch.config import AppConfig
from meteowatch.widgets.daily_card import DailyForecastPage
from meteowatch.widgets.hourly_panel import HourlyForecastPage
from meteowatch.widgets.location_search import LocationSearchPage

logger = logging.getLogger(__name__)


class MeteowatchWindow(Adw.ApplicationWindow):
    """Ventana principal con navegación entre páginas."""

    def __init__(self, config: AppConfig, **kwargs):
        """Inicializa la ventana principal.

        Args:
            config: Configuración de la aplicación.
        """
        super().__init__(**kwargs)
        self._config = config

        self.set_title("Meteowatch")
        self.set_default_size(420, 680)
        self.set_size_request(360, 500)

        # Navegación principal
        self._navigation = Adw.NavigationView()
        self.set_content(self._navigation)

        # Determinar página inicial
        if config.is_configured():
            self._show_daily_forecast()
        else:
            self._show_location_search()

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
        logger.info("Navegando a: pronóstico diario (hash=%s)", self._config.location_hash)
        page = DailyForecastPage(
            config=self._config,
            on_day_selected=self._on_day_selected,
            on_change_location=self._on_change_location,
        )
        self._navigation.push(page)
        page.load_forecast()

    def _show_hourly_forecast(self, location_hash: str, day_start: int) -> None:
        """Muestra la página de pronóstico por hora para un día específico.

        Args:
            location_hash: Hash de la ubicación.
            day_start: Timestamp del inicio del día.
        """
        logger.info("Navegando a: pronóstico por hora (hash=%s, start=%s)",
                    location_hash, day_start)
        page = HourlyForecastPage(
            config=self._config,
            location_hash=location_hash,
            day_start=day_start,
        )
        self._navigation.push(page)

    def _on_location_selected(self, location_hash: str, location_name: str) -> None:
        """Callback cuando el usuario selecciona una ubicación.

        Args:
            location_hash: Hash de la ubicación seleccionada.
            location_name: Nombre de la ubicación seleccionada.
        """
        logger.info("Ubicación seleccionada: %s (%s)", location_name, location_hash)
        self._show_daily_forecast()

    def _on_day_selected(self, location_hash: str, day_start: int) -> None:
        """Callback cuando el usuario hace clic en un día.

        Args:
            location_hash: Hash de la ubicación.
            day_start: Timestamp de inicio del día seleccionado.
        """
        logger.info("Día seleccionado: %s (start=%s)", location_hash, day_start)
        self._show_hourly_forecast(location_hash, day_start)

    def _on_change_location(self) -> None:
        """Callback para cambiar de ubicación (vuelve a búsqueda)."""
        logger.info("Cambiando ubicación...")
        # Limpiar ubicación guardada y volver a búsqueda
        self._config.location_hash = ""
        self._config.location_name = ""
        self._config.save()
        self._show_location_search()
