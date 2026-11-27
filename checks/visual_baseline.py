"""Verify the portfolio's approved typography and image treatment in a served static build."""
import argparse
import json
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin

from playwright.sync_api import expect, sync_playwright

CATALOG = Path(__file__).resolve().parents[1] / "content/projects.json"


class Spacing(NamedTuple):
    module: int
    inset: int
    paragraph: int
    work_columns: int
    start: int
    footer: int


COMPACT = Spacing(10, 20, 14, 46, 160, 216)
DESKTOP = Spacing(12, 22, 16, 50, 240, 360)


TYPE = """(nodes, {size, tracking, color, family}) => {
  for (const node of nodes) {
    const s = getComputedStyle(node);
    const pixels = {fontSize: size, lineHeight: size * 1.3, letterSpacing: size * tracking};
    const values = {fontFamily: family, fontWeight: '400'};
    if (color) values.color = color;
    for (const [key, value] of Object.entries({...pixels, ...values})) {
      const ok = typeof value === 'number' ? Math.abs(parseFloat(s[key]) - value) < .02 : s[key] === value;
      if (!ok) throw Error(node.outerHTML.slice(0, 100) + ' ' + key + ': ' + s[key] + ', expected ' + value);
    }
  }
}"""

FRAMES = """(frames, {ratio, radius, excess, cursor}) => {
  const near = (actual, expected, label) => {
    if (!Number.isFinite(actual) || Math.abs(actual - expected) > .1)
      throw Error(label + ': ' + actual + ', expected ' + expected);
  };
  frames.forEach((frame, i) => {
    const image = frame.querySelector('img,video'), style = getComputedStyle(image);
    const rect = frame.getBoundingClientRect(), art = image.getBoundingClientRect();
    const label = image.getAttribute('src') + ' ';
    const gallery = Array.isArray(ratio), aspect = gallery ? ratio[i] : ratio;
    // Compare the shorter edge so browser subpixel rounding does not compound on tall pages.
    if (aspect < 1) near(rect.width, rect.height * aspect, label + 'frame width');
    else near(rect.height, rect.width / aspect, label + 'frame height');
    if (cursor) near(rect.width, 115, label + 'preview width');
    const rules = getComputedStyle(frame);
    for (const corner of ['TopLeft','TopRight','BottomLeft','BottomRight']) {
      near(parseFloat(rules['border' + corner + 'Radius']), radius, label + corner);
      near(parseFloat(style['border' + corner + 'Radius']), 0, label + 'inner radius');
    }
    if (rules.overflow !== 'hidden' || rules.backgroundColor !== 'rgb(247, 247, 247)' || style.objectFit !== 'cover' ||
        style.objectPosition !== '50% 50%') throw Error(label + 'image fit, position or frame background');
    if (gallery) {
      const grid = frame.closest('.grid-project-figures'), column = grid.getBoundingClientRect();
      near(rect.width, column.width || document.querySelector('#site-main').getBoundingClientRect().width, label + 'column');
      if (style.backgroundColor !== 'rgba(0, 0, 0, 0)') throw Error(label + 'image matte');
    }
    near(art.width, rect.width + excess, label + 'image width');
    near(art.height, rect.height + excess, label + 'image height');
    near(art.left, rect.left - excess / 2, label + 'image left');
    near(art.top, rect.top - excess / 2, label + 'image top');
    const figure = frame.closest('figure');
    const layers = new Set([frame, image, figure, figure.querySelector('.grid-projects-figure-link'), frame.closest('a,widget-player')]);
    for (const layer of layers) {
      if (!layer) continue;
      const s = getComputedStyle(layer);
      for (const side of ['Top','Right','Bottom','Left']) {
        for (const prop of ['border' + side + 'Width','padding' + side,'margin' + side])
          near(parseFloat(s[prop]), 0, label + prop);
      }
      if (s.boxShadow !== 'none' || s.outlineStyle !== 'none' || s.backgroundImage !== 'none')
        throw Error(label + 'added frame decoration');
      for (const pseudo of ['::before','::after']) {
        if (!['none','normal'].includes(getComputedStyle(layer, pseudo).content))
          throw Error(label + 'added ' + pseudo);
      }
    }
  });
}"""


