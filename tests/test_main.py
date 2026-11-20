"""Tests para el arranque de la aplicación (selección de renderizador GSK)."""

import os
from unittest.mock import patch

import pytest

from meteowatch.main import _ensure_renderer_fallback


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Elimina las variables de entorno que afectan la selección de renderizador."""
    monkeypatch.delenv("GSK_RENDERER", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("GDK_BACKEND", raising=False)


class TestRendererFallback:
    """Pruebas para el fallback a Cairo cuando no hay dispositivos DRM."""

    def test_sets_cairo_when_no_drm_devices(self):
        """Debe forzar Cairo en X11 cuando /dev/dri no tiene dispositivos."""
        with patch("meteowatch.main.glob.glob", return_value=[]):
            _ensure_renderer_fallback()

        assert os.environ.get("GSK_RENDERER") == "cairo"

    def test_keeps_renderer_when_drm_device_present(self):
        """Debe respetar el renderizador por defecto si hay un dispositivo DRM."""
        with patch("meteowatch.main.glob.glob",
                   side_effect=lambda pattern: ["/dev/dri/renderD128"]):
            _ensure_renderer_fallback()

        assert "GSK_RENDERER" not in os.environ

    def test_respects_explicit_renderer(self, monkeypatch):
        """No debe sobrescribir un GSK_RENDERER definido por el usuario."""
        monkeypatch.setenv("GSK_RENDERER", "gl")

        with patch("meteowatch.main.glob.glob", return_value=[]):
            _ensure_renderer_fallback()

        assert os.environ.get("GSK_RENDERER") == "gl"

    def test_skips_on_wayland(self, monkeypatch):
        """No debe forzar Cairo en sesiones Wayland."""
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")

        with patch("meteowatch.main.glob.glob", return_value=[]):
            _ensure_renderer_fallback()

        assert "GSK_RENDERER" not in os.environ

    def test_applies_when_x11_forced_over_wayland(self, monkeypatch):
        """Debe aplicar si GDK_BACKEND fuerza X11 aunque exista Wayland."""
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        monkeypatch.setenv("GDK_BACKEND", "x11")

        with patch("meteowatch.main.glob.glob", return_value=[]):
            _ensure_renderer_fallback()

        assert os.environ.get("GSK_RENDERER") == "cairo"
