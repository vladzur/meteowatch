"""Tests para el mapeo de símbolos meteorológicos."""

import pytest

from meteowatch.icons import SYMBOL_MAP, WeatherSymbol, get_weather_symbol


class TestWeatherSymbolMap:
    """Pruebas para el mapeo de símbolos meteorológicos."""

    def test_symbol_map_has_expected_keys(self):
        """Debe contener entradas para los códigos 1–41 (catálogo oficial de Meteored)."""
        for code in range(1, 42):
            assert code in SYMBOL_MAP, f"Falta el código {code} en SYMBOL_MAP"

    def test_all_entries_have_emoji_and_description(self):
        """Cada entrada debe tener emoji y descripción no vacíos."""
        for code, symbol in SYMBOL_MAP.items():
            assert symbol.emoji, f"El código {code} no tiene emoji"
            assert symbol.description, f"El código {code} no tiene descripción"

    def test_get_weather_symbol_returns_correct_value(self):
        """Debe retornar el símbolo correcto para un código conocido."""
        symbol = get_weather_symbol(1)
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

    def test_common_symbols_have_distinct_values(self):
        """Los símbolos más comunes deben tener valores distintos."""
        symbols = {
            1: "Despejado",
            5: "Nublado",
            9: "Niebla",
            12: "Lluvia ligera",
            24: "Nieve",
            34: "Tormenta",
        }
        for code, expected_desc in symbols.items():
            symbol = get_weather_symbol(code)
            assert symbol.description == expected_desc, (
                f"Código {code}: esperado '{expected_desc}', "
                f"obtenido '{symbol.description}'"
            )

    def test_weather_symbol_is_named_tuple(self):
        """WeatherSymbol debe ser una tupla con nombre."""
        symbol = get_weather_symbol(1)
        assert hasattr(symbol, "emoji")
        assert hasattr(symbol, "description")
        assert isinstance(symbol, WeatherSymbol)
