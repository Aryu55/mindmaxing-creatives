import { projects, featuredEngineering, featuredMotion, featuredMarketing, categories } from './projects.mjs';
import { existsSync } from 'node:fs';

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}[c]));

const url = p => `/case-studies/${p.slug}`;
const arrow = '<span aria-hidden="true">↗</span>';

export function media(p, priority = false, kind = 'project') {
  if (p.slug === 'knittire-3d' && kind === 'demo-cover') {
    return `<img class="project-image garment-cover" src="/assets/previews/garment-closeup.webp" alt="Knittire - procedural demonstration garment, separate from the client model" width="800" height="600" fetchpriority="high" decoding="async" style="view-transition-name:project-${p.slug}" data-media-kind="${kind}">`;
  }
  if (p.poster) {
    return `<img class="project-image" src="${p.poster}" alt="${esc(p.title)}" width="1280" height="889" ${priority ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async" ${kind === 'demo-cover' ? `style="view-transition-name:project-${p.slug}"` : ''} data-media-kind="${kind}">`;
  }
  const actual = !['hero-demo', 'demo-cover'].includes(kind) && existsSync(`site/assets/projects/${p.slug}.webp`);
  const path = actual ? `/assets/projects/${p.slug}.webp` : `/assets/previews/${p.slug}.webp`;
  return `<img class="project-image" src="${path}" alt="${esc(p.title)} - ${actual ? 'public project screenshot' : 'interactive reconstruction preview'}" width="1280" height="889" ${priority ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async" ${kind === 'demo-cover' ? `style="view-transition-name:project-${p.slug}"` : ''} data-media-kind="${kind}">`;
}

export const header = active => `<a class="skip-link" href="#main">Skip to content</a><header class="site-header"><div class="nav-shell"><a href="/" class="brand" aria-label="Mindmaxing Studio home"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M3 23V5l11 13L25 5v18M3 5l11 13L25 5"/></svg><span>mindmaxing<span class="brand-studio">studio</span></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="navigation" aria-label="Open navigation">Menu <span>＋</span></button><nav id="navigation" aria-label="Main navigation"><a href="/case-studies" ${active === 'work' ? 'aria-current="page"' : ''}>Work <sup>${projects.length}</sup></a><a href="/about" ${active === 'about' ? 'aria-current="page"' : ''}>Studio</a><a class="nav-contact" href="/#contact">Let’s talk ${arrow}</a></nav></div></header>`;

export const footer = () => `<footer class="site-footer shell"><a class="footer-wordmark" href="/">mindmaxing</a><div class="footer-bottom"><p>Engineering, design & marketing.<br><span>Mumbai, India · Working everywhere.</span></p><div><a href="/case-studies">Work</a><a href="/about">Studio</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a></div><span>© ${new Date().getFullYear()} Mindmaxing</span></div></footer>`;

export function page({ title, description, path = '/', body, active = '', image = '/assets/social/knittire-3d.jpg' }) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080a0d"><meta name="color-scheme" content="dark"><meta name="project-slugs" content="${projects.map(p => p.slug).join(',')}"><title>${esc(title)} · Mindmaxing Studio</title><meta name="description" content="${esc(description)}"><link rel="canonical" href="https://mindmaxing.one${path}"><meta property="og:type" content="website"><meta property="og:title" content="${esc(title)} · Mindmaxing Studio"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="https://mindmaxing.one${path}"><meta property="og:image" content="https://mindmaxing.one${image}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/favicon.png"><link rel="preload" href="/assets/fonts/instrument-sans.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/assets/studio.css"><script src="/assets/studio.js" type="module"></script>${path === '/' ? '<script src="/assets/hero-preview.js" type="module"></script>' : ''}</head><body class="${path === '/' ? 'home-page' : ''}">${header(active)}<main id="main">${body}</main>${footer()}<div class="toast" role="status" aria-live="polite"></div></body></html>`;
}

