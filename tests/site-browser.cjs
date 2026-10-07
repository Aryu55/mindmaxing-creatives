const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const base = 'http://127.0.0.1:3107';

async function assertGarmentFits(frame) {
  const pixels = await frame.locator('#garment-canvas').evaluate(canvas => {
    const gl = canvas.getContext('webgl'), w = canvas.width, h = canvas.height, data = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, data);
    let painted = 0, edge = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (data[(y * w + x) * 4 + 3] > 0) {
          painted++;
          if (x < 2 || x >= w - 2 || y < 2 || y >= h - 2) edge++;
        }
      }
    }
    return { painted, edge };
  });
  assert.ok(pixels.painted > 100, 'Garment is visibly rendered');
  assert.equal(pixels.edge, 0, 'Garment does not clip at the canvas edge');
}

const server = spawn(process.execPath, ['scripts/preview-site.mjs'], { env: { ...process.env, PORT: '3107' }, stdio: 'pipe' });
const ready = new Promise((resolve, reject) => {
  server.stdout.once('data', resolve);
  server.once('error', reject);
});

(async () => {
  await ready;
  const { projects } = await import('../site/projects.mjs');
  assert.equal(projects.length, 42, 'Exactly 42 projects in catalogue');

  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage(), errors = [], failed = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => {
    if (r.status() >= 400 && !r.url().includes('/api/contact')) failed.push(r.url() + ': ' + r.status());
  });

  await page.goto(base);
  await page.evaluate(() => document.fonts.ready);
  assert.equal(await page.locator('.work-row').count(), 6);
  await page.locator('[data-preview-state="ready"]').waitFor();
  assert.equal(await page.locator('.night-photo img').evaluate(el => el.naturalWidth > 0), true);

  // Test Knittire material controls
  const cotton = await page.locator('#hero-garment').evaluate(el => el.toDataURL());
  await page.locator('[data-material="2"]').click();
  assert.match(await page.locator('#hero-material-name').innerText(), /Satin/);
  assert.notEqual(await page.locator('#hero-garment').evaluate(el => el.toDataURL()), cotton, 'Material visibly changes the garment');
  await page.locator('[data-material="0"]').click();
  assert.equal(await page.locator('[data-material="0"]').getAttribute('aria-pressed'), 'true');

  // Test 3-Project Hero Interactive Tab Switcher
  await page.locator('[data-hero-tab="dealstrike"]').click();
  assert.equal(await page.locator('#hero-stage-dealstrike').isVisible(), true);
  assert.match(await page.locator('#hero-project-title').innerText(), /DealStrike/);
  assert.equal(await page.locator('#hero-project-link').getAttribute('href'), '/case-studies/dealstrike');

  await page.locator('[data-hero-tab="zupee"]').click();
  assert.equal(await page.locator('#hero-stage-zupee').isVisible(), true);
  assert.match(await page.locator('#hero-project-title').innerText(), /Zupee/);
  assert.equal(await page.locator('#hero-project-link').getAttribute('href'), '/case-studies/zupee');
  await page.locator('#zupee-next-btn').click();
  assert.match(await page.locator('#zupee-slide-counter').innerText(), /2 \/ 3/);

  await page.locator('[data-hero-tab="knittire"]').click();
  assert.equal(await page.locator('#hero-stage-knittire').isVisible(), true);
  assert.match(await page.locator('#hero-project-title').innerText(), /Knittire/);

  // Founder Section Checks on Homepage
  await page.locator('#team').scrollIntoViewIfNeeded();
  assert.equal(await page.locator('#team').isVisible(), true);
  assert.match(await page.locator('.founder-kicker').innerText(), /Meet Aryan/i);
  assert.match(await page.locator('.founder-copy h2').innerText(), /Aryan Panchal/);
  assert.match(await page.locator('.founder-role').innerText(), /Founder & Engineering Lead/);
  await page.locator('.founder-portrait').scrollIntoViewIfNeeded();
  await page.locator('.founder-portrait').evaluate(el => el.decode());
  assert.equal(await page.locator('.founder-portrait').evaluate(el => el.naturalWidth > 0), true);

  fs.mkdirSync('site/review', { recursive: true });
  await page.screenshot({ path: 'site/review/home-desktop.png' });

  // Test lazy loaded images
  for (const img of await page.locator('.work-row img').all()) {
    await img.scrollIntoViewIfNeeded();
    await img.evaluate(el => el.decode());
  }
  const homeImages = await page.locator('img').evaluateAll(imgs => imgs.filter(i => !i.complete || !i.naturalWidth).map(i => i.src));
  assert.deepEqual(homeImages, []);

  // Search & Filter state preservation
  await page.goto(base + '/case-studies?category=software&q=ABX');
  assert.equal(await page.locator('.work-row:visible').count(), 1);
  await page.locator('.work-row:visible').click();
  await page.goBack();
  assert.equal(await page.locator('#project-search').inputValue(), 'ABX');
  assert.equal(await page.locator('.work-row:visible').count(), 1);

  // Hash-based legacy redirect checks
  await page.goto(base + '/#whatsapp-autopilot');
  await page.waitForURL('**/case-studies/whatsapp-autopilot');
  await page.goto(base + '/case-studies.html#knittire-3d');
  await page.waitForURL('**/case-studies/knittire-3d');

  // Explicit, mandatory action handlers for ALL 42 projects
  const actions = {
    'knittire-3d': async f => {
      await f.locator('#fabric').selectOption({ label: 'Satin · slate' });
      assert.match(await f.locator('#result').innerText(), /Satin/);
    },
    'saffron-origins': async f => {
      await f.locator('#colour').selectOption('Ink');
      await f.locator('#size').selectOption('XL');
      assert.equal(await f.locator('#add').isDisabled(), true);
      await f.locator('#size').selectOption('M');
      await f.locator('#add').click();
      assert.match(await f.locator('#cart-status').innerText(), /Ink · M/);
    },
    'abx-engine': async f => {
      await f.locator('#visitor').fill('test-visitor');
      await f.locator('#assign').click();
      const first = await f.locator('#variant').innerText();
      await f.locator('#assign').click();
      assert.equal(await f.locator('#variant').innerText(), first);
      await f.locator('#visitor').fill('');
      await f.locator('#assign').click();
      assert.match(await f.locator('#result').innerText(), /Enter/);
    },
    'whatsapp-autopilot': async f => {
      await f.locator('#event').selectOption('EVT-102');
      await f.locator('#run').click();
      assert.match(await f.locator('#result').innerText(), /retry/);
      await f.locator('#run').click();
      assert.match(await f.locator('#result').innerText(), /delivered/);
      await f.locator('#run').click();
      assert.match(await f.locator('#result').innerText(), /duplicate skipped/);
    },
    'shopify-cro': async f => {
      await f.locator('#quantity').fill('3');
      assert.match(await f.locator('#result').innerText(), /unlocked/);
    },
    'manifest': async f => {
      await f.locator('#offer').selectOption('Complete study bundle');
      assert.match(await f.locator('#result').innerText(), /899/);
    },
    'xalt-watches': async f => {
      await f.locator('#direction').selectOption('Right to left');
      assert.equal(await f.locator('#direction-card').getAttribute('dir'), 'rtl');
    },
    'glaze': async f => {
      await f.locator('#note').fill('<script>example</script>');
      await f.locator('#add-note').click();
      assert.equal(await f.locator('.note').first().innerText(), '<script>example</script>');
    },
    'janus': async f => {
      await f.locator('[data-next="0"]').click();
      assert.match(await f.locator('#result').innerText(), /in progress/);
    },
    'before-token': async f => {
      await f.locator('#record').selectOption('Project name');
      assert.match(await f.locator('#result').innerText(), /match/);
    },
    'hisaab': async f => {
      await f.locator('#person').fill('Demo Person');
      await f.locator('#draft').click();
      assert.match(await f.locator('#draft-copy').innerText(), /Demo Person/);
    },
    'freedoms-ai': async f => {
      await f.locator('#extract').click();
      assert.equal(await f.locator('#tasks input').count(), 3);
    },
    'pause': async f => {
      await f.locator('#breathe').click();
      await f.locator('#hold').click();
      assert.match(await f.locator('#result').innerText(), /Paused/);
    },
    'bhoomiputra': async f => {
      await f.locator('#programme').selectOption('Sanitation programme');
      assert.match(await f.locator('#programme-title').innerText(), /Sanitation/);
    },
    'safespot': async f => {
      await f.locator('#source').selectOption('Clear session');
      assert.match(await f.locator('#result').innerText(), /cleared/);
    },
    'weshub': async f => {
      await f.locator('#step-next').click();
      await f.locator('#step-next').click();
      assert.equal(await f.locator('#step-next').isDisabled(), true);
    },
    'bukl': async f => {
      await f.locator('#tension').fill('80');
      assert.match(await f.locator('#result').innerText(), /engages/);
    },
    'solar-solutions': async f => {
      await f.locator('#bill').fill('5000');
      assert.match(await f.locator('#saving').innerText(), /1,500/);
    },
    'healthy-meals': async f => {
      await f.locator('#compose').click();
      assert.match(await f.locator('#result').innerText(), /Hello/);
    },
    'zyron-tech': async f => {
      await f.locator('#stage').selectOption({ index: 1 });
      assert.match(await f.locator('#result').innerText(), /Stage 2/);
    },
    'luxury-spirits': async f => {
      await f.locator('#inspect-region').click();
      assert.match(await f.locator('#result').innerText(), /Auditing/);
    },
    'zupee': async f => {
      await f.locator('#post').selectOption({ index: 1 });
      assert.match(await f.locator('#result').innerText(), /Dialect/);
    },
    'd2c-fitness': async f => {
      await f.locator('#angle').selectOption({ index: 1 });
      assert.match(await f.locator('#result').innerText(), /Equipment/);
    },
    'shopify-saas': async f => {
      await f.locator('#lesson').selectOption({ index: 1 });
      assert.match(await f.locator('#result').innerText(), /Variant/);
    },

    // 18 New Additions:
    'dealstrike': async f => {
      await f.locator('#apply-crm').click();
      assert.match(await f.locator('#result').innerText(), /synchronized/);
    },
    'billfetch': async f => {
      await f.locator('#approve-bill').click();
      assert.match(await f.locator('#result').innerText(), /Approved/);
    },
    'gtm-tracker': async f => {
      await f.locator('#replies').fill('10');
      await f.locator('#gate-verdict').filter({ hasText: /SCALE/ }).waitFor();
      assert.match(await f.locator('#gate-verdict').innerText(), /SCALE/);
    },
    'mag-swimwear': async f => {
      await f.locator('#reserve').click();
      await f.locator('#result').filter({ hasText: /Hold confirmed/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Hold confirmed/);
    },
    'machhli': async f => {
      await f.locator('[data-col="Resort"]').click();
      await f.locator('#result').filter({ hasText: /Resort/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Resort/);
    },
    'naka': async f => {
      await f.locator('.duty-cell').first().click();
      await f.locator('#result').filter({ hasText: /Recalculated/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Recalculated/);
    },
    'codsure': async f => {
      await f.locator('#btn-otp').click();
      await f.locator('#result').filter({ hasText: /confirmed/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /confirmed/);
    },
    'jawaab-engine': async f => {
      await f.locator('#sim-reply').click();
      assert.match(await f.locator('#result').innerText(), /Customer reply/);
    },
    'service-picker': async f => {
      await f.locator('#team-role').selectOption('Growing Agency');
      await f.locator('#result').filter({ hasText: /Growing Agency/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Growing Agency/);
    },
    'message-tree': async f => {
      await f.locator('#obj-sel').selectOption({ index: 1 });
      await f.locator('#result').filter({ hasText: /Objection response/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Objection response/);
    },
    'audit-generator': async f => {
      await f.locator('#speed').fill('20');
      await f.locator('#result').filter({ hasText: /Generated forensic/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Generated forensic/);
    },
    'buyer-list-builder': async f => {
      await f.locator('[data-add]').first().click();
      await f.locator('#result').filter({ hasText: /1 shortlisted/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /1 shortlisted/);
    },
    'shortlist': async f => {
      await f.locator('#sample-bullet').click();
      await f.locator('#result').filter({ hasText: /passed/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /passed/);
    },
    'kirti-couture': async f => {
      await f.locator('#dir-sel').selectOption({ index: 1 });
      await f.locator('#result').filter({ hasText: /Old British/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Old British/);
    },
    'payments-dashboard-study': async f => {
      await f.locator('tr[data-id]').first().click();
      await f.locator('#result').filter({ hasText: /Inspecting/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Inspecting/);
    },
    'dtc-creative-os': async f => {
      await f.locator('#angle-sel').selectOption({ index: 1 });
      await f.locator('#result').filter({ hasText: /Generated storyboard/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Generated storyboard/);
    },
    'agency-followup-os': async f => {
      await f.locator('#mark-sent').click();
      await f.locator('#result').filter({ hasText: /sent/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /sent/);
    },
    'creator-sponsorship-os': async f => {
      await f.locator('#kit-sec').selectOption('Rate Card');
      await f.locator('#result').filter({ hasText: /Rate Card/ }).waitFor();
      assert.match(await f.locator('#result').innerText(), /Rate Card/);
    }
  };

  // Ensure every project in catalogue has an explicit action test
  for (const p of projects) {
    assert.ok(actions[p.slug], `Action handler exists for ${p.slug}`);
  }

  for (const p of projects) {
    await page.goto(base + '/case-studies/' + p.slug);
    assert.match(await page.title(), new RegExp(p.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    await page.locator('[data-demo-start]').click();
    await page.locator('[data-demo-url][data-ready="true"]').waitFor();
    const f = page.frameLocator('.demo-frame');
    await f.locator('#experience h1').waitFor();
    const before = await f.locator('#experience').innerText();
    assert.equal(await f.locator('html').evaluate(el => getComputedStyle(el).getPropertyValue('--project-accent').trim()), p.accent, 'Project colour reaches its isolated demo');

    await actions[p.slug](f);

    if (p.slug === 'knittire-3d') {
      await assertGarmentFits(f);
      await page.locator('[data-demo-expand]').click();
      assert.equal(await page.locator('.is-expanded').count(), 1);
      assert.match(await f.locator('#result').innerText(), /Satin/);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('.is-expanded').count(), 0);
    }

    await f.locator('#reset').click();
    assert.equal(await f.locator('#experience').innerText(), before, `${p.slug}: reset`);
    assert.equal(await page.locator('.demo-frame').getAttribute('sandbox'), 'allow-scripts');
    console.log('PASS route + demo + reset:', p.slug);
  }

  // Narrow layout responsive checks
  for (const width of [390, 768]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(base);
    await page.evaluate(() => document.fonts.ready);
    await page.locator('[data-preview-state="ready"]').waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: `site/review/home-${width}.png`, fullPage: width === 390 });
    await page.goto(base + '/case-studies');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));

    for (const p of projects) {
      await page.goto(base + '/case-studies/' + p.slug);
      await page.locator('[data-demo-start]').click();
      await page.locator('[data-demo-url][data-ready="true"]').waitFor();
      const f = page.frameLocator('.demo-frame');
      await f.locator('#experience h1').waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${p.slug} page overflow ${width}`);
      assert.ok(await f.locator('html').evaluate(el => el.scrollWidth <= el.clientWidth), `${p.slug} demo overflow ${width}`);
      if (p.slug === 'knittire-3d') await assertGarmentFits(f);
    }
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base);
  await page.locator('.menu-toggle').click();
  assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'), 'true');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');

  await page.goto(base + '/?project=Knittire#contact');
  assert.equal(await page.locator('input[name=project]').inputValue(), 'Knittire');

  await page.route('**/api/contact', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' }));
  await page.locator('[name=name]').fill('Test Person');
  await page.locator('[name=email]').fill('test@example.com');
  await page.locator('[name=details]').fill('A fictional project for testing only.');
  await page.locator('[type=submit]').click();
  await page.locator('[data-state=success]').waitFor();

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(base);
  await page.locator('[data-preview-state="ready"]').waitFor();
  await page.locator('[data-material="1"]').click();
  assert.match(await page.locator('#hero-material-name').innerText(), /Wool/);
  assert.equal(await page.locator('.night-photo').evaluate(el => getComputedStyle(el).transform), 'none');
  await page.goto(base + '/case-studies/knittire-3d');
  assert.equal(await page.locator('.button').first().evaluate(el => getComputedStyle(el).transitionDuration), '0s');

  await page.locator('[data-demo-start]').click();
  await page.locator('[data-demo-url][data-ready="true"]').waitFor();
  await page.frameLocator('.demo-frame').locator('#experience h1').waitFor();
  await page.locator('[data-demo-expand]').click();
  await page.screenshot({ path: 'site/review/demo-mobile.png' });
  await page.locator('[data-demo-expand]').click();

  assert.deepEqual(errors, [], 'Browser errors');
  assert.deepEqual([...new Set(failed)], [], 'Failed resources');
  console.log('PASS mobile, tablet, navigation, project context, mock contact, reduced motion, console and assets');

  const newTab = await context.newPage();
  await newTab.goto(base + '/case-studies/abx-engine', { referer: base + '/case-studies?category=software' });
  await newTab.locator('[data-back-work]').click();
  await newTab.waitForURL('**/case-studies');
  await newTab.close();

  const noJS = await browser.newContext({ javaScriptEnabled: false });
  const plain = await noJS.newPage();
  let nativeMethod;
  await plain.route('**/api/contact', route => {
    nativeMethod = route.request().method();
    return route.fulfill({ status: 200, contentType: 'text/plain', body: 'Mocked native fallback' });
  });
  await plain.goto(base);
  await plain.locator('[name=name]').fill('Test Person');
  await plain.locator('[name=email]').fill('test@example.com');
  await plain.locator('[name=details]').fill('Private test brief');
  await plain.locator('[type=submit]').click();
  await plain.waitForURL('**/api/contact');
  assert.equal(nativeMethod, 'POST');
  assert.equal(new URL(plain.url()).search, '');
  await noJS.close();

  const resilience = await context.newPage();
  await resilience.route('**/demos/garment.js', route => route.fulfill({ status: 200, contentType: 'application/javascript', body: '// Simulated unavailable WebGL renderer' }));
  await resilience.goto(base);
  await resilience.locator('[data-preview-state="fallback"]').waitFor();
  assert.equal(await resilience.locator('.hero-garment-fallback').isVisible(), true);
  assert.equal(await resilience.locator('[data-material="0"]').isDisabled(), true);
  await resilience.locator('.hero-live-link').click();
  await resilience.waitForURL('**/case-studies/knittire-3d');
  await resilience.unroute('**/demos/garment.js');

  await resilience.goto(base + '/case-studies/abx-engine');
  assert.equal(await resilience.locator('iframe').count(), 0, 'Demo is not loaded before request');
  await resilience.route('**/demos/demo.js', route => route.fulfill({ status: 200, contentType: 'application/javascript', body: '// Simulated initialization failure' }));
  await resilience.locator('[data-demo-start]').click();
  await resilience.evaluate(() => window.postMessage({ channel: 'mindmaxing-demo', type: 'ready' }, '*'));
  assert.equal(await resilience.locator('[data-demo-url]').getAttribute('data-ready'), null, 'Parent spoof cannot mark demo ready');
  await resilience.locator('.demo-error:visible').waitFor({ timeout: 16000 });
  assert.equal(await resilience.locator('iframe').count(), 0);
  assert.equal(await resilience.locator('[data-demo-url]').getAttribute('data-ready'), null);
  await resilience.unroute('**/demos/demo.js');
  await resilience.locator('[data-demo-retry]').click();
  await resilience.locator('[data-demo-url][data-ready="true"]').waitFor();

  await resilience.goto(base + '/?project=ABX%20Engine#contact');
  await resilience.route('**/api/contact', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'Temporarily unavailable. Please try again.' }) }));
  await resilience.locator('[name=name]').fill('Test Person');
  await resilience.locator('[name=email]').fill('test@example.com');
  await resilience.locator('[name=details]').fill('A fictional brief that must survive failure.');
  await resilience.locator('[type=submit]').click();
  await resilience.locator('[data-state=error]').waitFor();
  assert.equal(await resilience.locator('[name=details]').inputValue(), 'A fictional brief that must survive failure.');
  assert.equal(await resilience.locator('[type=submit]').isEnabled(), true);
  assert.equal(await resilience.locator('[name=project]').inputValue(), 'ABX Engine');
  await resilience.close();
  console.log('PASS static garment recovery, lazy demo loading, message-source rejection, timeout fallback, retry and contact failure recovery');

  await browser.close();
  server.kill();
})().catch(e => {
  console.error(e);
  server.kill();
  process.exit(1);
});
