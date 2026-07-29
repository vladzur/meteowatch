# forecast-service Specification

## Purpose
TBD - created by archiving change forecast-service-refresh. Update Purpose after archive.
## Requirements
### Requirement: Servicio centralizado de pronóstico

El sistema SHALL proporcionar un `ForecastService` como única fuente de verdad para los datos meteorológicos. El servicio DEBE mantener un cache en memoria con TTLs diferenciados: 15 minutos para condiciones actuales (`current`) y 1 hora para el pronóstico completo (`forecast`: daily + hourly + current). Cualquier componente que necesite datos meteorológicos DEBE obtenerlos a través de este servicio.

#### Scenario: Primer fetch al iniciar la aplicación

- **WHEN** la aplicación se inicia y no hay datos en cache
- **THEN** el servicio realiza una llamada a la API de Open-Meteo y almacena `current`, `daily` y `hourly` en cache con sus timestamps correspondientes

#### Scenario: Fetch desde cache cuando los datos están frescos

- **WHEN** un componente solicita el forecast y el timestamp `forecast_at` tiene menos de 3600 segundos de antigüedad
- **THEN** el servicio devuelve los datos desde cache sin llamar a la API

#### Scenario: Fetch desde cache cuando current está fresco

- **WHEN** un componente solicita current y el timestamp `current_at` tiene menos de 900 segundos de antigüedad
- **THEN** el servicio devuelve `current` desde cache sin llamar a la API

#### Scenario: Refresco de current cuando está stale

- **WHEN** se solicita un refresco de current y el timestamp `current_at` supera los 900 segundos
- **THEN** el servicio realiza una llamada a la API y notifica a los observers suscritos al evento `"current"`

#### Scenario: Refresco de forecast cuando está stale

- **WHEN** se solicita un refresco de forecast y el timestamp `forecast_at` supera los 3600 segundos
- **THEN** el servicio realiza una llamada a la API y notifica a los observers suscritos al evento `"forecast"`

### Requirement: Patrón observer para notificaciones

El servicio SHALL permitir que componentes externos se suscriban como observers mediante una interfaz `ForecastObserver`. El servicio DEBE notificar a todos los observers suscritos cuando los datos se actualizan, diferenciando entre actualizaciones de `current` y de `forecast` completo.

#### Scenario: Suscripción de un observer

- **WHEN** un componente llama a `service.subscribe(observer)`
- **THEN** el observer es registrado y recibirá notificaciones de actualizaciones futuras

#### Scenario: Notificación de forecast actualizado

- **WHEN** el servicio completa un fetch exitoso del forecast completo
- **THEN** todos los observers suscritos reciben `on_forecast_updated(forecast_result)` con los datos nuevos

#### Scenario: Notificación de current actualizado

- **WHEN** el servicio completa un fetch exitoso motivado por staleness de current (pero no de forecast)
- **THEN** todos los observers suscritos reciben `on_current_updated(current)` con los datos nuevos

#### Scenario: Cancelación de suscripción

- **WHEN** un componente llama a `service.unsubscribe(observer)`
- **THEN** el observer deja de recibir notificaciones y no causa errores ni memory leaks

### Requirement: Refresco periódico con dos timers independientes

La aplicación SHALL ejecutar dos timers GLib independientes: uno cada 15 minutos (900 segundos) para condiciones actuales y otro cada 60 minutos (3600 segundos) para el pronóstico completo. Ambos timers DEBEN delegar en el `ForecastService` para la obtención de datos.

#### Scenario: Timer de current cada 15 minutos

- **WHEN** transcurren 900 segundos desde el último refresco de current
- **THEN** la aplicación llama a `ForecastService.refresh_current()` y el tray se actualiza con la nueva temperatura e icono

#### Scenario: Timer de forecast cada 1 hora

