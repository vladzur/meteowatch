## Context

Meteowatch es una aplicación GTK 4 + libadwaita que consume la API gratuita de Open-Meteo para obtener pronósticos meteorológicos. Los datos se cachean en `ForecastService` con TTLs de 15 min (current) y 1 h (forecast). Actualmente, la UI muestra los datos en tarjetas diarias (`DailyForecastPage`) y una tabla horaria (`HourlyForecastPage`), pero no hay interpretación narrativa.

Se integrará la API de DeepSeek (`api.deepseek.com/v1/chat/completions`) para generar reportes textuales a partir de los datos ya cacheados. DeepSeek se elige por su excelente relación calidad/precio y su API compatible con OpenAI, lo que facilita la integración.

## Goals / Non-Goals

**Goals:**
- Generar un reporte meteorológico narrativo en español neutro a partir de los datos del `ForecastService`
- Integrar el reporte en la UI como una nueva sección dentro de la vista de pronóstico diario
- Minimizar llamadas a la API de DeepSeek mediante cache local (misma ventana de TTL que el forecast)
- Ser completamente opcional: sin API key configurada, la funcionalidad se deshabilita sin errores
- Mantener el prompt y la lógica de generación en un módulo independiente y testeable

**Non-Goals:**
- No se modificará el contrato de `ForecastService` ni se añadirán nuevos campos a los modelos de datos
- No se implementará streaming de la respuesta (se usará respuesta completa)
- No se soportarán múltiples idiomas en el reporte (solo español neutro)
- No se implementará historial de reportes ni persistencia en disco
- No se usará la API de DeepSeek para otra funcionalidad (solo generación de reportes)

## Decisions

### 1. Módulo independiente `meteowatch/report/`

**Decisión:** Crear un paquete `meteowatch/report/` con `engine.py` que contenga toda la lógica de generación del reporte (construcción del prompt, llamado HTTP, parseo de respuesta, cache).

**Alternativas consideradas:**
- Poner la lógica en `services/forecast.py`: rechazado porque mezcla responsabilidades (obtención de datos vs. análisis IA) y acoplaría el servicio de forecast a una dependencia externa opcional.
- Poner la lógica directamente en el widget: rechazado porque impide testear la lógica de generación sin UI.

### 2. API Key por variable de entorno

**Decisión:** Leer `DEEPSEEK_API_KEY` de `os.environ`. Sin ella, `ReportEngine.is_available()` retorna `False` y la UI oculta la sección de reporte.

**Alternativas consideradas:**
- Guardar en `AppConfig`: rechazado porque las API keys no deben persistirse en texto plano en `~/.config`.
- Pedirla al usuario en un diálogo: complejidad innecesaria para v1.

### 3. Prompt en español neutro con datos estructurados

**Decisión:** Construir un prompt que incluya los datos del pronóstico en formato estructurado (resumen diario: máx/min, precipitación, viento, código WMO) más los datos horarios relevantes, y pedir a DeepSeek que genere un informe en español neutro, tono amigable y claro, sin jerga técnica.

**Alternativas consideradas:**
- Enviar datos crudos JSON: la IA podría malinterpretar campos.
- Usar fine-tuning: excesivo para v1.

### 4. Cache del reporte alineado con forecast TTL

**Decisión:** El reporte generado se cachea en `ReportEngine` y se considera válido mientras el forecast del que se generó no haya cambiado. En la práctica, se invalida junto con el forecast (1 hora). Si el forecast se refresca, el reporte se regenera.

**Alternativas consideradas:**
- Regenerar siempre: desperdicio de créditos de API.
- TTL independiente: complejidad innecesaria.

### 5. Widget `WeatherReportCard` + `WeatherReportDialog`

**Decisión:** Un widget GTK con un `Gtk.Expander` (expandido por defecto) que contiene el botón "Generar reporte", spinner de carga e indicador de estado. El reporte generado se muestra en un **diálogo modal** (`WeatherReportDialog`) de 480×500px con área de texto completa con scroll, botón "Copiar" (copia al portapapeles con feedback visual) y botón "Cerrar".

**Alternativas consideradas:**
- Mostrar el texto incrustado en un `Gtk.ScrolledWindow` de altura fija (250px): rechazado por espacio insuficiente para leer reportes largos.
- Usar `Adw.MessageDialog`: no adecuado para textos extensos con formato.

## Risks / Trade-offs

- **[Riesgo] Latencia de la API de DeepSeek (2-5 segundos por request):** → La generación se hace en un hilo separado con `GLib.Thread` para no bloquear la UI. Se muestra un spinner durante la carga.
- **[Riesgo] Costo de API si el usuario regenera manualmente muchas veces:** → El botón de regeneración se deshabilita durante 60 segundos tras cada generación.
- **[Riesgo] La IA podría alucinar datos incorrectos:** → El prompt incluye instrucciones explícitas de no inventar datos y ceñirse solo a la información proporcionada.
- **[Riesgo] La respuesta de DeepSeek podría no ser parseable o venir vacía:** → Se implementa un fallback que muestra un mensaje genérico basado en los datos sin IA.
- **[Trade-off] Dependencia externa opcional:** → Si DeepSeek no está disponible (sin API key, sin red, error HTTP), la app sigue funcionando normalmente, solo sin reporte.
