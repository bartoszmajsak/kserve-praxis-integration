"""Drawing primitives for the figures: tiles, groups, edges, pills, rails and a legend.

Every mark carries CSS classes (`d-tile`, `d-head`, `d-edge` and so on) and no colour
of its own. Inlined in a page, the page CSS styles the marks through its colour tokens.
For a standalone file `themes.py` resolves the same rules to literal colours.

Text widths are estimated from the character count, so a label that is much longer
than its neighbours needs a look at the rendered figure.
"""
import html

ICONS = {
    "hex": '<path d="M9 2l6 3.5v7L9 16l-6-3.5v-7z"/><circle cx="9" cy="9" r="1.8" fill="currentColor" stroke="none"/>',
    "shield": '<path d="M9 2l5.5 2v4.6c0 3.3-2.3 5.9-5.5 7.4-3.2-1.5-5.5-4.1-5.5-7.4V4z"/><path d="M6.6 9l1.7 1.7 3.2-3.4"/>',
    "route": '<circle cx="4.5" cy="13.5" r="1.6" fill="currentColor" stroke="none"/><circle cx="13.5" cy="4.5" r="1.6" fill="currentColor" stroke="none"/><path d="M4.5 11.5V10c0-2 1.3-3 3.3-3h2.4c1.4 0 2.3-.4 2.9-1.1"/>',
    "pool": '<rect x="3" y="6" width="8.5" height="8.5" rx="1.5"/><path d="M6.5 6V4.5A1.5 1.5 0 0 1 8 3h5.5A1.5 1.5 0 0 1 15 4.5V10a1.5 1.5 0 0 1-1.5 1.5h-2"/>',
    "cr": '<rect x="2.5" y="2.5" width="13" height="13" rx="2.5"/><text x="9" y="11.6" text-anchor="middle" font-size="6.5" font-weight="700" fill="currentColor" stroke="none" font-family="sans-serif">CR</text>',
    "ext": '<path d="M3 6.5h10.5M11 4l2.5 2.5L11 9"/><path d="M15 11.5H4.5M7 9l-2.5 2.5L7 14"/>',
    "ctrl": '<path d="M14 9a5 5 0 1 1-1.7-3.75"/><path d="M12.6 2.6v2.9H9.7"/>',
}


def esc(s):
    return html.escape(s, quote=False)


