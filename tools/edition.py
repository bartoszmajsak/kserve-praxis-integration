"""The decision as one document in the format of an Open Data Hub architecture decision
record, for pasting into a doc that is shared elsewhere.

The template is ODH-ADR-0000-template.md in opendatahub-io/architecture-decision-records.
The sections are composed from the pages. The text of its own is what the template asks
for and the pages do not have: the header table, the stakeholder table and the
references. It leaves out what the pages keep for the record: the code references, the
state of Praxis, the migration and the list of what was not verified.
"""
import re

from errors import require

NAME = "doc-edition"
LABEL = "Doc edition"
TITLE = "Routing MaaS-published KServe models through Praxis"
DESCRIPTION = (
    "The decision in the format of an Open Data Hub architecture decision record, for pasting into a doc. "
    "It leaves out the code references, the state of Praxis and the migration."
)

SITE = "https://bartoszmajsak.github.io/kserve-praxis-integration/"
GITHUB = "https://github.com"

# The header table of the template. Authors and tickets are filled in by hand.
HEADER = (
    ("Date", "2026-11-20"),
    ("Scope", "Model Serving (KServe), Models-as-a-Service (MaaS), AI Gateway"),
    ("Status", "Approved"),
    ("Authors", ""),
    ("Supersedes", "N/A"),
    ("Superseded by:", "N/A"),
    ("Tickets", ""),
    ("Other docs:", f'<a href="{SITE}">KServe, MaaS and Praxis integration</a>'),
)

# Group and how it is impacted. Key contacts and dates are filled in by hand.
STAKEHOLDERS = (
    ("Model Serving (KServe)",
     "Publishes complete status for a service without a route and the request paths that go through the EPP, and skips the HTTPRoute for a Gateway that is in front of a Praxis proxy."),
    ("Models-as-a-Service (MaaS)",
     "Reads the service status in place of the HTTPRoute, writes the routing into the <code>Proxy</code> of the tenant and generates the Praxis <code>Policy</code>. It has the larger share of the work."),
    ("AI Gateway (Praxis)",
     "<code>gateway-controller</code> renders and deploys the proxy from the <code>Proxy</code> and the <code>Policy</code>. The EPP client and the policy engine have open work."),
    ("Dashboard", "TBD"),
    ("Users and API clients",
     "They keep the objects they write, the hostname and the model IDs. Per-model path URLs stop working."),
)

REFERENCES = (
    '<a href="decision.html">Decision</a>, with the impact on users and the dashboard',
    '<a href="alternatives.html">Alternatives</a>, with a figure of the custom resources of each option',
    '<a href="context.html">Context</a>, with the state of Praxis and its Gateway API support',
    '<a href="migration.html">Migration</a>, which is a work in progress',
    f'<a href="{GITHUB}/praxis-proxy/gateway-controller">praxis-proxy/gateway-controller</a> and its '
    f'<a href="{GITHUB}/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api.md">design</a>',
)

LEAD = r"</h2>\s*<p>(.*?)</p>"  # the first paragraph of a section

# A link to a line of code whose text is the file and the line, such as `router.go:83`.
CODE_REF = r'<a href="https://github\.com/[^"]+/blob/[^"]+"[^>]*><code>[^<]*:\d+(?:-\d+)?</code></a>'


def section(body, title):
    """The `<section>` of a page whose heading is `title`."""
    found = [m.group(0) for m in re.finditer(r"<section>.*?</section>", body, flags=re.S) if f"<h2>{title}</h2>" in m.group(0)]
    require(len(found) == 1, f"{NAME}: expected one section named '{title}', found {len(found)}")
    return found[0]


def inner(sec, title, heading=None):
    """What is inside a section, with its heading replaced by `heading` or removed."""
    text = sec[len("<section>"):-len("</section>")].strip("\n")
    return swap(text, f"    <h2>{title}</h2>\n", f"    {heading}\n" if heading else "")


def find(pattern, text, what):
    m = re.search(pattern, text, flags=re.S)
    require(m, f"{NAME}: no {what}")
    return m.group(1)


def swap(text, old, new):
    require(text.count(old) == 1, f"{NAME}: expected once, found {text.count(old)} times: {old[:70]}")
    return text.replace(old, new)


def list_after(text, heading):
    return find(re.escape(heading) + r"\s*(<ul>.*?</ul>)", text, f"list after {heading}")


def without_code_refs(text):
    """Drop the parenthesised code references. Links on words and issue links stay."""
    text = re.sub(rf"\s*\({CODE_REF}(?:,\s*{CODE_REF})*\)", "", text)
    left = re.search(CODE_REF, text)
    require(not left, f"{NAME}: a code reference that is not in parentheses of its own: {left.group(0)[-60:] if left else ''}")
    return text


