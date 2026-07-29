## Why

La aplicación actualmente tiene dos rutas independientes de fetching de datos meteorológicos (UI y refresco periódico) sin cache compartida. El refresco horario solo actualiza el icono del tray y las alertas, ignorando la UI. Esto genera llamadas redundantes a la API, datos inconsistentes entre componentes, y una experiencia de usuario deficiente sin indicador de frescura ni tolerancia a fallos de red.

## What Changes

- **Nuevo `ForecastService`** como única fuente de verdad para los datos del pronóstico, con cache en memoria y TTLs diferenciados (15 min para `current`, 1h para `forecast` completo).
- **Patrón observer**: UI, tray y alertas se suscriben al servicio y reaccionan a cambios sin conocimiento del fetching.
- **Dos timers independientes**: uno cada 15 minutos para condiciones actuales (tray) y otro cada 1 hora para el forecast completo (daily + hourly + alertas).
- **Refresco transparente de UI**: si el usuario está en la página diaria u horaria y llegan datos nuevos, la UI se reconstruye automáticamente solo si hay cambios.
- **Indicador sutil de frescura**: label "Actualizado hace X min" al pie de la página diaria, con cambio de color si los datos envejecen (>1h amarillo, >3h naranja).
- **Modo offline con cache**: si la API falla y hay datos en cache, se muestran los datos cacheados con un indicador de "Sin conexión" usando un emoji distinto al de alertas (🔌).
- **Control de concurrencia**: evita fetches simultáneos y condiciones de carrera.
- **Reintentos con backoff**: si la API falla, se reintenta con backoff exponencial antes del próximo ciclo programado.

## Capabilities

### New Capabilities

- `forecast-service`: Servicio centralizado de datos meteorológicos con cache, TTLs, control de concurrencia, reintentos y patrón observer para notificar cambios a suscriptores (UI, tray, alertas).
- `offline-resilience`: Tolerancia a fallos de red usando cache como fallback, con indicador visual de desconexión.

### Modified Capabilities

<!-- No hay specs existentes que modificar. -->

## Impact

- **Nuevo archivo**: `meteowatch/services/__init__.py` (paquete de servicios)
- **Nuevo archivo**: `meteowatch/services/forecast.py` (`ForecastCache`, `ForecastService`, `ForecastObserver`)
- **Modificado**: `meteowatch/window.py` — los timers delegan en `ForecastService`, la ventana se suscribe para tray y alertas
- **Modificado**: `meteowatch/widgets/daily_card.py` — se suscribe al servicio, añade label "Actualizado hace X min"
- **Modificado**: `meteowatch/widgets/hourly_panel.py` — se suscribe al servicio para recibir actualizaciones
- **Sin cambios**: `meteowatch/api/client.py`, `meteowatch/models/`, `meteowatch/config.py`, `meteowatch/alerts/engine.py`
- **Nuevos tests**: `tests/test_forecast_service.py`
