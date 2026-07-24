"""Página de pronóstico detallado por hora.

Muestra el desglose hora a hora del pronóstico para varios días,
con separadores visuales entre días y datos detallados por hora.
"""

import logging
from collections import OrderedDict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from meteowatch.api.client import OpenMeteoClient, OpenMeteoError
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.models.hourly import HourData, HourlyForecast

logger = logging.getLogger(__name__)

# Días de la semana en español
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _degrees_to_cardinal(degrees: int) -> str:
    """Convierte una dirección en grados (0-360) a punto cardinal."""
    if degrees < 0:
        return "?"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]


class HourlyForecastPage(Adw.NavigationPage):
    """Página que muestra el pronóstico detallado por hora."""

    def __init__(self, config: AppConfig, location_hash: str, day_start: int,
                 on_change_location=None):
        """Inicializa la página de detalle por hora.

        Args:
            config: Configuración de la aplicación.
            location_hash: No usado (mantenido por compatibilidad).
            day_start: Timestamp del inicio del día seleccionado.
            on_change_location: Callback opcional para cambiar de ubicación.
        """
        super().__init__()

        logger.info("Creando página de pronóstico por hora: day_start=%s", day_start)

        # Obtener la zona horaria desde la configuración
        try:
            tz = ZoneInfo(config.timezone) if config.timezone != "auto" else ZoneInfo("UTC")
        except Exception:
            tz = ZoneInfo("UTC")

        # Formatear la fecha del día como título
        dt = datetime.fromtimestamp(day_start / 1000, tz=tz)
        date_str = dt.strftime("%A %d de %B")
        # Capitalizar primera letra
        date_str = date_str[0].upper() + date_str[1:]
        self.set_title(date_str)

        self._config = config
        self._timezone = tz
        self._day_start = day_start
        self._on_change_location = on_change_location
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz de la página de pronóstico por hora."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar — el botón de retroceso lo provee automáticamente Adw.NavigationView
        header = Adw.HeaderBar()
        header.set_show_title(True)

        # Botón de cambio de ubicación (si el callback está disponible)
        if self._on_change_location is not None:
            change_btn = Gtk.Button()
            change_btn.set_icon_name("find-location-symbolic")
            change_btn.set_tooltip_text("Cambiar ubicación")
            change_btn.connect("clicked", lambda b: self._on_change_location())
            header.pack_end(change_btn)

        toolbar_view.add_top_bar(header)

        # Contenido con scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)

        # Caja principal
        self._main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        self._main_box.set_margin_start(16)
        self._main_box.set_margin_end(16)
        self._main_box.set_margin_top(16)
        self._main_box.set_margin_bottom(16)
        scrolled.set_child(self._main_box)

        # Spinner de carga
        self._spinner = Gtk.Spinner()
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_margin_top(40)
        self._spinner.set_visible(True)
        self._spinner.start()
        self._main_box.append(self._spinner)

        # Etiqueta de error
        self._error_label = Gtk.Label()
        self._error_label.set_halign(Gtk.Align.CENTER)
        self._error_label.set_wrap(True)
        self._error_label.set_margin_top(20)
        self._error_label.set_visible(False)
        self._main_box.append(self._error_label)

        # Cargar datos
        self._load_hourly_forecast()

    def _load_hourly_forecast(self) -> None:
        """Carga el pronóstico por hora desde la API en segundo plano."""
        logger.info("Cargando pronóstico por hora para lat=%.4f, lon=%.4f...",
                    self._config.latitude, self._config.longitude)

        def do_load():
            try:
                client = OpenMeteoClient()
                forecast = client.get_hourly_forecast(
                    self._config.latitude,
                    self._config.longitude,
                    self._config.timezone,
                )
                logger.info("Pronóstico por hora cargado: %d horas", len(forecast.hours))
                GLib.idle_add(self._on_forecast_loaded, forecast)
            except OpenMeteoError as e:
                logger.exception("Error de API al cargar pronóstico por hora")
                GLib.idle_add(self._on_forecast_error, str(e))
            except Exception:
                logger.exception("Error inesperado al cargar pronóstico por hora")
                GLib.idle_add(self._on_forecast_error, "Error inesperado. Revisa los logs para más detalles.")

        import threading
        thread = threading.Thread(target=do_load, daemon=True)
        thread.start()

    def _on_forecast_loaded(self, forecast: HourlyForecast) -> None:
        """Muestra el pronóstico por hora cargado con separadores entre días."""
        logger.debug("Mostrando %d horas en UI", len(forecast.hours))
        self._spinner.stop()
        self._spinner.set_visible(False)

        if not forecast.hours:
            logger.warning("No hay datos de horas en el pronóstico")
            no_data = Gtk.Label()
            no_data.set_text("No hay datos de pronóstico por hora disponibles.")
            no_data.set_halign(Gtk.Align.CENTER)
            no_data.set_margin_top(40)
            self._main_box.append(no_data)
            return

        # Agrupar horas por día
        hours_by_day = self._group_hours_by_day(forecast.hours)

        # Lista de horas con separadores entre días
        hours_list = Gtk.ListBox()
        hours_list.add_css_class("boxed-list")
        hours_list.set_selection_mode(Gtk.SelectionMode.NONE)

        for day_start_ms, day_hours in hours_by_day.items():
            # Separador visual del día
            separator_row = self._build_day_separator_row(day_start_ms)
            hours_list.append(separator_row)

            # Horas de ese día
            for hour_data in day_hours:
                row = self._build_hour_row(hour_data)
                hours_list.append(row)

        self._main_box.append(hours_list)

    def _on_forecast_error(self, message: str) -> None:
        """Muestra un error al cargar el pronóstico."""
        logger.error("Error al cargar pronóstico por hora: %s", message)
        self._spinner.stop()
        self._spinner.set_visible(False)

        self._error_label.set_markup(
            f"<b>Error al cargar el pronóstico por hora</b>\n\n{message}"
        )
        self._error_label.set_visible(True)

    # ------------------------------------------------------------------
    # Agrupación por día y separadores visuales
    # ------------------------------------------------------------------

    @staticmethod
    def _group_hours_by_day(hours: list[HourData]) -> OrderedDict:
        """Agrupa las horas por día basándose en el timestamp 'end'.

        Args:
            hours: Lista de datos horarios del pronóstico.

        Returns:
            OrderedDict con clave = timestamp inicio del día (medianoche) en ms,
            valor = lista de HourData de ese día, en orden cronológico.
        """
        grouped: OrderedDict = OrderedDict()
        for h in hours:
            dt = datetime.fromtimestamp(h.end / 1000, tz=timezone.utc)
            # Truncar a medianoche del día en UTC
            day_start = int(datetime(
                dt.year, dt.month, dt.day, 0, 0, 0,
                tzinfo=timezone.utc,
            ).timestamp() * 1000)
            if day_start not in grouped:
                grouped[day_start] = []
            grouped[day_start].append(h)
        return grouped

    def _build_day_separator_row(self, day_start_ms: int) -> Gtk.ListBoxRow:
        """Construye una fila separadora que indica el inicio de un nuevo día.

        Args:
            day_start_ms: Timestamp de medianoche del día en ms.

        Returns:
            Gtk.ListBoxRow con el nombre del día y la fecha.
        """
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.add_css_class("day-separator")

        dt = datetime.fromtimestamp(day_start_ms / 1000, tz=self._timezone)
        now = datetime.now(tz=self._timezone)
        today_start = int(datetime(
            now.year, now.month, now.day, 0, 0, 0,
            tzinfo=self._timezone,
        ).timestamp() * 1000)

        # Determinar etiqueta del día
        delta_days = (day_start_ms - today_start) // 86400000
        if delta_days == 0:
            day_name = "Hoy"
        elif delta_days == 1:
            day_name = "Mañana"
        else:
            day_name = WEEKDAYS[dt.weekday()]

        date_str = dt.strftime("%d de %B").lower()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(6)

        label = Gtk.Label()
        label.set_markup(f"<b>{day_name}</b>  <small>{date_str}</small>")
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        label.set_hexpand(True)
        box.append(label)

        row.set_child(box)
        return row

    def _build_hour_row(self, hour_data: HourData) -> Gtk.ListBoxRow:
        """Construye una fila con los datos de una hora específica.

        Args:
            hour_data: Datos del pronóstico para una hora.

        Returns:
            Gtk.ListBoxRow con el contenido formateado.
        """
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        # Contenedor horizontal principal
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(12)
        hbox.set_margin_end(12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)

        # --- Columna izquierda: hora + icono + alerta ráfagas ---
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        left_col.set_valign(Gtk.Align.CENTER)

        # Indicador de alerta de viento
        gust_alert = hour_data.wind_gust >= 50

        hour_str = datetime.fromtimestamp(hour_data.end / 1000, tz=self._timezone).strftime("%H:%M")
        hour_label = Gtk.Label()
        if gust_alert:
            hour_label.set_markup(f"<b>⚠️ {hour_str}</b>")
        else:
            hour_label.set_markup(f"<b>{hour_str}</b>")
        hour_label.set_halign(Gtk.Align.CENTER)
        left_col.append(hour_label)

        symbol = get_weather_symbol(hour_data.symbol)
        icon_label = Gtk.Label()
        icon_label.set_markup(f"<span size='large'>{symbol.emoji}</span>")
        icon_label.set_halign(Gtk.Align.CENTER)
        left_col.append(icon_label)

        hbox.append(left_col)

        # --- Columna central: temperatura + sensación ---
        center_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        center_col.set_valign(Gtk.Align.CENTER)
        center_col.set_hexpand(True)

        temp_label = Gtk.Label()
        temp_label.set_markup(
            f"<big><b>{hour_data.temperature:.0f}°C</b></big>"
        )
        temp_label.set_halign(Gtk.Align.START)
        temp_label.set_xalign(0)
        center_col.append(temp_label)

        feels_label = Gtk.Label()
        feels_label.set_markup(
            f"<small>Sensación {hour_data.temperature_feels_like:.0f}°C</small>"
        )
        feels_label.set_halign(Gtk.Align.START)
        feels_label.set_xalign(0)
        center_col.append(feels_label)

        desc_label = Gtk.Label()
        desc_label.set_text(symbol.description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_xalign(0)
        center_col.append(desc_label)

        hbox.append(center_col)

        # --- Columna derecha: datos adicionales ---
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        right_col.set_valign(Gtk.Align.CENTER)

        # Viento: velocidad base + ráfagas con alerta si > 50 km/h
        gust_alert = hour_data.wind_gust >= 50
        if gust_alert:
            wind_text = f"💨 {hour_data.wind_speed} km/h"
            gust_text = f"⚠️ Ráfagas {hour_data.wind_gust} km/h"
        else:
            wind_text = f"💨 {hour_data.wind_speed} km/h"
            gust_text = f"↗️ {hour_data.wind_gust} km/h"

        details = [
            (f"💧 {hour_data.humidity}%", False),
            (f"🌧️ {hour_data.rain_probability}%", False),
            (wind_text, False),
            (gust_text, gust_alert),
            (f"☁️ {hour_data.clouds}%", False),
        ]
        for text, is_alert in details:
            lbl = Gtk.Label()
            if is_alert:
                lbl.set_markup(f"<small><b>{text}</b></small>")
            else:
                lbl.set_markup(f"<small>{text}</small>")
            lbl.set_halign(Gtk.Align.END)
            lbl.set_xalign(1)
            right_col.append(lbl)

        hbox.append(right_col)

        row.set_child(hbox)
        return row
