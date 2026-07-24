"""Mapeo de símbolos meteorológicos WMO a emojis y descripciones.

Los códigos siguen el estándar WMO Weather interpretation codes.
Ver: https://open-meteo.com/en/docs#weathervariables
"""

from typing import NamedTuple


class WeatherSymbol(NamedTuple):
    """Tupla que asocia un símbolo numérico con su emoji y descripción en español."""

    emoji: str
    description: str


# Mapeo de códigos WMO a emojis y descripciones en español
SYMBOL_MAP: dict[int, WeatherSymbol] = {
    0: WeatherSymbol("☀️", "Despejado"),
    1: WeatherSymbol("🌤️", "Mayormente despejado"),
    2: WeatherSymbol("⛅", "Parcialmente nublado"),
    3: WeatherSymbol("☁️", "Nublado"),
    45: WeatherSymbol("🌫️", "Niebla"),
    48: WeatherSymbol("🌫️", "Niebla con escarcha"),
    51: WeatherSymbol("🌦️", "Llovizna ligera"),
    53: WeatherSymbol("🌦️", "Llovizna moderada"),
    55: WeatherSymbol("🌧️", "Llovizna densa"),
    56: WeatherSymbol("🌨️", "Llovizna helada ligera"),
    57: WeatherSymbol("🌨️", "Llovizna helada densa"),
    61: WeatherSymbol("🌦️", "Lluvia ligera"),
    63: WeatherSymbol("🌧️", "Lluvia moderada"),
    65: WeatherSymbol("🌧️", "Lluvia fuerte"),
    66: WeatherSymbol("🌨️", "Lluvia helada ligera"),
    67: WeatherSymbol("🌨️", "Lluvia helada fuerte"),
    71: WeatherSymbol("🌨️", "Nieve ligera"),
    73: WeatherSymbol("🌨️", "Nieve moderada"),
    75: WeatherSymbol("❄️", "Nieve fuerte"),
    77: WeatherSymbol("🌨️", "Granizo blando"),
    80: WeatherSymbol("🌦️", "Chubascos ligeros"),
    81: WeatherSymbol("🌧️", "Chubascos moderados"),
    82: WeatherSymbol("⛈️", "Chubascos fuertes"),
    85: WeatherSymbol("🌨️", "Chubascos de nieve ligeros"),
    86: WeatherSymbol("🌨️", "Chubascos de nieve fuertes"),
    95: WeatherSymbol("⛈️", "Tormenta"),
    96: WeatherSymbol("⛈️", "Tormenta con granizo ligero"),
    99: WeatherSymbol("⛈️", "Tormenta con granizo fuerte"),
}


def get_weather_symbol(code: int) -> WeatherSymbol:
    """Retorna el emoji y descripción para un código de símbolo meteorológico WMO.

    Si el código no está mapeado, retorna un símbolo genérico.
    """
    return SYMBOL_MAP.get(code, WeatherSymbol("❓", "Desconocido"))