export const workRow = p => `<a class="work-row" href="${url(p)}" data-project-link style="--project-accent:${p.accent}" data-category="${p.category}" data-lead="${p.lead}" data-search="${esc([p.title, p.summary, p.contribution, p.disciplines, p.leadName].join(' ').toLowerCase())}"><div class="work-thumb">${media(p)}<span class="thumb-corner">${p.number}</span></div><div class="work-info"><div class="work-meta-row"><span class="label">${categories[p.category]}</span><span class="lead-badge" data-lead="${p.lead}"><img src="${p.leadAvatar}" alt="" class="lead-mini-thumb" width="16" height="16" loading="lazy"><span>${esc(p.leadName)}</span></span></div><h3>${esc(p.title)}</h3><p>${esc(p.summary)}</p><span class="contribution">${esc(p.contribution)}</span></div><div class="work-action"><span class="demo-indicator"><i></i>${p.showcaseMode || 'Interactive demo'}</span><span class="round-arrow">↗</span></div></a>`;

export function contact() {
  return `<section class="contact-section shell" id="contact"><div class="contact-copy"><span class="section-kicker">An idea, a problem, a possibility.</span><h2>Tell us what you want to<br>build or grow<span class="warm">.</span></h2><p>Bring the complicated part.<br>We’ll figure out a considered way through it.</p><a class="text-link" href="mailto:mindmaxxxing@gmail.com">mindmaxxxing@gmail.com ${arrow}</a></div><form id="contact-form" class="contact-form" method="post" action="/api/contact"><p class="project-context" hidden></p><input name="project" type="hidden"><div class="field-pair"><label>Your name<input name="name" autocomplete="name" required maxlength="120" placeholder="Alex"></label><label>Email address<input name="email" type="email" autocomplete="email" required maxlength="320" placeholder="alex@company.com"></label></div><div class="field-pair"><label>Budget <span>(optional)</span><select name="budget"><option value="">Let’s scope it together</option><option>$500–$1,000</option><option>$1,000–$3,000</option><option>$3,000–$5,000</option><option>$5,000+</option></select></label><label>Phone <span>(optional)</span><input name="phone" type="tel" autocomplete="tel" maxlength="80" placeholder="Country code + number"></label></div><label>A little about the project<textarea name="details" rows="3" required minlength="12" maxlength="10000" placeholder="What are you trying to make or grow? What needs to work differently?"></textarea></label><div class="form-bottom"><span>Direct to the people building it.</span><button type="submit" class="button button-light">Send your brief ${arrow}</button></div><p class="form-status" role="status" aria-live="polite"></p></form></section>`;
}

