# ai-weather-report Specification

## Purpose

Generación de reportes meteorológicos narrativos usando DeepSeek como motor de IA. El sistema construye un prompt estructurado a partir de los datos del ForecastService (daily + hourly + current), consulta la API de DeepSeek y presenta el informe en la tarjeta de reporte y en un diálogo modal con opción de copiar al portapapeles. La llave de API se configura desde un diálogo de preferencias.

## Requirements
### Requirement: Disponibilidad condicional del motor de reportes

El sistema SHALL determinar la disponibilidad del motor de reportes a partir de la llave de API de DeepSeek. La llave DEBE obtenerse primero desde la configuración persistente (`AppConfig.deepseek_api_key`) y, si está vacía, desde la variable de entorno `DEEPSEEK_API_KEY`. Si ninguna llave está configurada, el motor DEBE reportar `is_available() == False` y la UI NO DEBE mostrar la sección de reporte.

#### Scenario: API key configurada en la configuración persistente

- **WHEN** `AppConfig.deepseek_api_key` contiene un valor no vacío
- **THEN** `ReportEngine.is_available()` retorna `True` y la UI muestra la sección "Reporte del tiempo"

#### Scenario: API key configurada solo en variable de entorno

- **WHEN** `AppConfig.deepseek_api_key` está vacía y la variable de entorno `DEEPSEEK_API_KEY` contiene un valor no vacío
- **THEN** `ReportEngine.is_available()` retorna `True` y la UI muestra la sección "Reporte del tiempo"

#### Scenario: Precedencia de la configuración sobre la variable de entorno

- **WHEN** `AppConfig.deepseek_api_key` y la variable de entorno `DEEPSEEK_API_KEY` tienen valores distintos no vacíos
- **THEN** el motor usa la llave de `AppConfig.deepseek_api_key`

#### Scenario: API key no configurada

- **WHEN** `AppConfig.deepseek_api_key` está vacía y la variable de entorno `DEEPSEEK_API_KEY` no está definida o está vacía
- **THEN** `ReportEngine.is_available()` retorna `False` y la UI oculta completamente la sección de reporte sin mostrar errores

### Requirement: Diálogo de preferencias para la llave de DeepSeek

El sistema SHALL proporcionar un diálogo de preferencias (`SettingsDialog`) accesible desde el menú principal (☰) que permita al usuario ingresar y guardar la llave de API de DeepSeek. Al guardar, la llave DEBE persistirse en `AppConfig.deepseek_api_key` y la UI DEBE actualizarse para mostrar u ocultar la sección de reporte según la disponibilidad del motor.

#### Scenario: Guardar llave válida

- **WHEN** el usuario ingresa una llave no vacía y presiona "Guardar"
- **THEN** `AppConfig.deepseek_api_key` se actualiza, se persiste en `config.json` y la sección "Reporte del tiempo" se muestra

#### Scenario: Limpiar la llave

- **WHEN** el usuario deja el campo vacío y presiona "Guardar"
- **THEN** `AppConfig.deepseek_api_key` queda vacía y la sección "Reporte del tiempo" se oculta (salvo que exista `DEEPSEEK_API_KEY` en el entorno)

#### Scenario: Cancelar sin cambios

- **WHEN** el usuario presiona "Cancelar"
- **THEN** no se modifica `AppConfig.deepseek_api_key` ni se persiste ningún cambio

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

El sistema SHALL proporcionar un widget `WeatherReportCard` con un expander que contiene los botones para generar y visualizar el reporte, y un indicador de carga. Al completarse la generación, el sistema DEBE mostrar el reporte de forma persistente en la tarjeta y DEBE abrir un diálogo modal `WeatherReportDialog` con el texto completo, un botón "Copiar" y un botón "Cerrar". El sistema DEBE permitir volver a leer el último reporte generado sin realizar una nueva llamada a la API.

#### Scenario: Mostrar reporte en diálogo

- **WHEN** el reporte ha sido generado exitosamente
- **THEN** se abre un `WeatherReportDialog` modal centrado en la ventana padre, con el texto completo del reporte en un `Gtk.Label` con scroll, y los botones "Copiar" y "Cerrar"

#### Scenario: Reporte persistente en la tarjeta

- **WHEN** el reporte ha sido generado exitosamente
- **THEN** el texto del reporte se muestra de forma persistente en el área de scroll de la tarjeta y el botón de generación pasa a llamarse "Regenerar reporte"

#### Scenario: Releer el último reporte sin regenerar

- **WHEN** existe un reporte generado y el usuario presiona "Ver reporte"
- **THEN** se abre el `WeatherReportDialog` con el último reporte cacheado sin realizar una nueva llamada a la API de DeepSeek

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

El prompt enviado a DeepSeek SHALL incluir instrucciones explícitas para: (a) generar el reporte en español neutro, (b) dirigirse al usuario en segunda persona con un registro formal y profesional, evitando el estilo de presentador de noticiario, (c) no inventar datos ni condiciones meteorológicas que no estén en los datos proporcionados, y (d) estructurar el reporte con una introducción general, un análisis día por día con magnitudes concretas y recomendaciones prácticas específicas.

#### Scenario: Reporte generado en español neutro

- **WHEN** se envía el prompt a DeepSeek con datos de ejemplo que incluyen temperatura máxima de 30°C y mínima de 18°C
- **THEN** el reporte retornado DEBE estar en español neutro (sin regionalismos argentinos como "re caluroso", "posta", "che") y DEBE mencionar correctamente los valores de temperatura proporcionados

#### Scenario: Tono profesional dirigido al usuario

- **WHEN** se evalúa el prompt de sistema enviado a DeepSeek
- **THEN** DEBE instruir a dirigirse al usuario en segunda persona ("tú") con tono profesional y NO DEBE instruir un estilo de presentador de noticiario o televisión

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
