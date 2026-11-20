"""Punto de entrada de la aplicación Meteowatch.

Inicia la aplicación GTK 4 + libadwaita para mostrar
pronósticos meteorológicos de Open-Meteo.
"""

import glob
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from meteowatch.app import MeteowatchApp


def _ensure_renderer_fallback() -> None:
    """Fuerza el renderizador Cairo cuando no hay dispositivos DRM disponibles.

    Sin nodos en `/dev/dri` (por ejemplo, un Flatpak sin `--device=dri`), GTK
    no puede inicializar EGL/OpenGL. En X11 eso termina en un error X fatal
    (`BadDrawable`, `request_code 149` = GLX) que aborta la aplicación durante
    el primer frame. Cairo no usa GL, así que evita ese camino.

    Solo aplica cuando el backend efectivo es X11; en Wayland el fallback lo
    maneja el compositor. No hace nada si el entorno ya define `GSK_RENDERER`.
    """
    if "GSK_RENDERER" in os.environ:
        return

    backends = [
        backend.strip()
        for backend in os.environ.get("GDK_BACKEND", "").split(",")
        if backend.strip()
    ]
    if not backends:
        backends = ["wayland"] if os.environ.get("WAYLAND_DISPLAY") else ["x11"]
    if backends[0] != "x11":
        return

    if glob.glob("/dev/dri/renderD*") or glob.glob("/dev/dri/card*"):
        return
    os.environ["GSK_RENDERER"] = "cairo"


def main() -> int:
    """Función principal de la aplicación.

    Returns:
        Código de salida (0 = éxito).
    """
    _ensure_renderer_fallback()

    # Inicializar libadwaita (tema, estilos, etc.)
    Adw.init()

    app = MeteowatchApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
