const hero = document.querySelector('[data-night-hero]');
const preview = hero?.querySelector('[data-hero-preview]');
const canvas = preview?.querySelector('#hero-garment');

if (hero && preview) {
  const photo = hero.querySelector('.night-photo');
  const fallback = preview.querySelector('.hero-garment-fallback');
  const label = preview.querySelector('#hero-material-name');
  const tabButtons = [...preview.querySelectorAll('.hero-tab-btn')];
  const stages = {
    knittire: preview.querySelector('#hero-stage-knittire'),
    dealstrike: preview.querySelector('#hero-stage-dealstrike'),
    zupee: preview.querySelector('#hero-stage-zupee'),
  };
  const heroProjectLink = preview.querySelector('#hero-project-link');
  const heroProjectTitle = preview.querySelector('#hero-project-title');
  const heroProjectDesc = preview.querySelector('#hero-project-desc');
  const heroProjectNote = preview.querySelector('#hero-project-note');

  let activeTab = 'knittire';

  // --- Knittire State & Controls ---
  const materialNames = ['Cotton · sage', 'Wool · sand', 'Satin · slate'];
  const materialControls = [...preview.querySelectorAll('button[data-material]')].map(button => ({
    button,
    index: Number(button.dataset.material),
    name: button.getAttribute('aria-label') || button.textContent.trim(),
  }));

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(any-hover: hover) and (any-pointer: fine)');
  const validMaterial = index => Number.isInteger(index) && index >= 0 && index < materialNames.length;
  const initial = materialControls.find(({ button, index }) => button.getAttribute('aria-pressed') === 'true' && validMaterial(index));

  let material = initial?.index ?? 0;
  let renderer = null;
  let modulePromise = null;
  let initializing = false;
  let unavailable = false;
  let inView = false;
  let pageActive = true;
  let wasActive = false;
  let frame = 0;
  let pointerX = 0;
  let pointerY = 0;

  const isGarmentActive = () => activeTab === 'knittire' && pageActive && !document.hidden && inView;
  const canMove = () => pageActive && !document.hidden && inView && !reducedMotion.matches && finePointer.matches;

  function updateMaterialSelection() {
    const name = materialControls.find(control => control.index === material)?.name || materialNames[material];
    for (const { button, index } of materialControls) {
      button.setAttribute('aria-pressed', String(index === material));
      button.disabled = !renderer || !validMaterial(index);
    }
    preview.dataset.materialName = name;
    if (label) label.textContent = name;
  }

  function resetDepth() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    photo?.style.removeProperty('translate');
    preview.style.removeProperty('translate');
  }

  function showFallback() {
    unavailable = true;
    try { renderer?.destroy(); } catch {}
    renderer = null;
    if (canvas) canvas.hidden = true;
    if (fallback) fallback.hidden = false;
    material = initial?.index ?? 0;
    preview.dataset.previewState = 'fallback';
    updateMaterialSelection();
  }

  function drawGarment() {
    if (!renderer || !isGarmentActive()) return;
    try {
      renderer.draw(-25, material);
    } catch {
      showFallback();
    }
  }

  async function ensureRenderer() {
    if (!canvas || renderer || unavailable || initializing || !isGarmentActive()) return;
    initializing = true;
    try {
      modulePromise ??= import('/demos/garment.js');
      await modulePromise;
      if (!isGarmentActive()) return;
      canvas.hidden = false;
      renderer = globalThis.GarmentRenderer?.(canvas);
      if (!renderer || typeof renderer.draw !== 'function') {
        showFallback();
        return;
      }
      drawGarment();
      if (!renderer) return;
      if (fallback) fallback.hidden = true;
      preview.dataset.previewState = 'ready';
      updateMaterialSelection();
    } catch {
      showFallback();
    } finally {
      initializing = false;
    }
  }

  function syncVisibility() {
    const isGActive = isGarmentActive();
    renderer?.setActive?.(isGActive);
    if (!pageActive || document.hidden || !inView) resetDepth();
    else if (renderer && !wasActive && isGActive) drawGarment();
    else if (!renderer && isGActive) void ensureRenderer();
    wasActive = isGActive;
  }

  function measureVisibility() {
    const rect = hero.getBoundingClientRect();
    inView = rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0
      && rect.top < innerHeight && rect.left < innerWidth;
    syncVisibility();
  }

  // --- Zupee Slides Data & Controls ---
  const zupeeSlides = [
    {
      img: '/assets/campaigns/zupee-1.jpg',
      tag: 'Gaming Culture / Hook',
      caption: 'Relatable gaming tension: "That one friend who always changes the rules."',
      count: '1 / 3'
    },
    {
      img: '/assets/campaigns/zupee-2.png',
      tag: 'Character Narrative',
      caption: 'Rapid character sketch: authentic dialect, comedic timing, and zero corporate stiffness.',
      count: '2 / 3'
    },
    {
      img: '/assets/campaigns/zupee-1.jpg',
      tag: 'Challenge / Conversion',
      caption: 'Direct challenge format: simple rules, instant payout curiosity, and clear mobile CTA.',
      count: '3 / 3'
    }
  ];
  let zupeeIndex = 0;

  function updateZupeeSlide() {
    const slide = zupeeSlides[zupeeIndex];
    const imgEl = preview.querySelector('#zupee-slide-img');
    const tagEl = preview.querySelector('#zupee-slide-tag');
    const captionEl = preview.querySelector('#zupee-slide-caption');
    const counterEl = preview.querySelector('#zupee-slide-counter');

    if (imgEl) imgEl.src = slide.img;
    if (tagEl) tagEl.textContent = slide.tag;
    if (captionEl) captionEl.textContent = slide.caption;
    if (counterEl) counterEl.textContent = slide.count;
  }

  const prevBtn = preview.querySelector('#zupee-prev-btn');
  const nextBtn = preview.querySelector('#zupee-next-btn');

  prevBtn?.addEventListener('click', () => {
    zupeeIndex = (zupeeIndex - 1 + zupeeSlides.length) % zupeeSlides.length;
    updateZupeeSlide();
  });

  nextBtn?.addEventListener('click', () => {
    zupeeIndex = (zupeeIndex + 1) % zupeeSlides.length;
    updateZupeeSlide();
  });

  // --- Project Tab Switching ---
  const tabConfigs = {
    knittire: {
      url: '/case-studies/knittire-3d',
      title: 'Knittire',
      desc: 'Explore the 3D material study',
      note: 'Interactive reconstruction · demonstration model'
    },
    dealstrike: {
      url: '/case-studies/dealstrike',
      title: 'DealStrike',
      desc: 'Explore the voice-to-CRM pipeline',
      note: 'Interactive reconstruction · sample data'
    },
    zupee: {
      url: '/case-studies/zupee',
      title: 'Zupee',
      desc: 'Explore the short-form creative archive',
      note: 'Campaign creative archive'
    }
  };

  function switchTab(newTab) {
    if (!tabConfigs[newTab] || activeTab === newTab) return;
    activeTab = newTab;

    // Update Tab Buttons
    tabButtons.forEach(btn => {
      const isSelected = btn.dataset.heroTab === newTab;
      btn.setAttribute('aria-selected', String(isSelected));
      btn.classList.toggle('active', isSelected);
    });

    // Update Stage Visibility
    Object.entries(stages).forEach(([key, stage]) => {
      if (stage) stage.hidden = key !== newTab;
    });

    // Update Project Link Info
    const config = tabConfigs[newTab];
    if (heroProjectLink) heroProjectLink.href = config.url;
    if (heroProjectTitle) heroProjectTitle.textContent = config.title;
    if (heroProjectDesc) heroProjectDesc.textContent = config.desc;
    if (heroProjectNote) heroProjectNote.textContent = config.note;

    preview.dataset.activeTab = newTab;

    if (newTab === 'knittire') {
      syncVisibility();
    } else {
      renderer?.setActive?.(false);
      // For Zupee, ensure first slide is rendered
      if (newTab === 'zupee') updateZupeeSlide();
    }
  }

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.heroTab));
  });

  // --- Depth Parallax Motion ---
  function moveDepth(event) {
    if (event.pointerType === 'touch' || event.isPrimary === false || !canMove()) return;
    pointerX = event.clientX;
    pointerY = event.clientY;
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (!canMove()) return;
      const rect = hero.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const clamp = value => Math.max(-1, Math.min(1, value));
      const x = clamp((pointerX - rect.left) / rect.width * 2 - 1);
      const y = clamp((pointerY - rect.top) / rect.height * 2 - 1);
      if (photo) photo.style.translate = `${(-x * 8).toFixed(2)}px ${(-y * 8).toFixed(2)}px`;
      preview.style.translate = `${(x * 3).toFixed(2)}px ${(y * 3).toFixed(2)}px`;
    });
  }

  // Material Button Listeners
  updateMaterialSelection();
  for (const { button, index } of materialControls) {
    button.addEventListener('click', () => {
      if (!renderer || !validMaterial(index)) return;
      material = index;
      updateMaterialSelection();
      drawGarment();
    });
  }

  hero.addEventListener('pointermove', moveDepth, { passive: true });
  hero.addEventListener('pointerleave', resetDepth, { passive: true });
  hero.addEventListener('pointercancel', resetDepth, { passive: true });

  for (const media of [reducedMotion, finePointer]) {
    if (media.addEventListener) media.addEventListener('change', resetDepth);
    else media.addListener(resetDepth);
  }

  if ('IntersectionObserver' in globalThis) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.target === hero) inView = entry.isIntersecting && entry.intersectionRatio > 0;
      }
      syncVisibility();
    }, { threshold: 0 });
    observer.observe(hero);
  } else {
    addEventListener('scroll', measureVisibility, { passive: true });
    addEventListener('resize', measureVisibility, { passive: true });
    measureVisibility();
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) syncVisibility();
    else measureVisibility();
  });
  addEventListener('pagehide', () => {
    pageActive = false;
    syncVisibility();
  });
  addEventListener('pageshow', () => {
    pageActive = true;
    measureVisibility();
  });
}