export function home() {
  return page({
    title: 'Complex engineering. Beautifully made.',
    description: 'Mindmaxing is an independent studio for engineering, design & marketing. Explore custom storefronts, interactive experiences, software, and creative campaigns.',
    body: `<section class="night-hero" data-night-hero>
<picture class="night-photo"><source media="(max-width: 700px)" srcset="/assets/atmosphere/manhattan-900.webp"><img src="/assets/atmosphere/manhattan-2200.webp" srcset="/assets/atmosphere/manhattan-900.webp 900w, /assets/atmosphere/manhattan-2200.webp 2200w" sizes="100vw" alt="" width="2200" height="3300" fetchpriority="high" decoding="async"></picture>
<div class="night-shade" aria-hidden="true"></div>
<div class="night-content shell">
  <div class="hero-intro">
    <p class="eyebrow"><span class="status-dot"></span> Engineering, design & marketing.</p>
    <h1>Complex<br>engineering.<br><span>Beautifully made.</span></h1>
    <p class="hero-description">We build websites, software and interactive experiences - and create the campaigns that bring people to them.</p>
    <div class="hero-actions">
      <a class="button button-light" href="#work">Explore the work <span>↓</span></a>
      <a class="text-link" href="#contact">Start a project ${arrow}</a>
    </div>
    <div class="hero-location">
      <span>Mumbai, India</span>
      <span>Engineering meets creative.</span>
    </div>
  </div>

  <article class="hero-live" data-hero-preview aria-labelledby="hero-project-title">
    <div class="hero-live-head">
      <span class="section-kicker">Interactive showcase</span>
      <div class="hero-tab-selector" role="tablist" aria-label="Foreground preview selection">
        <button type="button" class="hero-tab-btn" data-hero-tab="knittire" role="tab" aria-selected="true" aria-controls="hero-stage-knittire">Knittire</button>
        <button type="button" class="hero-tab-btn" data-hero-tab="dealstrike" role="tab" aria-selected="false" aria-controls="hero-stage-dealstrike">DealStrike</button>
        <button type="button" class="hero-tab-btn" data-hero-tab="zupee" role="tab" aria-selected="false" aria-controls="hero-stage-zupee">Zupee</button>
      </div>
    </div>

    <!-- Stage 1: Knittire (3D Fabric Configurator) -->
    <div class="hero-stage" id="hero-stage-knittire" data-stage="knittire">
      <div class="hero-garment-stage">
        <img class="hero-garment-fallback" src="/assets/previews/garment-closeup.webp" width="800" height="600" alt="Procedural demonstration garment in sage cotton">
        <canvas id="hero-garment" width="800" height="600" aria-label="Procedural demonstration garment" role="img" hidden></canvas>
      </div>
      <div class="hero-materials">
        <div class="material-options" role="group" aria-label="Garment material">
          <button type="button" data-material="0" aria-label="Cotton · sage" aria-pressed="true" style="--swatch:#829c91" disabled><span></span></button>
          <button type="button" data-material="1" aria-label="Wool · sand" aria-pressed="false" style="--swatch:#c0996e" disabled><span></span></button>
          <button type="button" data-material="2" aria-label="Satin · slate" aria-pressed="false" style="--swatch:#819fcc" disabled><span></span></button>
        </div>
        <span id="hero-material-name" role="status">Cotton · sage</span>
      </div>
    </div>

    <!-- Stage 2: DealStrike (Voice-to-CRM Transcript Preview) -->
    <div class="hero-stage" id="hero-stage-dealstrike" data-stage="dealstrike" hidden>
      <div class="hero-crm-preview">
        <div class="hero-crm-audio-bar">
          <span class="crm-pulse"></span>
          <span class="crm-caller">Field audio recap · 0:42s</span>
          <span class="crm-badge">AI Structured</span>
        </div>
        <div class="hero-crm-transcript">
          <p class="transcript-quote">"Met Rajesh at Apex Hardware. Agreed on 45 units for October shipment. Follow up Friday 2 PM for signed PO."</p>
        </div>
        <div class="hero-crm-cards">
          <div class="crm-metric-pill">
            <span class="crm-kicker">DEAL VALUE</span>
            <span class="crm-val">₹2,25,000</span>
          </div>
          <div class="crm-metric-pill">
            <span class="crm-kicker">STAGE</span>
            <span class="crm-val accent-deal">PO Pending</span>
          </div>
          <div class="crm-metric-pill">
            <span class="crm-kicker">ACTION</span>
            <span class="crm-val">Fri 2:00 PM</span>
          </div>
        </div>
      </div>
      <div class="hero-crm-controls">
        <span class="crm-status-label">Voice note parsed into pipeline in 1.4s</span>
      </div>
    </div>

    <!-- Stage 3: Zupee (Campaign Creative Gallery) -->
    <div class="hero-stage" id="hero-stage-zupee" data-stage="zupee" hidden>
      <div class="hero-zupee-gallery">
        <div class="zupee-frame-container">
          <img id="zupee-slide-img" src="/assets/campaigns/zupee-1.jpg" alt="Zupee campaign creative concept" width="600" height="400" loading="lazy">
          <div class="zupee-caption-overlay">
            <span id="zupee-slide-tag" class="zupee-tag">Gaming Culture / Hook</span>
            <p id="zupee-slide-caption">Relatable gaming tension: "That one friend who always changes the rules."</p>
          </div>
        </div>
      </div>
      <div class="hero-zupee-controls">
        <div class="zupee-nav-btns">
          <button type="button" id="zupee-prev-btn" class="zupee-btn" aria-label="Previous creative">←</button>
          <span id="zupee-slide-counter" class="zupee-counter">1 / 3</span>
          <button type="button" id="zupee-next-btn" class="zupee-btn" aria-label="Next creative">→</button>
        </div>
        <span class="zupee-status-label">High-retention social campaign framework</span>
      </div>
    </div>

    <a href="/case-studies/knittire-3d" id="hero-project-link" class="hero-live-link" data-project-link>
      <div>
        <h2 id="hero-project-title">Knittire</h2>
        <p id="hero-project-desc">Explore the 3D material study</p>
      </div>
      <span class="round-arrow">↗</span>
    </a>
    <p id="hero-project-note" class="reconstruction-note">Interactive reconstruction · demonstration model</p>
  </article>
</div>
<div class="night-bottom shell">
  <span>Built to be explored.</span>
  <a href="https://unsplash.com/photos/city-buildings-with-street-lights-during-night-time-LlY88Z8T8Tc" target="_blank" rel="noopener noreferrer" class="photo-credit">Photography · Lerone Pieters</a>
</div>
</section>

<!-- B. Selected Engineering Work -->
<section id="work" class="work-section shell">
  <div class="section-heading">
    <div>
      <span class="section-kicker">Selected engineering work</span>
      <h2>Built for the difficult parts.</h2>
    </div>
    <p>Voice systems, financial automation, and interactive commerce.<br>Open a project. Try the thinking.</p>
  </div>
  <div class="work-list">
    ${featuredEngineering.map(workRow).join('')}
  </div>
</section>

<!-- C. Selected 3D Motion & Animation -->
<section class="work-section shell motion-work-section">
  <div class="section-heading">
    <div>
      <span class="section-kicker">Selected 3D motion & animation</span>
      <h2>Visual direction that commands attention.</h2>
    </div>
    <p>Commercial 3D product rendering, broadcast TVC slates, and high-impact social films.<br>Led by partner Rahul Saranya.</p>
  </div>
  <div class="work-list">
    ${featuredMotion.map(workRow).join('')}
  </div>
  <div class="work-browse-row">
    <a class="button button-light" href="/case-studies?category=motion">View all 16 motion works ${arrow}</a>
  </div>
</section>

<!-- D. Selected Marketing Work -->
<section class="work-section shell marketing-work-section">
  <div class="section-heading">
    <div>
      <span class="section-kicker">Selected marketing & creative work</span>
      <h2>Campaigns that bring people in.</h2>
    </div>
    <p>Paid search architecture, feed optimization, and high-retention creative.<br>Led by partner Rahul Saranya.</p>
  </div>
  <div class="work-list">
    ${featuredMarketing.map(workRow).join('')}
  </div>
  <div class="work-browse-row">
    <a class="button button-light" href="/case-studies?category=growth">View marketing work ${arrow}</a>
    <a class="all-work" href="/case-studies">
      <span>Explore all ${projects.length} projects</span>
      <span>View the collection ${arrow}</span>
    </a>
  </div>
</section>

<!-- E. Capabilities -->
<section class="capabilities shell" id="capabilities">
  <span class="section-kicker">Studio capabilities</span>
  <a href="/case-studies?category=commerce">
    <span>01</span>
    <h3>Storefronts & commerce</h3>
    <p>High-speed headless storefronts, custom checkout experiences, and conversion architecture.</p>
    ${arrow}
  </a>
  <a href="/case-studies?category=software">
    <span>02</span>
    <h3>Software & automation</h3>
    <p>B2B voice workflows, internal financial tooling, automated pipelines, and Android applications.</p>
    ${arrow}
  </a>
  <a href="/case-studies?category=interactive">
    <span>03</span>
    <h3>Interactive experiences</h3>
    <p>Procedural 3D configurators, visual storytelling, lookbooks, and considered motion design.</p>
    ${arrow}
  </a>
  <a href="/case-studies?category=motion">
    <span>04</span>
    <h3>3D motion & animation</h3>
    <p>Commercial 3D spots, TVC end slates, photorealistic product rendering, and broadcast animation. Led by partner Rahul Saranya.</p>
    ${arrow}
  </a>
  <a href="/case-studies?category=growth">
    <span>05</span>
    <h3>Marketing & creative</h3>
    <p>Paid search and Meta campaigns, product feed architecture, direct-response copy, and campaign landing pages. Led by partner Rahul Saranya.</p>
    ${arrow}
  </a>
</section>

<!-- F. Studio Leadership -->
<section class="founder-section shell" id="team">
  <span class="section-kicker">Leadership</span>
  <div class="leadership-grid" style="display:flex;flex-direction:column;gap:64px;">
    <div class="founder-container">
      <div class="founder-portrait-wrap">
        <img class="founder-portrait" src="/assets/aryan-perfect.jpg" alt="Aryan Panchal - Founder & Engineering Lead" width="700" height="700" loading="lazy" decoding="async">
      </div>
      <div class="founder-copy">
        <span class="founder-kicker">Founder & Engineering Lead</span>
        <h2>Aryan Panchal</h2>
        <div class="founder-bio">
          <p>I build web products, Android apps and automation systems. I care about the difficult parts underneath - and how simple the finished experience feels.</p>
          <p>Mindmaxing brings that engineering approach together with design, campaign strategy and creative production.</p>
        </div>
        <div class="founder-actions">
          <a class="button button-light" href="/about">About the studio ${arrow}</a>
          <a class="text-link" href="#contact">Talk to Aryan ${arrow}</a>
        </div>
      </div>
    </div>

    <div class="founder-container">
      <div class="founder-portrait-wrap">
        <img class="founder-portrait" src="/assets/rahul.jpg" alt="Rahul Saranya - Partner & Motion Graphics Lead" width="700" height="700" loading="lazy" decoding="async">
      </div>
      <div class="founder-copy">
        <span class="founder-kicker">Partner & Motion Graphics Lead · Creative Growth</span>
        <h2>Rahul Saranya</h2>
        <div class="founder-bio">
          <p>I direct commercial 3D animation, broadcast motion design, and high-converting marketing campaigns. From national TVC end slates to digital campaign reels and acquisition strategy, I focus on creative that commands attention and drives revenue.</p>
          <p>Commercial portfolio spans 3D motion and campaign creative across Fevicol, Britannia, Fiama, Cuticura, Zupee, and MotoGP. At Mindmaxing, I lead visual direction, 3D motion, and creative growth.</p>
        </div>
        <div class="founder-actions">
          <a class="button button-light" href="/case-studies?lead=rahul">Explore creative work (24) ${arrow}</a>
          <a class="text-link" href="#contact">Discuss creative brief ${arrow}</a>
        </div>
      </div>
    </div>
  </div>
</section>

${contact()}`
  });
}

