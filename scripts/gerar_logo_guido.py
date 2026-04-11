"""Gera um PNG quadrado (1000x1000) com o logo do Guido centralizado.

As coordenadas do logo vêm do SVG usado no nav do site:
  viewBox 0 0 155 52, stroke-width=6, linecap=round, cor #1D9E75.

O output é salvo em scripts/guido-profile.png.
"""
from PIL import Image, ImageDraw

# ── Config ──
SIZE = 1000  # imagem quadrada final
BG_COLOR = (13, 17, 23)       # #0D1117 (night background do site)
FG_COLOR = (29, 158, 117)      # #1D9E75 (verde do Guido)

# O logo original é 155x52. Vou escalar pra ocupar ~70% da largura do quadrado,
# centralizado verticalmente.
LOGO_W_ORIG, LOGO_H_ORIG = 155, 52
TARGET_LOGO_W = int(SIZE * 0.70)
scale = TARGET_LOGO_W / LOGO_W_ORIG
TARGET_LOGO_H = int(LOGO_H_ORIG * scale)

# Offset pra centralizar no quadrado
ox = (SIZE - TARGET_LOGO_W) // 2
oy = (SIZE - TARGET_LOGO_H) // 2

def sx(x: float) -> float:
    return ox + x * scale
def sy(y: float) -> float:
    return oy + y * scale

STROKE = max(1, int(6 * scale))  # escala o stroke junto

# ── Canvas ──
img = Image.new("RGB", (SIZE, SIZE), BG_COLOR)
draw = ImageDraw.Draw(img)

def draw_line_round(p1, p2, color, width):
    """Linha com caps arredondados (simulado com círculos nas pontas)."""
    x1, y1 = p1
    x2, y2 = p2
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    r = width / 2
    draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=color)
    draw.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=color)

def draw_rounded_rect_outline(x, y, w, h, radius, color, width):
    """Retângulo arredondado só com contorno, escalado."""
    draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=radius,
        outline=color,
        width=width,
    )

# ── Desenho (coordenadas do SVG original, escaladas via sx/sy) ──
# Haste esquerda: line (18,17) → (2,5)
draw_line_round((sx(18), sy(17)), (sx(2), sy(5)), FG_COLOR, STROKE)
# Lente esquerda: rect x=18 y=8 w=40 h=28 rx=8
draw_rounded_rect_outline(
    sx(18), sy(8), 40 * scale, 28 * scale,
    radius=int(8 * scale), color=FG_COLOR, width=STROKE,
)
# Ponte: line (58,22) → (97,22)
draw_line_round((sx(58), sy(22)), (sx(97), sy(22)), FG_COLOR, STROKE)
# Lente direita: rect x=97 y=8 w=40 h=28 rx=8
draw_rounded_rect_outline(
    sx(97), sy(8), 40 * scale, 28 * scale,
    radius=int(8 * scale), color=FG_COLOR, width=STROKE,
)
# Haste direita: line (137,17) → (153,5)
draw_line_round((sx(137), sy(17)), (sx(153), sy(5)), FG_COLOR, STROKE)

# ── Salva ──
import os
out = os.path.join(os.path.dirname(__file__), "guido-profile.png")
img.save(out, "PNG", optimize=True)
print(f"OK: {out} ({os.path.getsize(out)} bytes)")
