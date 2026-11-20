"""Standalone HTML documents for `site/`.

A page source is a fragment that a host wraps. Here the build wraps it itself: a
document head, a reset that stands in for the host's, and a bar with the navigation,
the theme control and a switch to the Markdown of the page. CSS and JavaScript are inline.
"""
import html
import re

STORAGE_KEY = "kserve-praxis-integration:theme"

# What the host supplies around a fragment. It comes before the page styles, which override it.
RESET = """\
  body { margin: 0; font: 14px system-ui, sans-serif; }
  img { max-width: 100%; }
  [hidden] { display: none !important; }
"""

# Runs in the head, before the first paint, so a stored choice never flashes the other theme.
THEME_BOOT = f"""\
  (function () {{
    try {{
      var theme = localStorage.getItem("{STORAGE_KEY}");
      if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
    }} catch (e) {{}}
  }})();
"""

# The control is hidden in the markup and shown from here, because it does nothing without JavaScript.
THEME_CONTROL = f"""\
  (function () {{
    var root = document.documentElement;
    var control = document.querySelector(".theme");
    var stored = root.getAttribute("data-theme");
    var current = stored === "light" || stored === "dark" ? stored : "system";
    control.querySelectorAll("input").forEach(function (input) {{
      input.checked = input.value === current;
      input.addEventListener("change", function () {{
        var choice = input.value;
        if (choice === "system") root.removeAttribute("data-theme");
        else root.setAttribute("data-theme", choice);
        try {{
          if (choice === "system") localStorage.removeItem("{STORAGE_KEY}");
          else localStorage.setItem("{STORAGE_KEY}", choice);
        }} catch (e) {{}}
      }});
    }});
    control.hidden = false;
  }})();
"""

# The Markdown view replaces the page in place. Its address ends in #markdown, so it can be linked.
VIEW_CONTROL = """\
  (function () {
    var control = document.querySelector(".view");
    if (!control) return;
    var page = document.querySelector(".page");
    var view = document.querySelector(".md-view");
    var source = view.querySelector(".md-source");
    var status = view.querySelector(".md-status");
    function show(name) {
      var markdown = name === "markdown";
      page.hidden = markdown;
      view.hidden = !markdown;
      control.querySelectorAll("input").forEach(function (input) { input.checked = input.value === name; });
      try { history.replaceState(null, "", markdown ? "#markdown" : location.pathname + location.search); } catch (e) {}
    }
    control.querySelectorAll("input").forEach(function (input) {
      input.addEventListener("change", function () { show(input.value); });
    });
    view.querySelector(".md-copy").addEventListener("click", function () {
      function done(ok) { status.textContent = ok ? "Copied" : "Select the text and copy it"; }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(source.textContent).then(function () { done(true); }, function () { done(false); });
        return;
      }
      var range = document.createRange();
      range.selectNodeContents(source);
      var selection = getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) {}
      done(ok);
    });
    control.hidden = false;
    show(location.hash === "#markdown" ? "markdown" : "page");
  })();
"""

# The bar and the Markdown view line up with the reading column of `.page`.
CHROME = """\
  .site-bar {
    max-width: 1080px; margin: 0 auto; padding-top: 14px;
    padding-left: max(16px, env(safe-area-inset-left, 0px));
    padding-right: max(16px, env(safe-area-inset-right, 0px));
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 24px;
    font-family: var(--sans); font-size: 13px; line-height: 1.4;
  }
  .site-bar nav { display: flex; flex-wrap: wrap; gap: 4px 20px; }
  .site-bar a { color: var(--muted); font-weight: 500; text-decoration: none; padding: 4px 0; border-bottom: 2px solid transparent; }
  .site-bar a:hover { color: var(--fg); }
  .site-bar a[aria-current="page"] { color: var(--fg); border-bottom-color: var(--line-strong); }
  .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
  .switch { display: inline-flex; gap: 2px; padding: 2px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
  .switch label { position: relative; display: block; }
  .switch input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
  .switch span { display: block; padding: 4px 10px; border-radius: 6px; color: var(--muted); font-weight: 500; }
  .switch input:checked + span { background: var(--code-bg); color: var(--fg); }
  .site-bar a:focus-visible, .switch input:focus-visible + span { outline: 2px solid var(--fg); outline-offset: 2px; border-radius: 4px; }
  .md-view {
    max-width: 1080px; margin: 0 auto; padding-top: 28px; padding-bottom: 64px;
    padding-left: max(16px, env(safe-area-inset-left, 0px));
    padding-right: max(16px, env(safe-area-inset-right, 0px));
    font-family: var(--sans);
  }
  .md-tools { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .md-copy { font: inherit; font-size: 13px; font-weight: 500; padding: 6px 12px; border: 1px solid var(--line-strong); border-radius: 6px; background: var(--panel); color: var(--fg); cursor: pointer; }
  .md-copy:hover { background: var(--code-bg); }
  .md-copy:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; }
  .md-status { font-size: 13px; color: var(--muted); }
  .md-source { margin: 0; padding: 16px 18px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); color: var(--fg); font-family: var(--mono); font-size: 13px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
  .pages a { color: inherit; text-underline-offset: 3px; }
  .pages a:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; border-radius: 4px; }
"""


