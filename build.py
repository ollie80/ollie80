"""Draws the profile card, card-dark.svg and card-light.svg.

    python build.py [path to FreeBodyEngine]

The mark's geometry, the colours and the font come from the engine
(scripts/build_brand.py and engine_assets/font/). The mark is drawn as ASCII
line art traced from that geometry, so it changes if the logo does. Text is
FreeMono outlines rather than <text>: an SVG shown through <img> can't load
fonts, so GitHub would fall back to whatever monospace it has.
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "freebody", "FreeBodyEngine"))

spec = importlib.util.spec_from_file_location("build_brand", os.path.join(ENGINE, "scripts", "build_brand.py"))
brand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brand)

import freetype

FONTS = {
    "r": os.path.join(ENGINE, "FreeBodyEngine", "engine_assets", "font", "FreeMono.otf"),
    "b": os.path.join(ENGINE, "FreeBodyEngine", "engine_assets", "font", "FreeMono-Bold.otf"),
}

THEMES = {
    "dark": dict(bg="#060e08", edge="#174d2c", title="#d4fff0", key="#5df0a2", value="#8effc8",
                 dots="#245f3a", muted="#3d8f5c", mark="#8effc8", word="#5df0a2", glow=True,
                 swatches=["#0c1a0f", "#174d2c", "#245f3a", "#3d8f5c", "#1cb56a", "#5df0a2", "#8effc8", "#d4fff0"]),
    "light": dict(bg="#f4f9f5", edge="#d5e4d9", title="#0b3d22", key="#1f7a4a", value="#0b3d22",
                  dots="#b9d1c0", muted="#6c8a76", mark="#0b3d22", word="#1f7a4a", glow=False,
                  swatches=["#0b3d22", "#14532f", "#1f7a4a", "#2f8f5a", "#3d8f5c", "#6c8a76", "#9db8a5", "#d5e4d9"]),
}

# The wordmark from the old card, kept as it was.
WORDMARK = [
    "  ______                 ____             _",
    " |  ____|               |  _ \\           | |",
    " | |__  _ __  ___   ___ | |_| | ___    __| | _   _",
    " |  __|| '__|/ _ \\ / _ \\|  _ / / _ \\  / _` || | | |",
    " | |   | |  |  __/|  __/| |_| | (_) || |_| || |_| |",
    " |_|   |_|   \\___|\\___| |____/ \\___/ \\___,_| \\__, |",
    "                                             __/  |",
    "                                             |___/",
]

INFO_SECTIONS = [
    ("Languages", ["Python · C++ · JavaScript"]),
    ("Tools", ["OpenGL · Vulkan · WebGL2 · GLFW · SDL2",
               "pybind11 · NumPy · Pyodide · Git · Neovim"]),
    ("Projects", ["FreeBodyEngine  game engine · Python + C++",
                  "FBUSL           my shader language"]),
]
INFO_FIELDS = [
    ("Site", "freebody.dev"),
    ("Email", "olivermorrison08@outlook.com"),
]


# -- the mark as ASCII --------------------------------------------------------------------

def ascii_mark(cols):
    """The mark as line art, `cols` characters wide. Every edge is traced
    with characters picked by its angle: edges along the slope climb a row
    every four columns, which `_.-'` does too, and edges square to it run
    one column per row, like `\\`. Arrow shafts are single lines and the
    heads are filled, so they still read as arrows this small."""
    rows = round(cols * 0.6 / 1.25)  # FreeMono's cells are 0.6 x 1.25em: this keeps it square
    sx, sy = cols / 32, rows / 32
    grid = [[" "] * (cols + 2) for _ in range(rows + 2)]

    def put(c, r, ch):
        if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
            grid[r][c] = ch

    def edge(a, z):
        (x0, y0), (x1, y1) = (a[0] * sx, a[1] * sy), (z[0] * sx, z[1] * sy)
        dx, dy = x1 - x0, y1 - y0
        if abs(dy) * 2.2 < abs(dx):  # shallow: a character per column, by how high the edge is in it
            for c in range(math.floor(min(x0, x1)), math.ceil(max(x0, x1))):
                if min(x0, x1) <= c + 0.5 <= max(x0, x1):
                    y = y0 + (c + 0.5 - x0) / dx * dy
                    f = y - math.floor(y)
                    put(c, math.floor(y), "'" if f < 0.25 else "-" if f < 0.5 else "." if f < 0.75 else "_")
        else:  # steep: a character per row
            for r in range(math.floor(min(y0, y1)), math.ceil(max(y0, y1))):
                if min(y0, y1) <= r + 0.5 <= max(y0, y1):
                    x = x0 + (r + 0.5 - y0) / dy * dx
                    lean = dx / dy
                    put(math.floor(x), r, "|" if abs(lean) < 0.3 else "\\" if lean > 0 else "/")

    def inside(x, y, poly):
        hit = False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[i - 1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
        return hit

    # Resting right on the slope: the gap that keeps them apart when the
    # mark is drawn large only doubles the line here.
    gap, brand.GAP = brand.GAP, 0.0
    polygons, (centre, _) = brand.mark_shapes()
    brand.GAP = gap
    slope, block, *arrows = polygons

    for poly in (slope, block):
        for i in range(len(poly)):
            edge(poly[i - 1], poly[i])
    for shaft, head in (arrows[0:2], arrows[2:4]):
        mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        edge(mid(shaft[0], shaft[3]), mid(shaft[1], shaft[2]))
        for r in range(rows + 2):
            for c in range(cols + 2):
                if inside((c + 0.5) / sx, (r + 0.5) / sy, head):
                    put(c, r, "#")
        for i in range(len(head)):
            edge(head[i - 1], head[i])
    put(math.floor(centre[0] * sx) - 1, math.floor(centre[1] * sy), "(")
    put(math.floor(centre[0] * sx), math.floor(centre[1] * sy), ")")

    lines = ["".join(row).rstrip() for row in grid]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


# -- type ---------------------------------------------------------------------------

class Type:
    """FreeMono as SVG: each glyph used is one <path> in <defs>, in font
    units, drawn where it's needed with a <use>. FreeMono is monospaced, so
    laying out a line is just stepping 0.6em per character."""

    ADVANCE = 0.6

    def __init__(self):
        self.faces = {w: freetype.Face(path) for w, path in FONTS.items()}
        self.defs = {}

    def _glyph(self, weight, ch):
        key = f"{weight}{ord(ch)}"
        if key in self.defs:
            return key
        face = self.faces[weight]
        face.load_char(ch, freetype.FT_LOAD_NO_SCALE | freetype.FT_LOAD_NO_BITMAP)
        d = []
        pt = lambda p: f"{p.x},{-p.y}"
        face.glyph.outline.decompose(
            None,
            move_to=lambda p, _: d.append(f"M{pt(p)}"),
            line_to=lambda p, _: d.append(f"L{pt(p)}"),
            conic_to=lambda c, p, _: d.append(f"Q{pt(c)} {pt(p)}"),
            cubic_to=lambda c1, c2, p, _: d.append(f"C{pt(c1)} {pt(c2)} {pt(p)}"),
        )
        self.defs[key] = f'<path id="{key}" d="{"".join(d)}Z"/>' if d else ""
        return key

    def text(self, s, x, baseline, size, fill, weight="r"):
        """`s` with its first glyph's left edge at x, as <use>s."""
        k = size / self.faces[weight].units_per_EM
        out = []
        for i, ch in enumerate(s):
            if ch != " ":
                gx = x + i * self.ADVANCE * size
                out.append(f'<use href="#{self._glyph(weight, ch)}" transform="translate({gx:.1f} {baseline:.1f}) scale({k:.4f})"/>')
        return f'<g fill="{fill}">{"".join(out)}</g>'

    def block(self, lines, x, top, size, fill, weight="r"):
        """Lines of text, 1.25em apart - ASCII art's line height."""
        return "".join(self.text(line, x, top + size + i * size * 1.25, size, fill, weight) for i, line in enumerate(lines))

    def width(self, s, size):
        return len(s) * self.ADVANCE * size

    def defs_svg(self):
        return "".join(v for v in self.defs.values() if v)


