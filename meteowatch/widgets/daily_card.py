"""Página de pronóstico diario.

Muestra una lista con el pronóstico de los próximos 5 días
en tarjetas con iconos, temperaturas y datos relevantes.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from meteowatch.api.client import MeteoredClient, MeteoredError
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.models.daily import DailyForecast
from meteowatch.models.hourly import HourlyForecast

logger = logging.getLogger(__name__)

# Días de la semana en español
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Zona horaria de Chile (UTC-4 estándar, UTC-3 verano)
CLT = ZoneInfo("America/Santiago")


class DailyForecastPage(Adw.NavigationPage):
    """Página que muestra el pronóstico diario para la ubicación seleccionada."""

    def __init__(self, config: AppConfig, on_day_selected, on_change_location):
        """Inicializa la página de pronóstico diario.

        Args:
            config: Configuración de la aplicación.
            on_day_selected: Callback(location_hash, day_start_timestamp) al hacer clic en un día.
            on_change_location: Callback() para volver a la pantalla de búsqueda.
        """
        super().__init__()
        self.set_title(config.location_name or "Meteowatch")
        self._config = config
        self._on_day_selected = on_day_selected
        self._on_change_location = on_change_location
        self._forecast: Optional[DailyForecast] = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz de la página de pronóstico diario."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar con botón de cambiar ubicación
        header = Adw.HeaderBar()
        header.set_show_title(True)

        change_btn = Gtk.Button()
        change_btn.set_icon_name("find-location-symbolic")
        change_btn.set_tooltip_text("Cambiar ubicación")
        change_btn.connect("clicked", lambda b: self._on_change_location())
        header.pack_end(change_btn)

        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Actualizar pronóstico")
        refresh_btn.connect("clicked", lambda b: self.load_forecast())
        header.pack_end(refresh_btn)

        toolbar_view.add_top_bar(header)

        # Contenido con scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)

        # Caja principal
        self._main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
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

    def load_forecast(self) -> None:
        """Carga el pronóstico diario y la temperatura actual desde la API."""
        logger.info("Cargando pronóstico diario para hash=%s...", self._config.location_hash)
        self._spinner.set_visible(True)
        self._spinner.start()
        self._error_label.set_visible(False)

        # Limpiar widgets de forecast anteriores (todo excepto spinner y error_label)
        children_to_remove = []
        for child in self._main_box:
            if child is not self._spinner and child is not self._error_label:
                children_to_remove.append(child)

        for child in children_to_remove:
            self._main_box.remove(child)

        def do_load():
            try:
                client = MeteoredClient(self._config.get_api_key())
                forecast = client.get_daily_forecast(self._config.location_hash)
                logger.info("Pronóstico diario cargado: name=%s, %d días",
                           forecast.name, len(forecast.days))

                # Obtener temperatura actual desde el endpoint horario
                current_temp = None
                current_symbol = None
                try:
                    hourly = client.get_hourly_forecast(self._config.location_hash)
                    if hourly.hours:
                        # Buscar la hora más cercana al momento actual
                        now_ms = int(time.time() * 1000)
                        closest = min(
                            hourly.hours,
                            key=lambda h: abs(h.end - now_ms),
                        )
                        current_temp = closest.temperature
                        current_symbol = closest.symbol
                        closest_dt = datetime.fromtimestamp(
                            closest.end / 1000, tz=CLT
                        ).strftime("%H:%M")
                        logger.info(
                            "Temperatura actual: %.1f°C (symbol=%s, hora=%s CLT)",
                            current_temp, current_symbol, closest_dt,
                        )
                except Exception:
                    logger.exception("No se pudo obtener la temperatura actual")

                GLib.idle_add(self._on_forecast_loaded, forecast, current_temp, current_symbol)
            except MeteoredError as e:
                logger.exception("Error de API al cargar pronóstico diario")
                GLib.idle_add(self._on_forecast_error, str(e))
            except Exception:
                logger.exception("Error inesperado al cargar pronóstico diario")
                GLib.idle_add(self._on_forecast_error, "Error inesperado. Revisa los logs para más detalles.")

        import threading
        thread = threading.Thread(target=do_load, daemon=True)
        thread.start()

    def _on_forecast_loaded(self, forecast: DailyForecast,
                            current_temp=None, current_symbol=None) -> None:
        """Muestra el pronóstico diario cargado."""
        logger.debug("Mostrando pronóstico diario en UI: %s", forecast.name)
        self._spinner.stop()
        self._spinner.set_visible(False)
        self._forecast = forecast
        self.set_title(forecast.name)

        self._build_forecast_card(forecast, current_temp, current_symbol)

    def _on_forecast_error(self, message: str) -> None:
        """Muestra un error al cargar el pronóstico."""
        logger.error("Error al cargar pronóstico diario: %s", message)
        self._spinner.stop()
        self._spinner.set_visible(False)

        self._error_label.set_markup(f"<b>Error al cargar el pronóstico</b>\n\n{message}")
        self._error_label.set_visible(True)

    def _on_24h_clicked(self, button: Gtk.Button) -> None:
        """Navega al pronóstico detallado de las próximas 24 horas."""
        if self._forecast and self._forecast.days:
            today = self._forecast.days[0]
            logger.info("Navegando a pronóstico 24h: hash=%s", self._forecast.hash)
            self._on_day_selected(self._forecast.hash, today.start)

    def _build_forecast_card(self, forecast: DailyForecast,
                             current_temp=None, current_symbol=None) -> None:
        """Construye las tarjetas de pronóstico para cada día."""
        if not forecast.days:
            no_data = Gtk.Label()
            no_data.set_text("No hay datos de pronóstico disponibles.")
            no_data.set_halign(Gtk.Align.CENTER)
            no_data.set_margin_top(20)
            self._main_box.append(no_data)
            return

        # --- Encabezado: ubicación + temperatura actual ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header_box.set_margin_bottom(14)

        location_label = Gtk.Label()
        location_label.set_markup(f"<big><b>{forecast.name}</b></big>")
        location_label.set_halign(Gtk.Align.CENTER)
        header_box.append(location_label)

        if current_temp is not None:
            current_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            current_box.set_halign(Gtk.Align.CENTER)

            if current_symbol is not None:
                cur_symbol = get_weather_symbol(current_symbol)
                cur_icon = Gtk.Label()
                cur_icon.set_markup(f"<span size='large'>{cur_symbol.emoji}</span>")
                current_box.append(cur_icon)

            cur_temp_label = Gtk.Label()
            cur_temp_label.set_markup(
                f"<span size='xx-large'><b>{current_temp:.0f}°</b></span>"
            )
            current_box.append(cur_temp_label)

            cur_desc = Gtk.Label()
            cur_desc.set_markup("<small>Ahora</small>")
            cur_desc.set_valign(Gtk.Align.END)
            current_box.append(cur_desc)

            header_box.append(current_box)

        self._main_box.append(header_box)

        # --- Botón de pronóstico 24 horas (destacado) ---
        btn_24h = Gtk.Button()
        btn_24h.set_margin_bottom(8)
        btn_24h.add_css_class("suggested-action")

        btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_content.set_margin_top(6)
        btn_content.set_margin_bottom(6)
        btn_icon = Gtk.Label()
        btn_icon.set_markup("<span size='large'>🕐</span>")
        btn_content.append(btn_icon)
        btn_label = Gtk.Label()
        btn_label.set_markup("<b>Ver pronóstico de las próximas 24 horas</b>")
        btn_label.set_halign(Gtk.Align.START)
        btn_label.set_xalign(0)
        btn_label.set_hexpand(True)
        btn_content.append(btn_label)
        btn_arrow = Gtk.Image()
        btn_arrow.set_from_icon_name("go-next-symbolic")
        btn_content.append(btn_arrow)
        btn_24h.set_child(btn_content)
        btn_24h.connect("clicked", self._on_24h_clicked)
        self._main_box.append(btn_24h)

        # --- Tarjetas de cada día ---
        for i, day in enumerate(forecast.days):
            card = self._build_day_card(day, i)
            self._main_box.append(card)

    def _build_day_card(self, day, index: int) -> Gtk.Box:
        """Construye una tarjeta expandida con todos los detalles de un día.

        Args:
            day: Datos del día (DayData).
            index: Índice del día (0 = hoy).

        Returns:
            Gtk.Box con estilo de tarjeta y toda la información del día.
        """
        gust_alert = day.wind_gust >= 50

        # Formatear nombre del día y fecha (hora chilena)
        dt = datetime.fromtimestamp(day.start / 1000, tz=CLT)
        if index == 0:
            day_name = "Hoy"
        elif index == 1:
            day_name = "Mañana"
        else:
            day_name = WEEKDAYS[dt.weekday()]
        date_str = dt.strftime("%d de %B")

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_bottom(10)

        # --- Fila superior: icono grande + día/fecha/descripción + temps ---
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        symbol = get_weather_symbol(day.symbol)
        icon_label = Gtk.Label()
        icon_label.set_markup(f"<span size='xx-large'>{symbol.emoji}</span>")
        icon_label.set_valign(Gtk.Align.CENTER)
        top_row.append(icon_label)

        info_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_col.set_valign(Gtk.Align.CENTER)
        info_col.set_hexpand(True)

        alert_prefix = "⚠️ " if gust_alert else ""
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{alert_prefix}{day_name}</b>")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_xalign(0)
        info_col.append(name_label)

        date_label = Gtk.Label()
        date_label.set_markup(f"<small>{date_str}</small>")
        date_label.set_halign(Gtk.Align.START)
        date_label.set_xalign(0)
        info_col.append(date_label)

        desc_label = Gtk.Label()
        desc_label.set_text(symbol.description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_xalign(0)
        info_col.append(desc_label)

        top_row.append(info_col)

        temp_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        temp_col.set_valign(Gtk.Align.CENTER)
        temp_max_lbl = Gtk.Label()
        temp_max_lbl.set_markup(f"<big><b>{day.temperature_max:.0f}°</b></big>")
        temp_max_lbl.set_halign(Gtk.Align.END)
        temp_max_lbl.set_xalign(1)
        temp_col.append(temp_max_lbl)
        temp_min_lbl = Gtk.Label()
        temp_min_lbl.set_markup(f"<small>{day.temperature_min:.0f}°</small>")
        temp_min_lbl.set_halign(Gtk.Align.END)
        temp_min_lbl.set_xalign(1)
        temp_col.append(temp_min_lbl)
        top_row.append(temp_col)

        card.append(top_row)

        # --- Separador ---
        card.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # --- Grid de detalles (2 columnas) ---
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(6)
        grid.set_margin_start(4)
        grid.set_margin_end(4)

        sun_in = datetime.fromtimestamp(day.sun_in / 1000, tz=CLT).strftime("%H:%M")
        sun_out = datetime.fromtimestamp(day.sun_out / 1000, tz=CLT).strftime("%H:%M")

        self._add_grid_cell(grid, "💧 Humedad", f"{day.humidity}%", 0, 0)
        self._add_grid_cell(grid, "🌧️ Prob. lluvia", f"{day.rain_probability}%", 0, 1)
        self._add_grid_cell(grid, "💨 Viento", f"{day.wind_speed} km/h {day.wind_direction}", 1, 0)
        gust_text = f"{day.wind_gust} km/h"
        self._add_grid_cell(grid, "↗️ Ráfagas", gust_text, 1, 1, alert=gust_alert)
        self._add_grid_cell(grid, "🌅 Amanecer", sun_in, 2, 0)
        self._add_grid_cell(grid, "🌇 Atardecer", sun_out, 2, 1)
        self._add_grid_cell(grid, "📊 Presión", f"{day.pressure} hPa", 3, 0)
        self._add_grid_cell(grid, "🏔️ Cota nieve", f"{day.snowline} m", 3, 1)
        self._add_grid_cell(grid, "☀️ Índice UV", f"{day.uv_index_max:.1f}", 4, 0)
        self._add_grid_cell(grid, "🌙 Luna", f"{day.moon_illumination:.0f}%", 4, 1)

        card.append(grid)
        return card

    @staticmethod
    def _add_grid_cell(grid: Gtk.Grid, label_text: str, value_text: str,
                       row: int, col: int, alert: bool = False) -> None:
        """Agrega una celda de etiqueta + valor al grid de detalles."""
        cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cell.set_margin_top(2)
        cell.set_margin_bottom(2)

        label = Gtk.Label()
        label.set_markup(f"<small>{label_text}</small>")
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        cell.append(label)

        value = Gtk.Label()
        if alert:
            value.set_markup(f"<small><b>{value_text}</b></small>")
        else:
            value.set_markup(f"<small>{value_text}</small>")
        value.set_halign(Gtk.Align.END)
        value.set_xalign(1)
        value.set_hexpand(True)
        cell.append(value)

        grid.attach(cell, col, row, 1, 1)
