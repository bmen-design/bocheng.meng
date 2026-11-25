"""Render the overview, project pages and navigation from the content directory."""

import json
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WIDTHS = (320, 480, 640, 960, 1280, 1600, 1920)
ICONS = {p.stem: p.read_text() for p in (ROOT / "templates/icons").glob("*.svg")}
ROUND_PILL = "cta-pill cta-pill--blur cta-pill--filled cta-pill--rounded"


def icon(name):
    return f'<span class="cta-pill-icon">{ICONS[name]}</span>'


CARD_TONES = (
    ("#27332f", "#dce9b1"), ("#5b2c26", "#fff0cd"), ("#cec8bb", "#35312b"),
    ("#b5d2dd", "#1b3a44"), ("#34313a", "#f3dfff"), ("#d05e3c", "#251d17"),
    ("#25374a", "#d7eafa"), ("#b3b69c", "#343723"), ("#e2b63c", "#392d0b"),
    ("#50493e", "#e8dfbb"), ("#714555", "#f7dfe9"), ("#cad8d1", "#35453d"),
)


def media_card(src, label):
    slug = src.strip("/").split("/")[1]
    color, ink = CARD_TONES[sum((i + 1) * ord(c) for i, c in enumerate(slug)) % len(CARD_TONES)]
    return (f'<div class="media-card" style="--card-color:{color};--card-ink:{ink}">'
            f'<span>{escape(label)}</span></div>')


def image(src, alt):
    file = ROOT / src.lstrip("/")
    if not file.is_file():
        return (media_card(src, alt) + f'<img class="thumb" data-local-src="{escape(src)}" '
                f'alt="{escape(alt)}" hidden>')
    stem = src.lstrip("/").rsplit(".", 1)[0]
    variants = [f"{escape(stem)}-{width}.webp {width}w" for width in WIDTHS
                if (ROOT / f"{stem}-{width}.webp").is_file()]
    responsive = f'srcset="{", ".join(variants)}" sizes="auto, 50vw"' if variants else ""
    return (f'<img class="thumb" loading="lazy" decoding="async" src="{escape(src.lstrip("/"))}" '
            f'{responsive} alt="{escape(alt)}">')


def project_link(project, classes, current=None):
    slug = project["slug"]
    active = ' active' if slug == current else ''
    return (f'<a class="{classes} link-ajax{active}" href="work/{escape(slug)}/" '
            f'aria-label="{escape(project["title"])}"></a>')


def overview(projects):
    cards = []
    for project in projects:
        cover = image(project["cover"], project["title"])
        link = project_link(project, "grid-projects-figure-link")
        title = escape(project["title"])
        cards.append(f'''
          <figure class="grid-projects-figure" data-size="{escape(project["coverSize"])}">
            {link}
            <div class="grid-projects-figure-thumbnail">{cover}</div>
            <figcaption class="grid-projects-figure-caption">
              <h3 class="grid-projects-figure-caption-title"><span>{title}</span></h3>
            </figcaption>
          </figure>''')
    return (f'<div id="site-main-content"><div class="grid-projects">'
            f'<div class="grid-projects-figures">{"".join(cards)}</div></div></div>')


def section_header(kind, title):
    return (f'<header class="{kind}-header"><h2 class="{kind}-header-title font-subtle '
            f'font-uppercase">{escape(title)}</h2></header>')


def paragraph(title, value):
    return (f'<div class="text-body">{section_header("text-body", title)}'
            f'<div class="text-body-content"><p>{escape(value)}</p></div></div>')


def details(title, items):
    rows = []
    for label, value in items:
        rows.append(f'<div class="list-details-item"><dt class="list-details-item-title">'
                    f'{escape(label)}:</dt><dd class="list-details-item-content">'
                    f'<p>{escape(str(value))}</p></dd></div>')
    return (f'<div class="list-details font-sans-small">{section_header("list-details", title)}'
            f'<dl class="list-details-items">{"".join(rows)}</dl></div>')


def about_list(title, markup):
    items = "".join(f'<li class="list-rows-item"><p>{item}</p></li>' for item in markup)
    return (f'<div class="list-rows font-sans-small">{section_header("list-rows", title)}'
            f'<ul class="list-rows-items">{items}</ul></div>')


