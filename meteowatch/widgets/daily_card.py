"""Página de pronóstico diario.

Muestra una lista con el pronóstico de los próximos 5 días
en tarjetas con iconos, temperaturas y datos relevantes.

Se suscribe al ForecastService para recibir actualizaciones
automáticas y muestra un indicador de frescura de los datos.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from meteowatch.api.client import CurrentWeather, ForecastResult, OpenMeteoError
from meteowatch.alerts import AlertEngine
from meteowatch.alerts.rules import Alert
from meteowatch.config import AppConfig
from meteowatch.icons import get_weather_symbol
from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourlyForecast
from meteowatch.services.forecast import BaseForecastObserver, ForecastService

logger = logging.getLogger(__name__)

# Días de la semana en español
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _degrees_to_cardinal(degrees: int) -> str:
    """Convierte una dirección en grados (0-360) a punto cardinal.

    Args:
        degrees: Ángulo en grados (0=N, 90=E, 180=S, 270=W).

    Returns:
        Abreviatura del punto cardinal (N, NE, E, SE, S, SW, W, NW).
    """
    if degrees < 0:
        return "?"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]


class DailyForecastPage(Adw.NavigationPage, BaseForecastObserver):
    """Página que muestra el pronóstico diario para la ubicación seleccionada.

    Se suscribe al ForecastService y reacciona a on_forecast_updated
    reconstruyendo la UI solo si los datos cambiaron.
    """

    # Constantes para el indicador de frescura
    FRESHNESS_WARNING_MINUTES = 60    # >1h → amarillo
    FRESHNESS_ERROR_MINUTES = 180     # >3h → naranja

    def __init__(self, config: AppConfig, forecast_service: ForecastService,
                 on_day_selected, on_change_location):
        """Inicializa la página de pronóstico diario.

        Args:
            config: Configuración de la aplicación.
            forecast_service: Servicio centralizado de datos meteorológicos.
            on_day_selected: Callback(location_hash, day_start_timestamp) al hacer clic en un día.
            on_change_location: Callback() para volver a la pantalla de búsqueda.
        """
        super().__init__()
        self.set_title(config.location_name or "Meteowatch")
        self._config = config
        self._forecast_service = forecast_service
        self._on_day_selected = on_day_selected
        self._on_change_location = on_change_location
        self._forecast: Optional[DailyForecast] = None
        self._current: Optional[CurrentWeather] = None
        self._hourly: Optional[HourlyForecast] = None
        self._alert_engine = AlertEngine()
        self._alert_banner: Optional[Gtk.Revealer] = None
        self._alert_banner_label: Optional[Gtk.Label] = None
        self._freshness_label: Optional[Gtk.Label] = None
        self._freshness_timer_id: int = 0
        self._is_offline: bool = False

        self._build_ui()

        # Suscribirse al ForecastService para recibir actualizaciones
        self._forecast_service.subscribe(self)

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

        # Menú de opciones (izquierda, antes del nombre de la ubicación)
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Opciones")

        menu_model = Gio.Menu()

        # Sección: ayuda e información
        info_section = Gio.Menu()
        info_section.append("Ayuda", "app.help")
        info_section.append("Acerca de Meteowatch", "app.about")
        menu_model.append_section(None, info_section)

        # Sección: salir
        quit_section = Gio.Menu()
        quit_section.append("Salir", "app.quit")
        menu_model.append_section(None, quit_section)

        menu_btn.set_menu_model(menu_model)

        header.pack_start(menu_btn)

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

        # --- Banner de alertas (Revealer oculto por defecto) ---
        self._alert_banner_label = Gtk.Label()
        self._alert_banner_label.set_wrap(True)
        self._alert_banner_label.set_xalign(0)
        self._alert_banner_label.set_margin_start(12)
        self._alert_banner_label.set_margin_end(12)
        self._alert_banner_label.set_margin_top(10)
        self._alert_banner_label.set_margin_bottom(10)
        self._alert_banner_label.add_css_class("error")

        self._alert_banner = Gtk.Revealer()
        self._alert_banner.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._alert_banner.set_transition_duration(300)
        self._alert_banner.set_reveal_child(False)
        self._alert_banner.set_child(self._alert_banner_label)
        self._main_box.prepend(self._alert_banner)

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

        # Indicador de frescura (al pie, sutil)
        self._freshness_label = Gtk.Label()
        self._freshness_label.set_halign(Gtk.Align.CENTER)
        self._freshness_label.set_margin_top(8)
        self._freshness_label.set_margin_bottom(4)
        self._freshness_label.add_css_class("dim-label")
        self._freshness_label.set_visible(True)
        self._freshness_label.set_markup("<small>🕐 Cargando…</small>")
        self._main_box.append(self._freshness_label)

    def load_forecast(self) -> None:
        """Solicita el pronóstico al ForecastService.

        Delega el fetching en el servicio centralizado. Si los datos
        ya están en cache y frescos, la UI se construye inmediatamente.
        """
        logger.info("Cargando pronóstico diario para lat=%.4f, lon=%.4f...",
                    self._config.latitude, self._config.longitude)
        self._spinner.set_visible(True)
        self._spinner.start()
        self._error_label.set_visible(False)
        self._is_offline = False

        # Limpiar widgets de forecast anteriores (excepto spinner, error, banner y freshness)
        children_to_remove = []
        for child in self._main_box:
            if (child is not self._spinner
                    and child is not self._error_label
                    and child is not self._alert_banner
                    and child is not self._freshness_label):
                children_to_remove.append(child)

        for child in children_to_remove:
            self._main_box.remove(child)

        # Intentar mostrar datos cacheados inmediatamente si existen
        cached = self._forecast_service.get_cached_forecast()
        if cached is not None:
            self._forecast = cached.daily
            self._current = cached.current
            self._hourly = cached.hourly
            self._on_forecast_loaded(cached.daily, cached.current)
            # Iniciar indicador de frescura
            self._start_freshness_timer()
            # Si los datos están frescos, ocultar spinner
            age = self._forecast_service.get_age_minutes()
            if age < 60:
                self._spinner.stop()
                self._spinner.set_visible(False)

        # Solicitar refresh al servicio (no bloquea, usa hilo secundario)
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

        Compara con los datos actuales y reconstruye la UI solo si
        hay diferencias en los días del pronóstico.

        Args:
            result: ForecastResult con daily, hourly y current nuevos.
        """
        logger.debug("DailyForecastPage.on_forecast_updated: %d días",
                     len(result.daily.days) if result.daily else 0)

        new_forecast = result.daily
        new_current = result.current
        new_hourly = result.hourly

        # Determinar si los datos cambiaron respecto a lo mostrado
        changed = self._has_forecast_changed(new_forecast)

        # Actualizar estado interno
        self._forecast = new_forecast
        self._current = new_current
        self._hourly = new_hourly
        self._is_offline = False

        if changed or self._spinner.is_spinning():
            # Reconstruir UI solo si cambió o es la primera carga
            self._on_forecast_loaded(new_forecast, new_current)
        else:
            # Solo actualizar indicador de frescura
            self._update_freshness_label()

        # Evaluar alertas y mostrar banner
        alerts = self._alert_engine.evaluate(new_forecast, new_hourly)
        if alerts:
            self.set_alerts(alerts)

        # Iniciar timer de frescura si no estaba activo
        self._start_freshness_timer()

    def on_forecast_error(self, message: str, cached: bool) -> None:
        """Maneja errores del ForecastService.

        Args:
            message: Mensaje descriptivo del error.
            cached: True si hay datos en cache que pueden usarse como fallback.
        """
        if cached and self._forecast is not None:
            # Mostrar datos cacheados con indicador de desconexión
            logger.warning("Error de forecast, usando cache: %s", message)
            self._is_offline = True
            self._spinner.stop()
            self._spinner.set_visible(False)
            self._update_freshness_label()
            self._start_freshness_timer()
        else:
            # Sin cache: mostrar error
            logger.error("Error de forecast sin cache: %s", message)
            self._spinner.stop()
            self._spinner.set_visible(False)
            self._error_label.set_markup(
                f"<b>Error al cargar el pronóstico</b>\n\n{message}"
            )
            self._error_label.set_visible(True)

    # ------------------------------------------------------------------
    # Comparación de datos para refresco transparente
    # ------------------------------------------------------------------

    def _has_forecast_changed(self, new_forecast: DailyForecast) -> bool:
        """Compara el forecast nuevo con el actual para detectar cambios.

        Args:
            new_forecast: Forecast recién obtenido.

        Returns:
            True si los datos cambiaron (cantidad de días o contenido).
        """
        if self._forecast is None:
            return True

        old_days = self._forecast.days
        new_days = new_forecast.days

        if len(old_days) != len(new_days):
            return True

        # Comparar atributos clave de cada día
        for old_day, new_day in zip(old_days, new_days):
            if (old_day.temperature_max != new_day.temperature_max
                    or old_day.temperature_min != new_day.temperature_min
                    or old_day.symbol != new_day.symbol
                    or old_day.precipitation != new_day.precipitation
                    or old_day.rain_probability != new_day.rain_probability
                    or old_day.wind_speed != new_day.wind_speed
                    or old_day.wind_gust != new_day.wind_gust):
                return True

        return False

    # ------------------------------------------------------------------
    # Carga de datos en UI
    # ------------------------------------------------------------------

    def _on_forecast_loaded(self, forecast: DailyForecast,
                            current: Optional[CurrentWeather] = None) -> None:
        """Muestra el pronóstico diario cargado en la UI."""
        logger.debug("Mostrando pronóstico diario en UI: %s", self._config.location_name)
        self._spinner.stop()
        self._spinner.set_visible(False)
        self._forecast = forecast
        self.set_title(self._config.location_name or "Meteowatch")

        # Limpiar widgets de forecast anteriores (excepto spinner, error, banner y freshness)
        children_to_remove = []
        for child in self._main_box:
            if (child is not self._spinner
                    and child is not self._error_label
                    and child is not self._alert_banner
                    and child is not self._freshness_label):
                children_to_remove.append(child)

        for child in children_to_remove:
            self._main_box.remove(child)

        self._build_forecast_card(forecast, current)
        self._update_freshness_label()

    # ------------------------------------------------------------------
    # Indicador de frescura
    # ------------------------------------------------------------------

    def _start_freshness_timer(self) -> None:
        """Inicia el timer que actualiza el label de frescura cada 60s."""
        if self._freshness_timer_id != 0:
            return
        self._freshness_timer_id = GLib.timeout_add_seconds(
            60, self._on_freshness_timer
        )

    def _stop_freshness_timer(self) -> None:
        """Detiene el timer de frescura."""
        if self._freshness_timer_id != 0:
            GLib.source_remove(self._freshness_timer_id)
            self._freshness_timer_id = 0

    def _on_freshness_timer(self) -> bool:
        """Callback del timer de frescura (cada 60s).

        Returns:
            True para mantener el timer activo.
        """
        self._update_freshness_label()
        return True

    def _update_freshness_label(self) -> None:
        """Actualiza el texto y color del indicador de frescura."""
        if self._freshness_label is None:
            return

        age_minutes = self._forecast_service.get_age_minutes()

        if self._is_offline:
            self._set_offline_freshness(age_minutes)
        else:
            self._set_normal_freshness(age_minutes)

    def _set_offline_freshness(self, age_minutes: float) -> None:
        """Configura el label de frescura en modo sin conexión.

        Usa emoji 🔌 (distinto a ⚠️/🔴 de alertas).

        Args:
            age_minutes: Antigüedad de los datos cacheados en minutos.
        """
        assert self._freshness_label is not None
        if age_minutes < 1:
            text = "🔌 Sin conexión"
        elif age_minutes < 60:
            text = f"🔌 Sin conexión — hace {int(age_minutes)} min"
        else:
            hours = int(age_minutes / 60)
            text = f"🔌 Sin conexión — hace {hours}h"
        self._freshness_label.set_markup(f"<small>{text}</small>")
        self._freshness_label.remove_css_class("warning")
        self._freshness_label.remove_css_class("error")

    def _set_normal_freshness(self, age_minutes: float) -> None:
        """Configura el label de frescura en modo normal.

        Args:
            age_minutes: Antigüedad de los datos en minutos.
        """
        assert self._freshness_label is not None
        if age_minutes < 1:
            text = "🕐 Actualizado ahora"
        elif age_minutes < 60:
            text = f"🕐 Actualizado hace {int(age_minutes)} min"
        else:
            hours = int(age_minutes / 60)
            remaining_min = int(age_minutes % 60)
            if remaining_min > 0:
                text = f"🕐 Actualizado hace {hours}h {remaining_min}min"
            else:
                text = f"🕐 Actualizado hace {hours}h"

        self._freshness_label.set_markup(f"<small>{text}</small>")

        # Color según antigüedad
        if age_minutes > self.FRESHNESS_ERROR_MINUTES:
            self._freshness_label.remove_css_class("warning")
            self._freshness_label.add_css_class("error")
        elif age_minutes > self.FRESHNESS_WARNING_MINUTES:
            self._freshness_label.remove_css_class("error")
            self._freshness_label.add_css_class("warning")
        else:
            self._freshness_label.remove_css_class("warning")
            self._freshness_label.remove_css_class("error")

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
        """Navega al pronóstico detallado de las próximas 24 horas."""
        if self._forecast and self._forecast.days:
            today = self._forecast.days[0]
            logger.info("Navegando a pronóstico 24h")
            # Usar lat/lon como identificador para mantener compatibilidad con la interfaz
            location_id = f"{self._forecast.latitude},{self._forecast.longitude}"
            self._on_day_selected(location_id, today.start)

    def _build_forecast_card(self, forecast: DailyForecast,
                             current: Optional[CurrentWeather] = None) -> None:
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
        location_label.set_markup(f"<big><b>{self._config.location_name or 'Meteowatch'}</b></big>")
        location_label.set_halign(Gtk.Align.CENTER)
        header_box.append(location_label)

        if current is not None:
            current_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            current_box.set_halign(Gtk.Align.CENTER)

            # Icono del tiempo actual
            cur_symbol = get_weather_symbol(current.symbol)
            cur_icon = Gtk.Label()
            cur_icon.set_markup(f"<span size='large'>{cur_symbol.emoji}</span>")
            current_box.append(cur_icon)

            # Temperatura actual
            cur_temp_label = Gtk.Label()
            cur_temp_label.set_markup(
                f"<span size='xx-large'><b>{current.temperature:.0f}°C</b></span>"
            )
            current_box.append(cur_temp_label)

            # Columna de detalles: sensación térmica, humedad y "Ahora"
            details_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            details_col.set_valign(Gtk.Align.CENTER)

            feels_label = Gtk.Label()
            feels_label.set_markup(
                f"<small>Sensación {current.feels_like:.0f}°C</small>"
            )
            feels_label.set_halign(Gtk.Align.START)
            feels_label.set_xalign(0)
            details_col.append(feels_label)

            humidity_label = Gtk.Label()
            humidity_label.set_markup(
                f"<small>💧 {current.humidity}%</small>"
            )
            humidity_label.set_halign(Gtk.Align.START)
            humidity_label.set_xalign(0)
            details_col.append(humidity_label)

            cur_desc = Gtk.Label()
            cur_desc.set_markup("<small>Ahora</small>")
            cur_desc.set_halign(Gtk.Align.START)
            cur_desc.set_xalign(0)
            details_col.append(cur_desc)

            current_box.append(details_col)

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

        # --- Atribución a Open-Meteo (requerido por los términos de uso) ---
        attribution_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        attribution_box.set_margin_top(16)
        attribution_box.set_margin_bottom(8)

        attribution_label = Gtk.Label()
        attribution_label.set_markup(
            "<small>Datos meteorológicos proporcionados por "
            "<a href='https://open-meteo.com/'>Open-Meteo</a>"
            "</small>"
        )
        attribution_label.set_halign(Gtk.Align.CENTER)
        attribution_label.set_opacity(0.7)
        attribution_box.append(attribution_label)

        self._main_box.append(attribution_box)

    def _build_day_card(self, day, index: int) -> Gtk.Box:
        """Construye una tarjeta expandida con todos los detalles de un día.

        Args:
            day: Datos del día (DayData).
            index: Índice del día (0 = hoy).

        Returns:
            Gtk.Box con estilo de tarjeta y toda la información del día.
        """
        gust_alert = day.wind_gust >= 50

        # Obtener la zona horaria desde la configuración
        try:
            tz = ZoneInfo(self._config.timezone) if self._config.timezone != "auto" else ZoneInfo("UTC")
        except Exception:
            tz = ZoneInfo("UTC")

        # Formatear nombre del día y fecha
        dt = datetime.fromtimestamp(day.start / 1000, tz=tz)
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
        temp_max_lbl.set_markup(f"<big><b>{day.temperature_max:.0f}°C</b></big>")
        temp_max_lbl.set_halign(Gtk.Align.END)
        temp_max_lbl.set_xalign(1)
        temp_col.append(temp_max_lbl)
        temp_min_lbl = Gtk.Label()
        temp_min_lbl.set_markup(f"<small>{day.temperature_min:.0f}°C</small>")
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

        sun_in = datetime.fromtimestamp(day.sun_in / 1000, tz=tz).strftime("%H:%M")
        sun_out = datetime.fromtimestamp(day.sun_out / 1000, tz=tz).strftime("%H:%M")

        wind_dir_str = _degrees_to_cardinal(day.wind_direction)

        self._add_grid_cell(grid, "🌧️ Prob. lluvia", f"{day.rain_probability}%", 0, 0)
        self._add_grid_cell(grid, "💨 Viento", f"{day.wind_speed} km/h {wind_dir_str}", 0, 1)
        gust_text = f"{day.wind_gust} km/h"
        self._add_grid_cell(grid, "↗️ Ráfagas", gust_text, 1, 0, alert=gust_alert)
        self._add_grid_cell(grid, "🌅 Amanecer", sun_in, 1, 1)
        self._add_grid_cell(grid, "🌇 Atardecer", sun_out, 2, 0)
        self._add_grid_cell(grid, "🌧️ Precipitación", f"{day.precipitation:.1f} mm", 2, 1)
        self._add_grid_cell(grid, "☀️ Índice UV", f"{day.uv_index_max:.1f}", 3, 0)

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

    def set_alerts(self, alerts: list[Alert]) -> None:
        """Muestra u oculta el banner de alertas en la página de pronóstico.

        Args:
            alerts: Lista de alertas activas. Lista vacía para ocultar el banner.
        """
        if self._alert_banner is None or self._alert_banner_label is None:
            return

        if not alerts:
            self._alert_banner.set_reveal_child(False)
            return

        # Contar alertas por nivel
        orange_count = sum(1 for a in alerts if a.level == "orange")
        yellow_count = sum(1 for a in alerts if a.level == "yellow")

        # Construir mensaje del banner
        parts: list[str] = []
        if orange_count > 0:
            parts.append(f"🔴 {orange_count} alerta{'s' if orange_count > 1 else ''} naranja")
        if yellow_count > 0:
            parts.append(f"⚠️ {yellow_count} alerta{'s' if yellow_count > 1 else ''} amarilla")

        title = " · ".join(parts)

        # Agregar primer mensaje de alerta como detalle
        detail = alerts[0].message

        self._alert_banner_label.set_markup(
            f"<b>{title}</b>\n<small>{detail}</small>"
        )
        self._alert_banner.set_reveal_child(True)
        logger.debug("Banner de alertas mostrado: %s", title)
