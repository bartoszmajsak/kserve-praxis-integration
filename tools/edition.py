"""The decision as one document, for pasting into a doc that is shared elsewhere.

It is composed from sections of the pages and has no text of its own apart from its
title. It leaves out what the pages keep for the record: the code references, the state
of Praxis, the alternatives, the migration and the list of what was not verified.
"""
import re

from errors import require

NAME = "doc-edition"
LABEL = "Doc edition"
TITLE = "Option 3: KServe - MaaS - Praxis integration"
DESCRIPTION = (
    "The decision as one document, for pasting into a doc: the problem, the proposal and the changes in "
    "KServe and MaaS. It leaves out the code references, the state of Praxis, the alternatives and the migration."
)

# A link to a line of code whose text is the file and the line, such as `router.go:83`.
CODE_REF = r'<a href="https://github\.com/[^"]+/blob/[^"]+"[^>]*><code>[^<]*:\d+(?:-\d+)?</code></a>'
TILE = re.compile(r'<div>\s*<span class="q">(.*?)</span>\s*<span class="a">(.*?)</span>\s*<p>(.*?)</p>\s*</div>', flags=re.S)


def section(body, title):
    """The `<section>` of a page whose heading is `title`."""
    found = [m.group(0) for m in re.finditer(r"<section>.*?</section>", body, flags=re.S) if f"<h2>{title}</h2>" in m.group(0)]
    require(len(found) == 1, f"{NAME}: expected one section named '{title}', found {len(found)}")
    return found[0]


def swap(text, old, new):
    require(text.count(old) == 1, f"{NAME}: expected once, found {text.count(old)} times: {old[:70]}")
    return text.replace(old, new)


def without_code_refs(text):
    """Drop the parenthesised code references. Links on words and issue links stay."""
    text = re.sub(rf"\s*\({CODE_REF}(?:,\s*{CODE_REF})*\)", "", text)
    left = re.search(CODE_REF, text)
    require(not left, f"{NAME}: a code reference that is not in parentheses of its own: {left.group(0)[-60:] if left else ''}")
    return text


def compose(bodies):
    """The body of the edition from the bodies of the pages, as {page name: body}."""
    context, decision = bodies["context"], bodies["decision"]

    lede = re.search(r'<p class="lede">.*?</p>', context, flags=re.S)
    require(lede, f"{NAME}: the context page has no lede")
    tiles = {q: (headline, text) for q, headline, text in TILE.findall(context)}
    require({"Problem", "What can help"} <= set(tiles), f"{NAME}: the context page has no Problem and What can help tiles")
    proposal = swap(tiles["What can help"][1], ' The details are in <a href="decision.html">Decision</a>.', "")
    answers = "".join(
        f'  <div>\n    <span class="q">{q}</span>\n    <span class="a">{headline}</span>\n    <p>{text}</p>\n  </div>\n'
        for q, headline, text in (("Problem", *tiles["Problem"]), ("Proposal", tiles["What can help"][0], proposal))
    )

    problems = section(context, "Problems in today's integration")
    praxis = '  <div class="prose">\n    <h3>In Praxis</h3>'
    require(praxis in problems, f"{NAME}: the problems section has no 'In Praxis' part to leave out")
    problems = problems[:problems.index(praxis)].rstrip() + "\n</section>"

    kserve = swap(section(decision, "Changes in upstream KServe"), ", in the files under <code>pkg/controller/v1alpha2/llmisvc/</code>", "")
    maas = swap(section(decision, "Changes in MaaS"),
                ", and paths are under <code>maas-controller/pkg/controller/maas/</code> unless they say otherwise", "")

    parts = [
        section(context, "Praxis in the request path"),
        problems,
        swap(section(decision, "Decision"), "<h2>Decision</h2>", "<h2>MaaSModelRef only, ModelProvider later</h2>"),
        swap(section(decision, "Benefits"), "<h2>Benefits</h2>", "<h3>Benefits</h3>"),
        swap(section(decision, "Costs and limits"), "<h2>Costs and limits</h2>", "<h3>Costs and limits</h3>"),
        kserve,
        maas,
    ]
    return without_code_refs(
        '<div class="page">\n\n'
        f'<header class="prose">\n  <h1>{TITLE}</h1>\n  {lede.group(0)}\n</header>\n\n'
        f'<div class="answers">\n{answers}</div>\n\n'
        + "\n\n".join(parts)
        + "\n\n</div>\n"
    )
