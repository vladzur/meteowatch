"""Página de pronóstico detallado por hora.

Muestra el desglose hora a hora del pronóstico para un día específico,
con temperatura, sensación térmica, viento, lluvia y más.
"""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from meteowatch.api.client import MeteoredClient, MeteoredError
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.models.hourly import HourData, HourlyForecast

logger = logging.getLogger(__name__)

# Zona horaria de Chile (UTC-4 estándar, UTC-3 verano)
CLT = ZoneInfo("America/Santiago")


class HourlyForecastPage(Adw.NavigationPage):
    """Página que muestra el pronóstico detallado por hora."""

    def __init__(self, config: AppConfig, location_hash: str, day_start: int):
        """Inicializa la página de detalle por hora.

        Args:
            config: Configuración de la aplicación.
            location_hash: Hash de la ubicación.
            day_start: Timestamp del inicio del día seleccionado.
        """
        super().__init__()

        logger.info("Creando página de pronóstico por hora: hash=%s, day_start=%s",
                    location_hash, day_start)

        # Formatear la fecha del día como título (hora chilena)
        dt = datetime.fromtimestamp(day_start / 1000, tz=CLT)
        date_str = dt.strftime("%A %d de %B")
        # Capitalizar primera letra
        date_str = date_str[0].upper() + date_str[1:]
        self.set_title(date_str)

        self._config = config
        self._location_hash = location_hash
        self._day_start = day_start
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz de la página de pronóstico por hora."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

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
        logger.info("Cargando pronóstico por hora para hash=%s...", self._location_hash)

        def do_load():
            try:
                client = MeteoredClient(self._config.get_api_key())
                forecast = client.get_hourly_forecast(self._location_hash)
                logger.info("Pronóstico por hora cargado: %d horas", len(forecast.hours))
                GLib.idle_add(self._on_forecast_loaded, forecast)
            except MeteoredError as e:
                logger.exception("Error de API al cargar pronóstico por hora")
                GLib.idle_add(self._on_forecast_error, str(e))
            except Exception:
                logger.exception("Error inesperado al cargar pronóstico por hora")
                GLib.idle_add(self._on_forecast_error, "Error inesperado. Revisa los logs para más detalles.")

        import threading
        thread = threading.Thread(target=do_load, daemon=True)
        thread.start()

    def _on_forecast_loaded(self, forecast: HourlyForecast) -> None:
        """Muestra el pronóstico por hora cargado."""
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

        # Lista de horas
        hours_list = Gtk.ListBox()
        hours_list.add_css_class("boxed-list")
        hours_list.set_selection_mode(Gtk.SelectionMode.NONE)

        for hour_data in forecast.hours:
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

        hour_str = datetime.fromtimestamp(hour_data.end / 1000, tz=CLT).strftime("%H:%M")
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
