"""Draws the profile's SVGs: the fetch card and the two repo cards, each in
a dark and a light version.

    python build.py [path to FreeBodyEngine]

The mark, colours and font come from the engine (scripts/build_brand.py and
engine_assets/font/), and the engine's numbers - commits, tests - are read
from its checkout, so running this again brings them up to date. Text is
drawn as FreeMono outlines rather than <text>: an SVG shown through <img>
can't load fonts, so GitHub would fall back to whatever monospace it has.
"""
import importlib.util
import os
import re
import subprocess
import tempfile
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
                 dots="#245f3a", muted="#3d8f5c", mark="#8effc8", glow=True,
                 swatches=["#0c1a0f", "#174d2c", "#245f3a", "#3d8f5c", "#1cb56a", "#5df0a2", "#8effc8", "#d4fff0"]),
    "light": dict(bg="#f4f9f5", edge="#d5e4d9", title="#0b3d22", key="#1f7a4a", value="#0b3d22",
                  dots="#b9d1c0", muted="#6c8a76", mark="#0b3d22", glow=False,
                  swatches=["#0b3d22", "#14532f", "#1f7a4a", "#2f8f5a", "#3d8f5c", "#6c8a76", "#9db8a5", "#d5e4d9"]),
}


# -- facts ------------------------------------------------------------------------

def engine_facts():
    """The engine's numbers as of its last commit - what anyone looking at
    the public repo can see, not whatever's uncommitted locally."""
    git = lambda *args: subprocess.run(["git", "-C", ENGINE, *args], capture_output=True, text=True).stdout.strip()
    commits = int(git("rev-list", "--count", "HEAD"))
    first = git("log", "--reverse", "--format=%ad", "--date=format:%Y").splitlines()[0]
    with tempfile.TemporaryDirectory() as committed:
        archive = subprocess.run(["git", "-C", ENGINE, "archive", "HEAD", "tests", "pytest.ini"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", committed], input=archive, check=True)
        collected = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q", "-p", "no:cacheprovider",
                                    "--ignore=tests/graphics/test_vulkan.py"], cwd=committed, capture_output=True, text=True).stdout
    tests = int(re.search(r"(\d+) tests? collected", collected).group(1))
    # Rounded down: "400+" stays true between runs of this script.
    return dict(commits=commits, since=first, tests=f"{tests // 100 * 100}+")


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

    def text(self, s, x, baseline, size, fill, weight="r", tracking=0.0):
        """`s` with its first glyph's left edge at x, as <use>s."""
        k = size / self.faces[weight].units_per_EM
        out = []
        for i, ch in enumerate(s):
            if ch != " ":
                gx = x + i * (self.ADVANCE * size + tracking)
                out.append(f'<use href="#{self._glyph(weight, ch)}" transform="translate({gx:.1f} {baseline:.1f}) scale({k:.4f})"/>')
        return f'<g fill="{fill}">{"".join(out)}</g>'

    def width(self, s, size, tracking=0.0):
        return len(s) * self.ADVANCE * size + (len(s) - 1) * tracking

    def defs_svg(self):
        return "".join(v for v in self.defs.values() if v)


def svg(width, height, theme, body, type_, extra_defs=""):
    t = THEMES[theme]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
            f'<defs>{type_.defs_svg()}{extra_defs}</defs>'
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{t["bg"]}" stroke="{t["edge"]}"/>'
            f'{body}</svg>\n')


def mark(theme, x, y, size):
    """The FreeBody mark at (x, y), size x size, glowing on dark."""
    t = THEMES[theme]
    k = size / 32
    paths = brand.mark_svg_paths(t["mark"], k, (x, y))
    if t["glow"]:
        return f'<g filter="url(#glow)">{paths}</g>', brand.glow_filter(k).removeprefix("<defs>").removesuffix("</defs>")
    return paths, ""


# -- the fetch card --------------------------------------------------------------------

