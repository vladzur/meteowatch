"""Aplicación principal de Meteowatch.

Subclase de Adw.Application que gestiona el ciclo de vida
y los recursos de la aplicación GTK 4.
"""

import logging
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from meteowatch.config import AppConfig
from meteowatch.window import MeteowatchWindow

logger = logging.getLogger(__name__)


class MeteowatchApp(Adw.Application):
    """Aplicación GTK 4 + libadwaita de pronóstico meteorológico."""

    def __init__(self):
        super().__init__(
            application_id="com.meteowatch.app",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._config = AppConfig.load()

    def do_activate(self) -> None:
        """Activa la aplicación y crea la ventana principal."""
        logger.info("Activando Meteowatch...")
        logger.info("Configuración: api_key=%s..., location_hash=%s, location_name=%s, configured=%s",
                    self._config.api_key[:8] if self._config.api_key else "(vacía)",
                    self._config.location_hash or "(vacío)",
                    self._config.location_name or "(vacío)",
                    self._config.is_configured())
        window = MeteowatchWindow(application=self, config=self._config)
        window.present()

    def do_startup(self) -> None:
        """Inicializa recursos antes de activar la aplicación."""
        Adw.Application.do_startup(self)

        # Configurar logging básico — nivel DEBUG para diagnóstico
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stderr,
        )

        # Silenciar logs muy verbosos de bibliotecas externas
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

        # Cargar estilos CSS personalizados
        self._load_css()

    def _load_css(self) -> None:
        """Carga estilos CSS personalizados para la aplicación."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .error {
                color: @error_color;
            }
            .success {
                color: @success_color;
            }
            .card {
                background-color: @card_bg_color;
                border-radius: 12px;
                padding: 16px;
            }
        """)

        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
