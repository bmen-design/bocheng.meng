# bocheng.meng

[Open the site](https://bmen-design.github.io/bocheng.meng/)

Bocheng Meng’s portfolio. Each homepage card opens its project page.

## Preview

Run `python3 serve.py --open` or double-click `Start.command` on macOS. The preview listens on your computer. Python 3.9 or newer is sufficient.

## Edit

`content/projects.json` controls the homepage, Work menu and individual project pages. The project list sets their display order. Each project has a homepage cover, an information panel and a gallery. The Work menu uses the cover unless the project supplies a separate `preview`. The gallery displays images and videos in their listed order. Click a still to open it at full size.

Covers can use a supplied image directly or define a `coverCrop` with a source and rectangle in pixels, ordered as left, top, width and height. Run `python3 prepare_covers.py` with Pillow installed to rebuild the custom crops. Crops from video frames also require FFmpeg.

The site name, contact links and About text are in `content/site.json`. The page shell is in `templates/page.html`, with layout and interaction code in `assets/`. Media paths resolve from the site root. The build includes only catalogue media and available responsive image variants.

## Visual changes

Change the properties named in the brief. A new cover can use a crop of the original artwork. Adding a border, shadow, background, badge or overlay is a separate design decision. Show the proposed change beside the current version and get the site owner's approval before publishing it.

The interface uses Helvetica, with Arial as the system fallback. Uppercase section headings use ABC Marist Book with a green square. Pages supplies the font during the build. For a local preview, place the licensed OpenType file at `assets/fonts/section-heading.otf`. The regular desktop size is 10px with a 13px line height, weight 400, body tracking of 0.02em and label tracking of 0.08em. The responsive values live in `assets/css/typography.css`. Changes to type, scale or interaction require an explicit design request. Keep site copy in English and preserve lettering in the original work.

Homepage cards use a 4:5 crop. On project pages, images share a width and corner radius. Each image's original aspect ratio determines its height so the whole work stays visible.

Review changed images at their rendered size on desktop and mobile. Check the subject, device edges, cut-off text and empty bands, with the pointer both over and away from the card. The publishing workflow also checks the computed styles of the built pages in Chrome before deployment.

## Build

```sh
python3 export.py --base-path /bocheng.meng/
```

The build writes the static site to `dist/`. A push to `main` rebuilds and publishes it through GitHub Pages.
