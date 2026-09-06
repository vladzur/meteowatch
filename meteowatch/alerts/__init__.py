"""Módulo de alertas climáticas y notificaciones.

Proporciona:
- AlertEngine: evalúa datos de pronóstico contra reglas configurables.
- Alert: NamedTuple con los datos de cada alerta detectada.
- send_alerts: envía notificaciones de escritorio vía D-Bus.
"""

from meteowatch.alerts.engine import AlertEngine
from meteowatch.alerts.rules import Alert, get_hour_alerts
from meteowatch.alerts.notifier import send_alert_notification, send_alerts

__all__ = [
    "Alert",
    "AlertEngine",
    "get_hour_alerts",
    "send_alert_notification",
    "send_alerts",
]
