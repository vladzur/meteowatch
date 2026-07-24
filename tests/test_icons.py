"""Tests para el mapeo de símbolos meteorológicos WMO."""

import pytest

from meteowatch.icons import SYMBOL_MAP, WeatherSymbol, get_weather_symbol


class TestWeatherSymbolMap:
    """Pruebas para el mapeo de símbolos meteorológicos WMO."""

    def test_symbol_map_has_expected_keys(self):
        """Debe contener entradas para los códigos WMO esperados."""
        expected_codes = [0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57,
                          61, 63, 65, 66, 67, 71, 73, 75, 77,
                          80, 81, 82, 85, 86, 95, 96, 99]
        for code in expected_codes:
            assert code in SYMBOL_MAP, f"Falta el código WMO {code} en SYMBOL_MAP"

    def test_all_entries_have_emoji_and_description(self):
        """Cada entrada debe tener emoji y descripción no vacíos."""
        for code, symbol in SYMBOL_MAP.items():
            assert symbol.emoji, f"El código WMO {code} no tiene emoji"
            assert symbol.description, f"El código WMO {code} no tiene descripción"

    def test_get_weather_symbol_returns_correct_value(self):
        """Debe retornar el símbolo correcto para un código WMO conocido."""
        symbol = get_weather_symbol(0)
        assert symbol.emoji == "☀️"
        assert symbol.description == "Despejado"

    def test_get_weather_symbol_returns_default_for_unknown(self):
        """Debe retornar símbolo genérico para códigos no mapeados."""
        symbol = get_weather_symbol(999)
        assert symbol.emoji == "❓"
        assert symbol.description == "Desconocido"

    def test_get_weather_symbol_returns_default_for_negative(self):
        """Debe retornar símbolo genérico para códigos negativos."""
        symbol = get_weather_symbol(-1)
        assert symbol.emoji == "❓"
        assert symbol.description == "Desconocido"

    def test_common_wmo_symbols_have_distinct_values(self):
        """Los símbolos WMO más comunes deben tener valores distintos."""
        symbols = {
            0: "Despejado",
            3: "Nublado",
            45: "Niebla",
            61: "Lluvia ligera",
            71: "Nieve ligera",
            95: "Tormenta",
        }
        for code, expected_desc in symbols.items():
            symbol = get_weather_symbol(code)
            assert symbol.description == expected_desc, (
                f"Código WMO {code}: esperado '{expected_desc}', "
                f"obtenido '{symbol.description}'"
            )

    def test_weather_symbol_is_named_tuple(self):
        """WeatherSymbol debe ser una tupla con nombre."""
        symbol = get_weather_symbol(0)
        assert hasattr(symbol, "emoji")
        assert hasattr(symbol, "description")
        assert isinstance(symbol, WeatherSymbol)
