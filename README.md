# 🌦️ Meteowatch

Aplicación de escritorio GNOME para consultar el pronóstico meteorológico usando la API gratuita de Open-Meteo. Construida con **GTK 4 + libadwaita** y **Python 3**.

<p align="center">
  <img src="data/com.meteowatch.app.svg" alt="Meteowatch icon" width="96" height="96">
</p>

## ✨ Funcionalidades

- **Búsqueda de ubicaciones** por nombre de ciudad
- **Pronóstico diario** de 5 días con tarjetas detalladas:
  - Temperaturas máximas y mínimas
  - Condición climática con icono (códigos WMO oficiales)
  - Humedad, probabilidad de lluvia, viento y ráfagas
  - Amanecer, atardecer, precipitación e índice UV
- **Temperatura actual** obtenida del endpoint de condiciones actuales
- **Pronóstico por hora** de las próximas 24 horas con navegación de retroceso integrada
- **Alerta de ráfagas de viento** ≥ 50 km/h (⚠️ en la UI)
- **Icono en bandeja del sistema** (system tray) con:
  - Icono dinámico que muestra emoji del clima + temperatura actual
  - Minimizar al tray al cerrar la ventana (configurable)
  - Refresco automático cada hora
  - Protocolo `org.kde.StatusNotifierItem` (compatible con GNOME, KDE, XFCE)
- **Zona horaria dinámica** según la ubicación seleccionada
- **Configuración persistente** en `~/.config/meteowatch/config.json`
- **Empaquetado Flatpak** con GNOME SDK 49

## 📸 Capturas de pantalla

```
┌──────────────────────────────────────┐
│  🔄 Villarrica              📍      │
├──────────────────────────────────────┤
│          Villarrica                  │
│        🌫️   8°  Ahora               │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 🕐  Ver pronóstico 24h  →  →  │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 🌫️  Hoy          11°          │  │
│  │     20 de julio    2°          │  │
│  │     Niebla                     │  │
│  │ ────────────────────────────── │  │
│  │ 💧—  🌧️0%   💨8 km/h N   │  │
│  │ ↗️18    🌅08:02  🌇17:55      │  │
│  │ 🌧️0.0mm ☀️UV 1.6            │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ 🌧️  Mañana       13°         │  │
│  │     21 de julio    1°          │  │
│  │     Lluvia ligera              │  │
│  │ ────────────────────────────── │  │
│  │ 💧—  🌧️90%  💨19 km/h E   │  │
│  │ ⚠️ ↗️36  🌅08:03  🌇17:54    │  │
│  │ ...                            │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## 📁 Estructura del proyecto

```
meteowatch/
├── pyproject.toml                     # Proyecto Python, dependencias, entry point
├── com.meteowatch.app.json            # Manifiesto Flatpak (GNOME SDK 49)
├── README.md
├── .gitignore
│
├── data/
│   ├── com.meteowatch.app.desktop     # Lanzador .desktop
│   └── com.meteowatch.app.svg         # Icono de la aplicación
│
├── flatpak-deps/                      # Wheels Python offline para build Flatpak
│
├── docs/
│   └── tray_lessons_learned.md        # Lecciones aprendidas del system tray
│
├── meteowatch/                        # Paquete principal
│   ├── __init__.py
│   ├── main.py                        # Punto de entrada
│   ├── app.py                         # Adw.Application (ciclo de vida, CSS, CLI)
│   ├── window.py                      # Ventana principal con NavigationView + tray
│   ├── config.py                      # Configuración JSON (~/.config/meteowatch/)
│   ├── icons.py                       # Mapeo symbol → emoji (códigos WMO)
│   ├── status_notifier.py             # Protocolo SNI (org.kde.StatusNotifierItem)
│   ├── tray_icon.py                   # Generación dinámica de iconos PNG (Cairo/Pango)
│   ├── dbusmenu.py                    # Servidor D-Bus para menú contextual
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py                  # Cliente HTTP OpenMeteoClient
│   ├── models/
│   │   ├── __init__.py
│   │   ├── location.py                # Location (búsqueda)
│   │   ├── daily.py                   # DailyForecast + DayData (5 días)
│   │   └── hourly.py                  # HourlyForecast + HourData (24h)
│   └── widgets/
│       ├── __init__.py
│       ├── location_search.py         # Página de configuración y búsqueda
│       ├── daily_card.py              # Página de pronóstico diario
│       └── hourly_panel.py            # Página de detalle por hora
│
└── tests/
    ├── __init__.py
    ├── test_config.py                 # Tests de configuración
    ├── test_icons.py                  # Tests de símbolos meteorológicos
    ├── test_models.py                 # Tests de modelos de datos
    └── test_tray_icon.py              # Tests de generación de iconos PNG
