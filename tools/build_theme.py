#!/usr/bin/env python3
"""Alcantara themes for Home Assistant.

Suede (Alcantara) surfaces with upholstery stitching, in five colorways:
  - Page background: a quilted diamond tile. Suede grain (SVG feTurbulence), a soft "puff" in each diamond, and
    dashed thread along the seams.
  - Cards: the same grain, a stitched seam about 6 px inside the edge with dashed corners, and a pressed
    shadow under the thread. It's built only from layered CSS gradients in --ha-card-background, so no card-mod
    is needed.
  - Top bar: a dashed thread line under the header.

Themes:
  - Alcantara: auto. Dove when the device is light, Graphite when it's dark.
  - Alcantara Graphite, Nero, Navy, Cognac: dark only (modes.dark only, so HA forces dark mode).
  - Alcantara Dove: light only.

The textures are SVGs embedded as data URIs, so the theme is a single self-contained YAML file (HACS installs
only the themes/ folder; there's nothing to copy into www/).

  python3 tools/build_theme.py            # regenerate themes/alcantara.yaml
  python3 tools/build_theme.py --check    # exit 1 if themes/alcantara.yaml is out of date (CI)

Then reload themes in Home Assistant (Developer tools > Actions > frontend.reload_themes). Edit this script, not
the generated file. Standard library only, Python 3.9+.
"""
import base64
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
THEMES = REPO / "themes" / "alcantara.yaml"

# name, slug, dark?, page, card, border (seam), stitch (thread), primary, text, text2, icon
SCHEMES = [
    dict(name="Graphite", slug="graphite", dark=True, page="#1b1c1f", card="#25272b", seam="#121315",
         stitch="#d8232f", primary="#e5323e", text="#ececee", text2="#a3a5ab", icon="#bfc2c8"),
    dict(name="Nero", slug="nero", dark=True, page="#111111", card="#1b1b1c", seam="#070707",
         stitch="#f3c316", primary="#f5c518", text="#efefef", text2="#a6a6a6", icon="#c9c9c9"),
    dict(name="Navy", slug="navy", dark=True, page="#111a2a", card="#18233a", seam="#0a1120",
         stitch="#d6dbe3", primary="#7da8ff", text="#e7ecf4", text2="#9ca8bb", icon="#c3ccda"),
    dict(name="Cognac", slug="cognac", dark=True, page="#211812", card="#2c2119", seam="#140d09",
         stitch="#d48b3f", primary="#e39a4c", text="#f2e8dc", text2="#bba792", icon="#d9c6b1"),
    dict(name="Dove", slug="dove", dark=False, page="#cfccc6", card="#e5e2dc", seam="#b4b0a8",
         stitch="#d0531c", primary="#c24a15", text="#1f1e1c", text2="#5d5a55", icon="#55524d"),
]
DEFAULT_LIGHT, DEFAULT_DARK = "dove", "graphite"


