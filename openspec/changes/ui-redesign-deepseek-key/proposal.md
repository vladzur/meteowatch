## Why

La interfaz principal de Meteowatch presenta la información de forma vertical y poco aprovechada, sin una jerarquía visual clara para el día actual. Además, la llave de DeepSeek solo puede configurarse mediante una variable de entorno, lo que resulta inviable para usuarios de Flatpak, y las tarjetas diarias prometen navegación (según el texto de Ayuda) pero no son clicables.

## What Changes

- Rediseño del layout diario: grilla de 2 columnas donde "Hoy" ocupa ambas columnas con un estilo destacado.
- **BREAKING**: se elimina el botón "Ver pronóstico de las próximas 24 horas" (queda reemplazado por las tarjetas clicables).
- Las tarjetas de día pasan a ser clicables y navegan al pronóstico por hora del día específico seleccionado.
- La pantalla horaria acepta un día concreto y muestra únicamente las horas de ese día.
- Nueva configuración `deepseek_api_key` persistida en `config.json`, con precedencia sobre la variable de entorno `DEEPSEEK_API_KEY`.
- Nuevo diálogo "Preferencias" (menú ☰) para configurar la llave de DeepSeek.

## Capabilities

### New Capabilities

- `ui-daily-forecast`: layout en grilla con "Hoy" destacado y navegación por clic en las tarjetas diarias hacia el pronóstico horario del día seleccionado.

### Modified Capabilities

- `ai-weather-report`: la disponibilidad del motor ahora depende de la llave guardada en configuración (con respaldo de variable de entorno) y se añade un diálogo de preferencias para gestionarla.

## Impact

- `meteowatch/config.py`: nuevo campo `deepseek_api_key` en `AppConfig`.
- `meteowatch/report/engine.py`: `ReportEngine` acepta la llave por constructor; `is_available()` pasa a método de instancia.
- `meteowatch/window.py`: propagación de `day_start` y aplicación de ajustes en runtime.
- `meteowatch/widgets/daily_card.py`: grilla, tarjetas clicables e ítem de menú "Preferencias".
- `meteowatch/widgets/hourly_panel.py`: filtrado del pronóstico por día.
- `meteowatch/widgets/settings.py` (nuevo): diálogo de preferencias.
- `meteowatch/app.py`: acción `preferences` y CSS para tarjetas destacadas.
- Tests y documentación (`README.md`).
