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
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
            | Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self._config = AppConfig.load()
        self._window: "MeteowatchWindow | None" = None
        self._enable_tray: bool = True

        # Registrar flags de línea de comandos
        self.add_main_option(
            "background", ord("b"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Iniciar minimizado en la bandeja del sistema",
            None,
        )
        self.add_main_option(
            "no-tray", 0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Desactivar el icono de bandeja del sistema",
            None,
        )

    def do_activate(self) -> None:
        """Activa la aplicación y crea la ventana principal."""
        logger.info("Activando Meteowatch (tray=%s)...", self._enable_tray)
        logger.info("Configuración: latitude=%s, longitude=%s, location_name=%s, configured=%s",
                    self._config.latitude,
                    self._config.longitude,
                    self._config.location_name or "(vacío)",
                    self._config.is_configured())
        self._window = MeteowatchWindow(
            application=self,
            config=self._config,
            enable_tray=self._enable_tray,
        )
        self._window.present()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        """Procesa flags de línea de comandos.

        Soporta:
        - --background/-b: iniciar minimizado en la bandeja.
        - --no-tray: desactivar completamente el icono de bandeja.
        """
        options = command_line.get_options_dict()

        # Procesar --no-tray antes de activar
        if options.contains("no-tray"):
            self._enable_tray = False
            logger.info("Flag --no-tray detectado: bandeja desactivada")

        # Activar la aplicación normalmente (crea la ventana)
        self.activate()

        # Si se pasó --background y el tray está activo, ocultar al tray
        if options.contains("background") and self._enable_tray:
            logger.info("Flag --background detectado: ocultando al tray")
            if self._window is not None:
                self._window.hide()

        return 0

    def do_startup(self) -> None:
        """Inicializa recursos antes de activar la aplicación."""
        Adw.Application.do_startup(self)

        # Registrar acciones de la aplicación
        self._register_actions()

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

    def do_shutdown(self) -> None:
        """Limpia recursos al cerrar la aplicación."""
        logger.info("Cerrando Meteowatch...")
        if self._window is not None:
            self._window.cleanup_tray()
        Adw.Application.do_shutdown(self)

    def _register_actions(self) -> None:
        """Registra las acciones GAction de la aplicación.

        GTK4 no registra automáticamente la acción 'quit',
        por lo que debe hacerse manualmente.
        """
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit_action)
        self.add_action(quit_action)

    def _on_quit_action(self, action, param) -> None:
        """Acción 'quit': fuerza el cierre real de la aplicación.

        Establece force_quit en la ventana para saltar el guard
        de minimización al tray.
        """
        logger.info("Acción quit activada")
        if self._window is not None:
            self._window.force_quit = True
        self.quit()

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
