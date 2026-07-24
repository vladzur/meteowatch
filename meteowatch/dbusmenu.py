"""Implementación del protocolo com.canonical.dbusmenu para menú contextual del tray.

Proporciona un menú contextual que aparece al hacer clic derecho sobre
el icono de la bandeja del sistema, usando exclusivamente Gio.DBusConnection
(sin dependencias externas como AyatanaAppIndicator3).
"""

import logging

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib  # noqa: E402

logger = logging.getLogger(__name__)

# Ruta por defecto del objeto DBusMenu en el bus
DBUSMENU_PATH = "/com/canonical/dbusmenu"

# XML de introspección D-Bus para el protocolo com.canonical.dbusmenu
DBUSMENU_INTROSPECTION_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <property name="Version" type="u" access="read"/>
    <property name="Status" type="s" access="read"/>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
    <signal name="ItemActivationRequested">
      <arg name="id" type="i"/>
      <arg name="timestamp" type="u"/>
    </signal>
  </interface>
</node>
"""

# Información de la interfaz compilada desde el XML
_introspection_data = Gio.DBusNodeInfo.new_for_xml(DBUSMENU_INTROSPECTION_XML)
INTERFACE_INFO = _introspection_data.interfaces[0]


def _build_menu_node(item_id: int, label: str, icon: str, is_separator: bool,
                     children: list) -> GLib.Variant:
    """Construye un nodo de menú como GLib.Variant en el formato DBusMenu.

    El formato de cada nodo es (ia{sv}av):
    - i: ID del ítem
    - a{sv}: diccionario de propiedades (label, enabled, visible, type, icon-name)
    - av: array de hijos (cada uno es otra variante (ia{sv}av))

    Args:
        item_id: Identificador único del ítem.
        label: Etiqueta visible del ítem.
        icon: Nombre del icono (p.ej. 'view-restore-symbolic').
        is_separator: Si el ítem es un separador.
        children: Lista de GLib.Variant hijos (vacía para ítems hoja).

    Returns:
        GLib.Variant con formato (ia{sv}av).
    """
    # Construir diccionario de propiedades como dict Python → GLib lo convierte a a{sv}
    props = {
        "label": GLib.Variant("s", label),
        "enabled": GLib.Variant("b", not is_separator),
        "visible": GLib.Variant("b", True),
        "type": GLib.Variant("s", "separator" if is_separator else "standard"),
    }
    if icon and not is_separator:
        props["icon-name"] = GLib.Variant("s", icon)

    # Construir el nodo como (ia{sv}av)
    return GLib.Variant("(ia{sv}av)", (item_id, props, children))


def _build_root_props() -> dict:
    """Construye las propiedades de la raíz del menú como dict Python."""
    return {"children-display": GLib.Variant("s", "submenu")}


def _format_vardict_text(props: dict) -> str:
    """Convierte un dict de propiedades a formato texto de GVariant (a{sv}).

    En GVariant text format, a{sv} requiere que los valores estén
    envueltos en <...> (variants). Ej: {'key': <'value'>, 'flag': <true>}.

    Args:
        props: Dict de {str: GLib.Variant}.

    Returns:
        String en formato GVariant text para un a{sv}.
    """
    parts = []
    for key, value in props.items():
        # print_(True) da la representación interna del variant,
        # hay que envolverla en <...> para el formato a{sv}
        parts.append(f"'{key}': <{value.print_(True)}>")
    return "{" + ", ".join(parts) + "}"


class DbusMenu:
    """Implementa el protocolo com.canonical.dbusmenu para menú contextual del tray.

    Expone un menú con tres acciones: Abrir, Ocultar y Salir, más un separador.
    Cada acción dispara un callback configurable.
    """

    # IDs de los ítems del menú
    ITEM_SHOW = 1
    ITEM_HIDE = 2
    ITEM_QUIT = 3

    def __init__(
        self,
        connection: Gio.DBusConnection,
        path: str = DBUSMENU_PATH,
        *,
        on_show=None,
        on_hide=None,
        on_quit=None,
    ):
        """Inicializa el DBusMenu y registra el objeto en el bus.

        Args:
            connection: Conexión al bus de sesión D-Bus.
            path: Ruta del objeto D-Bus (por defecto /com/canonical/dbusmenu).
            on_show: Callback para la acción "Abrir".
            on_hide: Callback para la acción "Ocultar".
            on_quit: Callback para la acción "Salir".
        """
        self._connection = connection
        self._path = path
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit
        self._revision = 1
        self._reg_id = 0

        # Definir la estructura del menú
        self._items = [
            (self.ITEM_SHOW, "Abrir", "view-restore-symbolic", False),
            (self.ITEM_HIDE, "Ocultar", "window-minimize-symbolic", False),
            (None, "", "", True),  # separador
            (self.ITEM_QUIT, "Salir", "application-exit-symbolic", False),
        ]

        self._register()

    def _register(self) -> None:
        """Registra el objeto D-Bus en el bus de sesión."""
        self._reg_id = self._connection.register_object(
            self._path,
            INTERFACE_INFO,
            self._handle_method_call,
            self._handle_property_get,
        )
        logger.debug("DBusMenu registrado en %s", self._path)

    def _handle_method_call(self, connection, sender, object_path,
                            interface_name, method_name, parameters,
                            invocation):
        """Despacha llamadas a métodos D-Bus.

        Envuelve cada llamada en try/except para garantizar que
        SIEMPRE se responde, evitando bloquear el escritorio.
        """
        try:
            if method_name == "GetLayout":
                self._get_layout(parameters, invocation)
            elif method_name == "Event":
                self._event(parameters, invocation)
            elif method_name == "GetGroupProperties":
                self._get_group_properties(parameters, invocation)
            elif method_name == "AboutToShow":
                invocation.return_value(GLib.Variant("(b)", (False,)))
            else:
                logger.warning("Método DBusMenu no soportado: %s", method_name)
                invocation.return_value(None)
        except Exception:
            logger.exception("Error en DBusMenu.%s — respondiendo con error", method_name)
            try:
                invocation.return_value(None)
            except Exception:
                pass

    def _handle_property_get(self, connection, sender, object_path,
                             interface_name, key):
        """Retorna propiedades D-Bus bajo demanda."""
        try:
            props = {
                "Version": GLib.Variant("u", 3),
                "Status": GLib.Variant("s", "normal"),
            }
            return props.get(key)
        except Exception:
            logger.exception("Error en property get DBusMenu: %s", key)
            return None

    def _get_layout(self, params, invocation):
        """Devuelve la estructura completa del menú (método GetLayout).

        Usa GLib.Variant.parse con formato de texto de GVariant para
        evitar problemas de anidamiento de variantes en PyGObject.
        Este enfoque delega toda la construcción a GLib nativo (C).

        Formato de retorno: (u(ia{sv}av))
        """
        parent_id, _depth, _prop_names = params.unpack()
        child_nodes = []

        if parent_id == 0:
            for item_def in self._items:
                item_id, label, icon, is_sep = item_def
                if item_id is None:
                    node = _build_menu_node(0, "", "", True, [])
                else:
                    node = _build_menu_node(item_id, label, icon, is_sep, [])
                child_nodes.append(node)

        # Construir el texto del layout completo en formato GVariant.
        # Cada hijo va envuelto en <...> porque av es array de variants.
        props_text = _format_vardict_text(_build_root_props())
        children_text = ", ".join(
            f"<{node.print_(True)}>" for node in child_nodes
        )

        layout_text = (
            f"({self._revision}, "
            f"(0, {props_text}, [{children_text}]))"
        )

        try:
            result = GLib.Variant.parse(
                GLib.VariantType.new("(u(ia{sv}av))"),
                layout_text,
            )
            invocation.return_value(result)
        except Exception:
            logger.exception("Error al construir GetLayout con Variant.parse")
            invocation.return_value(None)

    def _event(self, params, invocation):
        """Maneja clics en ítems del menú (método Event).

        Espera: (id:i, eventId:s, data:v, timestamp:u).
        """
        item_id, event_id, _data, _timestamp = params.unpack()
        logger.debug("Evento DBusMenu: id=%d, event=%s", item_id, event_id)
        if event_id == "clicked":
            self._dispatch_action(item_id)
        invocation.return_value(None)

    def _get_group_properties(self, params, invocation):
        """Retorna propiedades para un grupo de ítems."""
        _ids, _prop_names = params.unpack()
        # Retornar array vacío — no implementamos propiedades por grupo
        invocation.return_value(GLib.Variant("(a(ia{sv}))", ([],)))

    def _dispatch_action(self, item_id: int) -> None:
        """Ejecuta el callback correspondiente al ítem cliqueado.

        Usa GLib.idle_add para ejecutar en el hilo principal de GTK.

        Args:
            item_id: ID del ítem que recibió el clic.
        """
        if item_id == self.ITEM_SHOW and self._on_show:
            GLib.idle_add(self._on_show)
        elif item_id == self.ITEM_HIDE and self._on_hide:
            GLib.idle_add(self._on_hide)
        elif item_id == self.ITEM_QUIT and self._on_quit:
            GLib.idle_add(self._on_quit)

    def cleanup(self) -> None:
        """Libera recursos D-Bus al cerrar la aplicación."""
        if self._reg_id != 0:
            self._connection.unregister_object(self._reg_id)
            self._reg_id = 0
            logger.debug("DBusMenu liberado")
