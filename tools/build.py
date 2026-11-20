#!/usr/bin/env python3
"""Build everything that is generated from `src/` and `tools/`.

Usage: build.py [--out DIR]

Writes, under DIR (the repository root by default):
  docs/NAME.md               the page as GitHub-flavoured Markdown
  docs/figs/FIG[-dark].svg   every figure as a standalone file, light and dark
  docs/doc-edition.md        the decision as one document, composed from the pages
  site/NAME.html, index.html standalone HTML documents, each with a Markdown view
  build/artifact/NAME.html   the page with the stylesheet and its figures inlined, for the host

`docs/figs/png/` is not written here. `tools/png.py` renders it, and the build leaves it alone.

A page that was renamed keeps its old address: `site/OLD.html` forwards to the new page
and `docs/OLD.md` points at it.

Files in those directories that the build no longer produces are removed. The output
depends on `src/` and `tools/` only, so two runs give the same bytes.
"""
import argparse
import html
import re
import sys
from pathlib import Path
from typing import NamedTuple

import edition
import html2md
import site_html
import themes
from errors import BuildError, require
from figures import FIGURES

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ("docs", "site", "build/artifact")
KEPT = "docs/figs/png/"  # rendered by tools/png.py
STYLE = "src/style.css"

SITE_TITLE = "KServe, MaaS and Praxis integration"
SITE_LEDE = (
    "How a KServe `LLMInferenceService` that is published through MaaS is served when the data plane moves "
    "from Gateway API on Istio to Praxis: the decision, the alternatives and the context."
)


class Page(NamedTuple):
    name: str         # src/NAME.html
    description: str  # one sentence for the site index


# In the order of the navigation.
PAGES = (
    Page(
        "decision",
        "The decision: `MaaSModelRef` stays the object users write, KServe publishes the backend in "
        "status, and MaaS writes the routing into the tenant's `Proxy`. What it gains, what it costs and "
        "what changes in KServe and MaaS.",
    ),
    Page(
        "alternatives",
        "The options that were considered and not preferred, with the custom resources of each: which one "
        "references which, which one owns which, and which controller writes each.",
    ),
    Page(
        "context",
        "How a request reaches the model today and with Praxis, what the move exposes in the integration "
        "between MaaS and KServe, and what Praxis supports of Gateway API.",
    ),
    Page(
        "external-models",
        "How MaaS external models are routed today, what Praxis offers when it connects to the provider itself, "
        "and what is undefined. It is a MaaS concern and not part of the decision.",
    ),
    Page(
        "migration",
        "Work in progress: the stages in which a tenant can move to Praxis, what each stage depends on, what can start "
        "now in MaaS and KServe, and how each stage is rolled back.",
    ),
)

# Old page name to the page that replaced it.
REDIRECTS = {"ingress-paths": "decision", "cr-relationships": "alternatives"}

# A link from one page to another is relative in the sources, which is what site/ needs.
# The Markdown gets the .md name. The fragments under build/artifact/ are hosted one per
# address, so there the link points at the published site.
SITE_URL = "https://bartoszmajsak.github.io/kserve-praxis-integration/"
RAW_URL = "https://raw.githubusercontent.com/bartoszmajsak/kserve-praxis-integration/main/docs/"
PAGE_LINK = re.compile(r'href="([a-z0-9-]+)\.html"')

# A fragment is listed by its host on its own, where a one-word title says too little.
ARTIFACT_TITLE = "Praxis {}"

PLACEHOLDER = re.compile(r"^([ \t]*)<!-- figure: ([a-z0-9-]+) -->[ \t]*$", flags=re.M)
BODY = '<div class="page">'


class Source(NamedTuple):
    head: str         # the title, the meta and the font link
    title: str        # as text, entities decoded
    font_links: list
    body: str         # from the page div on, placeholders included
    body_line: int    # line of the page div in the file


def read_source(page):
    """Split a page source into its parts and check that it is still a fragment: a title
    and a font link in front of the page div, no style block (the pages share
    `src/style.css`) and no document skeleton."""
    text = (ROOT / "src" / f"{page.name}.html").read_text(encoding="utf-8")
    require(text.startswith("<title>"), f"{page.name}: the source has to start with <title>")
    require(BODY in text, f"{page.name}: no {BODY}")
    skeleton = re.search(r"<(!doctype|html|head|body)\b", text, flags=re.I)
    if skeleton:
        raise BuildError(f"{page.name}: the source is a fragment, {skeleton.group(0)} does not belong in it")
    head, body = text.split(BODY, 1)
    require("<style" not in text, f"{page.name}: the pages share {STYLE}, a source has no <style> block")
    title = re.match(r"<title>(.*?)</title>", head)
    require(title, f"{page.name}: the <title> is not closed on the first line")
    links = re.findall(r"<link [^>]*>", head)
    return Source(head, html.unescape(title.group(1)), links, BODY + body, head.count("\n") + 1)


def check_classes(page, figs, css):
    """Every class a figure uses needs a rule among the diagram rules of the stylesheet."""
    svg = "\n".join(fig.inline() for fig in figs.values())
    used = {c for classes in re.findall(r'class="([^"]+)"', svg) for c in classes.split()}
    defined = set(re.findall(r"\.([a-z][a-z0-9-]*)", themes.marks_css(css)))
    missing = sorted(used - defined)
    require(not missing, f"{page.name}: figure classes without a rule in {STYLE}: {missing}")


