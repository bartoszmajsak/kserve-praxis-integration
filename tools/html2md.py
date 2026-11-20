"""Convert the body of a page to GitHub-flavoured Markdown.

It knows the elements the pages use and nothing else. Markup it does not know stops
the build, because the alternative is content that goes missing without notice.
"""
import html
import re
from html.parser import HTMLParser

from errors import BuildError, require

FIGURE = "#figure"  # the node a `<!-- figure: NAME -->` comment becomes
PLACEHOLDER = re.compile(r"figure:\s*([a-z0-9-]+)")
WRAPPERS = {"div", "section", "header", "figure"}  # layout only, their children are rendered in place
DECORATIVE = {"chips", "chip", "stroke"}  # legend swatches drawn with CSS


class Node:
    def __init__(self, tag, attrs=(), line=0):
        self.tag, self.attrs, self.line, self.children = tag, dict(attrs), line, []

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def elements(self):
        """Child elements. Text between them has to be whitespace."""
        for child in self.children:
            if isinstance(child, Node):
                yield child
            elif child.strip():
                raise unknown(self, f"text directly inside <{self.tag}>: {child.strip()[:40]!r}")


def unknown(node, what=None):
    return BuildError(f"line {node.line}: the Markdown converter does not handle {what or f'<{node.tag}> here'}")


def children(node, *tags):
    """The child elements of `node`, which all have to be one of `tags`."""
    for child in node.elements():
        if child.tag not in tags:
            raise unknown(child, f"<{child.tag}> inside <{node.tag}>")
        yield child


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.open = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.getpos()[0])
        self.open[-1].children.append(node)
        self.open.append(node)

    def handle_endtag(self, tag):
        node = self.open[-1]
        require(node.tag == tag, f"line {self.getpos()[0]}: </{tag}> does not close <{node.tag}> from line {node.line}")
        self.open.pop()

    def handle_data(self, data):
        self.open[-1].children.append(data)

    def handle_comment(self, data):
        m = PLACEHOLDER.fullmatch(data.strip())
        if m:
            self.open[-1].children.append(Node(FIGURE, {"name": m.group(1)}, self.getpos()[0]))


def escape(text):
    """Escape what Markdown would read as markup in running text."""
    text = re.sub(r"([\\`*_\[\]<])", r"\\\1", text)
    return re.sub(r"&(?=#?\w+;)", "&amp;", text)


def code(text):
    text = " ".join(text.split())
    fence = "`"
    while fence in text:
        fence += "`"
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def inline(node):
    parts = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(escape(child))
        elif child.tag == "code":
            if any(isinstance(part, Node) for part in child.children):
                raise unknown(child, "markup inside <code>")
            parts.append(code("".join(child.children)))
        elif child.tag == "a":
            parts.append(f"[{inline(child)}]({child.attrs.get('href', '')})")
        elif child.tag == "span" and child.classes & DECORATIVE:
            continue
        elif child.tag == "span" and not child.classes:
            parts.append(inline(child))
        else:
            raise unknown(child, f"<{child.tag}> inside <{node.tag}>")
    return " ".join("".join(parts).split())


def block_start(text):
    """Escape a first character that would turn a paragraph or a list item into a
    heading, a quote or a nested list."""
    text = re.sub(r"^(#{1,6}|[-+>])(?=\s|$)", r"\\\1", text)
    return re.sub(r"^(\d+)([.)])(?=\s|$)", r"\1\\\2", text)


def sentence(text):
    """The eyebrow is a label with a middle dot between its parts. Under the title it
    reads as a sentence."""
    text = text.replace(" · ", ", ")
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


def row(cells):
    return re.sub(r" {2,}", " ", "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")


def table(head, rows, line):
    for cells in rows:
        require(len(cells) == len(head),
                f"line {line}: a table row has {len(cells)} cells under {len(head)} headers: {cells[:1]}")
    return "\n".join([row(head), "|" + "---|" * len(head), *(row(cells) for cells in rows)])


def html_table(node):
    head, rows = None, []
    for part in children(node, "thead", "tbody"):
        for tr in children(part, "tr"):
            cells = [inline(cell) for cell in children(tr, "th", "td")]
            if part.tag == "thead":
                require(head is None, f"line {tr.line}: a pipe table has one header row")
                head = cells
            else:
                rows.append(cells)
    require(head, f"line {node.line}: a pipe table needs a header row")
    return table(head, rows, node.line)


def answers(node):
    """The summary tiles: a label, a headline and a paragraph each."""
    rows = []
    for tile in children(node, "div"):
        parts = list(tile.elements())
        require([(part.tag, part.classes) for part in parts] == [("span", {"q"}), ("span", {"a"}), ("p", set())],
                f"line {tile.line}: a summary tile is span.q, span.a and a paragraph")
        rows.append([inline(part) for part in parts])
    return table(["Topic", "Summary", "Detail"], rows, node.line)


class Converter:
    def __init__(self, alt):
        self.alt = alt        # figure name to alternative text
        self.eyebrow = None   # held until the title it belongs under

    def picture(self, node):
        name = node.attrs["name"]
        return (
            f'<picture><source media="(prefers-color-scheme: dark)" srcset="figs/{name}-dark.svg">'
            f'<img src="figs/{name}.svg" alt="{html.escape(self.alt[name])}"></picture>'
        )

    def blocks(self, parent):
        out = []
        for node in parent.elements():
            tag, classes = node.tag, node.classes
            if tag == "div" and "eyebrow" in classes:
                self.eyebrow = sentence(inline(node))
            elif tag == "div" and "answers" in classes:
                out.append(answers(node))
            elif tag in WRAPPERS:
                out += self.blocks(node)
            elif tag in ("h1", "h2", "h3"):
                out.append("#" * int(tag[1]) + " " + inline(node))
                if tag == "h1" and self.eyebrow:
                    out.append(self.eyebrow)
                    self.eyebrow = None
            elif tag == "p" and "src" in classes:
                continue  # points at notes that are not in the repository
            elif tag in ("p", "figcaption"):
                out.append(block_start(inline(node)))
            elif tag == "ul":
                out.append("\n".join("- " + block_start(inline(li)) for li in children(node, "li")))
            elif tag == "table":
                out.append(html_table(node))
            elif tag == FIGURE:
                out.append(self.picture(node))
            else:
                raise unknown(node)
        return out


def convert(body, alt, first_line=1):
    """`body` is the page from `<div class="page">` on, with figure placeholders. `alt`
    maps a figure name to its alternative text. `first_line` is where `body` starts in
    the source file, so that errors name the line to look at."""
    tree = Tree()
    tree.feed("\n" * (first_line - 1) + body)
    tree.close()
    require(tree.open == [tree.root], f"<{tree.open[-1].tag}> from line {tree.open[-1].line} is not closed")
    converter = Converter(alt)
    blocks = converter.blocks(tree.root)
    require(converter.eyebrow is None, "the eyebrow has no <h1> after it")
    return "\n\n".join(blocks) + "\n"
