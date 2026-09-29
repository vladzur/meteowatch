## 1. Configuración de la llave DeepSeek

- [x] 1.1 Añadir el campo `deepseek_api_key` a `AppConfig` en `meteowatch/config.py`
- [x] 1.2 Leer y persistir `deepseek_api_key` en `load()` y `save()`

## 2. Motor de reportes

- [x] 2.1 Aceptar `api_key` por constructor en `ReportEngine` con precedencia sobre la variable de entorno
- [x] 2.2 Convertir `is_available()` a método de instancia
- [x] 2.3 Añadir `set_api_key()` para actualización en runtime con invalidación de cache

## 3. Navegación horaria por día

- [x] 3.1 Propagar `day_start` desde `_show_hourly_forecast` en `window.py` y guardar `self._daily_page`
- [x] 3.2 Crear `ReportEngine` siempre con la llave del config y pasarlo a `DailyForecastPage`
- [x] 3.3 Añadir `apply_settings()` en `window.py`
- [x] 3.4 Aceptar `day_start` en `HourlyForecastPage` y añadir el helper `_day_start_of`
- [x] 3.5 Filtrar horas por día y titular la página según el día seleccionado
- [x] 3.6 Reemplazar `_on_24h_clicked` por `_on_day_clicked` y hacer clicables las tarjetas
- [x] 3.7 Añadir `set_report_engine()` en `DailyForecastPage`

## 4. Grilla de 2 columnas y estilos

- [x] 4.1 Reemplazar la lista vertical por `Gtk.Grid` con "Hoy" ocupando 2 columnas
- [x] 4.2 Añadir la clase `.today-card` a la tarjeta de hoy
- [x] 4.3 Añadir el CSS `.card-button` y `.today-card` en `app.py`

## 5. Diálogo de preferencias

- [x] 5.1 Crear `meteowatch/widgets/settings.py` con la clase `SettingsDialog`
- [x] 5.2 Registrar la acción `preferences` en `MeteowatchApp` y abrir el diálogo al guardar
- [x] 5.3 Añadir el ítem "Preferencias" al `Gio.Menu` de la vista diaria

## 6. Tests

- [x] 6.1 Tests de `deepseek_api_key` en `tests/test_config.py`
- [x] 6.2 Actualizar `TestIsAvailable` y añadir tests de precedencia en `tests/test_report_engine.py`
- [x] 6.3 Tests de `_day_start_of` en `tests/test_hourly_panel.py`
- [x] 6.4 Reemplazar `test_has_on_24h_clicked` y añadir tests de métodos nuevos en `tests/test_widgets_integration.py`

## 7. Documentación y verificación

- [x] 7.1 Actualizar `README.md` (layout y configuración de la llave)
- [x] 7.2 Ejecutar `pytest` y lint en verde
