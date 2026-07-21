"""Punto de entrada de la aplicación Meteowatch.

Inicia la aplicación GTK 4 + libadwaita para mostrar
pronósticos meteorológicos de Meteored.
"""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from meteowatch.app import MeteowatchApp


def main() -> int:
    """Función principal de la aplicación.

    Returns:
        Código de salida (0 = éxito).
    """
    # Inicializar libadwaita (tema, estilos, etc.)
    Adw.init()

    app = MeteowatchApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
