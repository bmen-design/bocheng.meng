# bocheng.meng

[Open the site](https://bmen-design.github.io/bocheng.meng/)

Selected projects by Bocheng Meng. Each homepage card opens its project page.

## Preview

Run `python3 serve.py --open` or double-click `Start.command` on macOS. The preview listens on your computer. Python 3.9 or newer is sufficient.

## Edit

`content/projects.json` controls the homepage, Work menu and individual project pages. Its project and gallery arrays set the display order. Sections can include paragraphs and links. A section’s optional `beforeFigure` places it before a specific gallery item, numbered from 1. Images open at full size. Add a gallery item’s optional `caption` to display an authored caption.

Each `coverCrop` records the original asset and crop rectangle in pixels, ordered as left, top, width, height. A cover can come from a gallery image, a film frame at the recorded time, or a separate project image stored as `cover-source.png`. Transparent covers can specify a `coverBackdrop` colour. To rebuild the covers, run `python3 prepare_covers.py` with Pillow installed and FFmpeg on your path.

The site name, contact links and About text are in `content/site.json`. The page shell is in `templates/page.html`, with layout and interaction code in `assets/`. Media paths resolve from the site root. The build includes only catalogue media and available responsive image variants.

## Visual changes

Change the properties named in the brief. A new cover can use a crop of the original artwork. Adding a border, shadow, background, badge or overlay is a separate design decision. Show the proposed change beside the current version and get the site owner's approval before publishing it.

The interface uses Helvetica, with Arial as the system fallback. The regular desktop size is 10px with a 13px line height, weight 400, body tracking of 0.02em and label tracking of 0.08em. The responsive values live in `assets/css/typography.css`. Changes to type, scale or interaction require an explicit design request. Keep site copy in English and preserve lettering in the original work.

Homepage cards use a 4:5 crop. On project pages, images share a width and corner radius. Each image's original aspect ratio determines its height so the whole work stays visible.

Review changed images at their rendered size on desktop and mobile. Check the subject, device edges, cut-off text and empty bands, with the pointer both over and away from the card. The publishing workflow also checks the computed styles of the built pages in Chrome before deployment.

## Build

```sh
python3 export.py --base-path /bocheng.meng/
```

The build writes the static site to `dist/`. A push to `main` rebuilds and publishes it through GitHub Pages.
