## 1. Crear paquete de servicios

- [x] 1.1 Crear `meteowatch/services/__init__.py` como paquete Python vacío
- [x] 1.2 Crear `meteowatch/services/forecast.py` con `ForecastCache`, `ForecastObserver`, `ForecastService`

## 2. Implementar ForecastCache

- [x] 2.1 Implementar almacenamiento de `CurrentWeather`, `DailyForecast`, `HourlyForecast` con timestamps `_current_at` y `_forecast_at`
- [x] 2.2 Implementar método `is_current_stale() -> bool` (TTL=900s)
- [x] 2.3 Implementar método `is_forecast_stale() -> bool` (TTL=3600s)
- [x] 2.4 Implementar método `has_data() -> bool` para verificar si hay cache disponible
- [x] 2.5 Implementar método `get_age_minutes() -> float` que retorna la antigüedad en minutos del forecast

## 3. Implementar ForecastObserver (protocolo)

- [x] 3.1 Definir `ForecastObserver` como `Protocol` con métodos: `on_forecast_updated(forecast_result)`, `on_current_updated(current)`, `on_forecast_error(message, cached)`
- [x] 3.2 Implementar clase base `BaseForecastObserver` con implementaciones no-op de los tres métodos

## 4. Implementar ForecastService

- [x] 4.1 Implementar `__init__()` que crea `ForecastCache`, lista de observers y `threading.Lock`
- [x] 4.2 Implementar `subscribe(observer: ForecastObserver)` y `unsubscribe(observer: ForecastObserver)`
- [x] 4.3 Implementar `refresh_forecast()`: verifica staleness, llama API, actualiza cache, notifica observers vía `GLib.idle_add`
- [x] 4.4 Implementar `refresh_current()`: verifica staleness, llama API, actualiza cache, notifica observers vía `GLib.idle_add`
- [x] 4.5 Implementar control de concurrencia: `threading.Lock` para evitar fetches simultáneos; si otro fetch ya está en vuelo, esperar y verificar frescura antes de llamar a la API
- [x] 4.6 Implementar reintentos con backoff exponencial (30s, 60s, 120s, máx 3 intentos)
- [x] 4.7 Implementar `get_cached_forecast()` y `get_cached_current()` para acceso síncrono a datos cacheados

## 5. Integrar ForecastService en MeteowatchWindow

- [x] 5.1 Instanciar `ForecastService` en `MeteowatchApp.do_startup()` y pasar referencia a `MeteowatchWindow`
- [x] 5.2 Reemplazar los dos timers existentes por: timer de 900s para `refresh_current()`, timer de 3600s para `refresh_forecast()`
- [x] 5.3 Suscribir la lógica de tray al servicio: en `on_current_updated`, actualizar icono y temperatura; en `on_forecast_updated`, también actualizar
- [x] 5.4 Suscribir la lógica de alertas al servicio: en `on_forecast_updated`, evaluar `AlertEngine` y enviar notificaciones
- [x] 5.5 Remover `_start_refresh_thread()` y `_on_periodic_refresh()` antiguos
- [x] 5.6 Eliminar el callback `on_weather_updated` de `MeteowatchWindow` (reemplazado por suscripción al servicio)

## 6. Integrar ForecastService en DailyForecastPage

- [x] 6.1 Recibir `ForecastService` como parámetro en constructor (en lugar de crear `OpenMeteoClient` propio)
- [x] 6.2 Suscribirse al servicio como `BaseForecastObserver`; implementar `on_forecast_updated` y `on_forecast_error`
- [x] 6.3 Modificar `load_forecast()` para delegar en `ForecastService.refresh_forecast()` en lugar de fetch directo
- [x] 6.4 En `on_forecast_updated`: comparar datos nuevos con `self._forecast` actual, reconstruir UI solo si hay diferencias
- [x] 6.5 En `on_forecast_error(cached=True)`: mostrar datos cacheados con indicador de desconexión
- [x] 6.6 En `on_forecast_error(cached=False)`: mostrar mensaje de error como antes
- [x] 6.7 Añadir label `_freshness_label` al pie del `_main_box` con formato "🕐 Actualizado hace X min"
- [x] 6.8 Implementar timer local de 60s (`GLib.timeout_add_seconds`) para actualizar `_freshness_label`
- [x] 6.9 Implementar cambio de color del label según antigüedad: normal (<1h), warning amarillo (1-3h), error naranja (>3h)
- [x] 6.10 En modo offline (error con cache), cambiar label a "🔌 Sin conexión — hace X min" en gris

## 7. Integrar ForecastService en HourlyForecastPage

- [x] 7.1 Recibir `ForecastService` como parámetro en constructor
- [x] 7.2 Suscribirse al servicio como `BaseForecastObserver`; implementar `on_forecast_updated` y `on_forecast_error`
- [x] 7.3 Modificar `load_forecast()` para delegar en `ForecastService.refresh_forecast()`
- [x] 7.4 En `on_forecast_updated`: comparar datos nuevos con los actuales, reconstruir grilla solo si hay diferencias

## 8. Actualizar MeteowatchWindow para pasar ForecastService a las páginas

- [x] 8.1 Pasar `ForecastService` a `DailyForecastPage` en `_show_daily_forecast()`
- [x] 8.2 Pasar `ForecastService` a `HourlyForecastPage` en `_show_hourly_forecast()`

## 9. Tests

- [x] 9.1 Crear `tests/test_forecast_service.py` con tests unitarios para `ForecastCache`
- [x] 9.2 Añadir tests para `ForecastService`: suscripción, notificación, control de concurrencia
- [x] 9.3 Añadir tests para modo offline: fallback a cache, error sin cache
- [x] 9.4 Añadir tests para reintentos con backoff (mock de requests)
- [x] 9.5 Añadir tests para `DailyForecastPage` con `ForecastService` mockeado: frescura, colores, modo offline (`tests/test_widgets_integration.py`)
- [x] 9.6 Actualizar tests existentes de `test_tray_icon.py` y `test_hourly_panel.py` si es necesario

## 10. Limpieza

- [x] 10.1 Remover imports y referencias a `OpenMeteoClient` de `daily_card.py` y `hourly_panel.py` si ya no se usan directamente
- [x] 10.2 Verificar que `meteowatch/api/client.py` no necesita cambios (debe permanecer intacto)
- [x] 10.3 Ejecutar linters y corregir advertencias
- [x] 10.4 Ejecutar todos los tests para verificar que nada se rompió
