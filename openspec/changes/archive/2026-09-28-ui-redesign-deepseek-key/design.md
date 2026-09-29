## Context

Meteowatch muestra el pronóstico diario en `DailyForecastPage` como una lista vertical: encabezado (ubicación + condiciones actuales), banner de alertas, botón "Ver pronóstico de las próximas 24 horas" y tarjetas de día una debajo de otra. Las tarjetas son `Gtk.Box` no clicables. La llave de DeepSeek solo se lee de la variable de entorno `DEEPSEEK_API_KEY` en `ReportEngine`, lo que impide su configuración cómoda en Flatpak.

## Goals / Non-Goals

**Goals:**

- Reorganizar la vista diaria en una grilla de 2 columnas con "Hoy" destacado.
- Hacer clicables las tarjetas y navegar al pronóstico horario del día seleccionado.
- Permitir configurar la llave de DeepSeek desde la UI, persistida en `config.json`.

**Non-Goals:**

- No modificar la lógica de alertas, `ForecastService`, tray ni el cliente Open-Meteo.
- No cifrar la llave en `config.json`.
- No añadir más preferencias de configuración además de la llave.

## Decisions

### 1. Grilla con `Gtk.Grid` en lugar de `Gtk.FlowBox`

`Gtk.FlowBox` no permite que un hijo ocupe dos columnas. Se usa `Gtk.Grid` con `attach(widget, col, row, width, height)`: "Hoy" (índice 0) con `width=2`, y los días 1-4 en una grilla 2×2.

Alternativa considerada: sección hero + `FlowBox`. Se descartó por duplicar la lógica de tarjeta.

### 2. Tarjetas clicables envueltas en `Gtk.Button`

Cada tarjeta se envuelve en un `Gtk.Button` plano (clase `.card-button`) con el `Gtk.Box` de la tarjeta como hijo. Se conecta `clicked` a `_on_day_clicked(day_start)`.

Alternativa considerada: `Gtk.GestureClick` sobre el `Gtk.Box`. Se descartó por perder foco/teclado y los estados hover/active nativos del botón.

### 3. Clase CSS `.today-card`

La tarjeta de hoy añade la clase `.today-card` (borde `@accent_color` + fondo `alpha(@accent_bg_color, 0.15)`), definida después de `.card` para ganar en cascada.

### 4. Precedencia de llave: configuración > entorno

`ReportEngine.__init__(api_key)` usa `api_key or os.environ.get("DEEPSEEK_API_KEY", "")`. `is_available()` pasa a método de instancia. Se añade `set_api_key()` para actualización en runtime con invalidación de cache.

### 5. Diálogo de preferencias con `Adw.Dialog`

Se crea `SettingsDialog` (en `meteowatch/widgets/settings.py`) con un `Gtk.Entry` (oculto + toggle de visibilidad) y botones Guardar/Cancelar. La acción `app.preferences` se registra en `MeteowatchApp` y se enlaza desde el `Gio.Menu` de la vista diaria.

### 6. Filtrado por día en la vista horaria

`HourlyForecastPage` acepta `day_start: Optional[int]`. Cuando está presente, filtra `forecast.hours` por el día local (helper puro `_day_start_of`) y muestra todas las horas de ese día sin toggle. Sin `day_start`, conserva el comportamiento actual.

## Risks / Trade-offs

- [La llave queda en texto plano en `config.json`] → Mitigación: es consistente con el resto de la configuración y se documenta; no se registra en logs.
- [Cambiar `is_available()` de estático a instancia rompe tests y call sites] → Mitigación: actualizar tests y `window.py` en el mismo cambio.
- [Eliminar el botón 24h puede confundir a usuarios acostumbrados] → Mitigación: "Hoy" es la tarjeta destacada y sigue siendo clicable; se actualiza el texto de Ayuda.
- [Las tarjetas dentro de botones pueden sumar padding/background no deseado] → Mitigación: clase `.card-button` que anula fondo, padding y sombra del botón.

## Migration Plan

- Persistencia retrocompatible: `AppConfig.load()` lee `deepseek_api_key` con valor por defecto `""`; las configuraciones existentes sin el campo siguen funcionando.
- Sin migración de datos: si el usuario ya usaba `DEEPSEEK_API_KEY`, esta sigue funcionando como respaldo.

## Open Questions

- Ninguna relevante para este cambio.