def fetch_card(theme, facts):
    t = THEMES[theme]
    type_ = Type()
    W, H = 985, 440
    body = []

    mark_svg, glow = mark(theme, 58, 52, 270)
    body.append(mark_svg)
    word = "FreeBody"
    body.append(type_.text(word, 193 - type_.width(word, 44) / 2, 392, 44, t["title"], "b"))

    x, size, step = 400, 16, 27
    body.append(type_.text("ollie@freebody", x, 66, 22, t["title"], "b"))
    # The prompt's cursor, blinking - CSS animations run in an <img>'d SVG.
    cx = x + type_.width("ollie@freebody", 22) + 6
    body.append(f'<rect class="cursor" x="{cx:.1f}" y="48" width="12" height="22" fill="{t["key"]}"/>')
    body.append(type_.text("-" * 14, x, 88, 22, t["muted"]))

    rows = [
        ("Studio", "FreeBody"),
        ("Engine", "FreeBodyEngine, Python + C++"),
        ("Renderers", "OpenGL 3.3/4.4 · Vulkan · GLES · WebGL2"),
        ("Runs on", "desktop · Android · browser · terminal"),
        ("Shaders", "FBUSL (mine) → GLSL + SPIR-V"),
        ("Engine stats", f"{facts['commits']} commits · {facts['tests']} tests · since {facts['since']}"),
        ("Languages", "Python · C++ · FBUSL"),
        ("Setup", "Arch · Hyprland · Neovim · kitty"),
        ("Site", "freebody.dev"),
        ("Discord", "ollie80"),
    ]
    label_cols = 16
    for i, (key, value) in enumerate(rows):
        baseline = 124 + i * step
        body.append(type_.text(key, x, baseline, size, t["key"], "b"))
        dots = " " + "." * (label_cols - len(key) - 2) + " "
        body.append(type_.text(dots, x + type_.width(key + " ", size) - type_.ADVANCE * size, baseline, size, t["dots"]))
        body.append(type_.text(value, x + label_cols * type_.ADVANCE * size, baseline, size, t["value"]))

    # neofetch's colour blocks, in the palette's greens
    sy = 124 + len(rows) * step - 2
    for i, colour in enumerate(t["swatches"]):
        body.append(f'<rect x="{x + i * 30}" y="{sy}" width="30" height="16" fill="{colour}"/>')

    style = ('<style>@keyframes blink{50%{opacity:0}}.cursor{animation:blink 1.1s steps(1) infinite}'
             '@media (prefers-reduced-motion: reduce){.cursor{animation:none}}</style>')
    return svg(W, H, theme, style + "".join(body), type_, glow)


# -- repo cards ---------------------------------------------------------------------------

def repo_card(theme, name, lines, footer):
    t = THEMES[theme]
    type_ = Type()
    W, H = 480, 150
    body = []
    mark_svg, glow = mark(theme, 22, 20, 40)
    body.append(mark_svg)
    body.append(type_.text(name, 76, 48, 22, t["title"], "b"))
    for i, line in enumerate(lines):
        body.append(type_.text(line, 24, 88 + i * 20, 14, t["value"]))
    body.append(type_.text(footer, 24, 132, 13, t["muted"]))
    return svg(W, H, theme, "".join(body), type_, glow)


REPOS = {
    "engine": ("FreeBodyEngine",
               ["A game engine in Python and C++. One codebase",
                "for OpenGL, Vulkan, Android and the browser."],
               "Python · C++ · docs.freebody.dev"),
    "fbusl": ("FBUSL",
              ["The FreeBody shader language: shaders written",
               "like Python, compiled to GLSL and SPIR-V."],
              "Python · transpiler"),
}


def main():
    facts = engine_facts()
    print("engine:", facts)
    for theme in THEMES:
        files = {f"card-{theme}.svg": fetch_card(theme, facts)}
        for key, (name, lines, footer) in REPOS.items():
            files[f"{key}-{theme}.svg"] = repo_card(theme, name, lines, footer)
        for filename, content in files.items():
            with open(os.path.join(HERE, filename), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  {filename}  {len(content) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
