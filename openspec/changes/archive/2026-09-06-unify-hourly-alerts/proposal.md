## Why

Hoy conviven dos sistemas de alerta paralelos: `AlertEngine` genera la lista completa de alertas climáticas (códigos WMO, ráfagas de viento, inundación repentina, heladas, calor y lluvia diaria) para las notificaciones de escritorio y el banner de la página diaria, mientras que el panel por hora duplica el umbral de viento con una comprobación hardcodeada (`wind_gust >= 50`) y solo muestra la alerta de viento. Esto genera lógica duplicada y deja fuera del desglose horario al resto de alertas.

## What Changes

- Añadir una función pura única `get_hour_alerts(hour)` en `meteowatch/alerts/rules.py` que evalúe una hora contra todas las reglas de alerta horarias (códigos WMO, viento, inundación, heladas y calor).
- Refactorizar `AlertEngine` para que agregue sus alertas a partir de esa función unificada, conservando las ventanas de evaluación, la alerta diaria de lluvia y la deduplicación (las notificaciones siguen agregadas).
- Refactorizar el desglose por hora (`HourlyForecastPage._build_hour_row`) para usar la función unificada y mostrar en cada hora afectada un icono de alerta (⚠️ amarillo / 🔴 naranja) con tooltip descriptivo.
- Eliminar la comprobación duplicada `wind_gust >= 50` del panel por hora.

## Capabilities

### New Capabilities
- `alerts`: reglas de alerta climática unificadas por hora y su visualización en el desglose horario.

### Modified Capabilities
<!-- Sin cambios de requisitos en specs existentes. -->

## Impact

- `meteowatch/alerts/rules.py`: nueva función pura `get_hour_alerts` (fuente única de verdad de reglas horarias).
- `meteowatch/alerts/engine.py`: `AlertEngine.evaluate` pasa a agregar sobre `get_hour_alerts`.
- `meteowatch/alerts/__init__.py`: exportar `get_hour_alerts`.
- `meteowatch/widgets/hourly_panel.py`: `_build_hour_row` usa la función unificada y renderiza icono + tooltip.
- `tests/test_alerts.py` y `tests/test_hourly_panel.py`: tests nuevos/actualizados.