def check_type(page, selector, size, tracking, color=None, family='Helvetica, Arial, sans-serif'):
    nodes = page.locator(selector)
    expect(nodes.first).to_be_attached()
    nodes.evaluate_all(TYPE, dict(size=size, tracking=tracking, color=color, family=family))


def check_section_headings(page, selector, size):
    check_type(page, selector, size, .08, color='rgba(0, 0, 0, 0.3)', family='"IBM Plex Mono", monospace')
    page.locator(selector).evaluate_all("""headings => {
      for (const heading of headings) {
        const square = getComputedStyle(heading, '::before');
        const style = getComputedStyle(heading);
        if (style.fontSizeAdjust !== 'cap-height 0.7173' || style.alignItems !== 'baseline' ||
            style.fontStyle !== 'normal' || style.textTransform !== 'uppercase' ||
            heading.innerText !== heading.textContent.toUpperCase() ||
            square.backgroundColor !== 'rgb(130, 255, 159)' ||
            square.width !== '4px' || square.height !== '4px' || style.columnGap !== '8px')
          throw Error(heading.textContent + ': expected uppercase upright type and two square widths of space');
      }
    }""")


def check_frames(frames, count, radius, ratio, excess=0, cursor=False):
    expect(frames).to_have_count(count)
    frames.evaluate_all(FRAMES, dict(ratio=ratio, radius=radius, excess=excess, cursor=cursor))


def near(label, actual, expected):
    if abs(actual - expected) > .25:
        raise AssertionError(f'{label}: {actual:.2f}px, expected {expected:.2f}px')


def check_panel_spacing(panel, spacing):
    measurements = panel.evaluate("""panel => {
      const style = getComputedStyle(panel), rect = e => e.getBoundingClientRect();
      const gapBefore = e => rect(e).top - rect(e.previousElementSibling).bottom;
      return {
        inset: [style.paddingTop, style.paddingLeft, style.paddingRight].map(parseFloat),
        bottom: parseFloat(style.paddingBottom),
        sections: [...panel.children].slice(1).map(gapBefore),
        paragraphs: [...panel.querySelectorAll('.text-body-content > p + p')].map(gapBefore),
      };
    }""")
    for inset in measurements['inset']:
        near('panel inset', inset, spacing.inset)
    near('panel bottom inset', measurements['bottom'], 2 * spacing.inset)
    for gap in measurements['sections']:
        near('panel section gap', gap, 2 * spacing.inset)
    for gap in measurements['paragraphs']:
        near('gap between paragraph boxes', gap, spacing.paragraph)


def check_project_layout(page, width, size, spacing):
    boxes = page.locator('#site-main').evaluate("""main => {
      const nodes = {main, title: main.querySelector('#site-main-header-title'),
        info: main.querySelector('#site-main-info'), back: main.querySelector('a.link-ajax--home'),
        gallery: main.querySelector('#site-main-content')};
      return Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, node.getBoundingClientRect().toJSON()]));
    }""")
    main, title, info, back, gallery = (boxes[k] for k in ('main', 'title', 'info', 'back', 'gallery'))

    gap = spacing.module
    narrow = width <= 840
    column = main['width'] if narrow else (main['width'] - 3 * gap) / 4
    for name, box in [('title', title), ('info', info), ('back', back)]:
        near(f'{name} left', box['left'], main['right'] - column)
        near(f'{name} width', box['width'], column)
    near('title top', title['top'], main['top'])
    near('title to info gap', info['top'] - title['bottom'], gap)
    rows = page.locator('#site-main-info .list-details-item').evaluate_all('''items => items.map(item => {
        const label = item.querySelector('dt').getBoundingClientRect();
        const value = item.querySelector('dd').getBoundingClientRect();
        return {left: value.left, valueTop: value.top, labelBottom: label.bottom};
    })''')
    stacked = info['width'] - 2 * spacing.inset <= 17 * size
    for row in rows:
        if stacked:
            near('detail value at left inset', row['left'], info['left'] + spacing.inset)
            if row['valueTop'] < row['labelBottom'] - .1:
                raise AssertionError('Detail value overlaps its label in a narrow card')
        else:
            near('detail value at card midpoint', row['left'], info['left'] + info['width'] / 2)
    near('info to back gap', back['top'] - info['bottom'], gap)
    near('gallery left', gallery['left'], main['left'])
    near('gallery width', gallery['width'], main['width'] if narrow else 3 * column + 2 * gap)
    near('gallery top', gallery['top'], back['bottom'] + gap if narrow else title['top'])
    check_panel_spacing(page.locator('#site-main-info'), spacing)
    media_gaps = page.locator('.grid-project-figure + .grid-project-figure').evaluate_all(
        'els => els.map(e => e.getBoundingClientRect().top - e.previousElementSibling.getBoundingClientRect().bottom)')
    for media_gap in media_gaps:
        near('gallery row gap', media_gap, gap)
    if page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth'):
        raise AssertionError('Project page overflows horizontally')


