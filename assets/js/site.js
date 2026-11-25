const desktop = matchMedia('(hover: hover) and (pointer: fine)');
const quiet = matchMedia('(prefers-reduced-motion: reduce)');

const selectedFiles = new Map();
const objectURLs = new Map();
const splitFilms = new Map();

function selectFiles(files) {
  for (const url of objectURLs.values()) URL.revokeObjectURL(url);
  objectURLs.clear();
  selectedFiles.clear();
  splitFilms.clear();
  for (const file of files) {
    const relative = file.webkitRelativePath.split('/');
    if (relative.length < 2 || file.name.startsWith('.')) continue;
    const key = '/media/' + relative.slice(1).join('/');
    selectedFiles.set(key, file);
    const part = /^(.*\.mp4)\.part(\d{3})$/i.exec(key);
    if (part) {
      const group = splitFilms.get(part[1]) ?? new Map();
      group.set(Number(part[2]), file);
      splitFilms.set(part[1], group);
    }
  }
}

function objectURL(key) {
  if (objectURLs.has(key)) return objectURLs.get(key);
  let file = selectedFiles.get(key);
  const parts = splitFilms.get(key);
  if (!file && parts) {
    const ordered = [];
    for (let i = 1; i <= parts.size; i++) {
      if (!parts.has(i)) return null;
      ordered.push(parts.get(i));
    }
    file = new Blob(ordered, { type: 'video/mp4' });
  }
  if (!file) return null;
  const url = URL.createObjectURL(file);
  objectURLs.set(key, url);
  return url;
}

