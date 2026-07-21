"""Mapeo de símbolos meteorológicos de la API de Meteored a emojis y descripciones.

Los códigos provienen del endpoint /api/doc/v1/forecast/symbol (IDs 1–41).
"""

from typing import NamedTuple


class WeatherSymbol(NamedTuple):
    """Tupla que asocia un símbolo numérico con su emoji y descripción en español."""

    emoji: str
    description: str


# Mapeo oficial de símbolos de Meteored (basado en /api/doc/v1/forecast/symbol)
SYMBOL_MAP: dict[int, WeatherSymbol] = {
    1: WeatherSymbol("☀️", "Despejado"),
    2: WeatherSymbol("🌤️", "Nubes altas"),
    3: WeatherSymbol("⛅", "Nubes dispersas"),
    4: WeatherSymbol("⛅", "Parcialmente nublado"),
    5: WeatherSymbol("☁️", "Nublado"),
    6: WeatherSymbol("🌫️", "Neblina de polvo"),
    7: WeatherSymbol("🌫️", "Neblina de polvo"),
    8: WeatherSymbol("🌫️", "Neblina"),
    9: WeatherSymbol("🌫️", "Niebla"),
    10: WeatherSymbol("⛈️", "Tormenta seca"),
    11: WeatherSymbol("⛈️", "Tormenta seca"),
    12: WeatherSymbol("🌦️", "Lluvia ligera"),
    13: WeatherSymbol("🌧️", "Lluvia ligera"),
    14: WeatherSymbol("🌦️", "Lluvia moderada"),
    15: WeatherSymbol("🌧️", "Lluvia moderada"),
    16: WeatherSymbol("🌧️", "Lluvia con polvo"),
    17: WeatherSymbol("🌧️", "Lluvia con polvo"),
    18: WeatherSymbol("🌨️", "Lluvia helada"),
    19: WeatherSymbol("🌨️", "Lluvia helada"),
    20: WeatherSymbol("🌨️", "Lluvia y nieve"),
    21: WeatherSymbol("🌨️", "Lluvia y nieve"),
    22: WeatherSymbol("🌨️", "Nieve y lluvia con polvo"),
    23: WeatherSymbol("🌨️", "Nieve y lluvia con polvo"),
    24: WeatherSymbol("🌨️", "Nieve"),
    25: WeatherSymbol("🌨️", "Nieve"),
    26: WeatherSymbol("🌨️", "Nieve con polvo"),
    27: WeatherSymbol("🌨️", "Nieve con polvo"),
    28: WeatherSymbol("🌧️", "Lluvia fuerte"),
    29: WeatherSymbol("🌧️", "Lluvia fuerte"),
    30: WeatherSymbol("🌨️", "Lluvia y nieve fuertes"),
    31: WeatherSymbol("🌨️", "Lluvia y nieve fuertes"),
    32: WeatherSymbol("❄️", "Nieve fuerte"),
    33: WeatherSymbol("❄️", "Nieve fuerte"),
    34: WeatherSymbol("⛈️", "Tormenta"),
    35: WeatherSymbol("⛈️", "Tormenta"),
    36: WeatherSymbol("🌨️", "Granizo"),
    37: WeatherSymbol("🌨️", "Granizo"),
    38: WeatherSymbol("⛈️", "Tormenta con granizo"),
    39: WeatherSymbol("⛈️", "Tormenta con granizo"),
    40: WeatherSymbol("🌪️", "Tormenta de polvo"),
    41: WeatherSymbol("🌨️", "Ventisca"),
}


def get_weather_symbol(code: int) -> WeatherSymbol:
    """Retorna el emoji y descripción para un código de símbolo meteorológico.

    Si el código no está mapeado, retorna un símbolo genérico.
    """
    return SYMBOL_MAP.get(code, WeatherSymbol("❓", "Desconocido"))