def portable(markdown):
    """The Markdown of a page for pasting somewhere else: figures as plain PNG images,
    which more places take than SVG, and links to other pages with their full address."""
    markdown = re.sub(
        r'<picture><source [^>]*><img src="figs/([^"]+)\.svg" alt="([^"]*)"></picture>',
        lambda m: f"![{html.unescape(m.group(2))}]({RAW_URL}figs/png/{m.group(1)}.png)",
        markdown,
    )
    return re.sub(r"\]\(([a-z0-9-]+)\.md\)", lambda m: f"]({SITE_URL}{m.group(1)}.html)", markdown)


def render():
    """Every generated file as {path relative to the output root: content}."""
    out, placed = {}, {}
    css = (ROOT / STYLE).read_text(encoding="utf-8")
    themes.check_tokens(css)
    standalone = {theme: themes.standalone_css(css, theme) for theme in themes.THEMES}
    sources = {page.name: read_source(page) for page in PAGES}
    links = [("index.html", "Overview")] + [(f"{p.name}.html", sources[p.name].title) for p in PAGES]

    for page in PAGES:
        src = sources[page.name]

        figs = {}
        for _, name in PLACEHOLDER.findall(src.body):
            require(name in FIGURES, f"{page.name}: no figure named {name} in tools/figures.py")
            require(name not in placed, f"figure {name} is placed twice, the second time in {page.name}")
            placed[name] = page.name
            figs[name] = FIGURES[name].build()
        prefixes = [fig.p for fig in figs.values()]
        require(len(set(prefixes)) == len(prefixes), f"{page.name}: two figures share an id prefix: {prefixes}")
        check_classes(page, figs, css)

        body = PLACEHOLDER.sub(lambda m: figs[m.group(2)].inline(m.group(1)), src.body)
        require("<!-- figure:" not in body, f"{page.name}: a figure placeholder has to be on a line of its own")
        for target in PAGE_LINK.findall(src.body):
            require(target in sources, f"{page.name}: link to {target}.html, which is not a page")

        alt = {name: FIGURES[name].alt for name in figs}
        try:
            markdown = html2md.convert(src.body, alt, src.body_line)
        except BuildError as error:
            raise BuildError(f"{page.name}: {error}") from None

        out[f"docs/{page.name}.md"] = markdown
        title = html.escape(ARTIFACT_TITLE.format(src.title.lower()))
        head = re.sub(r"<title>.*?</title>", lambda m: f"<title>{title}</title>", src.head, count=1)
        out[f"build/artifact/{page.name}.html"] = (
            f"{head.rstrip()}\n<style>\n{css}</style>\n\n"
            + PAGE_LINK.sub(lambda m: f'href="{SITE_URL}{m.group(1)}.html"', body)
        )
        out[f"site/{page.name}.html"] = site_html.document(
            f"{src.title} - {SITE_TITLE}", page.description, src.font_links, css, body, links, f"{page.name}.html",
            markdown=portable(markdown),
        )
        for name, fig in figs.items():
            for theme in themes.THEMES:
                suffix = "" if theme == "light" else f"-{theme}"
                out[f"docs/figs/{name}{suffix}.svg"] = fig.standalone(standalone[theme], themes.BACKGROUND[theme])

    unplaced = sorted(set(FIGURES) - set(placed))
    require(not unplaced, f"figures without a placeholder in any page: {unplaced}")

    # The index has no source of its own and no figure, so it takes the layout rules only.
    fonts = sources[PAGES[0].name].font_links
    layout = css[:css.index(themes.MARKS)].rstrip() + "\n"
    entries = [(f"{p.name}.html", sources[p.name].title, p.description) for p in PAGES]
    entries.append((f"{edition.NAME}.html", edition.LABEL, edition.DESCRIPTION))
    out["site/index.html"] = site_html.document(
        SITE_TITLE, SITE_LEDE, fonts, layout,
        site_html.index_body(SITE_TITLE, SITE_LEDE, entries), links, "index.html",
    )

    for old, new in REDIRECTS.items():
        require(new in sources and old not in sources, f"redirect {old}: the target has to be a page and the old name not")
        title = sources[new].title
        out[f"site/{old}.html"] = site_html.redirect(f"{new}.html", title)
        out[f"docs/{old}.md"] = f"# Moved\n\nThe content is now in [{title}]({new}.md).\n"

    # The doc edition is composed from the pages, so their figures appear in it a second time.
    # It is listed on the index and not in the navigation.
    source = edition.compose({name: src.body for name, src in sources.items()})
    figs = {name: FIGURES[name].build() for _, name in PLACEHOLDER.findall(source)}
    try:
        markdown = html2md.convert(source, {name: FIGURES[name].alt for name in figs})
    except BuildError as error:
        raise BuildError(f"{edition.NAME}: {error}") from None
    out[f"docs/{edition.NAME}.md"] = markdown
    out[f"site/{edition.NAME}.html"] = site_html.document(
        f"{edition.TITLE} - {SITE_TITLE}", edition.DESCRIPTION, fonts, css,
        PLACEHOLDER.sub(lambda m: figs[m.group(2)].inline(m.group(1)), source),
        links, f"{edition.NAME}.html", markdown=portable(markdown),
    )
    return out


def write(root, files):
    for directory in GENERATED:
        for path in sorted((root / directory).rglob("*")):
            name = path.relative_to(root).as_posix()
            if path.is_file() and name not in files and not name.startswith(KEPT):
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