- **WHEN** transcurren 3600 segundos desde el último refresco de forecast
- **THEN** la aplicación llama a `ForecastService.refresh_forecast()`, la UI se reconstruye si hay cambios y se evalúan alertas climáticas

#### Scenario: Los timers no interfieren entre sí

- **WHEN** ambos timers coinciden en el mismo ciclo (múltiplo de 900 y 3600)
- **THEN** el control de concurrencia del servicio evita que se ejecuten simultáneamente

### Requirement: Control de concurrencia en fetches

El servicio SHALL garantizar que nunca haya más de un fetch HTTP en vuelo simultáneamente. Si se solicita un fetch mientras otro está en curso, el segundo DEBE esperar a que el primero termine o retornar inmediatamente si el primero ya satisface la necesidad de frescura.

#### Scenario: Fetch simultáneo bloqueado por lock

- **WHEN** un timer dispara un fetch mientras otro fetch ya está en vuelo
- **THEN** el segundo fetch espera a que el lock se libere, verifica si los datos ya están frescos, y omite la llamada si el primer fetch ya los actualizó

### Requirement: Refresco transparente de UI

La UI SHALL reconstruirse automáticamente al recibir datos actualizados del `ForecastService`, pero solo si los datos cambiaron respecto a la versión previamente mostrada. Si los datos son idénticos, solo DEBE actualizarse el indicador de frescura.

#### Scenario: Reconstrucción de daily cards al detectar cambios

- **WHEN** el `DailyForecastPage` recibe `on_forecast_updated` con datos nuevos
- **THEN** compara los días del forecast nuevo con los actuales; si hay diferencias, reconstruye las tarjetas

#### Scenario: Sin reconstrucción si los datos no cambiaron

- **WHEN** el `DailyForecastPage` recibe `on_forecast_updated` con datos idénticos a los actuales
- **THEN** solo se actualiza el label "Actualizado hace X min" sin tocar las tarjetas

#### Scenario: Reconstrucción de hourly panel al detectar cambios

- **WHEN** el `HourlyForecastPage` recibe `on_forecast_updated` con datos nuevos
- **THEN** compara las horas del forecast nuevo con las actuales; si hay diferencias, reconstruye la grilla horaria

### Requirement: Indicador visual de frescura

La página de pronóstico diario SHALL mostrar un indicador textual de la antigüedad de los datos en formato "Actualizado hace X min". El indicador DEBE actualizarse cada 60 segundos y DEBE cambiar de color según la antigüedad.

#### Scenario: Indicador normal con datos frescos

- **WHEN** los datos tienen menos de 1 hora de antigüedad
- **THEN** el label muestra "🕐 Actualizado hace X min" en color gris (clase `dim-label`)

#### Scenario: Indicador warning con datos entre 1 y 3 horas

- **WHEN** los datos tienen entre 1 y 3 horas de antigüedad
- **THEN** el label muestra el texto en color amarillo (#b58900)

#### Scenario: Indicador error con datos de más de 3 horas

- **WHEN** los datos tienen más de 3 horas de antigüedad
- **THEN** el label muestra el texto en color naranja (#cb4b16)

#### Scenario: Actualización del indicador cada minuto

- **WHEN** transcurren 60 segundos
- **THEN** el texto del indicador se recalcula para reflejar la antigüedad actual

### Requirement: Reintentos con backoff exponencial

El servicio SHALL reintentar automáticamente las llamadas fallidas a la API con backoff exponencial. Después de 3 reintentos fallidos, DEBE rendirse y esperar al próximo ciclo programado.

#### Scenario: Reintento tras fallo de red

- **WHEN** una llamada a la API falla por error de conexión
- **THEN** el servicio reintenta después de 30 segundos, luego 60 segundos, luego 120 segundos

#### Scenario: Rendición tras reintentos agotados

- **WHEN** los 3 reintentos fallan
- **THEN** el servicio notifica `on_forecast_error` a los observers y espera al próximo ciclo del timer

