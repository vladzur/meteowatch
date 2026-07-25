"""Generación dinámica de iconos PNG para el system tray.

Usa Cairo (disponible vía GTK4) para renderizar texto con control
total sobre colores, evitando los problemas de currentColor en SVG
y la renderización impredecible de emojis en distintos paneles.
"""

import logging
import os

import gi

gi.require_version("PangoCairo", "1.0")
gi.require_version("Pango", "1.0")

import cairo  # noqa: E402
from gi.repository import Pango, PangoCairo  # noqa: E402

logger = logging.getLogger(__name__)

# Directorio donde se almacenan los iconos del tray
TRAY_ICON_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "meteowatch",
)
TRAY_ICON_PATH = os.path.join(TRAY_ICON_DIR, "tray-icon.png")
TRAY_ICON_NAME = "meteowatch-tray"

# Dimensiones del icono (ancho flexible, alto fijo ~altura del panel)
ICON_WIDTH = 48
ICON_HEIGHT = 24


def generate_tray_png(symbol_emoji: str, temperature: float | None,
                     output_path: str | None = None) -> str:
    """Genera un PNG con Cairo para el icono del tray.

    Layout horizontal: emoji a la izquierda, temperatura a la derecha.
    Dimensiones 48×24 — el ancho se adapta al panel, alto fijo.

    Args:
        symbol_emoji: Emoji representando la condición climática.
        temperature: Temperatura actual en grados Celsius (puede ser None).
        output_path: Ruta donde guardar el PNG. Si es None, usa TRAY_ICON_PATH.

    Returns:
        Ruta absoluta al archivo PNG generado.
    """
    path = output_path or TRAY_ICON_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ICON_WIDTH, ICON_HEIGHT)
    ctx = cairo.Context(surface)

    # Fondo transparente
    ctx.set_source_rgba(0, 0, 0, 0)
    ctx.paint()

    layout = PangoCairo.create_layout(ctx)
    y_center = ICON_HEIGHT // 2

    if temperature is None:
        _draw_text(ctx, layout, symbol_emoji, "Sans 11",
                   ICON_WIDTH // 2, y_center,
                   centered=True, shadow=False)
    else:
        temp_text = f"{temperature:.0f}°"

        # Emoji a la izquierda
        _draw_text(ctx, layout, symbol_emoji, "Sans 11",
                   3, y_center,
                   centered=False, shadow=False)

        # Temperatura a la derecha, blanca con sombra
        _draw_text(ctx, layout, temp_text, "Sans Bold 11",
                   26, y_center,
                   centered=False, shadow=True)

    surface.write_to_png(path)
    surface.finish()

    logger.debug("Icono PNG de tray escrito en %s", path)
    return path


def _draw_text(ctx, layout, text, font_desc, x, y,
               centered=True, shadow=False):
    """Renderiza texto en el contexto Cairo con Pango.

    Args:
        ctx: Contexto Cairo.
        layout: Layout de Pango.
        text: Texto a renderizar.
        font_desc: Descripción de fuente Pango.
        x, y: Posición del centro del texto.
        centered: Si se debe centrar horizontalmente.
        shadow: Si se debe dibujar sombra para contraste.
    """
    desc = Pango.FontDescription.from_string(font_desc)
    layout.set_font_description(desc)
    layout.set_text(text, -1)

    # Dimensiones del texto
    _ink_rect, logical_rect = layout.get_pixel_extents()
    text_width = logical_rect.width

    # Centrar horizontalmente
    draw_x = x - text_width // 2 if centered else x

    # Centrar verticalmente: Pango usa baseline como origen.
    # logical_rect.y es negativo (distancia baseline → tope del texto).
    # logical_rect.height es la altura total.
    text_midline = logical_rect.y + logical_rect.height // 2
    draw_y = y - text_midline

    if shadow:
        ctx.save()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.move_to(draw_x + 1, draw_y + 1)
        PangoCairo.update_layout(ctx, layout)
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()

    # Texto principal (blanco)
    ctx.set_source_rgb(1, 1, 1)
    ctx.move_to(draw_x, draw_y)
    PangoCairo.update_layout(ctx, layout)
    PangoCairo.show_layout(ctx, layout)


def ensure_tray_icon_exists() -> str:
    """Garantiza que existe un icono de tray por defecto (path 0).

    Returns:
        Ruta absoluta al archivo del icono por defecto.
    """
    default_path = os.path.join(TRAY_ICON_DIR, "tray-icon-0.png")
    if not os.path.isfile(default_path):
        logger.debug("Generando icono de tray PNG por defecto")
        return generate_tray_png("☀️", None, output_path=default_path)
    return default_path
