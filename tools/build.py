#!/usr/bin/env python3
"""Build everything that is generated from `src/` and `tools/`.

Usage: build.py [--out DIR]

Writes, under DIR (the repository root by default):
  docs/NAME.md               the page as GitHub-flavoured Markdown
  docs/figs/FIG[-dark].svg   every figure as a standalone file, light and dark
  site/NAME.html, index.html standalone HTML documents
  build/artifact/NAME.html   the page source with its figures inlined, for the host

Files in those directories that the build no longer produces are removed. The output
depends on `src/` and `tools/` only, so two runs give the same bytes.
"""
import argparse
import html
import re
import sys
from pathlib import Path
from typing import NamedTuple

import html2md
import site_html
import themes
from errors import BuildError, require
from figures import FIGURES

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ("docs", "site", "build/artifact")

SITE_TITLE = "KServe and Praxis integration"
SITE_LEDE = (
    "What changes for a KServe `LLMInferenceService` when the data plane moves "
    "from Gateway API on Istio to Praxis."
)


class Page(NamedTuple):
    name: str         # src/NAME.html
    description: str  # one sentence for the site index


PAGES = (
    Page(
        "ingress-paths",
        "How a request reaches the model today and with Praxis, what breaks between MaaS and KServe "
        "when the per-model HTTPRoute goes away, and who should own the `ModelProvider`.",
    ),
    Page(
        "cr-relationships",
        "Which custom resource references which, which one owns which, and which controller writes "
        "each, today and in three options for routing a model through Praxis.",
    ),
)

PLACEHOLDER = re.compile(r"^([ \t]*)<!-- figure: ([a-z0-9-]+) -->[ \t]*$", flags=re.M)
BODY = '<div class="page">'


class Source(NamedTuple):
    text: str         # the whole file
    title: str        # as text, entities decoded
    font_links: list
    css: str          # content of the style block
    body: str         # from the page div on, placeholders included
    body_line: int    # line of the page div in the file


def read_source(page):
    """Split a page source into its parts and check that it is still the fragment the
    host expects: a title, a font link and one style block in front of the page div,
    and no document skeleton."""
    text = (ROOT / "src" / f"{page.name}.html").read_text(encoding="utf-8")
    require(text.startswith("<title>"), f"{page.name}: the source has to start with <title>")
    require(BODY in text, f"{page.name}: no {BODY}")
    skeleton = re.search(r"<(!doctype|html|head|body)\b", text, flags=re.I)
    if skeleton:
        raise BuildError(f"{page.name}: the source is a fragment, {skeleton.group(0)} does not belong in it")
    head, body = text.split(BODY, 1)
    styles = re.findall(r"<style>(.*?)</style>", head, flags=re.S)
    require(len(styles) == 1, f"{page.name}: expected one <style> block, found {len(styles)}")
    title = re.match(r"<title>(.*?)</title>", head)
    require(title, f"{page.name}: the <title> is not closed on the first line")
    links = re.findall(r"<link [^>]*>", head)
    return Source(text, html.unescape(title.group(1)), links, styles[0], BODY + body, head.count("\n") + 1)


def check_classes(page, figs, css):
    """Every class a figure uses needs a rule in the diagram CSS of its page."""
    svg = "\n".join(fig.inline() for fig in figs.values())
    used = {c for classes in re.findall(r'class="([^"]+)"', svg) for c in classes.split()}
    defined = set(re.findall(r"\.([a-z][a-z0-9-]*)", themes.marks_css(page.name, css)))
    missing = sorted(used - defined)
    require(not missing, f"{page.name}: figure classes without a rule in the page CSS: {missing}")


def render():
    """Every generated file as {path relative to the output root: content}."""
    out, placed = {}, {}
    sources = {page.name: read_source(page) for page in PAGES}
    links = [("index.html", "Overview")] + [(f"{p.name}.html", sources[p.name].title) for p in PAGES]

    for page in PAGES:
        src = sources[page.name]
        themes.check_tokens(page.name, src.css)

        figs = {}
        for _, name in PLACEHOLDER.findall(src.text):
            require(name in FIGURES, f"{page.name}: no figure named {name} in tools/figures.py")
            require(name not in placed, f"figure {name} is placed twice, the second time in {page.name}")
            placed[name] = page.name
            figs[name] = FIGURES[name].build()
        prefixes = [fig.p for fig in figs.values()]
        require(len(set(prefixes)) == len(prefixes), f"{page.name}: two figures share an id prefix: {prefixes}")
        check_classes(page, figs, src.css)

        inlined = PLACEHOLDER.sub(lambda m: figs[m.group(2)].inline(m.group(1)), src.text)
        require("<!-- figure:" not in inlined, f"{page.name}: a figure placeholder has to be on a line of its own")

        out[f"build/artifact/{page.name}.html"] = inlined
        out[f"site/{page.name}.html"] = site_html.document(
            src.title, page.description, src.font_links, src.css, inlined[inlined.index(BODY):],
            links, f"{page.name}.html",
        )
        alt = {name: FIGURES[name].alt for name in figs}
        try:
            out[f"docs/{page.name}.md"] = html2md.convert(src.body, alt, src.body_line)
        except BuildError as error:
            raise BuildError(f"{page.name}: {error}") from None
        for name, fig in figs.items():
            for theme in themes.THEMES:
                suffix = "" if theme == "light" else f"-{theme}"
                css = themes.standalone_css(page.name, src.css, theme)
                out[f"docs/figs/{name}{suffix}.svg"] = fig.standalone(css, themes.BACKGROUND[theme])

    unplaced = sorted(set(FIGURES) - set(placed))
    require(not unplaced, f"figures without a placeholder in any page: {unplaced}")

    # The index has no source of its own. It borrows the layout rules of the first page.
    first = sources[PAGES[0].name]
    layout = first.css[:first.css.index(themes.MARKS)].rstrip() + "\n"
    entries = [(f"{p.name}.html", sources[p.name].title, p.description) for p in PAGES]
    out["site/index.html"] = site_html.document(
        SITE_TITLE, SITE_LEDE, first.font_links, layout,
        site_html.index_body(SITE_TITLE, SITE_LEDE, entries), links, "index.html",
    )
    return out


def write(root, files):
    for directory in GENERATED:
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.relative_to(root).as_posix() not in files:
                path.unlink()
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)


def main():
    parser = argparse.ArgumentParser(description="Build docs/, site/ and build/artifact/ from src/ and tools/.")
    parser.add_argument("--out", type=Path, default=ROOT, help="output root (default: the repository root)")
    root = parser.parse_args().out
    try:
        files = render()
    except BuildError as error:
        sys.exit(f"build: {error}")
    write(root, files)
    print(f"wrote {len(files)} files under {root}")


if __name__ == "__main__":
    main()
