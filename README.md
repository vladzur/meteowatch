# Meteowatch

Aplicación de escritorio GNOME para consultar el pronóstico meteorológico usando la API de Meteored.

## Requisitos

- Python 3.11+
- GTK 4 + libadwaita
- Dependencias Python: `requests`, `pygobject`

## Instalación

```bash
pip install -e .
```

## Uso

```bash
python -m meteowatch.main
```

Al iniciar por primera vez, ingresa tu API key de Meteored y busca una ubicación.

## Tests

```bash
python -m pytest tests/ -v
```

## Flatpak

```bash
flatpak-builder --run build-dir com.meteowatch.app.json meteowatch
```

## API

La aplicación consume tres endpoints de la API de Meteored:

| Endpoint | Descripción |
|---|---|
| `GET /api/location/v1/search/txt/{text}` | Búsqueda de ubicación |
| `GET /api/forecast/v1/daily/{hash}` | Pronóstico diario (5 días) |
| `GET /api/forecast/v1/hourly/{hash}` | Pronóstico por hora (24h) |

Autenticación vía header `x-api-key`.
