const desktop = matchMedia('(hover: hover) and (pointer: fine)');
const quiet = matchMedia('(prefers-reduced-motion: reduce)');
const motionEase = getComputedStyle(document.documentElement).getPropertyValue('--motion-ease').trim();

function mount() {
  const listeners = new AbortController();
  const signal = listeners.signal;
  const menu = Array.from(document.querySelectorAll('[data-accordion]'));
  const panels = menu.map(panelFor);
  const sidebar = document.querySelector('.project-sidebar');
  const cursor = document.querySelector('widget-cursor');
  const films = Array.from(document.querySelectorAll('widget-player video'));
  const filmControls = new Map();
  let activePreview = null;
  let menuScrollY = null;

  function setDevice() {
    document.body.classList.toggle('desktop', desktop.matches);
    document.body.classList.toggle('devices', !desktop.matches);
    if (!desktop.matches) showPreview(null);
  }

  function reveal(media) {
    media.classList.remove('lazy', 'lazyload', 'lazyloading');
    media.classList.add('lazyloaded');
  }

  for (const image of document.images) {
    if (image.complete && image.naturalWidth) reveal(image);
    else image.addEventListener('load', () => reveal(image), { once: true });
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
      if (image) image.loading = 'eager';
    }
  }

  const rows = document.querySelector('.list-projects-items');
  rows?.addEventListener('pointermove', (event) => {
    if (!desktop.matches || !cursor || event.pointerType === 'touch') return;
    cursor.classList.toggle('tracking', Boolean(activePreview));
    showPreview(event.target.closest('.list-projects-item'));
    if (activePreview)
      cursor.style.transform = `translate(${event.clientX + 15}px, ${event.clientY + 15}px)`;
  });
  rows?.addEventListener('pointerleave', () => showPreview(null));
  rows?.addEventListener('keydown', () => showPreview(null));
  rows?.closest('panel-track')?.addEventListener('scroll', () => showPreview(null));

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

  function positionSidebar() {
    if (!sidebar) return;
    const visible = panels.filter((panel) => !panel.hidden);
    if (!visible.length) {
      sidebar.style.removeProperty('--menu-offset');
      return;
    }
    // Measure from the sidebar's original position, even while its contents are moving.
    const slot = sidebar.getBoundingClientRect();
    const header = sidebar.firstElementChild;
    const gap = parseFloat(getComputedStyle(header).rowGap);
    let offset = 0;
    for (const panel of visible) {
      const box = panel.getBoundingClientRect();
      if (box.height && box.left < slot.right && box.right > slot.left &&
          slot.top + header.offsetHeight > box.top) {
        offset = Math.max(offset, box.bottom + Math.min(gap, box.height) - slot.top);
      }
    }
    sidebar.style.setProperty('--menu-offset', offset + 'px');
  }

  const measurePanels = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (entry.target.localName === 'panel-track') adjustPanel(entry.target);
    }
    positionSidebar();
  });
  for (const panel of panels) {
    measurePanels.observe(panel.querySelector('panel-track'));
    if (sidebar) measurePanels.observe(panel);
  }
  if (sidebar) window.addEventListener('resize', positionSidebar, { signal });

  function pageScrollY() {
    const root = document.documentElement;
    // Ignore Safari's bounce beyond the top and bottom of the page.
    return Math.max(0, Math.min(scrollY, root.scrollHeight - root.clientHeight));
  }

  function displayMenu(selected, animate) {
    menuScrollY = selected ? pageScrollY() : null;
    showPreview(null);
    const previousHeight = Math.max(0, ...panels.map((panel) => panel.getBoundingClientRect().height));
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
      const start = open ? Math.min(previousHeight, end) : height;
      panel.style.overflow = 'hidden';
      const motion = panel.animate(
        [{ height: start + 'px' }, { height: end + 'px' }],
        { duration: 230, easing: motionEase }
      );
      motion.onfinish = () => {
        panel.hidden = !open;
        panel.style.removeProperty('overflow');
        const track = panel.querySelector('panel-track');
        if (track && open) adjustPanel(track);
      };
    }
    positionSidebar();
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

  window.addEventListener('scroll', () => {
    if (menuScrollY !== null && pageScrollY() !== menuScrollY) selectMenu(null);
    else if (sidebar?.style.getPropertyValue('--menu-offset')) positionSidebar();
  }, { passive: true, signal });

  document.addEventListener('pointerup', (event) => {
    if (!event.isPrimary || event.button !== 0 ||
        event.target.closest('[data-accordion], .site-menu-item-panel-wrapper')) return;
    if (menu.some((button) => button.getAttribute('aria-expanded') === 'true'))
      selectMenu(null);
  }, { signal });

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
      if (isIntersecting && !quiet.matches && !document.hidden) {
        film.muted = true;
        startFilm(film);
      } else if (!isIntersecting) {
        film.pause();
      }
    }
  });

  for (const video of films) {
    video.controls = false;
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
      for (const other of films) if (other !== video) other.muted = true;
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else {
          // The custom toolbar stays in the page while the film is in fullscreen.
          video.controls = true;
          if (video.requestFullscreen) await video.requestFullscreen();
          else video.webkitEnterFullscreen?.();
        }
      } catch {
        // Leave the native toolbar available if the browser declines fullscreen.
        video.controls = true;
      }
    });
    video.addEventListener('fullscreenchange', () => {
      video.controls = document.fullscreenElement === video;
    });
    video.addEventListener('webkitendfullscreen', () => { video.controls = false; });
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
    inView.observe(video);
  }

  document.addEventListener(
    'visibilitychange',
    () => {
      if (document.hidden) {
        for (const video of films) video.pause();
      } else {
        for (const video of films) {
          inView.unobserve(video);
          inView.observe(video);
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
            easing: motionEase,
            fill: outgoing ? 'forwards' : 'none'
          }).finished
      )
    );
  }

  desktop.addEventListener('change', setDevice, { signal });
  setDevice();
  restoreMenu();
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

history.scrollRestoration = 'manual';
const scrollPositions = new Map();
let entry = history.state?.entry ?? crypto.randomUUID();
history.replaceState({...history.state, entry}, '');
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
    scrollPositions.set(entry, scrollY);
    page.unmount();
    if (fromHistory) {
      entry = history.state?.entry;
    } else {
      entry = crypto.randomUUID();
      history.pushState({entry}, '', response.url || url.href);
    }
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
    document.querySelector('meta[name="description"]').content =
      next.querySelector('meta[name="description"]').content;
    document.body.dataset.template = next.body.dataset.template;
    const nodes = [...next.body.children].filter(
      (node) => node.tagName !== 'SCRIPT'
    );
    document.body.replaceChildren(...nodes);
    route = routeKey(location);
    scrollTo(0, fromHistory ? scrollPositions.get(entry) || 0 : 0);
    page = mount();
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
  else {
    link.classList.add('active');
    navigate(url, false);
  }
});

window.addEventListener('popstate', () => {
  if (routeKey(location) === route && !request) page.restoreMenu();
  else navigate(new URL(location.href), true);
});