```

## 📋 Requisitos

| Dependencia | Versión |
|---|---|
| Python | ≥ 3.11 |
| GTK | 4.0 |
| libadwaita | 1.0 |
| PyGObject | ≥ 3.46 |
| requests | ≥ 2.31 |

## 🚀 Instalación y uso

### Desarrollo directo

```bash
# Instalar en modo editable
pip install -e .

# Ejecutar
python -m meteowatch.main

# Iniciar minimizado al tray
python -m meteowatch.main --background

# Desactivar el icono de bandeja
python -m meteowatch.main --no-tray
```

Al iniciar por primera vez, busca una ubicación. No se requiere clave de API. La configuración se guarda en `~/.config/meteowatch/config.json`.

### Flatpak

```bash
# 1. Descargar dependencias Python (si se actualizan)
python3 -m pip download --python-version 3.13 --only-binary=:all: requests setuptools -d flatpak-deps

# 2. Construir e instalar directamente
flatpak-builder --force-clean --user --install build-dir com.meteowatch.app.json

# 3. Ejecutar
flatpak run com.meteowatch.app

# 4. (Opcional) Generar bundle para distribuir
flatpak build-bundle repo meteowatch.flatpak com.meteowatch.app
```

### Flags de línea de comandos

| Flag | Descripción |
|---|---|
| `--background`, `-b` | Iniciar minimizado en la bandeja del sistema |
| `--no-tray` | Desactivar completamente el icono de bandeja |

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

**54 tests unitarios** cubriendo configuración, modelos de datos, mapeo de símbolos meteorológicos, cliente HTTP y generación de iconos del tray.

## 🌐 API de Open-Meteo

La aplicación consume dos APIs públicas sin autenticación:

| Endpoint | Descripción |
|---|---|
| [Geocoding API](https://open-meteo.com/en/docs/geocoding-api) | Búsqueda de ubicación por texto → retorna coordenadas y zona horaria |
| [Forecast API](https://open-meteo.com/en/docs) | Pronóstico diario, por hora y condiciones actuales en una sola llamada |

### Códigos meteorológicos WMO

El mapeo de iconos usa los códigos estándar WMO:

| Código | Descripción | Emoji |
|---|---|---|
| 0 | Despejado | ☀️ |
| 1 | Mayormente despejado | 🌤️ |
| 3 | Nublado | ☁️ |
| 45 | Niebla | 🌫️ |
| 61 | Lluvia ligera | 🌦️ |
| 63 | Lluvia moderada | 🌧️ |
| 71 | Nieve ligera | 🌨️ |
| 95 | Tormenta | ⛈️ |

## 🏗️ Arquitectura

```
main.py → app.py (Adw.Application + flags CLI)
            └── window.py (Adw.NavigationView + tray)
                  ├── LocationSearchPage   (API key + búsqueda)
                  ├── DailyForecastPage    (5 tarjetas expandidas)
                  │     └── clic en día →
                  └── HourlyForecastPage   (24h, alertas viento, ← botón volver)
                  │
                  └── StatusNotifierItem   (icono bandeja, protocolo SNI)
                        └── tray_icon.py   (PNG vía Cairo/Pango)
```

- **Navegación**: `Adw.NavigationView` con push/pop entre páginas. `Adw.HeaderBar` con botón de retroceso automático.
- **System tray**: Protocolo `org.kde.StatusNotifierItem` sobre D-Bus. Icono PNG generado con Cairo + Pango para control total del renderizado. Actualización horaria automática.
- **Hilos**: Las llamadas a la API se ejecutan en threads separados con `GLib.idle_add` para actualizar la UI
- **Timezone**: Zona horaria dinámica según la ubicación (vía API de geocoding y `zoneinfo`)

## 📦 Flatpak

| Campo | Valor |
|---|---|
| App ID | `com.meteowatch.app` |
| Runtime | `org.gnome.Platform//49` |
| SDK | `org.gnome.Sdk//49` |
| Permisos | Wayland, X11 fallback, red, IPC, bus de sesión D-Bus |

Las dependencias Python (`requests`, `urllib3`, `certifi`, `charset-normalizer`, `idna`, `setuptools`) se incluyen como wheels offline en `flatpak-deps/` para evitar acceso a red durante el build.

## 📄 Licencia

GPL-3.0-only
