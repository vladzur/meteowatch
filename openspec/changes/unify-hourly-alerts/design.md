## Context

El proyecto tiene un módulo de alertas (`meteowatch/alerts/`) que evalúa el pronóstico y genera una lista de `Alert` usada por:
- `window.py`: envía notificaciones de escritorio vía D-Bus (`send_alerts`).
- `daily_card.py`: muestra un banner resumen en la página diaria (`set_alerts`).

En paralelo, `hourly_panel.py` contiene su propia comprobación de ráfagas (`hour_data.wind_gust >= 50`), duplicando el umbral `WIND_GUST_YELLOW` de `rules.py` y mostrando únicamente la alerta de viento en el desglose por hora. El resto de alertas (tormenta, lluvia intensa, heladas, calor, inundación) no se visualiza por hora.

## Goals / Non-Goals

**Goals:**
- Tener una única fuente de verdad para las reglas de alerta horarias.
- Mostrar en cada fila del desglose por hora un indicador de alerta (icono + tooltip) cuando corresponda, para todas las reglas horarias.
- Mantener el comportamiento actual de las notificaciones (agregadas por tipo y nivel).

**Non-Goals:**
- No cambia la API de Open-Meteo ni los modelos de datos.
- No se muestra por hora la alerta diaria de lluvia (`daily_rain`), por ser de granularidad diaria.
- No se introducen nuevos umbrales ni reglas.

## Decisions

### 1. Función pura `get_hour_alerts(hour)` como fuente única
Se añade en `meteowatch/alerts/rules.py` una función pura que evalúa una única `HourData` contra todas las reglas horarias (WMO, viento, inundación, heladas, calor) y devuelve `list[Alert]`.

- **Alternativa considerada:** exponer el cálculo como método de `AlertEngine`. Se descarta porque obligaría a instanciar el motor (con estado de deduplicación) solo para consultar reglas puras, y acoplaría la UI a la clase con estado.
- **Racional:** separa las reglas (puras, testeables sin GTK) de la agregación/dedup con estado.

### 2. `AlertEngine` agrega sobre la función unificada
`AlertEngine.evaluate()` se refactoriza para iterar las horas y llamar `get_hour_alerts`, aplicando:
- Ventana general `HOURS_WINDOW` (6h) para todas las alertas horarias salvo inundación.
- Ventana propia `FLASH_FLOOD_WINDOW` (3h) para inundación repentina.
- `_check_daily_rain` se mantiene tal cual (diaria).
- `_filter_duplicates` se mantiene tal cual (dedup por `(category, level)`), por lo que las notificaciones siguen agregadas.

- **Alternativa considerada:** mantener los `_check_*` actuales y añadir una función aparte para la UI. Se descarta porque perpetúa la duplicación que se quiere eliminar.
- **Efecto colateral aceptado:** el valor del mensaje de viento refleja la primera hora que supera el umbral (antes era el máximo de la ventana). La dedup por nivel mantiene una única notificación por nivel.

### 3. Visualización por hora con icono + tooltip
En `_build_hour_row`, se llama una vez a `get_hour_alerts(hour_data)`:
- Si hay alguna alerta, se antepone un icono a la hora: 🔴 si hay nivel `orange`, ⚠️ si solo hay `yellow`.
- Se asigna `set_tooltip_text()` con los mensajes de las alertas.
- La línea de detalle "Ráfagas X km/h" se resalta solo si existe una alerta de categoría `wind` en el resultado unificado (se elimina el `>= 50` hardcodeado).

- **Alternativa considerada:** mantener la línea "Ráfagas" con su propio resaltado independiente. Se descarta para no duplicar la detección.

### 4. Sin cambios en la notificación
Las notificaciones de escritorio se mantienen agregadas (una por tipo y nivel) y sin cambios de comportamiento observable.

## Risks / Trade-offs

- [El mensaje de viento pasa de "máximo de ventana" a "valor de la primera hora que supera"] → Aceptable; la dedup mantiene una notificación por nivel. Si se desea conservar el máximo, se puede ordenar por `value` antes de deduplicar.
- [Importar `HourData` en `rules.py` crea una dependencia de `models`] → Sin ciclo de importación (`models` no importa `alerts`); verificado al revisar el código.
- [La UI GTK no es testeable sin display] → La lógica queda en la función pura `get_hour_alerts` y en helpers puros de icono/tooltip, cubiertos por tests unitarios.
