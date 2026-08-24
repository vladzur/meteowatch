## 1. Estructura del módulo

- [x] 1.1 Crear paquete `meteowatch/report/` con `__init__.py` vacío
- [x] 1.2 Crear `meteowatch/report/engine.py` con la clase `ReportEngine` (esqueleto: `__init__`, `is_available`, `build_prompt`, `_call_api`, `parse_response`, `generate`)
- [x] 1.3 Crear `tests/test_report_engine.py` con los imports y estructura de tests

## 2. Lógica de generación del prompt

- [x] 2.1 Implementar `ReportEngine.build_prompt(daily, hourly, current)` que construya un prompt en español con los datos estructurados del pronóstico
- [x] 2.2 Incluir en el prompt: resumen diario (máx/min, precip, viento, código WMO), datos horarios relevantes, instrucciones de tono y restricción de no alucinar
- [x] 2.3 Implementar tests para `build_prompt`: verificar que el prompt contiene los valores de los datos de entrada, está en español, y no contiene valores inventados

## 3. Integración con API de DeepSeek

- [x] 3.1 Implementar `ReportEngine._call_api(prompt)` que llame a `api.deepseek.com/v1/chat/completions` con el modelo `deepseek-chat`
- [x] 3.2 Implementar `ReportEngine.parse_response(api_json)` que extraiga `choices[0].message.content`
- [x] 3.3 Implementar `ReportEngine.is_available()` que verifique `DEEPSEEK_API_KEY` en `os.environ`
- [x] 3.4 Implementar tests para `parse_response` con una respuesta JSON mock de DeepSeek
- [x] 3.5 Implementar tests para `is_available` con y sin la variable de entorno configurada

## 4. Cache del reporte

- [x] 4.1 Implementar cache en `ReportEngine`: atributos `_cached_report`, `_cached_forecast_at`, método `_invalidate_cache()`
- [x] 4.2 Implementar `ReportEngine.generate(daily, hourly, current)` con lógica de cache: si el forecast no cambió, retornar cache; si cambió, llamar a la API
- [x] 4.3 Implementar fallback cuando no hay datos (`ForecastService.has_data() == False`): retornar mensaje genérico
- [x] 4.4 Implementar fallback cuando la API falla (timeout, HTTP error): retornar mensaje genérico basado en datos
- [x] 4.5 Implementar tests para el cache: verificar que se reutiliza con mismos datos, se invalida con datos nuevos

## 5. Widget de reporte en la UI

- [x] 5.1 Crear `meteowatch/widgets/report_card.py` con la clase `WeatherReportCard(Gtk.Box)`
- [x] 5.2 Implementar la UI del widget: `Gtk.Label` con wrapping en `Gtk.ScrolledWindow`, `Gtk.Spinner`, botón "Generar reporte"
- [x] 5.3 Conectar el botón a `ReportEngine.generate()` ejecutado en un hilo con `GLib.Thread` para no bloquear la UI
- [x] 5.4 Implementar período de enfriamiento de 60 segundos en el botón de regeneración
- [x] 5.5 Implementar ocultamiento del widget cuando `ReportEngine.is_available() == False`
- [x] 5.6 Implementar tests de existencia de métodos del widget (`hasattr` + `callable`)

## 6. Integración en la ventana principal

- [x] 6.1 Instanciar `ReportEngine` en `MeteowatchWindow.__init__()` (solo si `is_available()`)
- [x] 6.2 Agregar `WeatherReportCard` a la vista de pronóstico diario (`DailyForecastPage`) o a la ventana principal
- [x] 6.3 Conectar `ForecastService.on_forecast_updated` a la invalidación del cache del reporte
- [x] 6.4 Implementar tests de integración para verificar que `WeatherReportCard` se integra sin errores de importación

## 7. Pruebas y validación final

- [x] 7.1 Ejecutar todos los tests existentes para verificar que no hay regresiones
- [x] 7.2 Ejecutar los nuevos tests de `test_report_engine.py` y verificar que pasan
- [x] 7.3 Verificar que la app arranca sin errores con `DEEPSEEK_API_KEY` no configurada (la sección de reporte no aparece)
- [x] 7.4 Verificar que la app arranca sin errores con `DEEPSEEK_API_KEY` configurada (la sección de reporte aparece)
