# bocheng.meng

[Open the site](https://bmen-design.github.io/bocheng.meng/)

Selected projects by Bocheng Meng. Each homepage card opens its project page.

## Preview

Run `python3 serve.py --open` or double-click `Start.command` on macOS. The preview listens on your computer. Python 3.9 or newer is sufficient.

## Edit

`content/projects.json` controls the homepage, Work menu and individual project pages. Its project and gallery arrays set the display order. Sections can include paragraphs and links. A section’s optional `beforeFigure` places it before a specific gallery item, numbered from 1. Images open at full size. Add a gallery item’s optional `caption` to display an authored caption.

Each `coverCrop` records its gallery source and crop rectangle in original pixels, ordered as left, top, width, height. A film crop also records the frame time in seconds. To rebuild the checked-in covers after editing those values, run `python3 prepare_covers.py` with Pillow installed and FFmpeg on your path.

The site name, contact links and About text are in `content/site.json`. The page shell is in `templates/page.html`, with layout and interaction code in `assets/`. Media paths resolve from the site root. The build includes only catalogue media and available responsive image variants.

## Build

```sh
python3 export.py --base-path /bocheng.meng/
```

The build writes the static site to `dist/`. A push to `main` rebuilds and publishes it through GitHub Pages.
