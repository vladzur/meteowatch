"""Página de búsqueda y configuración de ubicación.

Permite al usuario introducir su API key y buscar una ubicación
para obtener el pronóstico meteorológico.
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from meteowatch.api.client import MeteoredClient, MeteoredError
from meteowatch.config import AppConfig
from meteowatch.models.location import Location

logger = logging.getLogger(__name__)


class LocationSearchPage(Adw.NavigationPage):
    """Página de configuración inicial: API key + búsqueda de ubicación."""

    def __init__(self, config: AppConfig, on_location_selected):
        """Inicializa la página de búsqueda de ubicación.

        Args:
            config: Configuración de la aplicación.
            on_location_selected: Callback(location_hash, location_name) al seleccionar ubicación.
        """
        super().__init__()
        self.set_title("Configuración")
        self._config = config
        self._on_location_selected = on_location_selected
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz de la página de configuración."""
        # Contenedor principal con scroll
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_title(True)
        toolbar_view.add_top_bar(header)

        # Contenido
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)

        # Caja vertical para el formulario
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        scrolled.set_child(vbox)

        # Título de bienvenida
        welcome = Gtk.Label()
        welcome.set_markup("<big><b>Bienvenido a Meteowatch</b></big>")
        welcome.set_halign(Gtk.Align.CENTER)
        welcome.set_margin_bottom(6)
        vbox.append(welcome)

        subtitle = Gtk.Label()
        subtitle.set_label(
            "Para comenzar, introduce tu clave de API de Meteored\n"
            "y busca una ubicación."
        )
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_wrap(True)
        vbox.append(subtitle)

        # --- Sección API Key ---
        api_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.append(api_section)

        api_label = Gtk.Label()
        api_label.set_markup("<b>Clave de API</b>")
        api_label.set_halign(Gtk.Align.START)
        api_label.set_xalign(0)
        api_section.append(api_label)

        self._api_entry = Gtk.Entry()
        self._api_entry.set_placeholder_text("Introduce tu x-api-key...")
        self._api_entry.set_visibility(False)  # Oculta el texto como contraseña
        if self._config.api_key:
            self._api_entry.set_text(self._config.api_key)
        api_section.append(self._api_entry)

        save_key_btn = Gtk.Button()
        save_key_btn.set_label("Guardar clave")
        save_key_btn.add_css_class("pill")
        save_key_btn.add_css_class("suggested-action")
        save_key_btn.set_halign(Gtk.Align.CENTER)
        save_key_btn.connect("clicked", self._on_save_api_key)
        api_section.append(save_key_btn)

        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.append(separator)

        # --- Sección Búsqueda de ubicación ---
        search_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.append(search_section)

        search_label = Gtk.Label()
        search_label.set_markup("<b>Buscar ubicación</b>")
        search_label.set_halign(Gtk.Align.START)
        search_label.set_xalign(0)
        search_section.append(search_label)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Ej: Madrid, Barcelona...")
        self._search_entry.connect("activate", self._on_search)
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_section.append(self._search_entry)

        search_btn = Gtk.Button()
        search_btn.set_label("Buscar")
        search_btn.add_css_class("pill")
        search_btn.set_halign(Gtk.Align.CENTER)
        search_btn.connect("clicked", self._on_search)
        search_section.append(search_btn)

        # --- Resultados de búsqueda ---
        self._results_label = Gtk.Label()
        self._results_label.set_markup("<b>Resultados</b>")
        self._results_label.set_halign(Gtk.Align.START)
        self._results_label.set_xalign(0)
        self._results_label.set_visible(False)
        search_section.append(self._results_label)

        self._results_list = Gtk.ListBox()
        self._results_list.add_css_class("boxed-list")
        self._results_list.set_visible(False)
        self._results_list.connect("row-activated", self._on_location_selected_row)
        search_section.append(self._results_list)

        # --- Spinner y estado ---
        self._spinner = Gtk.Spinner()
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_visible(False)
        search_section.append(self._spinner)

        self._status_label = Gtk.Label()
        self._status_label.set_halign(Gtk.Align.CENTER)
        self._status_label.set_wrap(True)
        self._status_label.set_visible(False)
        self._status_label.add_css_class("error")
        search_section.append(self._status_label)

    def _on_save_api_key(self, button: Gtk.Button) -> None:
        """Guarda la API key en la configuración."""
        api_key = self._api_entry.get_text().strip()
        if api_key:
            self._config.api_key = api_key
            self._config.save()
            self._show_status("Clave guardada correctamente.", is_error=False)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Reacciona a cambios en el campo de búsqueda."""
        # Reiniciar UI si se borra el texto
        if not entry.get_text().strip():
            self._results_list.set_visible(False)
            self._results_label.set_visible(False)
            self._status_label.set_visible(False)

    def _on_search(self, widget) -> None:
        """Ejecuta la búsqueda de ubicación en la API."""
        query = self._search_entry.get_text().strip()
        if not query:
            self._show_status("Introduce un texto para buscar.", is_error=True)
            return

        api_key = self._config.get_api_key()
        if not api_key:
            self._show_status("Primero guarda tu clave de API.", is_error=True)
            return

        # Mostrar spinner
        self._spinner.set_visible(True)
        self._spinner.start()
        self._status_label.set_visible(False)
        self._results_list.set_visible(False)
        self._results_label.set_visible(False)

        # Ejecutar búsqueda en segundo plano
        def do_search():
            try:
                client = MeteoredClient(api_key)
                locations = client.search_location(query)
                GLib.idle_add(self._on_search_result, locations)
            except MeteoredError as e:
                GLib.idle_add(self._on_search_error, str(e))

        import threading
        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

    def _on_search_result(self, locations: list[Location]) -> None:
        """Muestra los resultados de búsqueda en la lista."""
        self._spinner.stop()
        self._spinner.set_visible(False)

        # Limpiar lista anterior
        while True:
            row = self._results_list.get_first_child()
            if row is None:
                break
            self._results_list.remove(row)

        if not locations:
            self._show_status(
                "No se encontraron ubicaciones. Intenta con otro texto.",
                is_error=True,
            )
            return

        for location in locations:
            row = Gtk.ListBoxRow()
            row.location = location  # Guardar referencia para el callback

            label = Gtk.Label()
            label.set_text(location.display_name)
            label.set_halign(Gtk.Align.START)
            label.set_xalign(0)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(10)
            label.set_margin_bottom(10)
            label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            row.set_child(label)

            self._results_list.append(row)

        self._results_list.set_visible(True)
        self._results_label.set_visible(True)

    def _on_search_error(self, message: str) -> None:
        """Muestra un error de búsqueda."""
        self._spinner.stop()
        self._spinner.set_visible(False)
        self._show_status(f"Error: {message}", is_error=True)

    def _on_location_selected_row(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        """Maneja la selección de una ubicación de la lista."""
        location: Location = getattr(row, "location", None)
        if location is None:
            return

        self._config.set_location(location.hash, location.name)
        self._on_location_selected(location.hash, location.name)

    def _show_status(self, message: str, is_error: bool = True) -> None:
        """Muestra un mensaje de estado (éxito o error)."""
        self._status_label.set_text(message)
        self._status_label.set_visible(True)
        if is_error:
            self._status_label.remove_css_class("success")
            self._status_label.add_css_class("error")
        else:
            self._status_label.remove_css_class("error")
            self._status_label.add_css_class("success")