def accordion(key, content, size, after=""):
    return f'''
        <li class="site-menu-item">
          <button class="{ROUND_PILL}" data-accordion="{key}" type="button"
                  aria-expanded="false" aria-controls="{key}-panel">
            <span class="cta-pill-label">{key.title()}</span>{icon("triangle-south")}
          </button>
          <div id="{key}-panel" class="site-menu-item-panel-wrapper" data-size="{size}" hidden>
            <panel-track class="site-menu-item-panel" data-scroll="false">{content}</panel-track>
          </div>{after}
        </li>'''


def work_menu(projects, current):
    labels = [("index", "#"), ("title", "TITLE"), ("categories", "CATEGORIES"), ("year", "YEAR")]
    headings = "".join(f'<span class="list-projects-header-{key}">{val}</span>' for key, val in labels)
    rows, previews = [], []
    for index, project in enumerate(projects, 1):
        title = escape(project["title"])
        categories = escape(", ".join(project["categories"]))
        link = project_link(project, "list-projects-item-link", current)
        rows.append(f'''
            <li class="list-projects-item" data-index="{index}">{link}
              <span class="list-projects-item-index">{index:02}</span>
              <h3 class="list-projects-item-title">{title}</h3>
              <span class="list-projects-item-categories">{categories}</span>
              <span class="list-projects-item-year">{project["year"]}</span>
            </li>''')
        thumbnail = image(project["preview"], project["title"])
        previews.append(f'<figure class="widget-cursor-thumbnail" data-index="{index}" hidden>'
                        f'{thumbnail}</figure>')
    content = (f'<div class="list-projects"><header class="list-projects-header font-subtle">'
               f'{headings}</header><ul class="list-projects-items">{"".join(rows)}</ul></div>')
    return accordion("work", content, "large", f'<widget-cursor>{"".join(previews)}</widget-cursor>')


def about_menu(site, projects):
    by_slug = {p["slug"]: p for p in projects}
    films = [f'<a class="link-inline link-ajax" href="work/{escape(slug)}/">'
             f'{escape(by_slug[slug]["title"])}</a>' for slug in site.get("selectedFilms", []) if slug in by_slug]
    contacts = [f'<a class="link-inline" href="{escape(c["href"])}" target="_blank" rel="noreferrer">'
                f'{escape(c["label"])}</a>' for c in site["contact"]]
    content = "".join([
        paragraph("Information", site["introduction"]),
        about_list("Disciplines", map(escape, site["disciplines"])),
        about_list("Featured brands", map(escape, site["featured"])),
        about_list("Selected films", films) if films else "",
        about_list("Contact", contacts),
    ])
    return accordion("about", content, "small")


def video_controls(options):
    buttons = []
    for option in options:
        key = "audio" if option == "sound" else option
        drawings = ICONS[key] + (ICONS["pause"] if key == "play" else "")
        label = {"audio": "Unmute", "play": "Play", "fullscreen": "Fullscreen"}[key]
        buttons.append(f'<button type="button" aria-label="{label}" class="grid-project-figure-controls-{key} '
                       f'cta-pill cta-pill--blur cta-pill--filled cta-pill--round">'
                       f'<span class="cta-pill-icon">{drawings}</span></button>')
    return (f'<div class="grid-project-figure-controls" data-options="{",".join(options)}">'
            f'{"".join(buttons)}</div>')


