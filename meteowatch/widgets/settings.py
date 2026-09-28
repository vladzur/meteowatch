"""Diálogo de preferencias de Meteowatch.

Permite al usuario configurar la llave de API de DeepSeek para
habilitar la generación de reportes meteorológicos con IA.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from meteowatch.config import AppConfig

logger = logging.getLogger(__name__)


class SettingsDialog(Adw.Dialog):
    """Diálogo modal de preferencias de la aplicación."""

    def __init__(self, config: AppConfig, on_saved=None):
        """Inicializa el diálogo de preferencias.

        Args:
            config: Configuración persistente de la aplicación.
            on_saved: Callback invocado tras guardar los cambios.
        """
        super().__init__()
        self.set_title("Preferencias")
        self.set_content_width(420)
        self.set_content_height(320)

        self._config = config
        self._on_saved = on_saved
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz del diálogo."""
        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_show_title(True)
        toolbar.add_top_bar(header)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        toolbar.set_content(content)

        # --- Sección: llave de DeepSeek ---
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.append(section)

        title_label = Gtk.Label()
        title_label.set_markup("<b>Reporte con IA (DeepSeek)</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_xalign(0)
        section.append(title_label)

        desc_label = Gtk.Label()
        desc_label.set_label(
            "Ingresa tu llave de API de DeepSeek para generar reportes "
            "meteorológicos narrativos con inteligencia artificial. "
            "La llave se guarda localmente en tu configuración."
        )
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_xalign(0)
        desc_label.set_wrap(True)
        section.append(desc_label)

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("sk-...")
        self._entry.set_visibility(False)
        self._entry.set_text(self._config.deepseek_api_key or "")
        section.append(self._entry)

        show_check = Gtk.CheckButton(label="Mostrar llave")
        show_check.connect("toggled", self._on_show_toggled)
        section.append(show_check)

        # --- Botones de acción ---
        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)
        content.append(btn_box)

        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect("clicked", lambda b: self.close())
        btn_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Guardar")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        btn_box.append(save_btn)

        self.set_child(toolbar)

    def _on_show_toggled(self, check: Gtk.CheckButton) -> None:
        """Alterna la visibilidad de la llave en el campo de entrada."""
        self._entry.set_visibility(check.get_active())

    def _on_save_clicked(self, btn: Gtk.Button) -> None:
        """Guarda la llave en la configuración persistente y cierra."""
        self._config.deepseek_api_key = self._entry.get_text().strip()
        self._config.save()
        logger.info("Llave de DeepSeek guardada en la configuración")

        if self._on_saved is not None:
            self._on_saved()

        self.close()
