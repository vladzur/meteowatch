"""Widget de reporte meteorológico generado por IA.

Muestra un informe narrativo del tiempo generado por DeepSeek a partir
de los datos del ForecastService. El widget se mantiene colapsado por
defecto y el usuario decide cuándo expandirlo y generar el reporte.
"""

import logging
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from meteowatch.api.client import CurrentWeather
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast
from meteowatch.report.engine import ReportEngine

logger = logging.getLogger(__name__)

# Período de enfriamiento entre generaciones (segundos)
COOLDOWN_SECONDS = 60


class WeatherReportDialog(Gtk.Window):
    """Diálogo que muestra el reporte meteorológico generado por IA.

    Ofrece un área de texto con scroll para leer el informe completo
    y botones para copiar al portapapeles y cerrar.
    """

    def __init__(self, parent: Gtk.Window | None, report_text: str):
        """Inicializa el diálogo de reporte.

        Args:
            parent: Ventana padre (para centrar el diálogo).
            report_text: Texto del reporte a mostrar.
        """
        super().__init__()
        self.set_title("Reporte del tiempo")
        self.set_default_size(480, 500)
        self.set_modal(True)
        self.set_resizable(True)

        if parent is not None:
            self.set_transient_for(parent)

        self._report_text = report_text
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz del diálogo."""
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        self.set_child(main_box)

        # --- Área de texto con scroll ---
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.append(scrolled)

        report_label = Gtk.Label()
        report_label.set_wrap(True)
        report_label.set_xalign(0)
        report_label.set_yalign(0)
        report_label.set_margin_start(8)
        report_label.set_margin_end(8)
        report_label.set_margin_top(8)
        report_label.set_margin_bottom(8)
        report_label.set_selectable(True)
        report_label.set_label(self._report_text)
        scrolled.set_child(report_label)

        # --- Botones de acción ---
        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        btn_box.set_halign(Gtk.Align.END)
        main_box.append(btn_box)

        # Botón copiar
        copy_btn = Gtk.Button(label="Copiar")
        copy_btn.set_tooltip_text("Copiar el reporte al portapapeles")
        copy_btn.connect("clicked", self._on_copy_clicked)
        btn_box.append(copy_btn)

        # Botón cerrar
        close_btn = Gtk.Button(label="Cerrar")
        close_btn.set_tooltip_text("Cerrar el reporte")
        close_btn.connect("clicked", self._on_close_clicked)
        btn_box.append(close_btn)

    def _on_copy_clicked(self, btn: Gtk.Button) -> None:
        """Copia el texto del reporte al portapapeles."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self._report_text)
        logger.debug("Reporte copiado al portapapeles")

        # Feedback visual breve
        btn.set_label("¡Copiado!")
        GLib.timeout_add(1500, self._reset_copy_button, btn)

    def _reset_copy_button(self, btn: Gtk.Button) -> bool:
        """Restaura el texto del botón de copiar."""
        btn.set_label("Copiar")
        return False

    def _on_close_clicked(self, _btn: Gtk.Button) -> None:
        """Cierra el diálogo."""
        self.close()
        self.destroy()