export function archive() {
  const aryanWorks = projects.filter(p => p.lead === 'aryan').length;
  const rahulWorks = projects.filter(p => p.lead === 'rahul').length;
  return page({
    title: 'Selected work',
    description: `Explore ${projects.length} project records, interactive demonstrations, and creative campaigns by Mindmaxing Studio. Led by Aryan Panchal and Rahul Saranya.`,
    path: '/case-studies',
    active: 'work',
    body: `<section class="archive-intro shell"><span class="section-kicker">The collection</span><h1>Work you can<br><span>get your hands on.</span></h1><p>Storefronts, useful software, 3D motion and creative campaigns.<br>Every project opens up. Led by practitioners with distinct disciplines.</p></section><section class="authorship-strip shell" aria-label="Studio practice leads"><div class="authorship-card" data-lead-card="aryan"><div class="authorship-avatar-wrap"><img src="/assets/aryan-perfect.jpg" alt="Aryan Panchal - Founder & Engineering Lead" width="84" height="84" class="authorship-avatar" loading="lazy"></div><div class="authorship-body"><div class="authorship-meta"><span class="authorship-kicker">Founder & Technical Lead</span><span class="authorship-tag">${aryanWorks} works</span></div><h3>Aryan Panchal</h3><p class="authorship-desc">Headless storefronts, software systems, interactive WebGL, and automation engines.</p><div class="authorship-footer"><span class="authorship-scope">Commerce (7) · Software (24) · Interactive (3)</span><button type="button" class="authorship-btn" data-filter-lead="aryan">Show Aryan’s work <span aria-hidden="true">→</span></button></div></div></div><div class="authorship-card" data-lead-card="rahul"><div class="authorship-avatar-wrap"><img src="/assets/rahul.jpg" alt="Rahul Saranya - Partner & Creative Growth Lead" width="84" height="84" class="authorship-avatar" loading="lazy"></div><div class="authorship-body"><div class="authorship-meta"><span class="authorship-kicker">Partner & Creative Growth Lead</span><span class="authorship-tag">${rahulWorks} works</span></div><h3>Rahul Saranya</h3><p class="authorship-desc">Commercial 3D motion, TVC broadcast slates, visual brand direction, and marketing campaigns.</p><div class="authorship-footer"><span class="authorship-scope">3D Motion (16) · Marketing & Growth (8)</span><button type="button" class="authorship-btn" data-filter-lead="rahul">Show Rahul’s work <span aria-hidden="true">→</span></button></div></div></div></section><section class="shell archive-section"><div class="archive-controls"><div class="filters" role="group" aria-label="Project category"><button data-filter="all" aria-pressed="true">All work <span>${projects.length}</span></button>${Object.entries(categories).map(([id, label]) => `<button data-filter="${id}" aria-pressed="false">${label} <span>${projects.filter(p => p.category === id).length}</span></button>`).join('')}</div><label class="search"><span class="sr-only">Search projects</span><input id="project-search" type="search" placeholder="Find a project…" autocomplete="off"><span aria-hidden="true">⌕</span></label></div><div class="lead-active-bar" id="lead-active-bar" hidden><span id="lead-active-text">Showing Aryan’s work</span><button type="button" id="lead-clear-btn" class="text-link">Show all 58 projects ✕</button></div><p id="result-count" class="result-count" role="status">${projects.length} projects</p><div class="work-list" id="work-list">${projects.map(workRow).join('')}</div><div class="empty-state" hidden><h2>No projects found.</h2><p>Try another search or explore all work.</p><button class="button" data-clear-filters>Clear filters</button></div></section>`
  });
}

