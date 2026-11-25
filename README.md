# bocheng.meng

[Open the site](https://bmen-design.github.io/bocheng.meng/)

An independent educational study of a portfolio interface. The work index, overview grid and individual project pages share a single catalogue. The study is unaffiliated with the original portfolio and featured brands.

## Preview

Run `python3 serve.py --open` or double-click `Start.command` on macOS. The preview listens on your computer. Python 3.9 or newer is sufficient.

## Edit

`content/projects.json` contains the project order, metadata and gallery layouts. The site name, contact links and About panel are in `content/site.json`. The page shell is in `templates/page.html`, with layout and interaction code in `assets/`.

The media paths in the catalogue are relative to the site root. Images and films live under `media/<project>/`. The largest film is stored in numbered parts for Git and reassembled into a single MP4 during the build. The local preview also supports seeking within that film.

## Build

```sh
python3 export.py --base-path /bocheng.meng/
```

The build writes the static site to `dist/`. A push to `main` rebuilds and publishes it through GitHub Pages.
