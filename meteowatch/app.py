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

from meteowatch.alerts import Alert, send_alerts
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
        self._test_alert: str | None = None  # Nivel de alerta de prueba

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
        self.add_main_option(
            "test-alert", 0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Enviar una notificación de prueba (yellow, orange o all)",
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

        # Procesar --test-alert: guardar nivel para enviar tras activar
        if options.contains("test-alert"):
            self._test_alert = options.lookup_value("test-alert",
                                                      GLib.VariantType("s"))
            if self._test_alert is not None:
                self._test_alert = self._test_alert.unpack()
            logger.info("Flag --test-alert detectado: nivel=%s", self._test_alert)

        # Activar la aplicación normalmente (crea la ventana)
        self.activate()

        # Si se pidió --test-alert, enviar notificaciones de prueba
        if self._test_alert is not None:
            GLib.idle_add(self._send_test_alerts, self._test_alert)

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

    # ------------------------------------------------------------------
    # Alerta de prueba
    # ------------------------------------------------------------------

    def _send_test_alerts(self, level: str) -> None:
        """Envía notificaciones de prueba para verificar el sistema.

        Args:
            level: 'yellow', 'orange' o 'all'.
        """
        alerts: list[Alert] = []

        if level in ("yellow", "all"):
            alerts.append(Alert(
                level="yellow",
                category="test",
                message=(
                    "⚠️ Esta es una alerta amarilla de prueba. "
                    "El sistema de notificaciones de Meteowatch funciona correctamente."
                ),
                source_code=None,
                value=None,
            ))

        if level in ("orange", "all"):
            alerts.append(Alert(
                level="orange",
                category="test",
                message=(
                    "🔴 Esta es una alerta naranja de prueba. "
                    "El sistema de notificaciones de Meteowatch funciona correctamente."
                ),
                source_code=None,
                value=None,
            ))

        if not alerts:
            alerts.append(Alert(
                level="yellow",
                category="test",
                message="Notificación de prueba de Meteowatch.",
                source_code=None,
                value=None,
            ))

        logger.info("Enviando %d notificaciones de prueba (nivel=%s)...", len(alerts), level)
        send_alerts(alerts)
        logger.info("Notificaciones de prueba enviadas.")

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

        # Acción "Acerca de"
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_action)
        self.add_action(about_action)

        # Acción "Ayuda"
        help_action = Gio.SimpleAction.new("help", None)
        help_action.connect("activate", self._on_help_action)
        self.add_action(help_action)

    def _on_quit_action(self, action, param) -> None:
        """Acción 'quit': fuerza el cierre real de la aplicación.

        Establece force_quit en la ventana para saltar el guard
        de minimización al tray.
        """
        logger.info("Acción quit activada")
        if self._window is not None:
            self._window.force_quit = True
        self.quit()

    def _on_about_action(self, action, param) -> None:
        """Acción 'about': muestra el diálogo Acerca de con atribución a Open-Meteo."""
        logger.info("Mostrando diálogo Acerca de")

        # Evitamos new_from_appdata porque la ruta /app/share/metainfo/
        # solo existe dentro del sandbox de Flatpak y causa un crash fatal
        # si no se encuentra el archivo.
        dialog = Adw.AboutDialog()
        dialog.set_application_name("Meteowatch")
        dialog.set_application_icon("com.meteowatch.app")
        dialog.set_version("1.2.1")
        dialog.set_developer_name("vladzur")
        dialog.set_website("https://github.com/vladzur/meteowatch")
        dialog.set_copyright("© 2026 vladzur")
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_comments(
            "Datos meteorológicos proporcionados por Open-Meteo (open-meteo.com)"
        )
        dialog.set_developers(["vladzur"])
        dialog.set_designers(["vladzur"])

        dialog.present(self._window)

    def _on_help_action(self, action, param) -> None:
        """Acción 'help': muestra el diálogo de ayuda con instrucciones de uso."""
        logger.info("Mostrando diálogo de ayuda")

        dialog = Adw.Dialog()
        dialog.set_title("Ayuda de Meteowatch")
        dialog.set_content_width(420)
        dialog.set_content_height(440)

        # Toolbar con botón de cierre
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_title(False)
        toolbar.add_top_bar(header)

        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.set_tooltip_text("Cerrar")
        close_btn.connect("clicked", lambda b: dialog.close())
        header.pack_end(close_btn)

        # Contenido con scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar.set_content(scrolled)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        scrolled.set_child(content)

        # Secciones de ayuda
        sections = [
            (
                "Configuración inicial",
                "Al abrir Meteowatch por primera vez, se te pedirá que busques "
                "y selecciones una ciudad. Escribe el nombre de tu ciudad en el "
                "campo de búsqueda y selecciona la ubicación correcta de la lista. "
                "Puedes cambiar la ubicación en cualquier momento con el botón 📍 "
                "en la barra superior.",
            ),
            (
                "Pronóstico diario",
                "La pantalla principal muestra el pronóstico de los próximos 7 días "
                "con temperaturas máximas y mínimas, probabilidad de lluvia, "
                "velocidad del viento y más. Haz clic en el botón "
                "\"Próximas 24 horas\" o en cualquier día para ver el desglose "
                "hora por hora.",
            ),
            (
                "Pronóstico por hora",
                "Muestra el pronóstico detallado hora a hora a partir de la hora "
                "actual. Si hay horas ya transcurridas, aparecerá un botón "
                "\"Mostrar horas anteriores\" para consultarlas. "
                "Las ráfagas de viento ≥ 50 km/h se destacan con ⚠️.",
            ),
            (
                "Bandeja del sistema",
                "Al cerrar la ventana (✕), Meteowatch se minimiza a la bandeja "
                "del sistema y sigue ejecutándose en segundo plano. "
                "Haz clic en el icono de la bandeja para restaurar la ventana. "
                "El icono muestra la temperatura actual.",
            ),
            (
                "Cómo salir de la aplicación",
                "Hay tres formas de cerrar Meteowatch definitivamente:\n"
                "  • Menú ☰ → Salir\n"
                "  • Atajo de teclado Ctrl+Q\n"
                "  • Clic central (rueda del ratón) sobre el icono de la bandeja",
            ),
        ]

        for title, text in sections:
            section_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=6,
            )

            title_label = Gtk.Label()
            title_label.set_markup(f"<b>{title}</b>")
            title_label.set_halign(Gtk.Align.START)
            title_label.set_wrap(True)
            title_label.set_xalign(0)
            section_box.append(title_label)

            text_label = Gtk.Label()
            text_label.set_text(text)
            text_label.set_halign(Gtk.Align.START)
            text_label.set_wrap(True)
            text_label.set_xalign(0)
            section_box.append(text_label)

            content.append(section_box)

        dialog.set_child(toolbar)
        dialog.present(self._window)

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
            .day-separator {
                background-color: alpha(@accent_bg_color, 0.12);
                border-bottom: 1px solid alpha(@borders, 0.3);
            }
        """)

        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
