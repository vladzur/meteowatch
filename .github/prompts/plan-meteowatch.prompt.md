## Plan: Meteowatch — Aplicación GNOME de Pronóstico Meteorológico

**TL;DR:** App GTK 4 + libadwaita en Python que consume la API de Meteored para mostrar pronóstico diario (5 días) y, al hacer clic en un día, navega al detalle por hora. Se empaqueta como Flatpak con runtime `org.gnome.Sdk`.

---

### Fase 1: Estructura del proyecto y configuración

**1. Crear estructura de directorios y `pyproject.toml`**
- Crear `meteowatch/` como paquete Python.
- `pyproject.toml` con dependencias: `pygobject`, `requests`, `pydantic` (o `dataclasses`).
- Entry point: `meteowatch.main:main`.

**2. Implementar `meteowatch/config.py` — gestión de configuración**
- Lee/escribe `~/.config/meteowatch/config.json`.
- Campos: `api_key`, `location_hash`, `location_name`.
- Métodos: `load()`, `save()`, `get_api_key()`, `set_location(hash, name)`.

**3. Crear manifest Flatpak (`com.meteowatch.app.json`)**
- Runtime: `org.gnome.Sdk//46`.
- SDK: `org.gnome.Sdk`.
- Módulo Python con `pip` para instalar dependencias.
- Entry point: `meteowatch`.
- `.desktop` file en `data/com.meteowatch.app.desktop`.

---

### Fase 2: Capa de API y modelos

**4. Implementar modelos de datos (`meteowatch/models/`)**
- `location.py` — `Location`: `hash`, `name`, `description`, `country_name`.
- `daily.py` — `DailyForecast`: `url`, `hash`, `name`, `rain`, `start`, `sun_in`, `sun_out`, `symbol`, `humidity`, `pressure`, `snowline`, `wind_gust`, `wind_speed`, `wind_direction`, `temperature_max`, `temperature_min`, `rain_probability`, `moon_symbol`, `moon_illumination`, `uv_index_max`.
- `hourly.py` — `HourlyForecast`: `url`, `hash`, `name`, `start`, `hours: list[HourData]`. `HourData`: `end`, `rain`, `night`, `clouds`, `symbol`, `humidity`, `pressure`, `snowline`, `wind_gust`, `wind_speed`, `temperature`, `uv_index_max`, `wind_direction`, `rain_probability`, `temperature_feels_like`.

**5. Implementar `meteowatch/api/client.py` — cliente HTTP**
- Clase `MeteoredClient` con métodos:
  - `search_location(text: str) -> list[Location]`
  - `get_daily_forecast(hash: str) -> DailyForecast`
  - `get_hourly_forecast(hash: str) -> HourlyForecast`
- Usa `requests.Session`, header `x-api-key`.
- Manejo de errores: 400, 404, 429, 500, timeouts.
- Rate limiting básico máximo 5 requests diarias(respetar `expiracion` del response para cache).

**6. Implementar `meteowatch/icons.py` — mapeo de símbolos meteorológicos**
- Diccionario `SYMBOL_MAP` que mapea el `symbol` numérico de la API a tupla `(emoji, descripción_es)`.
- Basado en los códigos estándar de weather.com (0–47).
- Ejemplo: `4` → `("⛈️", "Tormentas")`, `32` → `("☀️", "Soleado")`, `26` → `("☁️", "Nublado")`.

---

### Fase 3: Interfaz gráfica (GTK 4 + libadwaita)

**7. Implementar `meteowatch/app.py` — `Gtk.Application`**
- Subclase de `Adw.Application`.
- Crea la ventana principal (`MeteowatchWindow`).
- Gestiona el ciclo de vida y recursos.

**8. Implementar `meteowatch/window.py` — ventana principal**
- `Adw.ApplicationWindow` con `Adw.NavigationView` como widget raíz.
- Título: "Meteowatch".
- Tamaño default: 420×680 px (formato móvil/vertical).
- Al abrirse: si no hay API key o ubicación → mostrar página de configuración. Si ya está configurado → cargar pronóstico diario.

**9. Implementar `meteowatch/widgets/location_search.py` — búsqueda de ubicación**
- Página de bienvenida/configuración (`Adw.NavigationPage`).
- Campo de entrada (`Gtk.Entry`) para API key + botón guardar.
- Campo de búsqueda (`Gtk.SearchEntry`) para ubicación.
- `Gtk.ListBox` con resultados de búsqueda.
- Al seleccionar ubicación: guarda en config y navega a pronóstico diario.