class WeatherReportCard(Gtk.Box):
    """Widget colapsable que muestra el reporte meteorológico generado por IA.

    Se mantiene colapsado por defecto. Al expandirlo, el usuario puede
    presionar "Generar reporte" para obtener un informe narrativo del
    pronóstico actual.

    Attributes:
        _engine: Motor de generación de reportes (ReportEngine).
        _daily: Pronóstico diario actual (o None).
        _hourly: Pronóstico horario actual (o None).
        _current: Condiciones actuales (o None).
    """

    def __init__(self, engine: ReportEngine):
        """Inicializa el widget de reporte.

        Args:
            engine: Instancia de ReportEngine para generar los reportes.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._engine = engine
        self._daily: DailyForecast | None = None
        self._hourly: HourlyForecast | None = None
        self._current: CurrentWeather | None = None
        self._last_report: str | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construye la interfaz del widget de reporte."""
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_bottom(12)

        # --- Separador visual ---
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(8)
        separator.set_margin_bottom(8)
        self.append(separator)

        # --- Expander (expandido por defecto para visibilidad) ---
        self._expander = Gtk.Expander(label="📋 Reporte del tiempo")
        self._expander.set_expanded(True)
        self._expander.connect("notify::expanded", self._on_expander_toggled)
        self.append(self._expander)

        # Contenedor interno del expander
        inner_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        inner_box.set_margin_top(8)
        inner_box.set_margin_start(4)
        inner_box.set_margin_end(4)
        inner_box.set_margin_bottom(4)
        self._expander.set_child(inner_box)

        # --- Área de reporte con scroll ---
        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_max_content_height(250)
        self._scrolled.set_vexpand(False)
        self._scrolled.set_visible(False)
        inner_box.append(self._scrolled)

        # Label del reporte
        self._report_label = Gtk.Label()
        self._report_label.set_wrap(True)
        self._report_label.set_xalign(0)
        self._report_label.set_yalign(0)
        self._report_label.set_margin_start(8)
        self._report_label.set_margin_end(8)
        self._report_label.set_margin_top(4)
        self._report_label.set_margin_bottom(4)
        self._report_label.set_selectable(True)
        self._scrolled.set_child(self._report_label)

        # --- Spinner de carga ---
        self._spinner_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        self._spinner_box.set_halign(Gtk.Align.CENTER)
        self._spinner_box.set_margin_top(8)
        self._spinner_box.set_margin_bottom(8)
        self._spinner_box.set_visible(False)
        inner_box.append(self._spinner_box)

        self._spinner = Gtk.Spinner()
        self._spinner_box.append(self._spinner)

        spinner_label = Gtk.Label(label="Generando reporte...")
        spinner_label.add_css_class("dim-label")
        self._spinner_box.append(spinner_label)

        # --- Botón de generación ---
        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(4)
        inner_box.append(btn_box)

        self._generate_btn = Gtk.Button(label="Generar reporte")
        self._generate_btn.set_tooltip_text(
            "Genera un informe del tiempo usando inteligencia artificial"
        )
        self._generate_btn.connect("clicked", self._on_generate_clicked)
        btn_box.append(self._generate_btn)

        # --- Indicador de estado ---
        self._status_label = Gtk.Label()
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0.5)
        self._status_label.set_margin_start(8)
        self._status_label.set_margin_end(8)
        self._status_label.set_margin_top(4)
        self._status_label.add_css_class("dim-label")
        self._status_label.set_visible(False)
        inner_box.append(self._status_label)

        # --- Mensaje de placeholder ---
        self._placeholder_label = Gtk.Label()
        self._placeholder_label.set_wrap(True)
        self._placeholder_label.set_xalign(0)
        self._placeholder_label.set_margin_start(8)
        self._placeholder_label.set_margin_end(8)
        self._placeholder_label.set_margin_top(8)
        self._placeholder_label.add_css_class("dim-label")
        self._placeholder_label.set_label(
            "Presiona \"Generar reporte\" para obtener un informe "
            "detallado del pronóstico meteorológico generado con "
            "inteligencia artificial."
        )
        inner_box.append(self._placeholder_label)

    # ------------------------------------------------------------------
    # Actualización de datos
    # ------------------------------------------------------------------

    def set_forecast_data(
        self,
        daily: DailyForecast,
        hourly: HourlyForecast,
        current: CurrentWeather,
    ) -> None:
        """Actualiza los datos de forecast usados para generar el reporte.

        Args:
            daily: Pronóstico diario.
            hourly: Pronóstico por hora.
            current: Condiciones actuales.
        """
        self._daily = daily
        self._hourly = hourly
        self._current = current

    # ------------------------------------------------------------------
    # Manejo de eventos
    # ------------------------------------------------------------------

    def _on_expander_toggled(self, expander, _pspec) -> None:
        """Maneja la expansión/colapso del widget."""
        # Si se colapsa, no hacemos nada especial
        pass

    def _on_generate_clicked(self, btn: Gtk.Button) -> None:
        """Inicia la generación del reporte en un hilo separado.

        Args:
            btn: Botón que disparó la acción.
        """
        # Verificar período de enfriamiento
        elapsed = time.time() - self._engine.last_generation_at
        if self._engine.last_generation_at > 0 and elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            logger.debug(
                "Generación bloqueada por enfriamiento: %d seg restantes",
                remaining,
            )
            self._status_label.set_label(
                f"Espera {remaining} segundos antes de generar otro reporte."
            )
            self._status_label.set_visible(True)
            return

        if self._daily is None or self._hourly is None or self._current is None:
            logger.warning("No hay datos de forecast para generar reporte")
            self._status_label.set_label(
                "No hay datos de pronóstico disponibles."
            )
            self._status_label.set_visible(True)
            self._placeholder_label.set_visible(False)
            return

        # Mostrar estado de carga
        self._set_loading_state(True)

        # Iniciar generación en hilo separado
        thread = GLib.Thread.new(
            "report-generation",
            self._do_generate,
        )

    def _set_loading_state(self, loading: bool) -> None:
        """Configura el estado de carga del widget.

        Args:
            loading: True para mostrar spinner y deshabilitar botón.
        """
        if loading:
            self._generate_btn.set_sensitive(False)
            self._spinner_box.set_visible(True)
            self._spinner.start()
            self._status_label.set_visible(False)
            self._placeholder_label.set_visible(False)
        else:
            self._spinner.stop()
            self._spinner_box.set_visible(False)

    def _do_generate(self) -> None:
        """Ejecuta la generación del reporte en el hilo secundario."""
        try:
            daily = self._daily
            hourly = self._hourly
            current = self._current

            if daily is None or hourly is None or current is None:
                return

            report = self._engine.generate(daily, hourly, current)
            self._last_report = report

            # Actualizar UI en el hilo principal
            GLib.idle_add(self._on_report_ready, report)
        except Exception as e:
            logger.error("Error inesperado al generar reporte: %s", e)
            GLib.idle_add(
                self._on_report_ready,
                "Ocurrió un error al generar el reporte. "
                "Inténtalo de nuevo más tarde.",
            )

    def _on_report_ready(self, report: str) -> bool:
        """Abre el diálogo con el reporte generado.

        Args:
            report: Texto del reporte generado.

        Returns:
            False para que GLib no reintente el callback.
        """
        self._set_loading_state(False)

        # Mostrar indicador de reporte disponible
        self._status_label.set_label(
            "✅ Reporte generado — presiona de nuevo para regenerar"
        )
        self._status_label.set_visible(True)
        self._placeholder_label.set_visible(False)

        # Abrir diálogo con el reporte
        parent = self.get_root()
        if isinstance(parent, Gtk.Window):
            dialog = WeatherReportDialog(parent, report)
        else:
            dialog = WeatherReportDialog(None, report)
        dialog.present()

        # Programar re-habilitación del botón tras cooldown
        GLib.timeout_add_seconds(
            COOLDOWN_SECONDS,
            self._enable_generate_button,
        )

        return False  # No reintentar

    def _enable_generate_button(self) -> bool:
        """Re-habilita el botón de generación tras el período de enfriamiento.

        Returns:
            False para que GLib no reintente el callback.
        """
        self._generate_btn.set_sensitive(True)
        return False  # No reintentar
