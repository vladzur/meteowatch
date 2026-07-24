"""Implementación del protocolo org.kde.StatusNotifierItem (SNI) para el system tray.

Registra un icono en la bandeja del sistema compatible con:
- GNOME Shell (extensión AppIndicator Support)
- KDE Plasma (soporte nativo)
- XFCE, Budgie, Cinnamon (vía plugins)

Usa exclusivamente Gio.DBusConnection (sin dependencias externas).
"""

import logging
import os

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib  # noqa: E402

from meteowatch.dbusmenu import DbusMenu, DBUSMENU_PATH
from meteowatch.tray_icon import (
    TRAY_ICON_DIR,
    ensure_tray_icon_exists,
    generate_tray_png,
)

logger = logging.getLogger(__name__)

# Archivos alternantes para forzar recarga del icono en el panel
_ICON_PATHS = [
    os.path.join(TRAY_ICON_DIR, "tray-icon-0.png"),
    os.path.join(TRAY_ICON_DIR, "tray-icon-1.png"),
]

# Constantes del protocolo SNI
SNI_NAME = "com.meteowatch.app.tray"
SNI_PATH = "/StatusNotifierItem"
SNI_WATCHER_BUS = "org.kde.StatusNotifierWatcher"
SNI_WATCHER_PATH = "/StatusNotifierWatcher"
SNI_WATCHER_IFACE = "org.kde.StatusNotifierWatcher"

# XML de introspección D-Bus para el protocolo StatusNotifierItem
SNI_INTROSPECTION_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
      <arg name="menu" type="o" direction="out"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <signal name="NewIcon"/>
    <signal name="NewIconThemePath">
      <arg name="path" type="s"/>
    </signal>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
    <signal name="NewTitle"/>
    <signal name="NewAttentionIcon"/>
  </interface>
