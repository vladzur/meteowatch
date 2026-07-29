## Context

Meteowatch actualmente tiene dos rutas independientes de fetching de datos:
1. `DailyForecastPage.load_forecast()` — llamado al navegar a la página o al presionar el botón refresh
2. `MeteowatchWindow._start_refresh_thread()` — llamado cada 1 hora por `GLib.timeout_add_seconds`

Ambas crean su propio `OpenMeteoClient`, hacen su propia llamada HTTP, y procesan los resultados de forma aislada. No comparten cache ni estado. El refresco periódico solo actualiza el icono del tray y evalúa alertas; la UI nunca se entera.

El objetivo es extraer la lógica de fetching en un servicio centralizado que actúe como única fuente de verdad, con cache en memoria, TTLs diferenciados, y patrón observer para notificar a los componentes interesados.

## Goals / Non-Goals

**Goals:**
- Única fuente de verdad para datos meteorológicos en la aplicación
- Cache en memoria con TTLs: 15 min para `current`, 1h para `forecast` completo
- Dos timers GLib independientes: 15 min (current → tray) y 1h (forecast → UI + alertas)
- UI se suscribe y se reconstruye automáticamente al recibir datos nuevos
- Indicador visual de frescura ("Actualizado hace X min")
- Tolerancia a fallos de red: cache como fallback con indicador de desconexión
- Control de concurrencia: evitar fetches simultáneos

**Non-Goals:**
- Persistencia en disco del cache (solo en memoria)
- TTLs configurables por usuario (hardcodeados por diseño)
- Soporte para múltiples ubicaciones simultáneas
- Skeleton screens o animaciones de carga avanzadas
- Cancelación de requests HTTP en vuelo (se usa daemon thread)

## Decisions

### 1. `ForecastService` como singleton a nivel de aplicación

**Decisión:** Una instancia única de `ForecastService` creada en `MeteowatchApp.do_startup()` y pasada a la ventana y páginas vía inyección.

**Alternativa considerada:** Módulo global con estado mutable. Rechazado porque complica el testing y crea acoplamiento implícito.

**Rationale:** El servicio vive mientras vive la aplicación. La ventana y sus páginas reciben una referencia. Esto permite testing con mocks y evita estado global oculto.

### 2. Cache unificada con TTLs por tipo de dato

```
ForecastCache:
  ├── _daily: DailyForecast | None
  ├── _hourly: HourlyForecast | None
  ├── _current: CurrentWeather | None
  ├── _forecast_at: float (timestamp del último fetch completo)
  ├── _current_at: float (timestamp del último fetch de current)
  └── is_stale(kind) → bool
```

**Decisión:** Un solo objeto cache que guarda daily, hourly y current juntos (vienen en una sola llamada HTTP), pero con dos timestamps independientes para determinar staleness por tipo.

**Alternativa considerada:** Dos caches separadas. Rechazado porque la API de Open-Meteo devuelve todo junto; separar no ahorra llamadas.

**Rationale:** La API gratuita de Open-Meteo no tiene endpoint solo para `current`. Cada llamada devuelve daily + hourly + current. La distinción de TTLs es solo a nivel de notificación: si solo `current` está stale, igual se fetchea todo, pero solo se notifica el evento `"current"` a los observers.

### 3. Patrón observer con callbacks tipados

```python
class ForecastObserver(Protocol):
    def on_forecast_updated(self, forecast: ForecastResult) -> None: ...
    def on_current_updated(self, current: CurrentWeather) -> None: ...
    def on_forecast_error(self, error: str, cached: bool) -> None: ...
```

**Decisión:** Protocolo con tres métodos. Los suscriptores implementan solo los que les interesan (por herencia de una base con no-ops).

**Alternativa considerada:** Señales GLib. Rechazado porque añade dependencia de GTK en el servicio, que debería ser agnóstico de UI.

**Rationale:** Un protocolo Python puro mantiene el servicio testeable sin GTK. Las notificaciones se despachan por `GLib.idle_add()` en el punto de suscripción (la ventana), no en el servicio.

### 4. Dos timers GLib en la ventana

```
Timer "current":  GLib.timeout_add_seconds(900, ...)   # cada 15 min
Timer "forecast": GLib.timeout_add_seconds(3600, ...)  # cada 1 hora
```

**Decisión:** Los timers viven en `MeteowatchWindow`, no en el servicio. Llaman a `ForecastService.refresh_current()` y `ForecastService.refresh_forecast()` respectivamente.