def table(head, rows, wide=False):
    cells = lambda tag, row: "".join(f"<{tag}>{cell}</{tag}>" for cell in row)
    body = "".join(f"        <tr>{cells('td', row)}</tr>\n" for row in rows)
    return (
        f'  <div class="tbl{" wide" if wide else ""}">\n    <table>\n      <thead><tr>{cells("th", head)}</tr></thead>\n'
        f"      <tbody>\n{body}      </tbody>\n    </table>\n  </div>"
    )


def prose(*blocks):
    return '  <div class="prose">\n' + "".join(f"    {block}\n" for block in blocks) + "  </div>"


def chapter(*parts):
    return "<section>\n" + "\n".join(parts) + "\n</section>"


def compose(bodies):
    """The body of the edition from the bodies of the pages, as {page name: body}."""
    context, decision, alternatives = bodies["context"], bodies["decision"], bodies["alternatives"]
    require(f"<h1>{TITLE}</h1>" in decision, f"{NAME}: the decision page and the doc edition have different titles")
    lede = lambda body, page: find(r'<p class="lede">(.*?)</p>', body, f"lede on the {page} page")

    request = section(context, "Praxis in the request path")
    problems = section(context, "Shortcomings in today's integration")
    why = chapter(
        prose("<h2>Why</h2>", f"<p>{lede(context, 'context')}</p>", f"<p>{find(LEAD, request, 'request path lead')}</p>"),
        find(r"\n(  <figure>.*?</figure>)", request, "request path figure"),
        prose("<h3>Shortcomings in today's integration</h3>", f"<p>{find(LEAD, problems, 'problems lead')}</p>"),
        find(r'\n(  <div class="tbl">.*?</div>)', problems, "problems table"),
    )

    goals = section(decision, "Goals and non-goals")
    chosen = section(decision, "Decision")
    kserve = swap(section(decision, "Changes in upstream KServe"), ", in the files under <code>pkg/controller/v1alpha2/llmisvc/</code>", "")
    maas = swap(section(decision, "Changes in MaaS"),
                ", and paths are under <code>maas-controller/pkg/controller/maas/</code> unless they say otherwise", "")
    how = chapter(
        inner(chosen, "Decision", "<h2>How</h2>"),
        inner(section(decision, "Benefits"), "Benefits", "<h3>Benefits</h3>"),
        inner(kserve, "Changes in upstream KServe", "<h3>Changes in upstream KServe</h3>"),
        inner(maas, "Changes in MaaS", "<h3>Changes in MaaS</h3>"),
        inner(section(decision, "Dependencies"), "Dependencies", "<h3>Dependencies</h3>"),
    )

    option1 = section(alternatives, "Option 1: KServe creates the ModelProvider")
    option2 = section(alternatives, "Option 2: MaaS creates the ModelProvider")
    comparison = section(alternatives, "Comparison")
    alternative = chapter(
        prose(
            "<h2>Alternatives</h2>",
            "<p>Two other ways to integrate KServe and MaaS with Praxis were considered.</p>",
            "<h3>Option 1: KServe creates the ModelProvider</h3>",
            f"<p>{find(LEAD, option1, 'option 1 lead')} It is not preferred for these reasons.</p>",
            list_after(option1, "<h3>Why it is not preferred</h3>"),
            "<h3>Option 2: MaaS creates the ModelProvider</h3>",
            f"<p>{find(LEAD, option2, 'option 2 lead')} These points are open in it.</p>",
            list_after(option2, "<h3>Open points</h3>"),
        ),
        inner(comparison, "Comparison", "<h3>Comparison</h3>"),
    )

    parts = [
        chapter(prose("<h2>What</h2>", f"<p>{lede(decision, 'decision')}</p>")),
        why,
        chapter(prose("<h2>Goals</h2>", list_after(goals, "<h3>Goals</h3>"))),
        chapter(prose("<h2>Non-Goals</h2>", list_after(goals, "<h3>Non-goals</h3>"))),
        how,
        chapter(inner(section(decision, "Open questions"), "Open questions", "<h2>Open Questions</h2>")),
        alternative,
        chapter(inner(section(decision, "Security and privacy"), "Security and privacy", "<h2>Security and Privacy Considerations</h2>")),
        chapter(inner(section(decision, "Costs and limits"), "Costs and limits", "<h2>Risks</h2>")),
        chapter(
            prose("<h2>Stakeholder Impacts</h2>"),
            table(("Group", "Key Contacts", "Date", "Impacted?"), [(group, "", "", impact) for group, impact in STAKEHOLDERS]),
        ),
        chapter(prose("<h2>References</h2>", "<ul>" + "".join(f"<li>{item}</li>" for item in REFERENCES) + "</ul>")),
        chapter(prose("<h2>Reviews</h2>"), table(("Reviewed by", "Date", "Notes"), [("", "", "")])),
    ]
    header = table(("", ""), HEADER)
    return without_code_refs(
        '<div class="page">\n\n'
        f'<header class="prose">\n  <h1>{TITLE}</h1>\n</header>\n\n'
        f"{header}\n\n"
        + "\n\n".join(parts)
        + "\n\n</div>\n"
    )