def rich(text):
    """Escape `text` for HTML and set its backticked identifiers as code."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text, quote=False))


def switch(name, label, choices):
    """A group of radio buttons drawn as one control. It is hidden in the markup and
    shown by its script."""
    items = "\n".join(
        f'      <label><input type="radio" name="{name}" value="{value}"><span>{text}</span></label>'
        for value, text in choices
    )
    return f'    <div class="switch {name}" role="radiogroup" aria-label="{label}" hidden>\n{items}\n    </div>\n'


def bar(links, current, markdown):
    """`links` are (file name, label) pairs. `current` is the file name of the document
    the bar is rendered into. `markdown` says whether the document has a Markdown view."""
    here = ' aria-current="page"'
    items = "\n".join(
        f'    <a href="{href}"{here if href == current else ""}>{html.escape(label)}</a>' for href, label in links
    )
    view = switch("view", "View", (("page", "Page"), ("markdown", "Markdown"))) if markdown else ""
    theme = switch("theme", "Theme", (("system", "System"), ("light", "Light"), ("dark", "Dark")))
    return (
        '<div class="site-bar">\n'
        f'  <nav aria-label="Pages">\n{items}\n  </nav>\n'
        f'  <div class="controls">\n{view}{theme}  </div>\n'
        "</div>\n"
    )


def markdown_view(markdown):
    return (
        '<div class="md-view" hidden>\n'
        '  <div class="md-tools"><button type="button" class="md-copy">Copy Markdown</button>'
        '<span class="md-status" role="status"></span></div>\n'
        f'  <pre class="md-source" tabindex="0">{html.escape(markdown, quote=False)}</pre>\n'
        "</div>\n\n"
        f"<script>\n{VIEW_CONTROL}</script>\n"
    )


def document(title, description, font_links, css, body, links, current, markdown=None):
    """A complete document. `css` is the stylesheet and `body` is everything from
    `<div class="page">` on. `markdown` is the same page as Markdown, for the view that
    shows it as text to copy."""
    fonts = "".join(link + "\n" for link in font_links)
    plain = html.escape(description.replace("`", ""))
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f'<meta name="description" content="{plain}">\n'
        f"<script>\n{THEME_BOOT}</script>\n"
        f"{fonts}"
        f"<style>\n{RESET}</style>\n"
        f"<style>\n{css}</style>\n"
        f"<style>\n{CHROME}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{bar(links, current, markdown is not None)}\n"
        f"{body.rstrip()}\n\n"
        f"{markdown_view(markdown) if markdown is not None else ''}"
        f"<script>\n{THEME_CONTROL}</script>\n"
        "</body>\n"
        "</html>\n"
    )


def index_body(title, lede, entries):
    """The list of pages. `entries` are (file name, title, description)."""
    items = "\n".join(
        '  <div class="prose">\n'
        f'    <h2><a href="{href}">{html.escape(name)}</a></h2>\n'
        f"    <p>{rich(description)}</p>\n"
        "  </div>"
        for href, name, description in entries
    )
    return (
        '<div class="page">\n\n'
        '<header class="prose">\n'
        f"  <h1>{html.escape(title)}</h1>\n"
        f'  <p class="lede">{rich(lede)}</p>\n'
        "</header>\n\n"
        f'<section class="pages">\n{items}\n</section>\n\n'
        "</div>\n"
    )


def redirect(href, title):
    """The document left at the address of a page that was renamed."""
    name = html.escape(title)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{name}</title>\n"
        f'<meta http-equiv="refresh" content="0; url={href}">\n'
        f'<link rel="canonical" href="{href}">\n'
        "</head>\n"
        "<body>\n"
        f'<p>The content is now in <a href="{href}">{name}</a>.</p>\n'
        "</body>\n"
        "</html>\n"
    )
