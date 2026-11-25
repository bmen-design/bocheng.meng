"""Render the overview, project pages and navigation from the content directory."""

import json
import re
from html import escape
from pathlib import Path
from string import Template
from textwrap import shorten
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WIDTHS = (320, 480, 640, 960, 1280, 1600, 1920)
ICONS = {p.stem: p.read_text() for p in (ROOT / "templates/icons").glob("*.svg")}
ROUND_PILL = "cta-pill cta-pill--blur cta-pill--filled cta-pill--rounded"


def icon(name):
    return f'<span class="cta-pill-icon">{ICONS[name]}</span>'


def image_variants(src):
    stem = src.lstrip("/").rsplit(".", 1)[0]
    for width in WIDTHS:
        path = f"{stem}-{width}.webp"
        if (ROOT / path).is_file():
            yield path, width


def image(src, alt):
    variants = [f"{escape(path)} {width}w" for path, width in image_variants(src)]
    responsive = f'srcset="{", ".join(variants)}" sizes="auto, 50vw"' if variants else ""
    return (f'<img class="thumb" loading="lazy" decoding="async" src="{escape(src.lstrip("/"))}" '
            f'{responsive} alt="{escape(alt)}">')


def project_link(project, classes, current=None):
    slug = project["slug"]
    active = ' active' if slug == current else ''
    selected = ' aria-current="page"' if active else ''
    return (f'<a class="{classes} link-ajax{active}" href="work/{escape(slug)}/"{selected} '
            f'aria-label="{escape(project["title"])}"></a>')


def overview(projects):
    cards = []
    for project in projects:
        cover = image(project["cover"], project["alt"])
        link = project_link(project, "grid-projects-figure-link")
        title = escape(project["title"])
        cards.append(f'''
          <figure class="grid-projects-figure">
            {link}
            <div class="grid-projects-figure-thumbnail">{cover}</div>
            <figcaption class="grid-projects-figure-caption">
              <h3 class="grid-projects-figure-caption-title"><span>{title}</span></h3>
            </figcaption>
          </figure>''')
    return (f'<div id="site-main-content"><h1 class="visually-hidden">Selected work</h1><div class="grid-projects">'
            f'<div class="grid-projects-figures">{"".join(cards)}</div></div></div>')


def section_header(kind, title):
    return (f'<header class="{kind}-header"><h2 class="{kind}-header-title font-subtle '
            f'font-uppercase">{escape(title)}</h2></header>')


def text_section(title, paragraphs, links=()):
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    content = "".join(f'<p>{escape(value)}</p>' for value in paragraphs if value)
    if links:
        anchors = [f'<li><a class="link-inline" href="{escape(link["href"])}">{escape(link["label"])}</a></li>'
                   for link in links]
        content += f'<ul class="text-links">{"".join(anchors)}</ul>'
    if not content:
        return ""
    header = section_header("text-body", title) if title else ""
    return f'<div class="text-body">{header}<div class="text-body-content">{content}</div></div>'


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
        thumbnail = image(project["cover"], project["alt"])
        previews.append(f'<figure class="widget-cursor-thumbnail" data-index="{index}" hidden>'
                        f'{thumbnail}</figure>')
    content = (f'<div class="list-projects"><header class="list-projects-header font-subtle">'
               f'{headings}</header><ul class="list-projects-items">{"".join(rows)}</ul></div>')
    return accordion("work", content, "large", f'<widget-cursor>{"".join(previews)}</widget-cursor>')


