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
    # Códigos de visibilidad reducida (WMO 4-19)
    4: WeatherSymbol("💨", "Humo"),
    5: WeatherSymbol("🌫️", "Neblina"),
    6: WeatherSymbol("🌫️", "Polvo en suspensión"),
    7: WeatherSymbol("💨", "Polvo levantado"),
    8: WeatherSymbol("🌪️", "Remolinos de polvo"),
    9: WeatherSymbol("🌪️", "Tormenta de polvo"),
    10: WeatherSymbol("🌫️", "Bruma"),
    11: WeatherSymbol("🌫️", "Bancos de niebla"),
    12: WeatherSymbol("🌫️", "Niebla parcial"),
    13: WeatherSymbol("🌩️", "Relámpagos visibles"),
    14: WeatherSymbol("🌧️", "Precipitación a la vista"),
    15: WeatherSymbol("🌧️", "Precipitación distante"),
    16: WeatherSymbol("🌧️", "Precipitación cercana"),
    17: WeatherSymbol("🌩️", "Tormenta sin precipitación"),
    18: WeatherSymbol("🌪️", "Turbonada"),
    19: WeatherSymbol("🌪️", "Nubes embudo"),
    # Códigos de niebla y escarcha
    20: WeatherSymbol("🌫️", "Niebla"),
    21: WeatherSymbol("🌨️", "Precipitación"),
    22: WeatherSymbol("🌨️", "Llovizna"),
    23: WeatherSymbol("🌧️", "Lluvia"),
    24: WeatherSymbol("❄️", "Nieve"),
    25: WeatherSymbol("🌧️", "Chubascos"),
    26: WeatherSymbol("🌩️", "Tormenta eléctrica"),
    27: WeatherSymbol("🌨️", "Granizo"),
    28: WeatherSymbol("🌫️", "Niebla"),
    29: WeatherSymbol("🌩️", "Tormenta"),
    # Códigos de tormenta de polvo/arena (WMO 30-35)
    30: WeatherSymbol("🌪️", "Tormenta de polvo ligera"),
    31: WeatherSymbol("🌪️", "Tormenta de polvo"),
    32: WeatherSymbol("🌪️", "Tormenta de polvo fuerte"),
    33: WeatherSymbol("🌪️", "Tormenta de arena ligera"),
    34: WeatherSymbol("🌪️", "Tormenta de arena"),
    35: WeatherSymbol("🌪️", "Tormenta de arena fuerte"),
    # Códigos de niebla y escarcha (WMO 40-49)
    40: WeatherSymbol("🌫️", "Niebla a distancia"),
    41: WeatherSymbol("🌫️", "Niebla en parches"),
    42: WeatherSymbol("🌫️", "Niebla"),
    43: WeatherSymbol("🌫️", "Niebla"),
    44: WeatherSymbol("🌫️", "Niebla"),
    45: WeatherSymbol("🌫️", "Niebla"),
    46: WeatherSymbol("🌫️", "Niebla"),
    47: WeatherSymbol("🌫️", "Niebla"),
    48: WeatherSymbol("🌫️", "Niebla con escarcha"),
    49: WeatherSymbol("🌫️", "Niebla con escarcha"),
    # Códigos de llovizna (WMO 50-59)
    50: WeatherSymbol("🌦️", "Llovizna ligera intermitente"),
    51: WeatherSymbol("🌦️", "Llovizna ligera"),
    52: WeatherSymbol("🌦️", "Llovizna moderada intermitente"),
    53: WeatherSymbol("🌦️", "Llovizna moderada"),
    54: WeatherSymbol("🌧️", "Llovizna densa intermitente"),
    55: WeatherSymbol("🌧️", "Llovizna densa"),
    56: WeatherSymbol("🌨️", "Llovizna helada ligera"),
    57: WeatherSymbol("🌨️", "Llovizna helada densa"),
    58: WeatherSymbol("🌧️", "Llovizna y lluvia ligera"),
    59: WeatherSymbol("🌧️", "Llovizna y lluvia fuerte"),
    # Códigos de lluvia (WMO 60-69)
    60: WeatherSymbol("🌦️", "Lluvia ligera intermitente"),
    61: WeatherSymbol("🌦️", "Lluvia ligera"),
    62: WeatherSymbol("🌧️", "Lluvia moderada intermitente"),
    63: WeatherSymbol("🌧️", "Lluvia moderada"),
    64: WeatherSymbol("🌧️", "Lluvia fuerte intermitente"),
    65: WeatherSymbol("🌧️", "Lluvia fuerte"),
    66: WeatherSymbol("🌨️", "Lluvia helada ligera"),
    67: WeatherSymbol("🌨️", "Lluvia helada fuerte"),
    68: WeatherSymbol("🌨️", "Lluvia y nieve ligera"),
    69: WeatherSymbol("🌨️", "Lluvia y nieve fuerte"),
    # Códigos de nieve (WMO 70-79)
    70: WeatherSymbol("🌨️", "Nieve ligera intermitente"),
    71: WeatherSymbol("🌨️", "Nieve ligera"),
    72: WeatherSymbol("🌨️", "Nieve moderada intermitente"),
    73: WeatherSymbol("🌨️", "Nieve moderada"),
    74: WeatherSymbol("❄️", "Nieve fuerte intermitente"),
    75: WeatherSymbol("❄️", "Nieve fuerte"),
    76: WeatherSymbol("❄️", "Agujas de hielo"),
    77: WeatherSymbol("🌨️", "Granizo blando"),
    78: WeatherSymbol("❄️", "Cristales de nieve"),
    79: WeatherSymbol("🌨️", "Hielo granulado"),
    # Códigos de chubascos (WMO 80-89)
    80: WeatherSymbol("🌦️", "Chubascos ligeros"),
    81: WeatherSymbol("🌧️", "Chubascos moderados"),
    82: WeatherSymbol("⛈️", "Chubascos fuertes"),
    83: WeatherSymbol("🌨️", "Chubascos de nieve y lluvia ligeros"),
    84: WeatherSymbol("🌨️", "Chubascos de nieve y lluvia fuertes"),
    85: WeatherSymbol("🌨️", "Chubascos de nieve ligeros"),
    86: WeatherSymbol("🌨️", "Chubascos de nieve fuertes"),
    87: WeatherSymbol("🌨️", "Chubascos de granizo blando ligeros"),
    88: WeatherSymbol("🌨️", "Chubascos de granizo blando fuertes"),
    89: WeatherSymbol("🌨️", "Chubascos de granizo ligeros"),
    90: WeatherSymbol("🌨️", "Chubascos de granizo fuertes"),
    # Códigos de tormenta (WMO 95-99)
    91: WeatherSymbol("🌧️", "Lluvia ligera con tormenta"),
    92: WeatherSymbol("⛈️", "Lluvia fuerte con tormenta"),
    93: WeatherSymbol("🌨️", "Nieve ligera con tormenta"),
    94: WeatherSymbol("🌨️", "Nieve fuerte con tormenta"),
    95: WeatherSymbol("⛈️", "Tormenta"),
    96: WeatherSymbol("⛈️", "Tormenta con granizo ligero"),
    97: WeatherSymbol("⛈️", "Tormenta con granizo fuerte"),
    98: WeatherSymbol("⛈️", "Tormenta con polvo o arena"),
    99: WeatherSymbol("⛈️", "Tormenta con granizo fuerte"),
}


def get_weather_symbol(code: int) -> WeatherSymbol:
    """Retorna el emoji y descripción para un código de símbolo meteorológico WMO.

    Si el código no está mapeado, retorna un símbolo genérico.
    """
    return SYMBOL_MAP.get(code, WeatherSymbol("❓", "Desconocido"))
