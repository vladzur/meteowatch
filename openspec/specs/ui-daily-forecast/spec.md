# ui-daily-forecast Specification

## Purpose

Presentación del pronóstico diario en una grilla de dos columnas con el día actual destacado, tarjetas clicables y navegación al pronóstico por hora del día seleccionado.

## Requirements
### Requirement: Grilla de pronóstico con el día actual destacado

El sistema SHALL mostrar el pronóstico diario en una grilla de dos columnas. La tarjeta del día actual ("Hoy") DEBE ocupar ambas columnas y DEBE distinguirse visualmente del resto de los días mediante un estilo destacado.

#### Scenario: Hoy ocupa ambas columnas

- **WHEN** se carga el pronóstico diario con 5 días
- **THEN** la tarjeta "Hoy" ocupa el ancho completo de la grilla y las 4 tarjetas restantes se distribuyen en 2 columnas

#### Scenario: Hoy destacado visualmente

- **WHEN** se renderiza la tarjeta "Hoy"
- **THEN** la tarjeta aplica una clase de estilo destacado (p. ej. `today-card`) distinta de las demás

### Requirement: Navegación por clic en las tarjetas diarias

El sistema SHALL hacer clicables las tarjetas de pronóstico diario. Al hacer clic en una tarjeta, la aplicación DEBE navegar a la pantalla de pronóstico por hora correspondiente al día seleccionado, propagando el timestamp de inicio del día (`day_start`).

#### Scenario: Clic en la tarjeta de un día

- **WHEN** el usuario hace clic en la tarjeta de un día con `day_start` conocido
- **THEN** se navega a la página de pronóstico por hora con ese `day_start`

#### Scenario: Botón de 24 horas eliminado

- **WHEN** se renderiza la página de pronóstico diario
- **THEN** no se muestra el botón "Ver pronóstico de las próximas 24 horas"

### Requirement: Vista horaria filtrada por día

El sistema SHALL permitir que la página de pronóstico por hora reciba un `day_start` y, cuando esté presente, DEBE mostrar únicamente las horas de ese día (desde medianoche hasta la medianoche siguiente en la zona horaria local) sin el filtro de horas pasadas ni el botón "Mostrar horas anteriores".

#### Scenario: Filtrado de horas por día

- **WHEN** la página horaria recibe un `day_start` y el forecast contiene horas de varios días
- **THEN** solo se muestran las horas cuyo inicio de día local coincide con `day_start`

#### Scenario: Título según el día seleccionado

- **WHEN** la página horaria recibe un `day_start`
- **THEN** el título de la página refleja el día seleccionado ("Hoy", "Mañana" o el nombre del día de la semana)

#### Scenario: Comportamiento sin día seleccionado

- **WHEN** la página horaria no recibe `day_start`
- **THEN** se conserva el comportamiento actual: horas futuras agrupadas por día con el botón "Mostrar horas anteriores"
