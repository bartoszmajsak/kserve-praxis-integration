# kserve-praxis-integration

How a KServe `LLMInferenceService` is served when the data plane moves from Gateway API on Istio to Praxis, written as a decision record, and the scripts that build it.

- [Decision](docs/decision.md) describes the preferred option: `MaaSModelRef` stays the object users write, KServe publishes the backend in status, and MaaS writes the routing into the tenant's `Proxy`. It lists what that gains, what it costs and what changes in KServe and MaaS.
- [Alternatives](docs/alternatives.md) describes the options that were considered and not preferred, with the custom resources of each: which one references which, which one owns which, and which controller writes each.
- [Context](docs/context.md) covers how a request reaches the model today and with Praxis, what the move exposes in the integration between MaaS and KServe, and what Praxis supports of Gateway API.
- [Migration](docs/migration.md) is a work in progress. It describes the stages in which a tenant can move, what each stage depends on, what can start now in MaaS and KServe, and how each stage is rolled back.

## Reading

The pages are published at https://bartoszmajsak.github.io/kserve-praxis-integration/ with a light and dark theme switch. Every page has a Markdown view with a copy button, for pasting a section somewhere else. Its address ends in `#markdown`.

GitHub also renders the Markdown in [`docs/`](docs/), and the figures follow its light or dark theme.

[`site/`](site/) is the source of the published pages: standalone HTML that also works from the file system, so you can clone the repository and open `site/index.html` in a browser.

## Building

You need Python 3 and `make`. The build uses the standard library only and no network.

`make build` regenerates everything under `docs/` and `site/` from `src/` and `tools/`. Both directories are committed, so edit `src/` or `tools/`, run `make build` and commit the result with your change.

`make check` builds into a temporary directory and fails if the committed `docs/` or `site/` differ from it. CI runs it on every push and pull request.

`make build` also writes `build/artifact/<page>.html`, which is not committed. It is the page source with the stylesheet and the figures inlined, in the fragment format of the hosting tool that the pages are published to as well.

`.github/workflows/pages.yml` deploys `site/` to GitHub Pages on every push to `main`, after the same `make check`. It can also be started by hand.

## Layout

```
src/                  page sources: an HTML fragment each, with a placeholder per figure
src/style.css         the stylesheet all pages share, with the colour tokens and the diagram rules
tools/build.py        what `make build` runs, with the list of pages
tools/figures.py      the figures, one function each
tools/figkit.py       drawing primitives for the figures
tools/themes.py       light and dark colours of the standalone figures
tools/html2md.py      HTML to Markdown converter
tools/site_html.py    standalone HTML documents, navigation, theme switch and Markdown view
tools/errors.py       the error a failed build check raises
docs/                 generated Markdown, with the figures as SVG in docs/figs/
site/                 generated standalone HTML
build/artifact/       generated fragments for the hosting tool, ignored by git
.github/workflows/    build.yml runs `make check`, pages.yml deploys site/ on push to main
```

## Adding a figure

1. Write a function in `tools/figures.py` that returns the figure, and register it under a name with a short alternative text:

   ```python
   @figure("relationships-option-3", "Custom resources in option 3")
   def relationships_option_3():
       f = RelFig("r4", 1040, 540, "Long description for screen readers.")
       ...
       return f
   ```

   The first argument of `RelFig` and `Fig` prefixes the SVG ids. It has to differ from the other figures on the same page.

2. Put the placeholder on a line of its own in the page source, inside the same markup the other figures use:

   ```html
   <figure>
     <div class="scroll">
       <!-- figure: relationships-option-3 -->
     </div>
     <figcaption>...</figcaption>
   </figure>
   ```

3. Run `make build`. It inlines the figure in the HTML, writes `docs/figs/relationships-option-3.svg` and `docs/figs/relationships-option-3-dark.svg`, and references both from the Markdown.

A new mark or accent needs a rule in `src/style.css`, after the `/* diagram marks` comment. The standalone SVGs are built from those rules, with the colour of each token taken from the table in `tools/themes.py`. The build stops when a figure uses a class that has no rule, or when the table and the tokens of the stylesheet disagree.

A new page is a file in `src/` and an entry in `PAGES` in `tools/build.py`. A page that is renamed gets an entry in `REDIRECTS`, so that its old address forwards to the new one.