</node>
"""

# Compilar información de la interfaz
_sni_introspection = Gio.DBusNodeInfo.new_for_xml(SNI_INTROSPECTION_XML)
SNI_INTERFACE_INFO = _sni_introspection.interfaces[0]


class StatusNotifierItem:
    """Implementa el protocolo org.kde.StatusNotifierItem para el icono de bandeja.

    Gestiona el ciclo de vida del icono en el tray: registro D-Bus,
    creación del menú contextual, actualización dinámica del icono
    y limpieza de recursos al cerrar.
    """

    def __init__(self, application, window):
        """Inicializa el StatusNotifierItem y registra el icono en la bandeja.

        Args:
            application: Instancia de Gtk.Application.
            window: Ventana principal (para toggle_window y present).
        """
        self._app = application
        self._window = window
        self._connection: Gio.DBusConnection | None = None
        self._sni_reg_id: int = 0
        self._owner_id: int = 0
        self._dbus_menu: DbusMenu | None = None
        self._registered: bool = False
        self._icon_path: str = ""
        self._icon_toggle: int = 0  # alterna entre _ICON_PATHS[0] y [1]

        # Asegurar que existe un icono por defecto (usa path-0)
        self._icon_path = ensure_tray_icon_exists()

        # Obtener conexión al bus de sesión
        try:
            self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except Exception:
            logger.warning("No se pudo conectar al bus de sesión D-Bus. "
                         "El tray no estará disponible.")
            return

        # Registrar objeto D-Bus en SNI_PATH
        self._sni_reg_id = self._connection.register_object(
            SNI_PATH,
            SNI_INTERFACE_INFO,
            self._handle_method_call,
            self._handle_property_get,
        )

        # Adquirir nombre de bus (dispara _on_name_acquired)
        self._owner_id = Gio.bus_own_name_on_connection(
            self._connection,
            SNI_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_name_acquired,
            self._on_name_lost,
        )

        logger.info("StatusNotifierItem inicializado en %s", SNI_NAME)

    @property
    def is_available(self) -> bool:
        """Indica si el tray está disponible (nombre D-Bus adquirido)."""
        return self._registered

    # ------------------------------------------------------------------
    # Ciclo de vida D-Bus
    # ------------------------------------------------------------------

    def _on_name_acquired(self, connection, name):
        """Callback cuando se adquiere el nombre en el bus D-Bus.

        DBusMenu está DESACTIVADO: causa congelamiento del escritorio
        en GNOME + AppIndicator. Ver docs/tray_lessons_learned.md.

        Alternativas: SecondaryActivate (clic medio) y Ctrl+Q para salir.
        """
        logger.debug("Nombre D-Bus adquirido: %s", name)

        # Registrar en el StatusNotifierWatcher (OBLIGATORIO para que sea visible)
        try:
            self._connection.call_sync(
                SNI_WATCHER_BUS,
                SNI_WATCHER_PATH,
                SNI_WATCHER_IFACE,
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (SNI_NAME,)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            self._registered = True
            logger.info("Icono registrado en StatusNotifierWatcher")
        except Exception:
            logger.exception("No se pudo registrar en StatusNotifierWatcher. "
                           "¿Está corriendo un servicio de tray compatible?")
            self._registered = False

    def _on_name_lost(self, connection, name):
        """Callback cuando se pierde el nombre en el bus D-Bus."""
        logger.warning("Nombre D-Bus perdido: %s", name)
        self._registered = False

    # ------------------------------------------------------------------
    # Manejo de métodos D-Bus
    # ------------------------------------------------------------------

    def _handle_method_call(self, connection, sender, object_path,
                            interface_name, method_name, parameters,
                            invocation):
        """Despacha llamadas a métodos D-Bus del protocolo SNI.

        Envuelve cada llamada en try/except para garantizar que
        SIEMPRE se responde, evitando bloquear el escritorio.
        """
        try:
            if method_name == "Activate":
                x, y = parameters.unpack()
                self._on_activate(x, y, invocation)
            elif method_name == "SecondaryActivate":
                x, y = parameters.unpack()
                self._on_secondary_activate(x, y, invocation)
            elif method_name == "ContextMenu":
                x, y = parameters.unpack()
                self._on_context_menu(x, y, invocation)
            elif method_name == "Scroll":
                invocation.return_value(None)
            else:
                logger.warning("Método SNI no soportado: %s", method_name)
                invocation.return_value(None)
        except Exception:
            logger.exception("Error en SNI.%s — respondiendo con error", method_name)
            try:
                invocation.return_value(None)
            except Exception:
                pass

    def _on_activate(self, x, y, invocation):
        """Clic primario en el icono del tray: alterna mostrar/ocultar ventana."""
        logger.debug("Activate SNI: x=%d, y=%d", x, y)
        GLib.idle_add(self._toggle_window)
        invocation.return_value(None)

    def _on_secondary_activate(self, x, y, invocation):
        """Clic secundario (medio) en el icono del tray: cierra la app."""
        logger.debug("SecondaryActivate SNI: x=%d, y=%d → quit", x, y)
        self._app.activate_action("quit", None)
        invocation.return_value(None)

    def _on_context_menu(self, x, y, invocation):
        """Solicitud de menú contextual: DBusMenu desactivado."""
        logger.debug("ContextMenu SNI: x=%d, y=%d (sin menú)", x, y)
        invocation.return_value(GLib.Variant("(o)", ("/",)))

    # ------------------------------------------------------------------
    # Propiedades D-Bus
    # ------------------------------------------------------------------

    def _handle_property_get(self, connection, sender, object_path,
                             interface_name, key):
        """Retorna propiedades D-Bus bajo demanda."""
        try:
            props = {
                "Category": GLib.Variant("s", "ApplicationStatus"),
                "Id": GLib.Variant("s", "meteowatch"),
                "Title": GLib.Variant("s", "Meteowatch"),
                "Status": GLib.Variant("s", "Active"),
                "WindowId": GLib.Variant("i", 0),
                "IconName": GLib.Variant("s", self._icon_path),
                "IconThemePath": GLib.Variant("s", ""),
                "ItemIsMenu": GLib.Variant("b", False),
                "Menu": GLib.Variant("o", "/"),
            }
            return props.get(key)
        except Exception:
            logger.exception("Error en property get SNI: %s", key)
            return None

    # ------------------------------------------------------------------
    # Actualización dinámica del icono
    # ------------------------------------------------------------------

    def update_icon(self, symbol_emoji: str, temperature: float | None) -> None:
        """Actualiza el icono del tray con nuevos datos del clima.

        Alterna entre dos archivos PNG para forzar al panel
        a recargar el icono (cambio de ruta en IconName).

        Args:
            symbol_emoji: Emoji de la condición climática actual.
            temperature: Temperatura actual en grados Celsius.
        """
        if not self._registered:
            return

        try:
            # Alternar entre path 0 y 1 para forzar recarga
            self._icon_toggle = 1 - self._icon_toggle
            new_path = _ICON_PATHS[self._icon_toggle]
            self._icon_path = generate_tray_png(
                symbol_emoji, temperature, output_path=new_path
            )
            self._emit_new_icon()
            logger.debug("Icono de tray actualizado: %s %.0f° → %s",
                        symbol_emoji, temperature or 0,
                        os.path.basename(self._icon_path))
        except Exception:
            logger.exception("Error al actualizar icono del tray")

    def _emit_new_icon(self) -> None:
        """Emite la señal D-Bus NewIcon para notificar cambio de icono."""
        if self._connection is None or self._sni_reg_id == 0:
            return
        try:
            self._connection.emit_signal(
                None,               # destination (None = broadcast)
                SNI_PATH,
                "org.kde.StatusNotifierItem",
                "NewIcon",
                GLib.Variant("()", ()),
            )
        except Exception:
            logger.exception("Error al emitir NewIcon")

    # ------------------------------------------------------------------
    # Lógica de toggle y callbacks del menú
    # ------------------------------------------------------------------

    def _toggle_window(self) -> None:
        """Alterna la visibilidad de la ventana principal."""
        if self._window.is_visible():
            logger.debug("Ocultando ventana al tray")
            self._window.hide()
        else:
            logger.debug("Mostrando ventana desde el tray")
            self._window.present()

    def _on_menu_show(self) -> None:
        """Callback del menú: Abrir ventana."""
        self._window.present()

    def _on_menu_hide(self) -> None:
        """Callback del menú: Ocultar ventana al tray."""
        self._window.hide()

    def _on_menu_quit(self) -> None:
        """Callback del menú: Salir de la aplicación."""
        self._app.activate_action("quit", None)

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Libera recursos D-Bus al cerrar la aplicación."""
        logger.debug("Limpiando StatusNotifierItem...")

        # DBusMenu desactivado — no hay recursos que liberar

        if self._owner_id != 0:
            Gio.bus_unown_name(self._owner_id)
            self._owner_id = 0

        if self._sni_reg_id != 0 and self._connection is not None:
            self._connection.unregister_object(self._sni_reg_id)
            self._sni_reg_id = 0

        self._registered = False
        logger.info("StatusNotifierItem liberado")