**Alternativa considerada:** Timers dentro del servicio usando `GLib.timeout_add`. Rechazado porque acopla el servicio a GLib.

**Rationale:** Mantener el servicio libre de GLib permite testearlo sin entorno gráfico. La ventana es el lugar natural para timers de UI.

### 5. Refresco de UI transparente (solo si hay cambios)

**Decisión:** Al recibir `on_forecast_updated`, la página diaria compara los datos nuevos con los actuales. Solo reconstruye las cards si `daily.days` cambió (cantidad o contenido).

**Alternativa considerada:** Reconstruir siempre. Rechazado porque causa flickering innecesario si los datos no cambiaron (ej: mismas temperaturas).

**Rationale:** La comparación es barata (listas de días con atributos). Si no hay cambios, se actualiza solo el timestamp de "Actualizado hace X min". Si hay cambios, se reconstruye in-place sin animación para que sea transparente.

### 6. Indicador de frescura

```
🕐 Actualizado hace 12 min          ← normal (dim-label)
🕐 Actualizado hace 1h 23 min       ← amarillo (>1h, warning)
🕐 Actualizado hace 3h 45 min       ← naranja (>3h, error)
🔌 Sin conexión — hace 2h           ← gris, datos cacheados
```

**Decisión:** Un `Gtk.Label` al pie del `DailyForecastPage`. Un timer local de 60s (`GLib.timeout_add_seconds(60)`) recalcula el texto. El color se determina por antigüedad. El emoji 🔌 es distinto a ⚠️/🔴 usado en alertas.

**Alternativa considerada:** Toolbar header. Rechazado porque compite con el título de ubicación.

**Rationale:** Al pie de la página es sutil pero visible. El timer de 60s es ligero (solo actualiza un label). Los colores siguen la semántica del sistema: normal → warning → error.

### 7. Modo offline con cache

**Decisión:** Si `fetch_forecast()` falla y hay datos en cache, se notifica a los observers con `on_forecast_error(error_msg, cached=True)`. La UI muestra los datos cacheados + indicador de desconexión. Si no hay cache, se muestra el error como antes.

**Alternativa considerada:** Reintentos silenciosos sin mostrar el error. Rechazado porque el usuario debe saber que los datos pueden estar desactualizados.

**Rationale:** El cache es el fallback natural. El indicador 🔌 es semánticamente distinto de ⚠️ (alerta climática), evitando confusión.

### 8. Reintentos con backoff exponencial

```
Intento 1: inmediato
Intento 2: +30s
Intento 3: +60s
Intento 4: +120s
Máximo: 3 reintentos, luego esperar al próximo ciclo
```

**Decisión:** Backoff dentro del mismo ciclo de timer. Si falla 3 veces, se rinde y espera al próximo timer programado.

**Rationale:** Evita bombardear la API. 3 reintentos en ~3.5 minutos es razonable para una intermitencia de red típica.

### 9. Control de concurrencia con lock

```python
with self._fetch_lock:
    # Solo un fetch a la vez
```

**Decisión:** Un `threading.Lock` simple. Si un timer dispara un fetch mientras otro está en vuelo, el segundo espera (o se omite si el primero ya actualizó los datos dentro del TTL).

**Alternativa considerada:** Cola de requests. Rechazado por complejidad innecesaria.

**Rationale:** El lock es suficiente porque solo hay dos timers y refresco manual. La contención es mínima.

## Risks / Trade-offs

- **[Riesgo] La API de Open-Meteo no tiene endpoint solo para current** → Cada refresh de 15 minutos descarga el forecast completo (daily + hourly). Esto consume ~7KB por request, que es aceptable incluso en conexiones lentas. El beneficio en simplicidad supera el costo de ancho de banda.
- **[Riesgo] El indicador de frescura usa un timer de 60s** → 60 timers GLib ligeros no impactan el rendimiento. Si se detecta consumo, se puede subir a 120s.
- **[Riesgo] Race condition si el usuario cierra la app durante un fetch** → El hilo es daemon, así que muere con el proceso. Los callbacks GLib.idle_add() verifican que la ventana siga viva antes de actualizar.
- **[Trade-off] El servicio no persiste el cache en disco** → Un reinicio de la app siempre requiere un fetch fresco. Esto es aceptable porque la app se inicia típicamente una vez por sesión.
