"""Notificador de alertas climáticas vía D-Bus.

Usa el protocolo org.freedesktop.Notifications para enviar
notificaciones de escritorio nativas, compatible con GNOME, KDE,
XFCE y otros entornos de escritorio.

Se integra con el motor de alertas (engine.py) para notificar
al usuario cuando se detectan condiciones climáticas peligrosas.
"""

import logging

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib  # noqa: E402

from meteowatch.alerts.rules import Alert

logger = logging.getLogger(__name__)

# Constantes del protocolo de notificaciones D-Bus
NOTIFICATIONS_BUS = "org.freedesktop.Notifications"
NOTIFICATIONS_PATH = "/org/freedesktop/Notifications"
NOTIFICATIONS_IFACE = "org.freedesktop.Notifications"

# Mapeo de nivel de alerta a urgencia de notificación
# 0=low, 1=normal, 2=critical
URGENCY_MAP = {
    "yellow": 1,
    "orange": 2,
}

# Iconos para cada nivel de alerta
LEVEL_PREFIX = {
    "yellow": "⚠️ ",
    "orange": "🔴 ",
}

# Tiempo de expiración de la notificación en milisegundos
NOTIFICATION_TIMEOUT = 12000  # 12 segundos


def send_alert_notification(alert: Alert) -> None:
    """Envía una notificación de escritorio para una alerta climática.

    Args:
        alert: La alerta a notificar, con level, category y message.
    """
    try:
        _send_notification(alert)
    except Exception:
        logger.exception("Error al enviar notificación de alerta: %s", alert)


def send_alerts(alerts: list[Alert]) -> None:
    """Envía notificaciones para una lista de alertas.

    Cada alerta se envía como una notificación independiente con una
    pequeña pausa entre ellas para evitar saturar el sistema.

    Args:
        alerts: Lista de alertas a notificar.
    """
    if not alerts:
        return

    logger.info("Enviando %d notificaciones de alerta...", len(alerts))
    for alert in alerts:
        send_alert_notification(alert)


def _send_notification(alert: Alert) -> None:
    """Envía una notificación individual usando D-Bus.

    Usa Gio.DBusConnection para llamar al método Notify del servicio
    org.freedesktop.Notifications.

    Args:
        alert: La alerta a notificar.
    """
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio  # noqa: E402

    prefix = LEVEL_PREFIX.get(alert.level, "")
    urgency_byte = URGENCY_MAP.get(alert.level, 1)
    summary = f"Meteowatch — {prefix}Alerta {alert.level.title()}"
    body = alert.message

    # Construir hints: dict de string → variant
    hints_dict = {
        "urgency": GLib.Variant("y", urgency_byte),
        "desktop-entry": GLib.Variant("s", "com.meteowatch.app"),
    }

    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        # Construir la variante completa usando new_tuple para evitar
        # problemas de anidamiento con a{sv} dentro de la tupla
        variant = GLib.Variant.new_tuple(
            GLib.Variant("s", "Meteowatch"),           # app_name
            GLib.Variant("u", 0),                       # replaces_id
            GLib.Variant("s", ""),                      # app_icon
            GLib.Variant("s", summary),                 # summary
            GLib.Variant("s", body),                    # body
            GLib.Variant("as", []),                     # actions
            GLib.Variant("a{sv}", hints_dict),          # hints
            GLib.Variant("i", NOTIFICATION_TIMEOUT),    # expire_timeout
        )

        result = connection.call_sync(
            NOTIFICATIONS_BUS,
            NOTIFICATIONS_PATH,
            NOTIFICATIONS_IFACE,
            "Notify",
            variant,
            None,                  # reply_type
            Gio.DBusCallFlags.NONE,
            -1,                    # timeout_ms (-1 = default)
            None,                  # cancellable
        )

        if result is not None:
            notification_id = result.unpack()[0]
            logger.debug(
                "Notificación enviada (id=%s): category=%s, level=%s",
                notification_id, alert.category, alert.level,
            )
        else:
            logger.warning("No se recibió respuesta del servicio de notificaciones")

    except Exception:
        logger.exception(
            "Error D-Bus al enviar notificación: category=%s, level=%s",
            alert.category, alert.level,
        )
