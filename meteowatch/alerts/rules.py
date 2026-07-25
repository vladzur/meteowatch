"""Definición de reglas y umbrales para el motor de alertas climáticas.

Las reglas están separadas de la lógica de evaluación para facilitar
su mantenimiento y posible externalización futura a un archivo de configuración.
"""

from typing import NamedTuple


class Alert(NamedTuple):
    """Representa una alerta climática detectada.

    Atributos:
        level: Nivel de severidad ('yellow' o 'orange').
        category: Categoría de la alerta (ej: 'thunderstorm', 'wind').
        message: Mensaje descriptivo en español para mostrar al usuario.
        source_code: Código WMO que originó la alerta, o None si es por umbral.
        value: Valor numérico que disparó la alerta, o None si es por código WMO.
    """

    level: str
    category: str
    message: str
    source_code: int | None
    value: float | None


# ------------------------------------------------------------------
# Reglas basadas en códigos WMO (weather_code)
# ------------------------------------------------------------------

# Códigos WMO que disparan alerta naranja automática
WMO_ORANGE_CODES: dict[int, str] = {
    95: "Tormenta eléctrica detectada en tu área. Posibilidad de rayos y ráfagas.",
    96: "Tormenta eléctrica con granizo. Busca refugio y evita desplazamientos.",
    99: "Tormenta eléctrica severa con granizo grande. Riesgo de daños materiales.",
    66: "Lluvia engelante. Riesgo extremo de formación de hielo en superficies.",
    67: "Lluvia engelante intensa. Condiciones muy peligrosas para la conducción.",
    77: "Granizo blando. Acumulación rápida y riesgo para la conducción.",
}

# Códigos WMO que disparan alerta amarilla
WMO_YELLOW_CODES: dict[int, str] = {
    65: "Lluvia de intensidad fuerte. Posibles acumulaciones en zonas bajas.",
    75: "Nevada de intensidad fuerte. Precaución en carreteras y desplazamientos.",
}


# ------------------------------------------------------------------
# Umbrales para alertas basadas en variables cuantitativas
# ------------------------------------------------------------------

# Viento (ráfagas en km/h, variable: hourly.wind_gusts_10m)
WIND_GUST_YELLOW: float = 50.0   # Alerta amarilla
WIND_GUST_ORANGE: float = 90.0   # Alerta naranja

# Lluvia extrema (precipitación en mm)
FLASH_FLOOD_ORANGE: float = 15.0   # hourly.precipitation > 15 mm en hora actual o próximas 2h
DAILY_RAIN_YELLOW: float = 40.0    # daily.precipitation_sum > 40 mm

# Temperatura peligrosa (sensación térmica en °C, variable: hourly.apparent_temperature)
FROST_YELLOW: float = 0.0    # Sensación térmica < 0°C
HEAT_YELLOW: float = 35.0    # Sensación térmica > 35°C

# Ventana de horas a evaluar desde la hora actual (para alertas horarias)
HOURS_WINDOW: int = 6
# Ventana específica para riesgo de inundación repentina
FLASH_FLOOD_WINDOW: int = 3  # hora actual + 2 siguientes


# ------------------------------------------------------------------
# Categorías de alerta para agrupar y deduplicar
# ------------------------------------------------------------------

CATEGORY_THUNDERSTORM = "thunderstorm"
CATEGORY_FREEZING = "freezing"
CATEGORY_HEAVY_RAIN = "heavy_rain"
CATEGORY_HEAVY_SNOW = "heavy_snow"
CATEGORY_WIND = "wind"
CATEGORY_FLASH_FLOOD = "flash_flood"
CATEGORY_DAILY_RAIN = "daily_rain"
CATEGORY_FROST = "frost"
CATEGORY_HEAT = "heat"

# Mapeo de códigos WMO a categorías para deduplicación
WMO_CATEGORY_MAP: dict[int, str] = {
    95: CATEGORY_THUNDERSTORM,
    96: CATEGORY_THUNDERSTORM,
    99: CATEGORY_THUNDERSTORM,
    66: CATEGORY_FREEZING,
    67: CATEGORY_FREEZING,
    77: CATEGORY_FREEZING,
    65: CATEGORY_HEAVY_RAIN,
    75: CATEGORY_HEAVY_SNOW,
}