export function project(p) {
  const actual = existsSync(`site/assets/projects/${p.slug}.webp`);
  const related = projects.filter(x => x.slug !== p.slug && x.category === p.category).slice(0, 2);
  const isMarketing = p.caseStudyType === 'marketing';
  const isMotion = p.caseStudyType === 'motion' || p.category === 'motion';

  return page({
    title: p.title,
    description: p.summary,
    path: url(p),
    active: 'work',
    image: p.socialImage,
    body: `<article class="project-page" style="--project-accent:${p.accent}" data-project="${p.slug}">
<div class="shell project-back">
  <a href="/case-studies" data-back-work>← All work</a>
  <button class="text-link" data-copy-link>Copy project link ${arrow}</button>
</div>

<section class="project-intro shell">
  <div>
    <span class="section-kicker">${categories[p.category]} / ${p.title}</span>
    <h1>${esc(p.heading)}</h1>
    <p>${esc(p.summary)}</p>
  </div>
  <dl class="project-facts">
    <div>
      <dt>Project lead</dt>
      <dd class="project-lead-val"><img src="${p.leadAvatar}" alt="" class="lead-tiny-avatar" width="20" height="20" loading="lazy"><span><strong>${esc(p.leadName)}</strong> · ${esc(p.leadRole)}</span></dd>
    </div>
    <div>
      <dt>Contribution</dt>
      <dd>${esc(p.contribution)}</dd>
    </div>
    <div>
      <dt>Project</dt>
      <dd>${p.status}</dd>
    </div>
    <div>
      <dt>Disciplines</dt>
      <dd>${esc(p.disciplines)}</dd>
    </div>
  </dl>
</section>

${isMotion ? `
<section class="demo-section shell" aria-labelledby="demo-title">
  <div class="demo-section-heading">
    <div>
      <span class="section-kicker">Commercial motion & 3D space</span>
      <h2 id="demo-title">${esc(p.instruction)}</h2>
    </div>
    <span class="demo-indicator"><i></i>${p.showcaseMode}</span>
  </div>

  <div class="demo-shell motion-theatre-shell">
    <div class="demo-toolbar">
      <span>${esc(p.title)} <span class="toolbar-divider">/</span> ${esc(p.formatLabel || 'Commercial 3D Motion')}</span>
      <span class="motion-format-pill">${esc(p.aspectRatio || '16:9')}</span>
    </div>
    <div class="demo-mount motion-theatre-mount">
      <div class="motion-player-wrap aspect-${(p.aspectRatio || '16:9').replace(':', '-')}">
        <video class="motion-video-player" controls playsinline preload="metadata" poster="${p.poster || `/assets/motion/${p.slug}.jpg`}">
          <source src="${p.videoSrc || `/assets/motion/${p.slug}.mp4`}" type="video/mp4">
          Your browser does not support HTML5 video playback.
        </video>
      </div>
    </div>
    <div class="demo-foot">
      <span>Commercial client production</span>
      <span>Direction: Rahul Saranya · Mindmaxing Studio</span>
    </div>
  </div>

  <details class="how-it-works">
    <summary>Motion craft & visual breakdown <span>＋</span></summary>
    <div>
      <p>${esc(p.approach)}</p>
      <p><strong>Creative constraint.</strong> ${esc(p.tradeoff)}</p>
    </div>
  </details>
</section>
` : `
<section class="demo-section shell" aria-labelledby="demo-title">
  <div class="demo-section-heading">
    <div>
      <span class="section-kicker">${isMarketing ? 'Explore the campaign' : 'Try the interaction'}</span>
      <h2 id="demo-title">${esc(p.instruction)}</h2>
    </div>
    <span class="demo-indicator"><i></i>${p.showcaseMode}</span>
  </div>

  <div class="demo-shell" data-demo-url="${esc(p.demo)}">
    <div class="demo-toolbar">
      <span>${esc(p.title)} <span class="toolbar-divider">/</span> ${isMarketing ? 'Campaign workspace' : 'Interaction lab'}</span>
      <button data-demo-expand hidden aria-haspopup="dialog">Expand ⤢</button>
    </div>
    <div class="demo-mount">
      <div class="demo-cover">
        ${media(p, true, 'demo-cover')}
        <div class="demo-cover-shade"></div>
        <div class="demo-cover-action">
          <button class="button button-light" data-demo-start>
            <span aria-hidden="true">▷</span> ${isMarketing ? 'Open campaign walkthrough' : 'Start interactive demo'}
          </button>
          <p>${p.showcaseMode}</p>
        </div>
      </div>
    </div>
    <p class="demo-error" role="status" hidden>The demonstration couldn’t load. You can still explore the project below. <button data-demo-retry>Try again</button></p>
    <div class="demo-foot">
      <span>${p.showcaseMode}</span>
      <span>${isMarketing ? 'Strategy: Rahul Saranya · Mindmaxing Studio' : 'Engineering: Aryan Panchal · Mindmaxing Studio'}</span>
    </div>
  </div>

  <details class="how-it-works">
    <summary>${isMarketing ? 'Campaign strategy & rationale' : 'How this works'} <span>＋</span></summary>
    <div>
      <p>${esc(p.approach)}</p>
      <p><strong>The boundary.</strong> ${esc(p.tradeoff)}</p>
    </div>
  </details>
</section>
`}

${isMotion ? `
<section class="project-story shell">
  <span class="section-kicker">Motion direction</span>
  <div>
    <h2>Commercial brief.</h2>
    <p>${esc(p.problem)}</p>
    <h2>Motion & 3D execution.</h2>
    <p>${esc(p.approach)}</p>
    <div class="technical-note">
      <span class="label">Production note</span>
      <p>${esc(p.tradeoff)}</p>
    </div>
  </div>
</section>
` : isMarketing ? `
<section class="project-story shell marketing-story">
  <span class="section-kicker">Campaign overview</span>
  <div>
    <h2>Campaign brief.</h2>
    <p>${esc(p.problem)}</p>
    <h2>Work delivered.</h2>
    <p>${esc(p.contribution)}</p>
    <h2>Creative and strategy.</h2>
    <p>${esc(p.approach)}</p>
    <div class="technical-note">
      <span class="label">Evidence & source material</span>
      <p>${esc(p.tradeoff)}</p>
    </div>
  </div>
</section>
` : `
<section class="project-story shell">
  <span class="section-kicker">Inside the build</span>
  <div>
    <h2>The problem worth solving.</h2>
    <p>${esc(p.problem)}</p>
    <h2>A considered approach.</h2>
    <p>${esc(p.approach)}</p>
    <div class="technical-note">
      <span class="label">Design decision</span>
      <p>${esc(p.tradeoff)}</p>
    </div>
  </div>
</section>
`}

${actual ? `
<section class="project-evidence shell">
  <div class="section-heading">
    <div>
      <span class="section-kicker">Project in context</span>
      <h2>The actual interface.</h2>
    </div>
    ${p.liveUrl ? `<a class="text-link" href="${esc(p.liveUrl)}" target="_blank" rel="noopener noreferrer">Visit project ${arrow}</a>` : ''}
  </div>
  <figure>
    ${media(p)}
    <figcaption>Public interface captured September 2026. The sandbox above is a separate, illustrative reconstruction.</figcaption>
  </figure>
</section>
` : ''}

<section class="project-cta shell">
  <span class="section-kicker">Something similar in mind?</span>
  <h2>Let’s make it work.<br><span>And make it feel right.</span></h2>
  <a class="button button-light" href="/?project=${encodeURIComponent(p.title)}#contact">
    ${isMarketing ? 'Discuss a similar campaign' : isMotion ? 'Commission motion or 3D project' : 'Build something like this'} ${arrow}
  </a>
</section>

${related.length ? `
<section class="shell related">
  <span class="section-kicker">Keep exploring</span>
  <div class="work-list">
    ${related.map(workRow).join('')}
  </div>
</section>
` : ''}
</article>`
  });
}