def gallery(project):
    figures = []
    for i, item in enumerate(project["gallery"], 1):
        label = f'{project["title"]}, figure {i}'
        controls = ""
        state = ""
        tag = "figure"
        if "controls" in item:
            tag = "widget-player"
            state = ' data-state="idle"'
            source = item["src"]
            file = ROOT / source.lstrip("/")
            available = file.is_file() or file.with_name(file.name + ".part001").is_file()
            path_attr = (f'src="{escape(source.lstrip("/"))}#t=0.1"' if available
                         else f'data-local-src="{escape(source)}" hidden')
            player = (f'<video class="thumb lazy" preload="metadata" playsinline webkit-playsinline '
                      f'muted loop {path_attr} aria-label="{escape(label)}"></video>')
            if not available:
                player = media_card(source, label) + player
            controls = video_controls(item["controls"])
            if not available:
                controls = controls.replace('class="grid-project-figure-controls"', 'class="grid-project-figure-controls" hidden', 1)
        else:
            player = image(item["src"], label)
        figures.append(f'<{tag} class="grid-project-figure" data-size="{escape(item["size"])}">'
                       f'<div class="grid-project-figure-thumbnail ratio-{escape(item["crop"])}" '
                       f'style="--ratio: {item["ratio"]};"{state}>{player}</div>{controls}</{tag}>')
    return (f'<div id="site-main-content"><div class="grid-project">'
            f'<div class="grid-project-figures">{"".join(figures)}</div></div></div>')


def page_heading(title, back_label):
    return (f'<header id="site-main-header"><h1 id="site-main-header-title"><span>{escape(title)}</span></h1>'
            f'<a class="{ROUND_PILL} link-ajax link-ajax--home" href="./">'
            f'<span class="cta-pill-label">{back_label}</span>{icon("triangle-west")}</a></header>')


def project_page(project):
    categories = project["categories"]
    info = details("Information", [("Client", project["client"]),
                   ("Categories" if len(categories) > 1 else "Category", ", ".join(categories)),
                   ("Year", project["year"])])
    description = paragraph("Description", project["description"])
    videos = sum("controls" in item for item in project["gallery"])
    production = []
    if project.get("production"):
        production.append(("Disciplines", ", ".join(project["production"])))
    production.extend([("Stills", len(project["gallery"]) - videos), ("Films", videos)])
    archive = details("Production", production)
    return (page_heading(project["title"], "Back to Overview")
            + f'<div id="site-main-info">{info}{description}{archive}</div>' + gallery(project))


def footer(contacts):
    links = []
    for contact in contacts:
        url, label = escape(contact["href"]), escape(contact["label"])
        if url.startswith("mailto:"):
            caption = f'<span class="cta-pill-label" data-email="{url[7:]}"></span>'
        else:
            caption = f'<span class="cta-pill-label">{label}</span>'
        links.append(f'<li class="site-footer-menu-item"><a class="cta-pill cta-pill--filled cta-pill--rounded" '
                     f'aria-label="{label}" href="{url}" target="_blank" rel="noreferrer">'
                     f'{caption}{icon("triangle-east")}</a></li>')
    return "".join(links)


def render(path, document_base="/"):
    site = json.loads((ROOT / "content/site.json").read_text())
    catalog = json.loads((ROOT / "content/projects.json").read_text())
    projects = {p["slug"]: p for p in catalog["projects"]}
    route = urlsplit(path).path.rstrip("/")
    status, slug = 200, None
    title = site["name"]
    if route in ("", "/index.html"):
        view = "home"
        main = overview([projects[key] for key in catalog["overview"]])
    elif route.startswith("/work/") and route[6:] in projects:
        slug = route[6:]
        view = "project"
        main = project_page(projects[slug])
        title = f'{projects[slug]["title"]} — {title}'
    else:
        status, view = 404, "error"
        main = (page_heading("404", "Back to Homepage") + '<div id="site-main-info">'
                + paragraph("Information", "The page doesn’t exist.") + '</div>')
        title = f'404 — {title}'
    template = Template((ROOT / "templates/page.html").read_text())
    local_picker = ""
    if not all((ROOT / p["cover"].lstrip("/")).is_file() for p in projects.values()):
        local_picker = ('<label class="study-load"><span>Open local media</span>'
                        '<input type="file" id="local-media" webkitdirectory multiple></label>'
                        '<span id="media-status" role="status"></span>')
    html = template.substitute(
        document_base=escape(document_base), local_picker=local_picker,
        title=escape(title), view=view, name=escape(site["name"]), wordmark=escape(site["name"].upper()),
        tagline=escape(site["tagline"]), home_active=" active" if view == "home" else "",
        menu=work_menu(catalog["projects"], slug) + about_menu(site, catalog["projects"]), main=main,
        footer_links=footer(site["contact"]), footer_note=escape(site["footerNote"]),
    )
    return status, html
