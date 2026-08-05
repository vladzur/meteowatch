"""Tests de estructura para el widget WeatherReportCard y WeatherReportDialog.

Verifica que los métodos requeridos existen y son callables.
La lógica de UI con GTK requiere display, por lo que se testea
la estructura de la clase y las funciones helper.
"""

import pytest

from meteowatch.report.engine import ReportEngine


# ------------------------------------------------------------------
# Tests: WeatherReportDialog (estructura)
# ------------------------------------------------------------------

class TestWeatherReportDialogStructure:
    """Tests de estructura de la clase WeatherReportDialog."""

    def test_class_exists(self):
        """La clase WeatherReportDialog debe poder importarse."""
        from meteowatch.widgets.report_card import WeatherReportDialog
        assert WeatherReportDialog is not None

    def test_has_required_methods(self):
        """Debe tener los métodos requeridos."""
        from meteowatch.widgets.report_card import WeatherReportDialog

        required = [
            "_build_ui",
            "_on_copy_clicked",
            "_on_close_clicked",
            "_reset_copy_button",
        ]
        for method_name in required:
            assert hasattr(WeatherReportDialog, method_name), \
                f"Falta el método {method_name} en WeatherReportDialog"
            assert callable(getattr(WeatherReportDialog, method_name)), \
                f"{method_name} no es callable"


# ------------------------------------------------------------------
# Tests: WeatherReportCard (estructura)
# ------------------------------------------------------------------

class TestWeatherReportCardStructure:
    """Tests de estructura de la clase WeatherReportCard."""

    def test_class_exists_and_imports(self):
        """La clase WeatherReportCard debe poder importarse."""
        from meteowatch.widgets.report_card import WeatherReportCard
        assert WeatherReportCard is not None

    def test_has_required_methods(self):
        """Debe tener los métodos requeridos por la spec."""
        from meteowatch.widgets.report_card import WeatherReportCard

        required_methods = [
            "set_forecast_data",
            "_on_generate_clicked",
            "_set_loading_state",
            "_do_generate",
            "_on_report_ready",
            "_enable_generate_button",
            "_on_expander_toggled",
            "_build_ui",
        ]

        # Verificar que la clase define estos métodos
        for method_name in required_methods:
            assert hasattr(WeatherReportCard, method_name), \
                f"Falta el método {method_name} en WeatherReportCard"

    def test_constructor_accepts_engine(self, monkeypatch):
        """El constructor debe aceptar un ReportEngine como argumento."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        from meteowatch.widgets.report_card import WeatherReportCard

        engine = ReportEngine()

        # Verificar que la clase acepta un engine (sin instanciar GTK)
        # Solo verificamos la signatura, no instanciamos
        import inspect
        sig = inspect.signature(WeatherReportCard.__init__)
        params = list(sig.parameters.keys())
        # Debe tener 'engine' como parámetro (después de self)
        assert "engine" in params


class TestWeatherReportCardFunctions:
    """Tests de funciones y constantes del módulo report_card."""

    def test_cooldown_constant_exists(self):
        """La constante COOLDOWN_SECONDS debe existir y ser positiva."""
        from meteowatch.widgets.report_card import COOLDOWN_SECONDS
        assert COOLDOWN_SECONDS > 0

    def test_imports_no_circular(self):
        """Las importaciones del módulo no deben causar errores circulares."""
        # Si llegamos aquí, las importaciones funcionaron
        import meteowatch.widgets.report_card  # noqa: F401
