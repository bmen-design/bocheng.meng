# bocheng.meng

[Open the site](https://bmen-design.github.io/bocheng.meng/)

An independent educational study of a portfolio interface. The homepage links to selected projects on Cargo. The study is unaffiliated with the original portfolio and featured brands.

## Preview

Run `python3 serve.py --open` or double-click `Start.command` on macOS. The preview listens on your computer. Python 3.9 or newer is sufficient.

## Edit

`content/home.json` sets the order, titles, covers and destinations for the homepage grid and its Work menu. `content/projects.json` contains the local project pages, their Work menu order and gallery layouts. The site name, contact links and About panel are in `content/site.json`. The page shell is in `templates/page.html`, with layout and interaction code in `assets/`.

The media paths in the catalogue are relative to the site root. Images and films live under `media/<project>/`. The largest film is stored in numbered parts for Git and reassembled into a single MP4 during the build. The local preview also supports seeking within that film.

## Build

```sh
python3 export.py --base-path /bocheng.meng/
```

The build writes the static site to `dist/`. A push to `main` rebuilds and publishes it through GitHub Pages.