# -- the card --------------------------------------------------------------------------

GLOW = ('<filter id="glow" x="-10%" y="-10%" width="120%" height="120%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="blur"/>'
        '<feComponentTransfer in="blur" result="soft"><feFuncA type="linear" slope="0.8"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="soft"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def card(theme):
    t = THEMES[theme]
    type_ = Type()
    W, H = 985, 585
    art = 14  # the ASCII art's font size
    body = []

    left = 26
    mark = type_.block(ascii_mark(52), left, 22, art, t["mark"], "b")
    word = type_.block(WORDMARK, left, 22 + 24 * art * 1.25, art, t["word"], "b")
    body.append(f'<g filter="url(#glow)">{mark}{word}</g>' if t["glow"] else mark + word)

    x, size, step = 500, 16, 26
    # Centred down the card, beside the art.
    info_height = 62 + sum(step * (1 + len(items)) + 8 for _, items in INFO_SECTIONS) + step * len(INFO_FIELDS) + 20
    top = (H - info_height) / 2
    body.append(type_.text("ollie@freebody", x, top + 18, 22, t["title"], "b"))
    # The prompt's cursor, blinking - CSS animations run in an <img>'d SVG.
    cx = x + type_.width("ollie@freebody", 22) + 6
    body.append(f'<rect class="cursor" x="{cx:.1f}" y="{top:.1f}" width="12" height="22" fill="{t["key"]}"/>')
    body.append(type_.text("-" * 14, x, top + 40, 22, t["muted"]))

    baseline = top + 80
    for heading, items in INFO_SECTIONS:
        body.append(type_.text(heading, x, baseline, size, t["key"], "b"))
        baseline += step
        for item in items:
            body.append(type_.text("  " + item, x, baseline, size, t["value"]))
            baseline += step
        baseline += 8

    label_cols = 10
    for key, value in INFO_FIELDS:
        body.append(type_.text(key, x, baseline, size, t["key"], "b"))
        dots = "." * (label_cols - len(key) - 2)
        body.append(type_.text(dots, x + type_.width(key + " ", size), baseline, size, t["dots"]))
        body.append(type_.text(value, x + type_.width(" " * label_cols, size), baseline, size, t["value"]))
        baseline += step

    # neofetch's colour blocks, in the palette's greens
    for i, colour in enumerate(t["swatches"]):
        body.append(f'<rect x="{x + i * 30}" y="{baseline + 4}" width="30" height="16" fill="{colour}"/>')

    style = ('<style>@keyframes blink{50%{opacity:0}}.cursor{animation:blink 1.1s steps(1) infinite}'
             '@media (prefers-reduced-motion: reduce){.cursor{animation:none}}</style>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<defs>{type_.defs_svg()}{GLOW if t["glow"] else ""}</defs>{style}'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" stroke="{t["edge"]}"/>'
            f'{"".join(body)}</svg>\n')


def main():
    print("\n".join(ascii_mark(52)))
    for theme in THEMES:
        content = card(theme)
        with open(os.path.join(HERE, f"card-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  card-{theme}.svg  {len(content) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