**10. Implementar `meteowatch/widgets/daily_card.py` — tarjeta de día**
- `Adw.NavigationPage` con `Gtk.ListBox`.
- Cada fila (`Gtk.ListBoxRow`) muestra un día con:
  - Nombre del día (formateado desde timestamp `start`)
  - Emoji del clima (`symbol`)
  - Temp máx / mín
  - Probabilidad de lluvia
  - Humedad
- Al hacer clic en una fila → `Adw.NavigationView.push()` a la página de detalle por hora.
- Encabezado con nombre de la ubicación y botón para cambiar ubicación.

**11. Implementar `meteowatch/widgets/hourly_panel.py` — detalle por hora**
- `Adw.NavigationPage`.
- `Gtk.ListBox` con filas por cada hora del array `hours`.
- Cada fila muestra:
  - Hora (formateada desde `end` timestamp)
  - Emoji del clima
  - Temperatura real y sensación térmica
  - Viento (velocidad + dirección)
  - Probabilidad de lluvia
  - Humedad
  - Nubosidad
- Encabezado con fecha del día seleccionado y botón "volver" (nativo de NavigationView).

**12. Implementar `meteowatch/main.py` — punto de entrada**
- `def main():` → instancia `MeteowatchApp`, llama a `run()`.

---

### Fase 4: Pruebas y empaquetado

**13. Implementar tests unitarios**
- `tests/test_config.py` — lectura/escritura de configuración.
- `tests/test_models.py` — parseo de JSON de API a modelos.
- `tests/test_icons.py` — cobertura del mapeo de símbolos.

**14. Verificar build Flatpak**
- `flatpak-builder build-dir com.meteowatch.app.json --force-clean`
- `flatpak-builder --run build-dir com.meteowatch.app.json meteowatch`

---

### Archivos relevantes (a crear)

| Archivo | Propósito |
|---|---|
| `pyproject.toml` | Definición del proyecto, dependencias, entry point |
| `com.meteowatch.app.json` | Manifiesto Flatpak |
| `data/com.meteowatch.app.desktop` | Archivo .desktop para el lanzador |
| `meteowatch/__init__.py` | Inicialización del paquete |
| `meteowatch/main.py` | Punto de entrada (`main()`) |
| `meteowatch/app.py` | Subclase de `Adw.Application` |
| `meteowatch/window.py` | Ventana principal con `Adw.NavigationView` |
| `meteowatch/config.py` | Gestión de `~/.config/meteowatch/config.json` |
| `meteowatch/icons.py` | Mapeo `symbol` → `(emoji, descripción)` |
| `meteowatch/api/__init__.py` | Inicialización del submódulo API |
| `meteowatch/api/client.py` | Cliente HTTP `MeteoredClient` |
| `meteowatch/models/__init__.py` | Inicialización de modelos |
| `meteowatch/models/location.py` | Dataclass `Location` |
| `meteowatch/models/daily.py` | Dataclass `DailyForecast` |
| `meteowatch/models/hourly.py` | Dataclasses `HourlyForecast`, `HourData` |
| `meteowatch/widgets/__init__.py` | Inicialización de widgets |
| `meteowatch/widgets/location_search.py` | Página de configuración/búsqueda |
| `meteowatch/widgets/daily_card.py` | Página de pronóstico diario |
| `meteowatch/widgets/hourly_panel.py` | Página de detalle por hora |
| `tests/__init__.py` | Inicialización de tests |
| `tests/test_config.py` | Tests de configuración |
| `tests/test_models.py` | Tests de modelos |
| `tests/test_icons.py` | Tests de iconos |

---

### Verificación

1. `python -m meteowatch.main` — la app abre, pide API key y ubicación.
2. Buscar "Madrid" → muestra resultados → seleccionar → guarda hash.
3. Carga pronóstico diario (5 días) con iconos y datos.
4. Clic en un día → navega a vista por hora con datos detallados.
5. Botón volver → regresa a vista diaria.
6. `python -m pytest tests/` — todos los tests pasan.
7. `flatpak-builder --run build-dir com.meteowatch.app.json meteowatch` — ejecuta desde Flatpak.

---

### Decisiones

- **GTK 4 + libadwaita**: look nativo GNOME moderno, navegación con `Adw.NavigationView`.
- **Config en archivo JSON**: `~/.config/meteowatch/config.json`, simple y portable.
- **Emojis para iconos**: sin dependencias externas, mapeo basado en códigos weather.com.
- **Flatpak**: runtime `org.gnome.Sdk//46`, entry point Python.
- **Sin caché persistente**: se respeta el campo `expiracion` de la API para evitar llamadas innecesarias dentro de la misma sesión, pero no se persiste en disco.
- **Idioma UI**: español neutro (textos visibles al usuario). Código y nombres técnicos en inglés.
