"""Tests para el módulo de generación de iconos PNG del tray con Cairo."""

import os
import tempfile
from unittest.mock import patch

from meteowatch.tray_icon import (
    TRAY_ICON_DIR,
    ensure_tray_icon_exists,
    generate_tray_png,
)


class TestGenerateTrayPng:
    """Pruebas para la generación de iconos PNG con Cairo."""

    def test_generates_png_with_temperature(self):
        """Debe generar un archivo PNG válido con emoji y temperatura."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "tray-icon.png")
            result = generate_tray_png("\u2600\ufe0f", 22.5,
                                       output_path=test_path)
            assert result == test_path
            assert os.path.isfile(test_path)
            with open(test_path, "rb") as f:
                header = f.read(8)
            assert header[:4] == b"\x89PNG"

    def test_generates_png_without_temperature(self):
        """Debe generar un PNG solo con el emoji si temperature es None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "tray-icon.png")
            result = generate_tray_png("\u2600\ufe0f", None,
                                       output_path=test_path)
            assert result == test_path
            assert os.path.isfile(test_path)

    def test_uses_default_path_when_none(self):
        """Debe usar TRAY_ICON_PATH cuando no se especifica output_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "tray-icon.png")
            with patch("meteowatch.tray_icon.TRAY_ICON_PATH", test_path):
                result = generate_tray_png("\u26c5", 18.0)
                assert result == test_path
                assert os.path.isfile(test_path)

    def test_creates_directory_if_not_exists(self):
        """Debe crear el directorio si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "new", "deep", "dir")
            test_path = os.path.join(subdir, "tray-icon.png")
            generate_tray_png("\u26c5", 18.0, output_path=test_path)
            assert os.path.isfile(test_path)


class TestEnsureTrayIconExists:
    """Pruebas para la creación del icono por defecto."""

    def test_creates_default_icon_when_not_exists(self):
        """Debe crear un icono PNG por defecto si el archivo no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = os.path.join(tmpdir, "tray-icon-0.png")
            with patch("meteowatch.tray_icon.TRAY_ICON_DIR", tmpdir):
                if os.path.exists(default_path):
                    os.remove(default_path)
                result = ensure_tray_icon_exists()
                assert result == default_path
                assert os.path.isfile(default_path)

    def test_does_not_overwrite_existing_icon(self):
        """No debe sobrescribir un icono existente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            default_path = os.path.join(tmpdir, "tray-icon-0.png")
            with patch("meteowatch.tray_icon.TRAY_ICON_DIR", tmpdir):
                generate_tray_png("\U0001f327\ufe0f", 12.0,
                                  output_path=default_path)
                mtime_before = os.path.getmtime(default_path)

                result = ensure_tray_icon_exists()
                assert result == default_path
                mtime_after = os.path.getmtime(default_path)
                assert mtime_before == mtime_after