# ---- color helpers -------------------------------------------------------------------------------------------------
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    """t=0 -> a, t=1 -> b"""
    ra, rb = rgb(a), rgb(b)
    return hexc([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def luminance(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgbs(h):
    return ", ".join(str(v) for v in rgb(h))


def rgba(h, a):
    return "rgba(%s, %s)" % (rgbs(h), a)


# ---- SVG assets ----------------------------------------------------------------------------------------------------
def grain_filter(fid, fiber, alpha_gain, alpha_bias, freq, seed):
    r, g, b = (v / 255 for v in rgb(fiber))
    return (f'<filter id="{fid}" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" seed="{seed}" stitchTiles="stitch"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 {r:.3f} 0 0 0 0 {g:.3f} 0 0 0 0 {b:.3f} {alpha_gain} 0 0 0 {alpha_bias}"/>'
            f'</filter>')


def grain_layers(s, size):
    """Two noise layers: light fibers catching light, dark fibers in shadow. Directional (x finer than y) like a nap."""
    lite = "#ffffff" if s["dark"] else "#fffdf8"
    return (grain_filter("gl", lite, 0.32 if s["dark"] else 0.3, -0.13 if s["dark"] else -0.12, "0.7 0.45", 11)
            + grain_filter("gd", "#000000", 0.42, -0.16 if s["dark"] else -0.18, "0.6 0.38", 29)
            + grain_filter("gm", "#000000", 0.6 if s["dark"] else 0.3, -0.24 if s["dark"] else -0.13, "0.03 0.018", 5),
            f'<rect width="{size}" height="{size}" filter="url(#gm)"/>'
            f'<rect width="{size}" height="{size}" filter="url(#gl)"/>'
            f'<rect width="{size}" height="{size}" filter="url(#gd)"/>')


def quilt_svg(s, size=96):
    """One quilted diamond tile: seams on both diagonals, so diamonds are centered on the edge midpoints."""
    defs, layers = grain_layers(s, size)
    diag = size * math.sqrt(2)
    n = round(diag / 7.4)                     # whole number of stitches per diagonal, so tiles meet seamlessly
    period = diag / n
    dash, gap = period * 0.6, period * 0.4
    half = size / 2
    puff_hi = 0.07 if s["dark"] else 0.10
    puff_lo = 0.30 if s["dark"] else 0.07
    puffs = "".join(f'<circle cx="{x}" cy="{y}" r="{half}" fill="url(#puff)"/>'
                    for x, y in ((half, 0), (0, half), (size, half), (half, size)))
    seam = f"M0 0L{size} {size}M{size} 0L0 {size}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<defs>{defs}'
            f'<radialGradient id="puff"><stop offset="0" stop-color="#fff" stop-opacity="{puff_hi}"/>'
            f'<stop offset=".7" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#000" stop-opacity="{puff_lo * 0.5}"/></radialGradient></defs>'
            f'<rect width="{size}" height="{size}" fill="{s["page"]}"/>{puffs}{layers}'
            # the seam: a soft groove, then the thread with a needle-hole shadow under it
            f'<path d="{seam}" stroke="#000" stroke-opacity="{puff_lo * 0.7:.2f}" stroke-width="4"/>'
            f'<path d="{seam}" stroke="#000" stroke-opacity="{.45 if s["dark"] else .18}" stroke-width="1.6" stroke-dasharray="{dash:.3f} {gap:.3f}" '
            f'transform="translate(0 .7)"/>'
            f'<path d="{seam}" stroke="{s["stitch"]}" stroke-opacity="{0.38 if s["dark"] else 0.4}" stroke-width="1.3" '
            f'stroke-dasharray="{dash:.3f} {gap:.3f}" stroke-linecap="round"/>'
            f'</svg>')


def grain_svg(s, size=160):
    defs, layers = grain_layers(s, size)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<defs>{defs}</defs>{layers}</svg>')


# ---- card background: stitched seam in CSS gradients ---------------------------------------------------------------
INSET, RADIUS, THREAD, DASH, GAP = 6, 16, 1.6, 5, 3.5


def stitch_layers(color, dx=0.0, dy=0.0):
    """Four dashed runs 6px inside the edge, stopping where the corner radius starts, plus two dashes per corner
    (quarter-ring radial gradients clipped by small boxes)."""
    c, t, i, r = color, THREAD, INSET, RADIUS
    run = f"calc(100% - {2 * r}px)"
    h = f"repeating-linear-gradient(90deg, {c} 0 {DASH}px, transparent {DASH}px {DASH + GAP}px)"
    v = f"repeating-linear-gradient(180deg, {c} 0 {DASH}px, transparent {DASH}px {DASH + GAP}px)"
    L = [f"{h} left {r + dx}px top {i + dy}px / {run} {t}px no-repeat",
         f"{h} left {r + dx}px bottom {i - dy}px / {run} {t}px no-repeat",
         f"{v} left {i + dx}px top {r + dy}px / {t}px {run} no-repeat",
         f"{v} right {i - dx}px top {r + dy}px / {t}px {run} no-repeat"]
    # Corner: ring centered on (r, r) from the corner, radius r - i - t/2. Two short dashes, split by a gap.
    rr = r - i
    ring = lambda cx, cy: (f"radial-gradient(circle at {cx}px {cy}px, transparent {rr - t / 2:.2f}px, {c} {rr - t / 2:.2f}px "
                           f"{rr + t / 2:.2f}px, transparent {rr + t / 2:.2f}px)")
    a = 5.4  # how far each corner dash reaches from the run's end towards the corner (px along the axis)
    for hx, vy in (("left", "top"), ("right", "top"), ("left", "bottom"), ("right", "bottom")):
        # dash 1: box hugging the vertical run's end; dash 2: box hugging the horizontal run's end
        bx1, by1, bw1, bh1 = i - t / 2, r - a, a + t, a        # box in corner-local coords (corner at 0,0)
        bx2, by2, bw2, bh2 = r - a, i - t / 2, a, a + t
        for bx, by, bw, bh in ((bx1, by1, bw1, bh1), (bx2, by2, bw2, bh2)):
            cx, cy = r - bx, r - by                          # ring center relative to the box (top-left corner case)
            if hx == "right":
                cx = bw - cx
            if vy == "bottom":
                cy = bh - cy
            L.append(f"{ring(round(cx, 2), round(cy, 2))} {hx} {bx + (dx if hx == 'left' else -dx):.2f}px "
                     f"{vy} {by + (dy if vy == 'top' else -dy):.2f}px / {bw:.2f}px {bh:.2f}px no-repeat")
    return L


def card_background(s, grain_url):
    shadow = rgba("#000000", 0.55 if s["dark"] else 0.25)
    return ", ".join(stitch_layers(s["stitch"]) + stitch_layers(shadow, 0, 0.8)
                     + [f"url('{grain_url}') 0 0 / 160px 160px", s["card"]])


# ---- theme variables -----------------------------------------------------------------------------------------------
def scheme_vars(s, urls):
    d = s["dark"]
    p = s["primary"]
    v = {
        "primary-color": p,
        "dark-primary-color": mix(p, "#000000", 0.25),
        "light-primary-color": mix(p, "#ffffff", 0.45),
        "accent-color": s["stitch"],
        "text-primary-color": "#141414" if luminance(p) > 0.33 else "#ffffff",
        "primary-background-color": s["page"],
        "secondary-background-color": mix(s["page"], s["card"], 0.5),
        "card-background-color": s["card"],
        "ha-card-background": card_background(s, urls["grain"]),
        "ha-card-border-color": s["seam"],
        "ha-card-border-width": "1px",
        "ha-card-border-radius": f"{RADIUS}px",
        "ha-card-box-shadow": ("inset 0 1px 0 rgba(255,255,255,.05), inset 0 -1px 0 rgba(0,0,0,.35), "
                               "0 2px 3px rgba(0,0,0,.35), 0 10px 24px rgba(0,0,0,.30)") if d else
                              ("inset 0 1px 0 rgba(255,255,255,.55), inset 0 -1px 0 rgba(0,0,0,.08), "
                               "0 1px 2px rgba(0,0,0,.12), 0 8px 20px rgba(0,0,0,.10)"),
        "ha-dialog-surface-background": s["card"],
        "lovelace-background": f"url('{urls['quilt']}') 0 0 / 96px 96px, {s['page']}",
        "app-header-background-color": mix(s["page"], "#000000", 0.25 if d else 0.0) if d else s["card"],
        "app-header-text-color": s["text"],
        "app-header-border-bottom": f"2px dashed {rgba(s['stitch'], 0.85)}",
        "app-header-edit-background-color": mix(s["page"], p, 0.25),
        "app-header-edit-text-color": s["text"],
        "sidebar-background-color": mix(s["page"], "#000000", 0.3) if d else mix(s["page"], "#ffffff", 0.25),
        "sidebar-text-color": s["text2"],
        "sidebar-icon-color": s["text2"],
        "sidebar-selected-icon-color": s["stitch"],
        "sidebar-selected-text-color": s["text"],
        "sidebar-menu-button-text-color": s["text"],
        "primary-text-color": s["text"],
        "secondary-text-color": s["text2"],
        "disabled-text-color": mix(s["text2"], s["page"], 0.45),
        "divider-color": rgba(s["seam"], 0.9) if d else rgba(s["seam"], 0.8),
        "state-icon-color": s["icon"],
        "state-active-color": p,
        "state-switch-active-color": p,
        "state-fan-active-color": p,
        "state-light-active-color": "#ffc65a" if d else "#e09a12",
        "switch-checked-color": p,
        "switch-checked-button-color": p,
        "switch-checked-track-color": p,
        "slider-color": p,
        "slider-track-color": mix(s["card"], s["text2"], 0.35),
        "success-color": "#3cbf63" if d else "#2a8f48",
        "warning-color": "#f0a43a" if d else "#b8700c",
        "error-color": "#ff4d4d" if d else "#c62828",
        "info-color": "#64a0ff" if d else "#2f67c7",
        "code-editor-background-color": mix(s["card"], "#000000", 0.25 if d else 0.04),
        "markdown-code-background-color": mix(s["card"], "#000000" if d else "#ffffff", 0.2),
        "data-table-background-color": s["card"],
        "scrollbar-thumb-color": mix(s["card"], s["text2"], 0.35),
        "badge-background-color": s["card"],
        "alcantara-stitch-color": s["stitch"],
        "graph-color-1": p,
        "graph-color-2": s["text2"],
        "graph-color-3": "#f0a43a",
        "graph-color-4": "#64a0ff",
        "graph-color-5": "#3cbf63",
        "graph-color-6": s["text"],
        "graph-color-7": "#c75fd6",
        "graph-color-8": "#33b6a8",
        "mdc-theme-primary": p,
        "mdc-theme-secondary": s["stitch"],
    }
    # Primary scale used by the newer components (buttons, chips, selection): 05 darkest .. 95 lightest
    for step, t in ((5, -0.85), (10, -0.75), (20, -0.55), (30, -0.3), (40, -0.12), (50, 0.0), (60, 0.2), (70, 0.4),
                    (80, 0.6), (90, 0.8), (95, 0.9)):
        v[f"ha-color-primary-{step:02d}"] = mix(p, "#000000", -t) if t < 0 else mix(p, "#ffffff", t)
    for key in ("primary-color", "accent-color", "primary-text-color", "secondary-text-color", "disabled-text-color",
                "text-primary-color", "primary-background-color", "card-background-color", "state-icon-color",
                "success-color", "warning-color", "error-color", "info-color"):
        v[f"rgb-{key}"] = rgbs(v[key])
    return v


def yaml_block(d, indent):
    pad = " " * indent
    return "".join(f'{pad}{k}: "{val}"\n' for k, val in d.items())


def data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def build():
    out = ["# Generated by tools/build_theme.py (https://github.com/edwork/alcantara-theme).\n",
           "# Edit the generator, not this file.\n",
           "# Alcantara: suede surfaces with upholstery stitching (quilted page, stitched cards, stitched header).\n"]
    by_slug = {}
    for s in SCHEMES:
        urls = {"quilt": data_uri(quilt_svg(s)), "grain": data_uri(grain_svg(s))}
        by_slug[s["slug"]] = scheme_vars(s, urls)
        mode = "dark" if s["dark"] else "light"
        out.append(f'"Alcantara {s["name"]}":\n  modes:\n    {mode}:\n' + yaml_block(by_slug[s["slug"]], 6))
    out.append('"Alcantara":\n  modes:\n    light:\n' + yaml_block(by_slug[DEFAULT_LIGHT], 6)
               + "    dark:\n" + yaml_block(by_slug[DEFAULT_DARK], 6))
    return "".join(out)


def main():
    text = build()
    if "--check" in sys.argv:
        if not THEMES.exists() or THEMES.read_text() != text:
            sys.exit(f"{THEMES.relative_to(REPO)} is out of date: run python3 tools/build_theme.py")
        print(f"{THEMES.relative_to(REPO)} is up to date")
        return
    THEMES.write_text(text)
    print(f"wrote {THEMES.relative_to(REPO)} ({len(text) // 1024} KB, {len(SCHEMES) + 1} themes)")


if __name__ == "__main__":
    main()
