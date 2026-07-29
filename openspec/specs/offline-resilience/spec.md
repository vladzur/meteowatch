# offline-resilience Specification

## Purpose
TBD - created by archiving change forecast-service-refresh. Update Purpose after archive.
## Requirements
### Requirement: Fallback a cache en caso de error de red

El sistema SHALL mostrar datos cacheados cuando una llamada a la API falle y existan datos previos en cache. El indicador de frescura DEBE cambiar para reflejar el estado de desconexión, usando un emoji distinto al de alertas climáticas.

#### Scenario: Error de red con cache disponible

- **WHEN** una llamada a la API falla y hay datos en cache
- **THEN** la UI muestra los datos cacheados y el indicador muestra "🔌 Sin conexión — hace X min" en color gris

#### Scenario: Error de red sin cache disponible

- **WHEN** una llamada a la API falla y no hay datos en cache (primer inicio sin conexión)
- **THEN** la UI muestra el mensaje de error estándar, sin datos de pronóstico

#### Scenario: Recuperación tras reconexión

- **WHEN** la API vuelve a responder después de un período de desconexión
- **THEN** el indicador de desconexión desaparece y se restaura el indicador normal "🕐 Actualizado hace X min"

### Requirement: Emoji de desconexión distinto al de alertas

El sistema SHALL usar el emoji 🔌 (electric plug) para indicar falta de conexión, DEBE ser visualmente distinto de ⚠️ (warning) y 🔴 (red circle) usados para alertas climáticas.

#### Scenario: El usuario distingue desconexión de alerta

- **WHEN** el indicador muestra "🔌 Sin conexión"
- **THEN** el emoji es claramente diferente al usado en notificaciones de alerta climática, evitando confusión

### Requirement: Notificación de error a observers

El servicio SHALL notificar a los observers suscritos cuando ocurre un error de fetch, indicando si hay datos cacheados disponibles.

#### Scenario: Notificación de error con cache

- **WHEN** un fetch falla y hay datos en cache
- **THEN** los observers reciben `on_forecast_error(mensaje, cached=True)`

#### Scenario: Notificación de error sin cache

- **WHEN** un fetch falla y no hay datos en cache
- **THEN** los observers reciben `on_forecast_error(mensaje, cached=False)`