def check_project_menu_clearance(page, width, spacing):
    gap = spacing.module
    sidebar = page.locator('#site-main-header')
    gallery = page.locator('#site-main-content')
    initial_sidebar = sidebar.bounding_box()
    initial_gallery = gallery.bounding_box()
    for name in ('Work', 'About'):
        toggle = page.get_by_role('button', name=name)
        toggle.click()
        panel = page.locator(f'#{name.lower()}-panel')
        expect(panel).to_be_visible()
        box = panel.bounding_box()
        button = toggle.bounding_box()
        near(f'{name} toggle to panel gap', box['y'] - button['y'] - button['height'], gap)
        check_panel_spacing(panel.locator('.site-menu-item-panel'), spacing)
        expected_top = max(initial_sidebar['y'], box['y'] + box['height'] + gap)
        if abs(sidebar.bounding_box()['y'] - expected_top) > .5:
            raise AssertionError(f'Sidebar should clear {name} and start at {expected_top:.1f}px')
        if width > 840 and gallery.bounding_box() != initial_gallery:
            raise AssertionError(f'Desktop gallery moved when {name} opened')
    page.keyboard.press('Escape')
    expect(page.locator('#about-panel')).to_be_hidden()
    if sidebar.bounding_box() != initial_sidebar or gallery.bounding_box() != initial_gallery:
        raise AssertionError('Sidebar or gallery did not return to its closed-menu position')


