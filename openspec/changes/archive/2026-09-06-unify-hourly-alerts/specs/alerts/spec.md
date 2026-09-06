## ADDED Requirements

### Requirement: Reglas de alerta unificadas por hora

El sistema SHALL proporcionar una función pura `get_hour_alerts(hour)` en `meteowatch/alerts/rules.py` que evalúe una única hora del pronóstico contra todas las reglas de alerta horarias (códigos WMO, ráfagas de viento, inundación repentina, heladas y calor) y retorne la lista de alertas aplicables. Ningún otro componente DEBE duplicar umbrales ni reglas de alerta.

#### Scenario: Hora con ráfaga sobre el umbral amarillo
- **WHEN** una hora tiene `wind_gust` mayor a `WIND_GUST_YELLOW` y menor o igual a `WIND_GUST_ORANGE`
- **THEN** `get_hour_alerts` retorna una alerta `wind` de nivel `yellow` con `value` igual a la ráfaga

#### Scenario: Hora con ráfaga sobre el umbral naranja
- **WHEN** una hora tiene `wind_gust` mayor a `WIND_GUST_ORANGE`
- **THEN** `get_hour_alerts` retorna una alerta `wind` de nivel `orange`

#### Scenario: Hora con código WMO de tormenta
- **WHEN** una hora tiene un `symbol` en `WMO_ORANGE_CODES`
- **THEN** `get_hour_alerts` retorna una alerta de nivel `orange` con `source_code` igual al código WMO

#### Scenario: Hora con precipitación torrencial
- **WHEN** una hora tiene `precipitation` mayor a `FLASH_FLOOD_ORANGE`
- **THEN** `get_hour_alerts` retorna una alerta `flash_flood` de nivel `orange`

#### Scenario: Hora con helada o calor extremo
- **WHEN** una hora tiene `temperature_feels_like` menor a `FROST_YELLOW` o mayor a `HEAT_YELLOW`
- **THEN** `get_hour_alerts` retorna la alerta correspondiente (`frost` o `heat`) de nivel `yellow`

#### Scenario: Hora sin condiciones de alerta
- **WHEN** una hora no supera ningún umbral ni contiene códigos WMO de alerta
- **THEN** `get_hour_alerts` retorna una lista vacía

#### Scenario: Hora con múltiples condiciones
- **WHEN** una hora supera varios umbrales a la vez
- **THEN** `get_hour_alerts` retorna todas las alertas aplicables a esa hora

### Requirement: El motor de alertas usa la fuente unificada

El `AlertEngine` SHALL generar sus alertas agregadas a partir de `get_hour_alerts`, manteniendo las ventanas de evaluación (`HOURS_WINDOW` y `FLASH_FLOOD_WINDOW`), la alerta diaria de lluvia y la deduplicación por categoría y nivel.

#### Scenario: Notificaciones agregadas por nivel
- **WHEN** varias horas superan el mismo umbral de viento en la ventana de evaluación
- **THEN** `AlertEngine.evaluate` retorna una única alerta de viento por nivel, no una por hora

#### Scenario: Inundación evaluada en su ventana propia
- **WHEN** una hora con precipitación torrencial queda fuera de `FLASH_FLOOD_WINDOW`
- **THEN** `AlertEngine.evaluate` no genera la alerta de inundación para esa hora

#### Scenario: Lluvia diaria sigue evaluándose
- **WHEN** la precipitación acumulada del día supera `DAILY_RAIN_YELLOW`
- **THEN** `AlertEngine.evaluate` retorna la alerta `daily_rain` aunque no sea de granularidad horaria

### Requirement: Alertas por hora en el desglose horario

La página `HourlyForecastPage` SHALL mostrar en cada fila horaria un indicador de alerta cuando `get_hour_alerts(hour)` retorne alertas, con un icono (🔴 para naranja, ⚠️ para amarillo) y un tooltip descriptivo. DEBE reemplazar la verificación hardcodeada de ráfagas.

#### Scenario: Hora con alerta de viento
- **WHEN** una fila horaria tiene una alerta de viento
- **THEN** la fila muestra el icono de alerta junto a la hora y un tooltip con el mensaje de la alerta

#### Scenario: Hora con alerta de tormenta
- **WHEN** una fila horaria tiene una alerta por código WMO
- **THEN** la fila muestra el icono de alerta y un tooltip con el mensaje correspondiente

#### Scenario: Hora sin alertas
- **WHEN** una fila horaria no tiene alertas aplicables
- **THEN** la fila no muestra icono de alerta ni tooltip

#### Scenario: Múltiples alertas en una hora
- **WHEN** una fila horaria tiene varias alertas aplicables
- **THEN** el tooltip lista todos los mensajes de alerta y el icono refleja el nivel más grave

### Requirement: Testeabilidad sin display

La lógica de alertas por hora SHALL ser testeable unitariamente sin depender de GTK ni de un display gráfico.

#### Scenario: Evaluación pura de una hora
- **WHEN** se llama a `get_hour_alerts` con datos de `HourData` de prueba
- **THEN** la función retorna las alertas esperadas sin realizar llamadas de red ni requerir display
