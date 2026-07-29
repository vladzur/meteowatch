"""Página de pronóstico detallado por hora.

Muestra el desglose hora a hora del pronóstico para varios días,
con separadores visuales entre días y datos detallados por hora.

Se suscribe al ForecastService para recibir actualizaciones
automáticas del pronóstico.
"""

import logging
from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from meteowatch.api.client import ForecastResult, OpenMeteoError
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.models.hourly import HourData, HourlyForecast
from meteowatch.services.forecast import BaseForecastObserver, ForecastService

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


class HourlyForecastPage(Adw.NavigationPage, BaseForecastObserver):
    """Página que muestra el pronóstico detallado por hora.

    Se suscribe al ForecastService y reconstruye la grilla automáticamente
    cuando llegan datos actualizados, solo si hay cambios.
    """

    def __init__(self, config: AppConfig, forecast_service: ForecastService,
                 location_hash: str, on_change_location=None):
        """Inicializa la página de detalle por hora.

        Args:
            config: Configuración de la aplicación.
            forecast_service: Servicio centralizado de datos meteorológicos.
            location_hash: No usado (mantenido por compatibilidad).
            on_change_location: Callback opcional para cambiar de ubicación.
        """
        super().__init__()
        self.set_title("Pronóstico por hora")

        # Obtener la zona horaria desde la configuración
        try:
            tz = ZoneInfo(config.timezone) if config.timezone != "auto" else ZoneInfo("UTC")
        except Exception:
            tz = ZoneInfo("UTC")

        self._config = config
        self._forecast_service = forecast_service
        self._timezone = tz
        self._on_change_location = on_change_location

        # Datos del forecast
        self._forecast: Optional[HourlyForecast] = None

        # Estado interno para el filtro de horas pasadas
        self._all_hours: list[HourData] = []
        self._future_hours: list[HourData] = []
        self._hours_list: Gtk.ListBox | None = None
        self._toggle_btn: Gtk.ToggleButton | None = None

        self._build_ui()

        # Suscribirse al ForecastService
        self._forecast_service.subscribe(self)

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
        """Carga el pronóstico por hora desde el ForecastService.

        Si hay datos en cache, los muestra inmediatamente y solicita
        un refresh en segundo plano.
        """
        logger.info("Cargando pronóstico por hora para lat=%.4f, lon=%.4f...",
                    self._config.latitude, self._config.longitude)

        # Intentar mostrar datos cacheados inmediatamente
        cached = self._forecast_service.get_cached_forecast()
        if cached is not None and cached.hourly is not None:
            self._on_forecast_loaded(cached.hourly)

        # Solicitar refresh al servicio
        self._forecast_service.refresh_forecast(
            GLib.idle_add,
            self._config.latitude,
            self._config.longitude,
            self._config.timezone,
        )

    # ------------------------------------------------------------------
    # ForecastObserver implementation
    # ------------------------------------------------------------------

    def on_forecast_updated(self, result: ForecastResult) -> None:
        """Recibe datos actualizados del ForecastService.

        Reconstruye la grilla horaria solo si los datos cambiaron.

        Args:
            result: ForecastResult con hourly nuevo.
        """
        new_hourly = result.hourly
        if new_hourly is None:
            return

        logger.debug("HourlyForecastPage.on_forecast_updated: %d horas",
                     len(new_hourly.hours))

        # Comparar con datos actuales
        if self._has_hourly_changed(new_hourly):
            self._on_forecast_loaded(new_hourly)

    def on_forecast_error(self, message: str, cached: bool) -> None:
        """Maneja errores del ForecastService.

        Args:
            message: Mensaje descriptivo del error.
            cached: True si hay datos en cache.
        """
        if cached and self._forecast is not None:
            # Ya tenemos datos cacheados mostrados, solo loguear
            logger.warning("Error de forecast en página horaria (con cache): %s", message)
        else:
            logger.error("Error de forecast en página horaria (sin cache): %s", message)
            self._spinner.stop()
            self._spinner.set_visible(False)
            self._error_label.set_markup(
                f"<b>Error al cargar el pronóstico</b>\n\n{message}"
            )
            self._error_label.set_visible(True)

    # ------------------------------------------------------------------
    # Comparación para refresco transparente
    # ------------------------------------------------------------------

    def _has_hourly_changed(self, new_hourly: HourlyForecast) -> bool:
        """Compara el forecast horario nuevo con el actual.

        Args:
            new_hourly: Forecast horario recién obtenido.

        Returns:
            True si los datos cambiaron.
        """
        if self._forecast is None:
            return True

        old_hours = self._forecast.hours
        new_hours = new_hourly.hours

        if len(old_hours) != len(new_hours):
            return True

        # Comparar atributos clave de cada hora
        for old_h, new_h in zip(old_hours, new_hours):
            if (old_h.temperature != new_h.temperature
                    or old_h.symbol != new_h.symbol
                    or old_h.precipitation != new_h.precipitation
                    or old_h.rain_probability != new_h.rain_probability
                    or old_h.wind_speed != new_h.wind_speed):
                return True

        return False

    def _on_forecast_loaded(self, forecast: HourlyForecast) -> None:
        """Muestra el pronóstico por hora cargado, filtrando horas pasadas."""
        logger.debug("Mostrando %d horas en UI", len(forecast.hours))
        self._spinner.stop()
        self._spinner.set_visible(False)
        self._forecast = forecast

        if not forecast.hours:
            logger.warning("No hay datos de horas en el pronóstico")
            no_data = Gtk.Label()
            no_data.set_text("No hay datos de pronóstico por hora disponibles.")
            no_data.set_halign(Gtk.Align.CENTER)
            no_data.set_margin_top(40)
            self._main_box.append(no_data)
            return

        # Calcular timestamp actual en ms
        now_ms = int(datetime.now(tz=self._timezone).timestamp() * 1000)

        # Guardar todas las horas y filtrar solo las futuras
        self._all_hours = forecast.hours
        self._future_hours = [h for h in forecast.hours if h.end >= now_ms]

        if not self._future_hours:
            logger.warning("Todas las horas del pronóstico ya pasaron")
            no_data = Gtk.Label()
            no_data.set_text("No hay más horas de pronóstico disponibles.")
            no_data.set_halign(Gtk.Align.CENTER)
            no_data.set_margin_top(40)
            self._main_box.append(no_data)
            return

        # Determinar si hay horas pasadas para mostrar el toggle
        has_past_hours = len(self._future_hours) < len(self._all_hours)

        if has_past_hours:
            self._toggle_btn = Gtk.ToggleButton()
            self._toggle_btn.set_label("⏮️ Mostrar horas anteriores")
            self._toggle_btn.set_halign(Gtk.Align.CENTER)
            self._toggle_btn.set_margin_bottom(4)
            self._toggle_btn.connect("toggled", self._on_toggle_past_hours)
            self._main_box.append(self._toggle_btn)

        # Construir la lista inicial solo con horas futuras
        self._hours_list = self._build_hours_list_widget(self._future_hours)
        self._main_box.append(self._hours_list)

    def _on_toggle_past_hours(self, button: Gtk.ToggleButton) -> None:
        """Alterna entre mostrar solo horas futuras o todas las horas."""
        if self._hours_list is None:
            return

        # Remover la lista actual del contenedor
        self._main_box.remove(self._hours_list)

        if button.get_active():
            button.set_label("⏮️ Ocultar horas anteriores")
            self._hours_list = self._build_hours_list_widget(self._all_hours)
        else:
            button.set_label("⏮️ Mostrar horas anteriores")
            self._hours_list = self._build_hours_list_widget(self._future_hours)

        self._main_box.append(self._hours_list)

    def _build_hours_list_widget(self, hours: list[HourData]) -> Gtk.ListBox:
        """Construye un Gtk.ListBox con las horas agrupadas por día.

        Args:
            hours: Lista de datos horarios a mostrar.

        Returns:
            Gtk.ListBox con separadores de día y filas de horas.
        """
        hours_by_day = self._group_hours_by_day(hours, self._timezone)

        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        for day_start_ms, day_hours in hours_by_day.items():
            # Separador visual del día
            separator_row = self._build_day_separator_row(day_start_ms)
            list_box.append(separator_row)

            # Horas de ese día
            for hour_data in day_hours:
                row = self._build_hour_row(hour_data)
                list_box.append(row)

        return list_box

    # ------------------------------------------------------------------
    # Agrupación por día y separadores visuales
    # ------------------------------------------------------------------

    @staticmethod
    def _group_hours_by_day(hours: list[HourData], tz: ZoneInfo) -> OrderedDict:
        """Agrupa las horas por día basándose en el timestamp 'end'.

        Args:
            hours: Lista de datos horarios del pronóstico.
            tz: Zona horaria local para la agrupación por día.

        Returns:
            OrderedDict con clave = timestamp inicio del día (medianoche local) en ms,
            valor = lista de HourData de ese día, en orden cronológico.
        """
        grouped: OrderedDict = OrderedDict()
        for h in hours:
            dt = datetime.fromtimestamp(h.end / 1000, tz=tz)
            # Truncar a medianoche del día en la zona horaria local
            day_start = int(datetime(
                dt.year, dt.month, dt.day, 0, 0, 0,
                tzinfo=tz,
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
            f"<big><b>{hour_data.temperature:.1f}°C</b></big>"
        )
        temp_label.set_halign(Gtk.Align.END)
        temp_label.set_xalign(1)
        temp_box.append(temp_label)

        feels_label = Gtk.Label()
        feels_label.set_markup(
            f"<small>Sensación {hour_data.temperature_feels_like:.1f}°C</small>"
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
