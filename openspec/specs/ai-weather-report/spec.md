# ai-weather-report Specification

## Purpose

Generación de reportes meteorológicos narrativos usando DeepSeek como motor de IA. El sistema construye un prompt estructurado a partir de los datos del ForecastService (daily + hourly + current), consulta la API de DeepSeek y presenta el informe en un diálogo modal con opción de copiar al portapapeles.

## Requirements
### Requirement: Disponibilidad condicional del motor de reportes

El sistema SHALL verificar la presencia de la variable de entorno `DEEPSEEK_API_KEY` al iniciar. Si la variable no está definida o está vacía, el motor de reportes DEBE reportar `is_available() == False` y la UI NO DEBE mostrar la sección de reporte.

#### Scenario: API key configurada

- **WHEN** la variable de entorno `DEEPSEEK_API_KEY` contiene un valor no vacío
- **THEN** `ReportEngine.is_available()` retorna `True` y la UI muestra la sección "Reporte del tiempo"

#### Scenario: API key no configurada

- **WHEN** la variable de entorno `DEEPSEEK_API_KEY` no está definida o está vacía
- **THEN** `ReportEngine.is_available()` retorna `False` y la UI oculta completamente la sección de reporte sin mostrar errores

### Requirement: Generación de reporte a partir del ForecastService

El sistema SHALL generar un reporte meteorológico narrativo en español neutro tomando como entrada los datos cacheados del `ForecastService` (daily, hourly y current). El reporte DEBE ser generado mediante una llamada a la API de DeepSeek (`api.deepseek.com/v1/chat/completions`) usando el modelo `deepseek-chat`.

#### Scenario: Generación exitosa de reporte

- **WHEN** se solicita generar un reporte y `ForecastService` tiene datos frescos (daily, hourly, current)
- **THEN** el sistema construye un prompt con los datos meteorológicos estructurados, llama a la API de DeepSeek, y retorna el texto del reporte generado

#### Scenario: Generación sin datos disponibles

- **WHEN** se solicita generar un reporte pero `ForecastService` no tiene datos (`has_data() == False`)
- **THEN** el sistema retorna un mensaje indicando que no hay datos de pronóstico disponibles para generar el reporte

#### Scenario: Error de red o API

- **WHEN** la llamada a la API de DeepSeek falla por timeout, error HTTP o error de red
- **THEN** el sistema retorna un mensaje de fallback genérico basado en los datos disponibles, sin mostrar errores técnicos al usuario

### Requirement: Cache del reporte generado

El sistema SHALL cachear el reporte generado en memoria y reutilizarlo mientras los datos del forecast no hayan sido refrescados. Al detectar nuevos datos del forecast (vía observer `on_forecast_updated`), el cache DEBE invalidarse.

#### Scenario: Reporte cacheado se reutiliza

- **WHEN** se solicita un reporte y ya existe un reporte cacheado generado con los mismos datos de forecast
- **THEN** el sistema retorna el reporte desde cache sin llamar a la API de DeepSeek

#### Scenario: Cache invalidado al refrescar forecast

- **WHEN** `ForecastService` notifica `on_forecast_updated` con datos nuevos
- **THEN** el cache del reporte se invalida y la próxima solicitud generará un nuevo reporte

### Requirement: Widget de reporte en la UI

El sistema SHALL proporcionar un widget `WeatherReportCard` con un expander que contiene el botón para generar el reporte y un indicador de carga. Al completarse la generación, el sistema DEBE abrir un diálogo modal `WeatherReportDialog` que muestre el texto completo del reporte con scroll, un botón "Copiar" para copiar al portapapeles y un botón "Cerrar".

#### Scenario: Mostrar reporte en diálogo

- **WHEN** el reporte ha sido generado exitosamente
- **THEN** se abre un `WeatherReportDialog` modal centrado en la ventana padre, con el texto completo del reporte en un `Gtk.Label` con scroll, y los botones "Copiar" y "Cerrar"

#### Scenario: Copiar reporte al portapapeles

- **WHEN** el usuario presiona el botón "Copiar" en el diálogo de reporte
- **THEN** el texto del reporte se copia al portapapeles del sistema y el botón muestra "¡Copiado!" como feedback durante 1.5 segundos

#### Scenario: Generación en progreso

- **WHEN** el usuario presiona el botón "Generar reporte" y la generación comienza
- **THEN** el botón se deshabilita, se muestra un `Gtk.Spinner` animado, y el label muestra "Generando reporte..."

#### Scenario: Botón deshabilitado tras generación reciente

- **WHEN** el usuario presiona "Generar reporte" y han transcurrido menos de 60 segundos desde la última generación
- **THEN** el botón permanece deshabilitado hasta que transcurra el período de enfriamiento

### Requirement: Prompt en español neutro y sin alucinaciones

El prompt enviado a DeepSeek SHALL incluir instrucciones explícitas para: (a) generar el reporte en español neutro, (b) usar un tono amigable y claro sin jerga técnica, (c) no inventar datos ni condiciones meteorológicas que no estén en los datos proporcionados, y (d) estructurar el reporte en párrafos cortos con un resumen general, detalle por días, y recomendaciones prácticas.

#### Scenario: Reporte generado en español neutro

- **WHEN** se envía el prompt a DeepSeek con datos de ejemplo que incluyen temperatura máxima de 30°C y mínima de 18°C
- **THEN** el reporte retornado DEBE estar en español neutro (sin regionalismos argentinos como "re caluroso", "posta", "che") y DEBE mencionar correctamente los valores de temperatura proporcionados

#### Scenario: Sin invención de datos

- **WHEN** se envía el prompt a DeepSeek con datos que NO incluyen información de nieve
- **THEN** el reporte retornado NO DEBE mencionar nieve ni condiciones invernales que no estén en los datos

### Requirement: Testeabilidad del motor de reportes

El motor de reportes SHALL ser testeable sin depender de una API key real ni de conexión a Internet. La lógica de construcción del prompt y el parseo de la respuesta DEBEN ser funciones puras testeables unitariamente.

#### Scenario: Construcción del prompt sin efectos secundarios

- **WHEN** se llama a `ReportEngine.build_prompt(daily, hourly, current)` con datos de prueba
- **THEN** la función retorna un string que contiene los valores de temperatura, precipitación y códigos WMO de los datos proporcionados, sin realizar llamadas de red

#### Scenario: Parseo de respuesta exitosa

- **WHEN** se llama a `ReportEngine.parse_response(api_json)` con una respuesta JSON válida de DeepSeek
- **THEN** la función extrae y retorna el texto del reporte del campo `choices[0].message.content`
