## Why

Meteowatch actualmente muestra datos meteorológicos en forma numérica y gráfica (tarjetas diarias, tabla horaria, iconos), pero no ofrece una interpretación narrativa del pronóstico. Los usuarios quieren un resumen escrito, claro y amigable, al estilo "hombre del tiempo", que traduzca los datos crudos en lenguaje natural y les ayude a planificar su día. La integración de DeepSeek como motor de IA permitirá generar estos informes de forma automatizada y contextual.

## What Changes

- Nuevo módulo `meteowatch/report/` con el motor de generación de reportes meteorológicos usando la API de DeepSeek
- El reporte se genera a partir de los datos ya cacheados por `ForecastService` (daily + hourly + current), sin llamadas adicionales a Open-Meteo
- Nueva sección en la UI (widget `WeatherReportCard`) con un expander para el botón de generación, integrado en la vista de pronóstico diario. El expander inicia expandido para visibilidad, y el reporte se abre en un diálogo modal (`WeatherReportDialog`) con botones de copiar y cerrar.
- El reporte se genera bajo demanda (botón "Generar reporte") o automáticamente al recibir datos frescos del `ForecastService`
- Cache local del reporte para evitar llamadas innecesarias a la API de DeepSeek (misma ventana de TTL que el forecast: 1 hora)
- La API key de DeepSeek se configura desde una variable de entorno (`DEEPSEEK_API_KEY`) y es opcional; si no está configurada, la funcionalidad se deshabilita sin errores

## Capabilities

### New Capabilities
- `ai-weather-report`: Generación de reportes meteorológicos narrativos usando DeepSeek para analizar los datos del pronóstico (daily + hourly + current) y producir un resumen textual amigable y claro para el usuario.

### Modified Capabilities
<!-- No se modifican requerimientos de specs existentes -->

## Impact

- **Nuevo código**: `meteowatch/report/` (módulo con `engine.py` para el prompt y llamado a API de DeepSeek)
- **UI**: nuevo widget `WeatherReportCard` en `meteowatch/widgets/report_card.py`
- **Dependencia externa**: `requests` (ya existe) para llamadas HTTP a la API de DeepSeek
- **Dependencia de servicio**: `ForecastService` — el reporte consume datos ya cacheados, sin modificar su contrato
- **Configuración**: nueva variable de entorno `DEEPSEEK_API_KEY`, sin cambios en `AppConfig`
- **Internacionalización**: el prompt enviado a DeepSeek se redacta en español para que el reporte generado esté en español neutro
