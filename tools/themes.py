"""Colours of the standalone figures.

A figure inlined in a page is styled by `src/style.css` through `var(--token)`. A
standalone SVG has no page around it, so the build takes the diagram rules of the
stylesheet and replaces every token with the literal value of one theme.

The table repeats the token values of the `:root` and dark blocks of the stylesheet.
`check_tokens` stops the build when the two disagree.
"""
import re

from errors import require

THEMES = ("light", "dark")

# What a standalone file is painted on. The dark value is GitHub's dark canvas. The marks
# keep the colours they have in the page, tints included. Only this backdrop differs from
# the page, where a figure sits on `--canvas`.
BACKGROUND = {"light": "#ffffff", "dark": "#0d1117"}

# A standalone file cannot load the web font of the pages.
SANS = "'Inter','Helvetica Neue',Arial,sans-serif"

# token: (light, dark)
TOKENS = {
    "panel":       ("#ffffff", "#161d25"),
    "canvas":      ("#eef1f5", "#121920"),
    "actor":       ("#eaeef3", "#202a35"),
    "fg":          ("#16202b", "#e5eaf0"),
    "muted":       ("#586574", "#9ba8b6"),
    "line":        ("#d6dce4", "#2a3541"),
    "line-strong": ("#8492a2", "#6b7a8b"),
    # the request path figures
    "gw":   ("#2459a6", "#78aef0"),
    "px":   ("#0b7d60", "#4ecba6"),
    # the relationship maps, one accent per writer
    "ks":   ("#2459a6", "#78aef0"),
    "maas": ("#0b7d60", "#4ecba6"),
    "gc":   ("#6b46c1", "#b79cf2"),
    "agc":  ("#8a6100", "#e0b040"),
    "warn": ("#c0352b", "#ff8a80"),
}

MARKS = "/* diagram marks"  # the diagram rules of the stylesheet start at this comment

_HEX = r"#[0-9a-f]{6}"
_DECLARATION = re.compile(r"--([a-z-]+):\s*([^;]+);")
_BLOCKS = {
    "light": r":root\s*\{(.*?)\}",
    "dark, system setting": r':root:not\(\[data-theme="light"\]\)\s*\{(.*?)\}',
    "dark, explicit": r':root\[data-theme="dark"\]\s*\{(.*?)\}',
}


def mix(a, percent, b):
    """`color-mix(in srgb, a percent%, b)` for two opaque `#rrggbb` colours."""
    share = percent / 100
    channels = (int(a[i:i + 2], 16) * share + int(b[i:i + 2], 16) * (1 - share) for i in (1, 3, 5))
    return "#" + "".join(f"{int(c + 0.5):02x}" for c in channels)


def check_tokens(css):
    """Compare the table with the token blocks in the stylesheet."""
    found = {}
    for block, pattern in _BLOCKS.items():
        m = re.search(pattern, css, flags=re.S)
        require(m, f"style.css: no {block} token block")
        found[block] = dict(_DECLARATION.findall(re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)))
    require(found["dark, system setting"] == found["dark, explicit"], "style.css: the two dark token blocks differ")
    for token, (light, dark) in TOKENS.items():
        for block, want in (("light", light), ("dark, explicit", dark)):
            got = found[block].get(token, "missing").strip()
            require(got == want, f"style.css: --{token} is {got} ({block}) and {want} in tools/themes.py")


def marks_css(css):
    require(MARKS in css, f"style.css: no '{MARKS}' comment in front of the diagram rules")
    return css[css.index(MARKS):]


def standalone_css(css, theme):
    """The diagram rules of the stylesheet with literal colours for `theme`."""
    index = THEMES.index(theme)
    values = {token: pair[index] for token, pair in TOKENS.items()}
    values["sans"] = SANS

    def token(m):
        require(m.group(1) in values, f"style.css: the diagram rules use --{m.group(1)}, which tools/themes.py does not define")
        return values[m.group(1)]

    rules = re.sub(r"/\*.*?\*/", "", marks_css(css), flags=re.S)
    rules = re.sub(r"var\(--([a-z-]+)\)", token, rules)
    rules = re.sub(
        rf"color-mix\(in srgb, ({_HEX}) (\d+)%, ({_HEX})\)",
        lambda m: mix(m.group(1), int(m.group(2)), m.group(3)),
        rules,
    )
    for left_over in ("var(", "color-mix(", "<", "&"):
        require(left_over not in rules, f"style.css: cannot resolve '{left_over}' in the diagram rules")
    return "".join(line.strip() + "\n" for line in rules.splitlines() if line.strip())