class Fig:
    """A figure. `pfx` prefixes the ids of its markers, filter and icons, so it has to
    be unique among the figures of one page."""

    ACCENTS = ("", "warn", "px")  # edge colours, one arrowhead marker each
    ICONS = ICONS

    def __init__(self, pfx, w, h, label):
        self.p, self.w, self.h, self.label = pfx, w, h, label
        self.under = []  # edges, drawn first
        self.over = []   # tiles and labels

    # --- marks -----------------------------------------------------------
    def title(self, x, y, text, accent):
        self.over.append(f'<text class="d-title {accent}" x="{x}" y="{y}">{esc(text)}</text>')

    def group(self, x, y, w, h, label, accent=""):
        tw = round(len(label) * 6.3 + 22)
        self.under.insert(0, f'<rect class="d-grp {accent}" x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>')
        self.over.append(f'<rect class="d-tab {accent}" x="{x + 14}" y="{y - 10}" width="{tw}" height="20" rx="5"/>')
        self.over.append(f'<text class="d-tabt" x="{x + 14 + tw / 2}" y="{y + 4}" text-anchor="middle">{esc(label)}</text>')

    def tile(self, x, y, w, h, kind, owner=None, subs=(), accent="", icon=None):
        r, hh = 8, 24
        o = self.over
        o.append(f'<rect class="d-tile" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" filter="url(#{self.p}-sh)"/>')
        o.append(
            f'<path class="d-head {accent}" d="M{x + .6} {y + hh}V{y + r}Q{x + .6} {y + .6} {x + r} {y + .6}'
            f'H{x + w - r}Q{x + w - .6} {y + .6} {x + w - .6} {y + r}V{y + hh}Z"/>'
        )
        o.append(f'<rect class="d-tile-b {accent}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>')
        tx = x + 12
        if icon:
            o.append(f'<use class="d-ico {accent}" href="#{self.p}-i-{icon}" x="{x + 8}" y="{y + 3}" width="18" height="18"/>')
            tx = x + 32
        o.append(f'<text class="d-kind {accent}" x="{tx}" y="{y + 16.5}">{esc(kind)}</text>')
        if owner:
            o.append(f'<text class="d-own" x="{x + w - 10}" y="{y + 16}" text-anchor="end">{esc(owner)}</text>')
        for i, s in enumerate(subs):
            o.append(f'<text class="d-s" x="{x + 12}" y="{y + hh + 18 + i * 16}">{esc(s)}</text>')

    def plain(self, x, y, w, h, text):
        o = self.over
        o.append(f'<rect class="d-tile" x="{x}" y="{y}" width="{w}" height="{h}" rx="8" filter="url(#{self.p}-sh)"/>')
        o.append(f'<rect class="d-tile-b" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
        o.append(f'<text class="d-t" x="{x + w / 2}" y="{y + h / 2 + 4.5}" text-anchor="middle">{esc(text)}</text>')

    def edge(self, pts, accent="", dash=False, both=False):
        m = f"{self.p}-ah" + (f"-{accent}" if accent else "")
        cls = f"d-edge {accent}" + (" dash" if dash else "")
        p = " ".join(f"{x},{y}" for x, y in pts)
        start = f' marker-start="url(#{m})"' if both else ""
        self.under.append(f'<polyline class="{cls}" points="{p}"{start} marker-end="url(#{m})"/>')

    def pill(self, cx, cy, text, accent=""):
        w = round(len(text) * 5.6 + 18)
        self.over.append(f'<rect class="d-pill {accent}" x="{cx - w / 2}" y="{cy - 9}" width="{w}" height="18" rx="9"/>')
        self.over.append(f'<text class="d-pillt {accent}" x="{cx}" y="{cy + 3.6}" text-anchor="middle">{esc(text)}</text>')

    def text(self, x, y, text, cls="d-s", anchor="start"):
        self.over.append(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(text)}</text>')

    def rule(self, x1, y1, x2, y2):
        self.under.append(f'<line class="d-rule" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')

    def legend(self, items):
        """A key along the bottom edge. Items are (swatch, accent, text), where swatch is
        tile, line, dash, rail, group or None. Grows the figure by the height it needs."""
        sizes = {"tile": 18, "line": 30, "dash": 30, "rail": 14, "group": 18, None: 0}
        x0, y0, row_h = 32, self.h + 4, 22
        rows, x = [[]], x0
        for sw, accent, text in items:
            w = sizes[sw] + (8 if sw else 0) + len(text) * 5.9 + 26
            if x + w > self.w - 24 and rows[-1]:
                rows.append([])
                x = x0
            rows[-1].append((x, sw, accent, text))
            x += w
        h = len(rows) * row_h + 10
        o = self.over
        o.append(f'<rect class="d-legend" x="16" y="{y0}" width="{self.w - 32}" height="{h}" rx="8"/>')
        for r, row in enumerate(rows):
            cy = y0 + 5 + r * row_h + row_h / 2
            for x, sw, accent, text in row:
                if sw == "tile":
                    o.append(f'<rect class="d-tile" x="{x}" y="{cy - 6}" width="18" height="12" rx="3"/>')
                    o.append(f'<rect class="d-tile-b {accent}" x="{x}" y="{cy - 6}" width="18" height="12" rx="3"/>')
                elif sw in ("line", "dash"):
                    m = f"{self.p}-ah" + (f"-{accent}" if accent else "")
                    cls = f"d-edge {accent}" + (" dash" if sw == "dash" else "")
                    o.append(f'<line class="{cls}" x1="{x}" y1="{cy}" x2="{x + 30}" y2="{cy}" marker-end="url(#{m})"/>')
                elif sw == "rail":
                    o.append(f'<polyline class="d-rail {accent}" points="{x + 2},{cy - 7} {x + 2},{cy + 3} {x + 14},{cy + 3}"/>')
                elif sw == "group":
                    o.append(f'<rect class="d-grp {accent}" x="{x}" y="{cy - 6}" width="18" height="12" rx="3"/>')
                tx = x + sizes[sw] + (8 if sw else 0)
                o.append(f'<text class="d-lg" x="{tx}" y="{cy + 3.8}">{esc(text)}</text>')
        self.h = y0 + h + 12

    # --- output ----------------------------------------------------------
    def defs(self):
        d = ["<defs>"]
        for a in self.ACCENTS:
            mid = f"{self.p}-ah" + (f"-{a}" if a else "")
            d.append(
                f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" '
                f'orient="auto-start-reverse"><path class="d-ah {a}" d="M0 0 L10 5 L0 10 z"/></marker>'
            )
        d.append(
            f'<filter id="{self.p}-sh" x="-5%" y="-15%" width="110%" height="140%">'
            '<feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.09"/></filter>'
        )
        for name, body in self.ICONS.items():
            d.append(
                f'<symbol id="{self.p}-i-{name}" viewBox="0 0 18 18" fill="none" stroke="currentColor" '
                f'stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">{body}</symbol>'
            )
        d.append("</defs>")
        return d

    def _lines(self, extra=(), xmlns=""):
        return [
            f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{html.escape(self.label)}"{xmlns}>',
            *self.defs(), *extra, *self.under, *self.over, "</svg>",
        ]

    def inline(self, indent=""):
        """The figure for a page: marks with classes only, indented like the placeholder
        it replaces."""
        first, *inner, last = self._lines()
        return "\n".join([indent + first, *(indent + "  " + line for line in inner), indent + last])

    def standalone(self, css, background):
        """The figure as a file of its own: the rules in `css` have literal colours, and
        a rectangle paints the background."""
        extra = (f"<style>\n{css}</style>", f'<rect width="{self.w}" height="{self.h}" fill="{background}"/>')
        return "\n".join(self._lines(extra, ' xmlns="http://www.w3.org/2000/svg"')) + "\n"


# --- relationship maps: three lanes of tiles, one lane per namespace -----------

LANE_W, TILE_W, INDENT = 250, 226, 14
LANES = {"T": 16, "M": 395, "G": 774}


class RelFig(Fig):
    ACCENTS = ("", "warn", "maas")
    ICONS = {}

    def line(self, pts, accent="", dash=False, head=True):
        m = f"{self.p}-ah" + (f"-{accent}" if accent else "")
        cls = f"d-edge {accent}" + (" dash" if dash else "")
        p = " ".join(f"{x},{y}" for x, y in pts)
        end = f' marker-end="url(#{m})"' if head else ""
        self.under.append(f'<polyline class="{cls}" points="{p}"{end}/>')

    def rail(self, owner, children, accent=""):
        """Ownership: a rail from the owner's bottom edge with a tick to each owned tile."""
        x = owner[0] + INDENT / 2
        last = children[-1]
        self.under.append(
            f'<line class="d-rail {accent}" x1="{x}" y1="{owner[1] + owner[3]}" x2="{x}" y2="{last[1] + last[3] / 2}"/>'
        )
        for c in children:
            y = c[1] + c[3] / 2
            self.under.append(f'<line class="d-rail {accent}" x1="{x}" y1="{y}" x2="{c[0]}" y2="{y}"/>')


class Lane:
    """A column of tiles stacked top to bottom. `add` returns the tile's box as
    (x, y, width, height), which `left`, `right` and `RelFig.rail` take."""

    def __init__(self, fig, key, title):
        self.f, self.x, self.y, self.title = fig, LANES[key], 78, title

    def add(self, kind, writer, subs, accent="", indent=0):
        h = 38 + 16 * len(subs)
        x, w = self.x + 12 + INDENT * indent, TILE_W - INDENT * indent
        self.f.tile(x, self.y, w, h, kind, writer, subs, accent=accent)
        box = (x, self.y, w, h)
        self.y += h + 8
        return box

    def close(self):
        bottom = self.y + 6
        self.f.group(self.x, 54, LANE_W, bottom - 54, self.title)
        return bottom


def left(b, y=None):
    return (b[0], b[1] + b[3] / 2 if y is None else y)


def right(b, y=None):
    return (b[0] + b[2], b[1] + b[3] / 2 if y is None else y)