def home(page, projects, size, radius, touch, spacing):
    card = page.locator('.grid-projects-figure').first
    covers = page.locator('.grid-projects-figure-thumbnail')
    title = card.locator('h3')
    layout = page.evaluate('''() => {
      const rect = id => document.querySelector(id).getBoundingClientRect();
      const main = rect('#site-main');
      const grid = getComputedStyle(document.querySelector('.grid-projects-figures'));
      return {left: main.left, right: document.documentElement.clientWidth - main.right,
        start: main.top - rect('#site-menu').bottom, footer: rect('#site-footer').top - main.bottom,
        rows: parseFloat(grid.rowGap), columns: parseFloat(grid.columnGap)};
    }''')
    for key in ('left', 'right', 'rows', 'columns'):
        near(key, layout[key], spacing.module)
    near('menu to first card', layout['start'], spacing.start)
    near('last card to footer', layout['footer'], spacing.footer)
    check_catalog_links(page.locator('.grid-projects-figure-link'), projects)
    check_sources(covers.locator('img'), [p['cover'] for p in projects])
    check_type(page, '.grid-projects-figure-caption-title > span', size, .08)
    expect(title).to_have_css('opacity', '0')
    offset = title.evaluate("e => new DOMMatrix(getComputedStyle(e).transform).m42")
    if abs(offset - size * 1.5) > .02:
        raise AssertionError(f"Hidden title offset {offset}px")
    check_frames(covers, len(projects), radius, .8, 2 if touch else 2 * size)
    if not touch:
        card.locator('a').hover()
        expect(title).to_have_css('opacity', '1')
        check_frames(covers.first, 1, radius, .8, 2)
        centered = card.evaluate("""e => {const a=e.getBoundingClientRect(), b=e.querySelector('h3').getBoundingClientRect();
          return Math.abs(a.x+a.width/2-b.x-b.width/2)<.1 && Math.abs(a.y+a.height/2-b.y-b.height/2)<.1;}""")
        if not centered:
            raise AssertionError('Hover title is off center')
    page.get_by_role('button', name='Work').click()
    page.mouse.move(0, 0)
    check_catalog_links(page.locator('.list-projects-item-link'), projects)
    check_sources(page.locator('widget-cursor img'), [p.get('preview', p['cover']) for p in projects])
    for row in ('.list-projects-header', '.list-projects-item'):
        gap = page.locator(row).first.evaluate('e => parseFloat(getComputedStyle(e).columnGap)')
        near(f'{row} column gap', gap, spacing.work_columns)
    check_type(page, '.list-projects-header > span', size, .08, 'rgba(0, 0, 0, 0.3)', '"IBM Plex Mono", monospace')
    expect(page.locator('.list-projects-header')).to_have_css('text-transform', 'uppercase')
    expect(page.locator('.list-projects-header')).to_have_css('font-size-adjust', 'cap-height 0.7173')
    cells = page.locator('.list-projects-header > span')
    expect(cells).to_have_text(['Project number', 'TITLE', 'CATEGORIES', 'YEAR'])
    expect(cells.first.locator('.visually-hidden')).to_have_text('Project number')
    cells.evaluate_all("""cells => cells.forEach((cell, index) => {
      const square = getComputedStyle(cell, '::before');
      if (square.content !== '""' || square.width !== '4px' || square.height !== '4px' ||
          square.backgroundColor !== 'rgb(130, 255, 159)' ||
          square.marginInlineEnd !== (index === 0 ? '0px' : '8px'))
        throw Error(cell.textContent + ': incorrect Work header marker');
    })""")
    check_type(page, '.list-projects-item > :is(h3, span)', size, .08, 'rgb(0, 0, 0)')
    if touch:
        expect(page.locator('widget-cursor')).to_be_hidden()
    else:
        page.locator('.list-projects-item-link').first.hover()
        check_frames(page.locator('widget-cursor figure:not([hidden])'), 1, 15, 1, cursor=True)
    page.get_by_role('button', name='About').click()
    check_section_headings(page, '#about-panel h2', size)
    faces = page.evaluate('''async () => (await document.fonts.load('400 11px "IBM Plex Mono"')).length''')
    assert faces == 1, 'Section heading font failed to load'
    check_type(page, '#about-panel .text-body-content > p', size, .02)
    about_panel = page.locator('#about-panel')
    about_panel.locator('h2').first.click()
    expect(about_panel).to_be_visible()
    if touch:
        page.touchscreen.tap(1, 120)
    else:
        page.mouse.click(1, 120)
    expect(about_panel).to_be_hidden()
    expect(page.get_by_role('button', name='About')).to_have_attribute('aria-expanded', 'false')
    bars = [page.locator(selector) for selector in ('#site-header', '#site-menu')]
    bar_positions = [bar.bounding_box()['y'] for bar in bars]
    page.evaluate('window.scrollTo(0, 160)')
    for bar, initial_top in zip(bars, bar_positions):
        if abs(bar.bounding_box()['y'] - initial_top) > .25:
            raise AssertionError('The top navigation moved when the page scrolled')
    for name, offset in [('Work', 80), ('About', 120)]:
        button = page.get_by_role('button', name=name)
        button.click()
        expect(button).to_have_attribute('aria-expanded', 'true')
        page.evaluate('y => window.scrollTo(0, y)', offset)
        expect(page.locator(f'#{name.lower()}-panel')).to_be_hidden()
        expect(button).to_have_attribute('aria-expanded', 'false')
    page.evaluate('window.scrollTo(0, 0)')
    if touch:
        card.locator('a').tap()
        expect(page.locator('body')).to_have_attribute('data-template', 'project')


def check_catalog_links(nodes, projects):
    links = nodes.evaluate_all("nodes => nodes.map(n => [n.getAttribute('href'), n.getAttribute('aria-label')])")
    if links != [[f"work/{p['slug']}/", p['title']] for p in projects]:
        raise AssertionError(f'Project navigation titles or order changed: {links}')


def check_sources(nodes, sources):
    actual = nodes.evaluate_all("nodes => nodes.map(n => n.getAttribute('src'))")
    if actual != [src.lstrip('/') for src in sources]:
        raise AssertionError(f'Media order or source changed: {actual}')