function mount() {
  const listeners = new AbortController();
  const signal = listeners.signal;
  const menu = Array.from(document.querySelectorAll('[data-accordion]'));
  const cursor = document.querySelector('widget-cursor');
  const films = Array.from(document.querySelectorAll('widget-player video'));
  const filmControls = new Map();
  let activePreview = null;

  function setDevice() {
    document.body.classList.toggle('desktop', desktop.matches);
    document.body.classList.toggle('devices', !desktop.matches);
    if (!desktop.matches) showPreview(null);
  }

  function reveal(media) {
    media.classList.remove('lazy', 'lazyload', 'lazyloading');
    media.classList.add('lazyloaded');
  }

  function sizeImage(image) {
    const width = image.clientWidth;
    if (width) image.sizes = Math.ceil(width) + 'px';
  }

  const measureImages = new ResizeObserver((entries) => {
    for (const entry of entries) sizeImage(entry.target);
  });

  for (const image of document.images) {
    if (image.dataset.localSrc) continue;
    image.addEventListener('load', () => reveal(image), { once: true });
    image.decoding = 'async';
    image.loading = 'lazy';
    if (image.dataset.srcset) {
      sizeImage(image);
      measureImages.observe(image);
      image.srcset = image.dataset.srcset;
    }
    if (image.dataset.src) image.src = image.dataset.src;
    if (image.complete && image.naturalWidth) reveal(image);
  }

  function showPreview(row) {
    if (!cursor) return;
    const next =
      row &&
      Array.from(cursor.children).find(
        (figure) => figure.dataset.index === row.dataset.index
      );
    if (next === activePreview) return;
    if (activePreview) activePreview.hidden = true;
    activePreview = next;
    if (next) {
      next.hidden = false;
      const image = next.querySelector('img');
      if (image) {
        image.loading = 'eager';
        if (image.dataset.srcset) sizeImage(image);
      }
    }
  }

  const rows = document.querySelector('.list-projects-items');
  rows?.addEventListener('pointermove', (event) => {
    if (!desktop.matches || !cursor) return;
    showPreview(event.target.closest('.list-projects-item'));
    if (activePreview)
      cursor.style.transform = `translate(${event.clientX + 15}px, ${event.clientY + 15}px)`;
  });
  rows?.addEventListener('pointerleave', () => showPreview(null));

  function panelFor(button) {
    return (
      document.getElementById(button.getAttribute('aria-controls')) ??
      button.nextElementSibling
    );
  }

  function adjustPanel(track) {
    if (track.clientHeight)
      track.dataset.scroll = String(track.scrollHeight > track.clientHeight);
  }

  const measurePanels = new ResizeObserver((entries) => {
    for (const entry of entries) adjustPanel(entry.target);
  });
  for (const track of document.querySelectorAll('panel-track'))
    measurePanels.observe(track);

  function displayMenu(selected, animate) {
    showPreview(null);
    for (const button of menu) {
      const panel = panelFor(button);
      const open = button === selected;
      const height = panel.getBoundingClientRect().height;
      for (const animation of panel.getAnimations()) animation.cancel();
      panel.style.removeProperty('overflow');
      button.setAttribute('aria-expanded', String(open));
      button.classList.toggle('active', open);
      panel.inert = !open;
      if (!animate || quiet.matches || (!open && panel.hidden)) {
        panel.hidden = !open;
        continue;
      }
      panel.hidden = false;
      const end = open ? panel.offsetHeight : 0;
      panel.style.overflow = 'hidden';
      const motion = panel.animate(
        [{ height: height + 'px' }, { height: end + 'px' }],
        { duration: 230, easing: 'cubic-bezier(.75,0,.25,1)' }
      );
      motion.onfinish = () => {
        panel.hidden = !open;
        panel.style.removeProperty('overflow');
        const track = panel.querySelector('panel-track');
        if (track && open) adjustPanel(track);
      };
    }
  }

  function selectMenu(button, animate = true) {
    const url = new URL(location.href);
    for (const item of menu) url.searchParams.delete(item.dataset.accordion);
    if (button) url.searchParams.set(button.dataset.accordion, 'open');
    history.replaceState(history.state, '', url);
    displayMenu(button, animate);
  }

  function restoreMenu() {
    const query = new URLSearchParams(location.search);
    displayMenu(
      menu.find((item) => query.get(item.dataset.accordion) === 'open'),
      false
    );
  }

  for (const button of menu) {
    button.addEventListener('click', () => {
      selectMenu(
        button.getAttribute('aria-expanded') === 'true' ? null : button
      );
    });
  }

  document.addEventListener(
    'keydown',
    (event) => {
      if (event.key !== 'Escape' || document.fullscreenElement) return;
      const button = menu.find(
        (item) => item.getAttribute('aria-expanded') === 'true'
      );
      if (button) {
        selectMenu(null);
        button.focus({ preventScroll: true });
      }
    },
    { signal }
  );

  function playbackState(video, state) {
    const controls = filmControls.get(video);
    video.parentElement.dataset.state = state;
    reveal(video);
    const playing = state === 'playing';
    controls.play?.classList.toggle('active', playing);
    controls.play?.setAttribute('aria-label', playing ? 'Pause' : 'Play');
  }

  async function startFilm(video) {
    try {
      await video.play();
    } catch (error) {
      if (error.name !== 'AbortError') {
        playbackState(
          video,
          error.name === 'NotAllowedError' ? 'blocked' : 'error'
        );
      }
    }
  }

  function syncAudio(video) {
    const { audio } = filmControls.get(video);
    audio?.classList.toggle('active', !video.muted);
    audio?.setAttribute('aria-label', video.muted ? 'Unmute' : 'Mute');
  }

  const inView = new IntersectionObserver((entries) => {
    for (const { target: film, isIntersecting } of entries) {
      if (
        isIntersecting &&
        film.hasAttribute('src') &&
        !quiet.matches &&
        !document.hidden
      ) {
        film.muted = true;
        startFilm(film);
      } else if (!isIntersecting) {
        film.pause();
      }
    }
  });

  for (const video of films) {
    const player = video.closest('widget-player');
    const control = (key) =>
      player.querySelector('.grid-project-figure-controls-' + key);
    const play = control('play');
    const audio = control('audio');
    filmControls.set(video, { play, audio });
    play?.addEventListener('click', () =>
      video.paused ? startFilm(video) : video.pause()
    );
    audio?.addEventListener('click', () => {
      const enable = video.muted;
      for (const other of films) other.muted = true;
      if (enable) video.muted = false;
    });
    control('fullscreen')?.addEventListener('click', async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else if (video.requestFullscreen) await video.requestFullscreen();
        else video.webkitEnterFullscreen?.();
      } catch {
        video.controls = true;
      }
    });
    video.addEventListener('volumechange', () => syncAudio(video));
    video.addEventListener('loadeddata', () => reveal(video));
    for (const [event, state] of [
      ['playing', 'playing'],
      ['pause', 'paused'],
      ['waiting', 'loading'],
      ['error', 'error']
    ]) {
      video.addEventListener(event, () => playbackState(video, state));
    }
    syncAudio(video);
    if (video.readyState >= 2) reveal(video);
    if (video.hasAttribute('src')) inView.observe(video);
  }

  document.addEventListener(
    'visibilitychange',
    () => {
      if (document.hidden) {
        for (const video of films) video.pause();
      } else {
        for (const video of films) {
          inView.unobserve(video);
          if (video.hasAttribute('src')) inView.observe(video);
        }
      }
    },
    { signal }
  );

  const pages = Array.from(
    document.querySelectorAll('#site-main, #site-footer')
  );
  function fade(outgoing) {
    if (quiet.matches) return Promise.resolve();
    const duration = outgoing ? 150 : 250;
    const frames = outgoing
      ? [
          { opacity: 1, transform: 'translateY(0)' },
          { opacity: 0, transform: 'translateY(15px)' }
        ]
      : [
          { opacity: 0, transform: 'translateY(15px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ];
    return Promise.allSettled(
      pages.map(
        (element) =>
          element.animate(frames, {
            duration,
            easing: outgoing ? 'ease-in' : 'ease-out',
            fill: outgoing ? 'forwards' : 'none'
          }).finished
      )
    );
  }

  function applyFolder() {
    let found = 0;
    for (const media of document.querySelectorAll('[data-local-src]')) {
      const local = objectURL(media.dataset.localSrc);
      const thumbnail =
        media.closest('figure, widget-player') ?? media.parentElement;
      const fallback = thumbnail.querySelector('.media-card');
      const controls = thumbnail.querySelector('.grid-project-figure-controls');
      if (fallback) fallback.hidden = !!local;
      if (controls) controls.hidden = !local;
      media.hidden = !local;
      if (local) {
        found++;
        media.src = local;
        if (media.tagName === 'VIDEO') {
          inView.observe(media);
        } else {
          media.onload = () => reveal(media);
          reveal(media);
        }
      } else if (media.hasAttribute('src')) {
        if (media.tagName === 'VIDEO') {
          inView.unobserve(media);
          media.pause();
        }
        media.removeAttribute('src');
        if (media.tagName === 'VIDEO') media.load();
      }
    }
    const feedback = document.querySelector('#media-status');
    if (feedback && selectedFiles.size) {
      feedback.textContent = found
        ? 'Local media connected.'
        : 'No matching media on this page.';
    }
  }

  const picker = document.getElementById('local-media');
  picker?.addEventListener('change', () => {
    if (!picker.files.length) return;
    selectFiles(picker.files);
    applyFolder();
  });
  desktop.addEventListener('change', setDevice, { signal });
  setDevice();
  restoreMenu();
  applyFolder();
  document.getElementById('loader')?.classList.add('completed');
  fade(false);
  return {
    fade,
    selectMenu,
    restoreMenu,
    unmount() {
      listeners.abort();
      inView.disconnect();
      measurePanels.disconnect();
      measureImages.disconnect();
      for (const film of films) {
        film.pause();
        film.removeAttribute('src');
        film.load();
      }
    }
  };
}

function routeKey(url) {
  return url.pathname.replace(/\/index\.html$/, '/').replace(/\/$/, '');
}

let page = mount();
let route = routeKey(location);
let request;
let sequence = 0;

async function navigate(url, fromHistory) {
  const id = ++sequence;
  request?.abort();
  const active = new AbortController();
  request = active;
  document.body.classList.add('transition');
  try {
    const [response] = await Promise.all([
      fetch(url.href, { signal: active.signal }),
      page.fade(true)
    ]);
    if (!response.ok && response.status !== 404)
      throw new Error('Unavailable route');
    const next = new DOMParser().parseFromString(
      await response.text(),
      'text/html'
    );
    if (id !== sequence) return;
    if (!next.getElementById('site-main')) throw new Error('Unavailable page');
    page.unmount();
    if (!fromHistory) history.pushState(null, '', response.url || url.href);
    const base = next.querySelector('base[href]');
    if (base) {
      let current = document.querySelector('base');
      if (!current) {
        current = document.createElement('base');
        document.head.prepend(current);
      }
      current.href = new URL(base.getAttribute('href'), response.url).href;
    } else {
      document.querySelector('base')?.remove();
    }
    document.title = next.title;
    document.body.dataset.template = next.body.dataset.template;
    const nodes = [...next.body.children].filter(
      (node) => node.tagName !== 'SCRIPT'
    );
    document.body.replaceChildren(...nodes);
    route = routeKey(location);
    page = mount();
    scrollTo(0, 0);
    const main = document.getElementById('site-main');
    main.tabIndex = -1;
    main.focus({ preventScroll: true });
  } catch (error) {
    if (error.name !== 'AbortError' && id === sequence)
      location.assign(url.href);
  } finally {
    if (id === sequence) {
      document.body.classList.remove('transition');
      request = null;
    }
  }
}

document.addEventListener('click', (event) => {
  const link = event.target.closest('a.link-ajax');
  if (
    !link ||
    event.defaultPrevented ||
    event.button !== 0 ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    link.target === '_blank' ||
    link.hasAttribute('download')
  )
    return;
  const url = new URL(link.href);
  if (url.origin !== location.origin || url.hash) return;
  event.preventDefault();
  if (request) return;
  page.selectMenu(null, false);
  if (routeKey(url) === route && !url.search) scrollTo(0, 0);
  else navigate(url, false);
});

window.addEventListener('popstate', () => {
  if (routeKey(location) === route && !request) page.restoreMenu();
  else navigate(new URL(location.href), true);
});
