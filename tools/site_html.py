"""Standalone HTML documents for `site/`.

A page source is a fragment that a host wraps. Here the build wraps it itself: a
document head, a reset that stands in for the host's, a bar with the navigation and the
theme control, and nothing else. CSS and JavaScript are inline.
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

# Uses only the tokens both pages define. The bar lines up with the reading column of `.page`.
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
  .theme { display: inline-flex; gap: 2px; padding: 2px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
  .theme label { position: relative; display: block; }
  .theme input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
  .theme span { display: block; padding: 4px 10px; border-radius: 6px; color: var(--muted); font-weight: 500; }
  .theme input:checked + span { background: var(--code-bg); color: var(--fg); }
  .site-bar a:focus-visible, .theme input:focus-visible + span { outline: 2px solid var(--fg); outline-offset: 2px; border-radius: 4px; }
  .pages a { color: inherit; text-underline-offset: 3px; }
  .pages a:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; border-radius: 4px; }
"""


def rich(text):
    """Escape `text` for HTML and set its backticked identifiers as code."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text, quote=False))


def bar(links, current):
    """`links` are (file name, label) pairs. `current` is the file name of the document
    the bar is rendered into."""
    here = ' aria-current="page"'
    items = "\n".join(
        f'    <a href="{href}"{here if href == current else ""}>{html.escape(label)}</a>' for href, label in links
    )
    choices = "\n".join(
        f'    <label><input type="radio" name="theme" value="{value}"><span>{label}</span></label>'
        for value, label in (("system", "System"), ("light", "Light"), ("dark", "Dark"))
    )
    return (
        '<div class="site-bar">\n'
        f'  <nav aria-label="Pages">\n{items}\n  </nav>\n'
        f'  <div class="theme" role="radiogroup" aria-label="Theme" hidden>\n{choices}\n  </div>\n'
        "</div>\n"
    )


def document(title, description, font_links, css, body, links, current):
    """A complete document. `css` and `body` come from a page source: the content of its
    `<style>` block and everything from `<div class="page">` on."""
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
        f"<style>{css}</style>\n"
        f"<style>\n{CHROME}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{bar(links, current)}\n"
        f"{body.rstrip()}\n\n"
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