def check_media_files(request, base, projects):
    sources = set()
    for project in projects:
        sources.add(project['cover'])
        sources.add(project.get('preview', project['cover']))
        sources.update(item['src'] for item in project['gallery'])
    for src in sorted(sources):
        response = request.head(urljoin(base, src.lstrip('/')))
        media_type = response.headers.get('content-type', '')
        if not response.ok or not media_type.startswith(('image/', 'video/')):
            raise AssertionError(f'{response.url}: expected media, received {response.status} {media_type}')


def run(browser, base, projects, width):
    spacing = COMPACT if width <= 600 else DESKTOP
    touch = width == 390
    size = 1 + (width / 44 if width < 440 else max(10, width / 192))
    cover_radius = width * 80 / (840 if width <= 840 else 1512)
    page = browser.new_page(viewport={'width': width, 'height': 900}, has_touch=touch,
                            is_mobile=touch, reduced_motion='reduce')
    routes = [('', 'home', None), ('404.html', 'error', None)]
    routes.extend((f"work/{p['slug']}/", 'project', p) for p in projects)
    try:
        if width == 1440:
            check_media_files(page.request, base, projects)
        for path, view, project in routes:
            page.goto(urljoin(base, path), wait_until='domcontentloaded')
            page.mouse.move(0, 0)
            expect(page.locator('body')).to_have_attribute('data-template', view)
            check_type(page, '#site-header-tagline, .cta-pill-label, #site-footer-colophon p', size, .08)
            if view == 'home':
                work = page.get_by_role('button', name='Work', exact=True)
                for prop in ('background-color', 'backdrop-filter'):
                    value = work.evaluate('(button, prop) => getComputedStyle(button).getPropertyValue(prop)', prop)
                    expect(page.locator('#site-header')).to_have_css(prop, value)
                home(page, projects, size, cover_radius, touch, spacing)
            else:
                check_type(page, '#site-main-header-title > span', size, .08)
                check_section_headings(page, '#site-main-info h2', size)
                check_type(page, '#site-main-info .text-body-content > p', size, .02)
            if project:
                check_project_layout(page, width, size, spacing)
                if project['slug'] == 'uxtester':
                    check_project_menu_clearance(page, width, spacing)
                expect(page.locator('#site-main-header-title')).to_have_text(project['title'])
                if project['slug'] == 'bull-user-echo':
                    title_link = page.get_by_role('heading', level=1).get_by_role('link', name=project['title'])
                    page.evaluate('window.scrollTo(0, 120)')
                    page.wait_for_function('scrollY > 0')
                    initial_url = page.url
                    edge = {'x': title_link.bounding_box()['width'] - 12, 'y': 12}
                    if touch:
                        title_link.tap(position=edge)
                    else:
                        title_link.click(position=edge)
                    page.wait_for_function('scrollY === 0')
                    expect(page).to_have_url(initial_url)
                check_type(page, '.list-details-item > :is(dt, dd)', size, .02)
                lead = page.locator('#site-main-info .text-body-content').first.locator(':scope > p')
                expect(lead).to_have_text([project['description'], *project.get('paragraphs', [])])
                art = project['gallery']
                gallery = page.locator('#site-main-content')
                expect(gallery).to_have_text('')
                expect(gallery.locator('h1,h2,h3,h4,h5,h6,p,figcaption,.grid-project-figures > :not(figure)')).to_have_count(0)
                check_sources(gallery.locator('img,video'), [a['src'] for a in art])
                controls = gallery.locator('.grid-project-figure-controls').evaluate_all(
                    "groups => groups.map(group => group.getAttribute('data-options'))")
                if controls != [','.join(a['controls']) for a in art if 'controls' in a]:
                    raise AssertionError('Video controls differ from the project catalogue')
                check_frames(page.locator('.grid-project-figure-thumbnail'), len(art), 1.5 * size, [a['ratio'] for a in art])
        print(f'{width}px: {len(routes)} pages passed', flush=True)
    except Exception as exc:
        raise AssertionError(f'{width}px {page.url}: {exc}') from exc
    finally:
        page.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, help='URL of the served export, including its site prefix')
    base = parser.parse_args().base_url.rstrip('/') + '/'
    projects = json.loads(CATALOG.read_text(encoding='utf-8'))['projects']
    with sync_playwright() as playwright:
        with playwright.chromium.launch(channel='chrome') as browser:
            for width in (390, 840, 841, 1440, 2560):
                run(browser, base, projects, width)