def about_content(site):
    contacts = [f'<a class="link-inline" href="{escape(c["href"])}">{escape(c["label"])}</a>'
                for c in site["contact"]]
    lead = site["introduction"]
    paragraphs = [lead] if isinstance(lead, str) else list(lead)
    paragraphs.extend(site.get("paragraphs", []))
    content = [text_section("About", paragraphs)]
    for section in site.get("aboutSections", []):
        content.append(text_section(section["title"], section["paragraphs"], section.get("links", [])))
    if site.get("disciplines"):
        content.append(about_list("Disciplines", map(escape, site["disciplines"])))
    if contacts:
        content.append(about_list("Contact", contacts))
    return "".join(content)


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
    inserts = {}
    for section in project.get("sections", []):
        if "beforeFigure" in section:
            index = section["beforeFigure"]
            if not 1 <= index <= len(project["gallery"]) + 1:
                raise ValueError(f'Invalid gallery section position in {project["slug"]}')
            inserts.setdefault(index, []).append(text_section(section["title"], section["paragraphs"], section.get("links", [])))

    for i, item in enumerate(project["gallery"], 1):
        figures.extend(inserts.get(i, []))
        source = escape(item["src"].lstrip("/"))
        label = item.get("alt") or item.get("caption") or f'{project["title"]}, figure {i}'
        ratio = float(item["ratio"])
        if ratio <= 0:
            raise ValueError(f'Invalid media ratio in {project["slug"]}')
        preview = ""
        if ratio < 0.4 and "controls" not in item:
            preview = ' data-preview="top"'
        elif abs(ratio / 1.5 - 1) <= 0.025:
            preview = ' data-preview="fill"'
        style = f"--source-ratio: {ratio}"
        if "matte" in item:
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", item["matte"]):
                raise ValueError(f'Invalid media background in {project["slug"]}')
            style += f'; --matte: {item["matte"]}'
        frame = f'class="grid-project-figure-thumbnail"{preview} style="{style}"'
        if "controls" in item:
            media = (f'<widget-player><div {frame} data-state="idle">'
                     f'<video class="thumb" controls preload="metadata" playsinline muted loop '
                     f'src="{source}" aria-label="{escape(label)}"></video></div>'
                     + video_controls(item["controls"]) + '</widget-player>')
        else:
            media = (f'<a class="project-still" href="{source}" target="_blank" rel="noopener" '
                     f'aria-haspopup="dialog" aria-label="Enlarge image: {escape(label)}">'
                     f'<div {frame}>{image(item["src"], label)}</div></a>')
        caption = f'<figcaption>{escape(item["caption"])}</figcaption>' if item.get("caption") else ""
        figures.append('<figure class="grid-project-figure">'
                       f'{media}{caption}</figure>')
    figures.extend(inserts.get(len(project["gallery"]) + 1, []))
    return (f'<div id="site-main-content"><div class="grid-project">'
            f'<div class="grid-project-figures">{"".join(figures)}</div></div></div>')


def page_heading(title, back_label):
    return (f'<header id="site-main-header"><h1 id="site-main-header-title"><span>{escape(title)}</span></h1>'
            f'<a class="{ROUND_PILL} link-ajax link-ajax--home" href="./">'
            f'<span class="cta-pill-label">{back_label}</span>{icon("triangle-west")}</a></header>')


def project_page(project):
    facts = [("Year", project["year"]), ("Categories", ", ".join(project["categories"]))]
    facts.extend((row["label"], row["value"]) for row in project.get("details", []))
    lead = [project["description"], *project.get("paragraphs", [])]
    info = [details("Project", facts), text_section("Overview", lead, project.get("links", []))]
    for section in project.get("sections", []):
        if "beforeFigure" not in section:
            info.append(text_section(section["title"], section["paragraphs"], section.get("links", [])))
    if project.get("credits"):
        info.append(details("Credits", [(row["label"], row["value"]) for row in project["credits"]]))
    return (page_heading(project["title"], "Back to Overview")
            + f'<div id="site-main-info">{"".join(info)}</div>' + gallery(project))


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
    route = urlsplit(path).path.rstrip("/").removesuffix("/index.html")
    status, slug = 200, None
    title = site["name"]
    summary = site["introduction"]
    if isinstance(summary, list):
        summary = " ".join(summary)
    if not route:
        view = "home"
        main = overview(catalog["projects"])
    elif route.startswith("/work/") and route[6:] in projects:
        slug = route[6:]
        view = "project"
        main = project_page(projects[slug])
        summary = projects[slug]["description"]
        title = f'{projects[slug]["title"]} — {title}'
    else:
        status, view = 404, "error"
        main = (page_heading("404", "Back to Homepage") + '<div id="site-main-info">'
                + text_section("Information", "The page doesn’t exist.") + '</div>')
        title = f'404 — {title}'
    about = about_content(site)
    plain_links = [f'<li><a href="work/{escape(item["slug"])}/">{escape(item["title"])}</a></li>'
                   for item in catalog["projects"]]
    template = Template((ROOT / "templates/page.html").read_text())
    html = template.substitute(
        document_base=escape(document_base), description=escape(shorten(summary, width=180, placeholder="…")),
        title=escape(title), view=view, name=escape(site["name"]), wordmark=escape(site["name"].upper()),
        tagline=escape(site["tagline"]), home_active=" active" if view == "home" else "",
        menu=work_menu(catalog["projects"], slug) + accordion("about", about, "small"), main=main,
        simple_work="".join(plain_links), simple_about=about,
        footer_links=footer(site["contact"]), footer_note=escape(site["footerNote"]),
    )
    return status, html