export function about() {
  return page({
    title: 'The studio',
    description: 'Mindmaxing is an independent studio in Mumbai for engineering, design & marketing. Led by Aryan Panchal and Rahul Saranya.',
    path: '/about',
    active: 'about',
    body: `<section class="about-hero shell">
  <span class="section-kicker">Mindmaxing Studio / Mumbai</span>
  <h1>Curiosity starts it.<br><span>Craft carries it through.</span></h1>
  <p>We are an independent studio working across engineering, design, and marketing. Led by Aryan Panchal (Engineering & Systems) and Rahul Saranya (3D Motion & Growth Campaigns), Mindmaxing brings technical engineering and commercial creative direction together under one roof.</p>
</section>

<section class="founder-section shell about-founder-section" id="team">
  <div class="about-leadership-head">
    <span class="section-kicker">Leadership</span>
    <h2>Two partners. Two disciplines.</h2>
    <p>Aryan leads engineering systems, storefronts, and software. Rahul directs 3D motion, commercial visuals, and growth campaigns.<br>Direct collaboration with the practitioners doing the work.</p>
  </div>
  <div class="leadership-grid" style="display:flex;flex-direction:column;gap:64px;">
    <div class="founder-container" data-partner="aryan">
      <div class="founder-portrait-wrap">
        <img class="founder-portrait" src="/assets/aryan-perfect.jpg" alt="Aryan Panchal - Founder & Engineering Lead" width="700" height="700" loading="lazy" decoding="async">
      </div>
      <div class="founder-copy">
        <span class="founder-kicker">Founder & Engineering Lead</span>
        <h2>Aryan Panchal</h2>
        <span class="founder-scope-tag">34 works · Storefronts, Software & Interactive Systems</span>
        <div class="founder-bio">
          <p>I build web products, Android apps and automation systems. I care about the difficult parts underneath - robust state models, low-latency APIs, and how simple the finished experience feels.</p>
          <p>Mindmaxing brings that engineering approach together with design, campaign strategy and creative production. Every system we build is designed to be explored, tested, and relied upon under real-world load.</p>
        </div>
        <div class="founder-actions">
          <a class="button button-light" href="/case-studies?lead=aryan">Explore engineering work (34) ${arrow}</a>
          <a class="text-link" href="/#contact">Talk to Aryan ${arrow}</a>
        </div>
      </div>
    </div>

    <div class="founder-container" data-partner="rahul">
      <div class="founder-portrait-wrap">
        <img class="founder-portrait" src="/assets/rahul.jpg" alt="Rahul Saranya - Partner & Motion Graphics Lead" width="700" height="700" loading="lazy" decoding="async">
      </div>
      <div class="founder-copy">
        <span class="founder-kicker">Partner & Motion Graphics Lead · Creative Growth</span>
        <h2>Rahul Saranya</h2>
        <span class="founder-scope-tag">24 works · 3D Motion, Visuals & Marketing Campaigns</span>
        <div class="founder-bio">
          <p>I direct commercial 3D animation, broadcast motion graphics, and high-converting marketing campaigns. From national TVC end slates to digital campaign reels, I focus on creative that commands attention and drives revenue.</p>
          <p>Commercial portfolio spans 3D motion, visual direction, and growth campaigns across Fevicol, Britannia, Fiama, Cuticura, Zupee, and MotoGP. At Mindmaxing, I lead visual direction, commercial animation, and creative growth.</p>
        </div>
        <div class="founder-actions">
          <a class="button button-light" href="/case-studies?lead=rahul">Explore creative work (24) ${arrow}</a>
          <a class="text-link" href="/#contact">Discuss creative brief ${arrow}</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="studio-statement shell">
  <span class="section-kicker">Studio disciplines</span>
  <h2>Engineering, 3D motion<br>and <span>visual direction.</span></h2>
  <div>
    <p>How it looks. How it moves. How it responds under load. These are the same conversation.</p>
    <p>Aryan leads technical architecture, systems engineering, and interactive web software. Rahul directs 3D motion, broadcast animation, and creative growth campaigns.</p>
  </div>
</section>

<section class="process shell">
  <span class="section-kicker">Working together</span>
  ${[
    ['01', 'Make the problem clear.', 'Agree on the user, the scope and what a useful result looks like.'],
    ['02', 'Build where you can see it.', 'Working versions, concrete feedback and visible decisions.'],
    ['03', 'Leave it ready for the next person.', 'A considered release, documented details and a clear handover.']
  ].map(([n, t, d]) => `<div><span>${n}</span><h2>${t}</h2><p>${d}</p></div>`).join('')}
</section>

${contact()}`
  });
}
