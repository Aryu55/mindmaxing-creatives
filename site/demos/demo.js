(function(){
  'use strict';
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)], area = $('#experience'), L = globalThis.DemoLogic;
  const slug = new URLSearchParams(location.search).get('project') || 'knittire-3d';
  document.documentElement.dataset.project = slug;
  const e = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  let cleanup = () => {}, visible = !document.hidden, parentVisible = true, visibilityHandler = () => {};
  const send = (type, value) => parent.postMessage({ channel: 'mindmaxing-demo', type, value }, '*');
  const title = (h, p) => `<h1>${h}</h1><p class="lead">${p}</p>`;
  const button = (id, label, cls = 'primary') => `<button type="button" id="${id}" class="${cls}">${label}</button>`;
  const field = (id, label, value = '', type = 'text') => `<label>${label}<input id="${id}" type="${type}" value="${e(value)}"></label>`;
  const choose = (id, label, options) => `<label>${label}<select id="${id}">${options.map(x => `<option>${x}</option>`).join('')}</select></label>`;
  const layout = (left, right) => `<div class="layout"><div class="panel stack">${left}</div><div class="panel stack">${right}</div></div>`;
  const output = (text = '') => `<div id="result" class="result" role="status" aria-live="polite">${text}</div>`;

  async function init() {
    cleanup();
    cleanup = () => {};
    visibilityHandler = () => {};
    area.innerHTML = '';
    if (!demos[slug]) {
      area.innerHTML = title('Demonstration unavailable', 'This project does not have an active sandbox.');
      height();
      send('ready', true);
      return;
    }
    demos[slug]();
    await document.fonts.load('400 16px Instrument').catch(() => {});
    height();
    send('ready', true);
  }

  function height() {
    send('height', Math.ceil(document.documentElement.getBoundingClientRect().height));
  }

  const demos = {
    // --- 1. Knittire ---
    'knittire-3d'() {
      area.innerHTML = title('A material changes everything.', 'Explore a demonstration garment. Change the fabric and rotate the view.') +
        layout(
          `<div class="visual garment-stage"><canvas id="garment-canvas" width="600" height="600" aria-label="Rotatable demonstration tee" role="img"></canvas><span class="visual-caption">Procedural demonstration garment · not the client model</span></div>`,
          `${choose('fabric', 'Material', ['Cotton · sage', 'Wool · sand', 'Satin · slate'])}<label>Rotation<input id="rotation" type="range" min="-180" max="180" value="-20"></label><div class="rule"></div><span class="small">CONFIGURATION</span>${output('Cotton · sage / −20°')}<p class="small">A procedural 3D study. Surface lighting and material settings respond to the controls. No production tech pack is generated.</p>`
        );
      let renderer = null;
      try { renderer = globalThis.GarmentRenderer?.($('#garment-canvas')); } catch {}
      if (!renderer) {
        $('#garment-canvas').outerHTML = '<div class="garment" id="garment-flat" role="img" aria-label="Static garment fallback"></div>';
        $('.visual-caption').textContent = '2D fallback · WebGL unavailable';
      }
      const update = () => {
        const index = $('#fabric').selectedIndex, angle = Number($('#rotation').value);
        renderer?.draw(angle, index);
        const flat = $('#garment-flat');
        if (flat) {
          flat.className = 'garment ' + ['', 'wool', 'satin'][index];
          flat.style.setProperty('--angle', angle + 'deg');
        }
        $('#result').textContent = `${$('#fabric').value} / ${angle}°`;
      };
      $('#fabric').onchange = update;
      $('#rotation').oninput = update;
      update();
      visibilityHandler = () => renderer?.setActive(visible);
      visibilityHandler();
      cleanup = () => renderer?.destroy();
    },

    // --- 2. Saffron Origins ---
    'saffron-origins'() {
      area.innerHTML = title('Make the selection unmistakable.', 'A sample apparel detail-to-cart interaction.') +
        layout(
          `<div class="visual"><div id="tee" class="garment"></div><span class="visual-caption">Sample tee · illustrative garment</span></div>`,
          `${choose('colour', 'Colour', ['Sage', 'Sand', 'Ink'])}${choose('size', 'Size', ['S', 'M', 'L', 'XL'])}<p class="small">Try Ink + XL to see an unavailable combination.</p>${button('add', 'Add sample tee')}${output('Choose your colour and size.')}<div class="rule"></div><p id="cart-status">Your sample cart is empty.</p>`
        );
      const update = () => {
        const unavailable = $('#colour').value === 'Ink' && $('#size').value === 'XL';
        $('#tee').className = 'garment ' + ['', 'wool', 'satin'][$('#colour').selectedIndex];
        $('#add').disabled = unavailable;
        $('#result').textContent = unavailable
          ? 'This combination is unavailable. Choose another size or colour.'
          : `${$('#colour').value} / ${$('#size').value} - available in this sample.`;
      };
      $('#colour').onchange = update;
      $('#size').onchange = update;
      $('#add').onclick = () => {
        $('#cart-status').textContent = `1 × sample tee · ${$('#colour').value} · ${$('#size').value}`;
        $('#result').textContent = 'Selection added to the local cart.';
      };
      update();
    },

    // --- 3. ABX Engine ---
    'abx-engine'() {
      area.innerHTML = title('Same visitor. Same experience.', 'Deterministic allocation keeps the treatment stable for a sample visitor.') +
        layout(
          `${field('visitor', 'Visitor identifier', 'visitor-21')}<div class="wrap">${button('assign', 'Assign variant')}${button('next', 'Try another visitor', 'quiet')}</div><p class="small">The identifier is hashed locally. A 50/50 bucket rule selects A or B. No identity is stored or sent.</p>`,
          `<span class="small">ASSIGNED TREATMENT</span><div id="variant" class="value accent">—</div>${output()}<div class="preview-card"><span class="tag">Sample storefront</span><h2 id="variant-copy"></h2><p id="variant-cta"></p></div>`
        );
      let n = 22;
      const assign = () => {
        const id = $('#visitor').value.trim();
        if (!id) { $('#result').textContent = 'Enter a visitor identifier first.'; return; }
        const variant = L.bucket(id);
        $('#variant').textContent = `Variant ${variant}`;
        $('#result').textContent = `${id} → bucket ${variant}. Repeating this ID produces the same assignment.`;
        $('#variant-copy').textContent = variant === 'A' ? 'Made for the everyday.' : 'A better kind of everyday.';
        $('#variant-cta').textContent = variant === 'A' ? 'Explore the collection ↗' : 'Find your everyday ↗';
      };
      $('#assign').onclick = assign;
      $('#next').onclick = () => { $('#visitor').value = 'visitor-' + n++; assign(); };
      assign();
    },

    // --- 4. WhatsApp Autopilot ---
    'whatsapp-autopilot'() {
      let queue = L.initialPipeline();
      area.innerHTML = title('A workflow that remembers.', 'Run a sample event, recover a failure, then repeat it to test duplicate prevention.') +
        layout(
          `<span class="small">EVENT INPUT</span>${choose('event', 'Event identifier', queue.map(x => x.id))}<div class="wrap">${button('run', 'Process event')}${button('all', 'Run all events', 'quiet')}</div><p class="notice">EVT-102 fails on its first attempt. Processing it again retries that step. Delivered events stay delivered.</p>`,
          `${output('Ready to process a sample event.')}<div id="queue" class="stack"></div>`
        );
      const render = () => {
        $('#queue').innerHTML = queue.map(x => `<div class="queue-item"><span>${x.status === 'delivered' ? '✓' : x.status === 'retry' ? '↻' : '○'}</span><div><h3>${x.id}</h3><p class="small">${x.label}</p></div><span class="tag">${x.status}</span></div>`).join('');
      };
      const run = id => {
        const before = queue.find(x => x.id === id);
        queue = L.processEvent(queue, id);
        $('#result').textContent = before.status === 'delivered'
          ? `${id}: duplicate skipped. No second delivery.`
          : `${id}: ${queue.find(x => x.id === id).status}. Attempts: ${queue.find(x => x.id === id).attempts}.`;
        render();
      };
      $('#run').onclick = () => run($('#event').value);
      $('#all').onclick = () => { queue.forEach(x => run(x.id)); };
      render();
    },

    // --- 5. Shopify CRO ---
    'shopify-cro'() {
      area.innerHTML = title('Every quantity has a consequence.', 'The subtotal, shipping and progress indicator share one cart state.') +
        layout(
          `<div class="visual"><div class="garment wool"></div><span class="visual-caption">Sample everyday tee</span></div>`,
          `${field('quantity', 'Quantity', 1, 'number')}<span class="small">SAMPLE UNIT PRICE ₹490 / FREE SHIPPING AT ₹1,000</span><div id="cart-lines"></div><div class="meter"><span id="progress"></span></div>${output()}`
        );
      $('#quantity').min = 0; $('#quantity').max = 10;
      const render = () => {
        const c = L.cart($('#quantity').value);
        $('#cart-lines').innerHTML = `<div class="row"><p>Subtotal</p><span>₹${c.subtotal}</span></div><div class="row"><p>Shipping</p><span>₹${c.shipping}</span></div><div class="rule"></div><div class="row"><h2>Total</h2><h2>₹${c.total}</h2></div>`;
        $('#progress').style.width = Math.min(c.subtotal / 1000 * 100, 100) + '%';
        $('#result').textContent = c.quantity === 0
          ? 'Your sample cart is empty.'
          : c.remaining ? `₹${c.remaining} to sample free shipping.` : 'Free shipping unlocked in this sample.';
      };
      $('#quantity').oninput = render;
      render();
    },

    // --- 6. Manifest ---
    'manifest'() {
      area.innerHTML = title('One offer. A clear total.', 'Compare sample bundles and see exactly what changes.') +
        layout(
          `${choose('offer', 'Choose a sample offer', ['Digital guide', 'Guide + workbook', 'Complete study bundle'])}${field('copies', 'Copies', 1, 'number')}<p class="small">Illustrative catalogue and prices. No checkout or payment connection.</p>`,
          `<span class="small">ORDER SUMMARY</span><div id="bundle"></div>${output()}`
        );
      $('#copies').min = 1; $('#copies').max = 10;
      const render = () => {
        const offers = [{ price: 399, items: ['Digital guide'] }, { price: 599, items: ['Digital guide', 'Workbook'] }, { price: 899, items: ['Digital guide', 'Workbook', 'Audio companion'] }];
        const v = offers[$('#offer').selectedIndex];
        const q = Math.max(1, Math.min(10, parseInt($('#copies').value) || 1));
        $('#bundle').innerHTML = v.items.map(x => `<p>✓ ${x}</p>`).join('');
        $('#result').innerHTML = `<span class="small">${q} × ₹${v.price}</span><div class="value">₹${q * v.price}</div>`;
      };
      $('#offer').onchange = render;
      $('#copies').oninput = render;
      render();
    },

    // --- 7. Xalt Watches ---
    'xalt-watches'() {
      area.innerHTML = title('Get closer. Change perspective.', 'A sample dial and direction-aware product interface.') +
        layout(
          `<div class="visual watch-visual"><div id="dial" class="dial"><span>STUDY / 01</span></div><span class="visual-caption">Illustrative dial · not an original product render</span></div>`,
          `<label>Dial zoom<input id="zoom" type="range" min="100" max="150" value="100"></label>${choose('direction', 'Layout direction', ['Left to right', 'Right to left'])}<div id="direction-card" class="preview-card"><span class="tag">Sample watch</span><h2>A closer look.</h2><p>Details → Selection → Summary</p></div>`
        );
      $('#zoom').oninput = () => { $('#dial').style.transform = `scale(${$('#zoom').value / 100})`; };
      $('#direction').onchange = () => { $('#direction-card').dir = $('#direction').selectedIndex ? 'rtl' : 'ltr'; };
    },

    // --- 8. Glaze ---
    'glaze'() {
      area.innerHTML = title('A note becomes a conversation.', 'Try the smallest useful feedback loop, using local sample notes.') +
        layout(
          `<label>Your sample note<textarea id="note" maxlength="200" placeholder="The interaction feels thoughtful…"></textarea></label>${button('add-note', 'Add sample note')}${output('Notes stay in this sandbox until it resets.')}`,
          `<div id="notes" class="notes"><div class="note">A little more clarity goes a long way.</div><div class="note">Keep making the complicated feel simple.</div></div>`
        );
      $('#add-note').onclick = () => {
        const v = $('#note').value.trim();
        if (!v) { $('#result').textContent = 'Write a short note first.'; return; }
        const el = document.createElement('div');
        el.className = 'note';
        el.textContent = v;
        $('#notes').prepend(el);
        if ($('#notes').children.length > 4) $('#notes').lastElementChild.remove();
        $('#note').value = '';
        $('#result').textContent = 'Sample note added. Nothing was published.';
      };
    },

    // --- 9. Janus ---
    'janus'() {
      let jobs = [['Draft script', 'queued'], ['Render reel', 'queued'], ['Review captions', 'queued']];
      area.innerHTML = title('Keep the next step in sight.', 'A sample content-production queue. Advance a job or move its priority.') +
        layout(
          `<p class="notice">Each job moves from queued → in progress → ready for review. Nothing is published.</p>${output('Three sample jobs queued.')}`,
          `<div id="jobs" class="stack"></div>`
        );
      const render = () => {
        $('#jobs').innerHTML = jobs.map((j, i) => `<div class="queue-item"><button data-up="${i}" aria-label="Move ${j[0]} earlier" ${i === 0 ? 'disabled' : ''}>↑</button><div><h3>${j[0]}</h3><span class="small">${j[1]}</span></div><button data-next="${i}" aria-label="Advance ${j[0]}" ${j[1] === 'ready for review' ? 'disabled' : ''}>→</button></div>`).join('');
      };
      $('#jobs').onclick = ev => {
        const up = ev.target.closest('[data-up]'), next = ev.target.closest('[data-next]');
        if (up) {
          const i = +up.dataset.up;
          [jobs[i - 1], jobs[i]] = [jobs[i], jobs[i - 1]];
          $('#result').textContent = 'Priority updated.';
        }
        if (next) {
          const i = +next.dataset.next;
          jobs[i][1] = jobs[i][1] === 'queued' ? 'in progress' : 'ready for review';
          $('#result').textContent = jobs[i][0] + ': ' + jobs[i][1];
        }
        render();
      };
      render();
    },

    // --- 10. Before Token ---
    'before-token'() {
      area.innerHTML = title('A mismatch should be inspectable.', 'Compare a fictional brochure against a fictional source record.') +
        layout(
          `${choose('record', 'Field to compare', ['Completion date', 'Declared area', 'Project name'])}<p class="notice">Fictional fixtures. No registry query or risk verdict.</p>`,
          `<div class="document"><span class="small">BROCHURE / SOURCE RECORD</span><h2 id="compare-field"></h2><div class="rule"></div><p id="left-record"></p><p id="right-record"></p></div>${output()}`
        );
      const render = () => {
        const i = $('#record').selectedIndex;
        const rows = [['December 2026', 'March 2027'], ['920 sq ft', '870 sq ft'], ['Example Residence', 'Example Residence']];
        $('#compare-field').textContent = $('#record').value;
        $('#left-record').textContent = 'Brochure: ' + rows[i][0];
        $('#right-record').textContent = 'Source record: ' + rows[i][1];
        $('#result').textContent = rows[i][0] === rows[i][1] ? 'Values match in this fixture.' : 'Different values. Open the original records before drawing a conclusion.';
      };
      $('#record').onchange = render;
      render();
    },

    // --- 11. Hisaab ---
    'hisaab'() {
      area.innerHTML = title('A structured start to a draft.', 'Fill in fictional details and see them reflected in a sample document.') +
        layout(
          `${field('person', 'Fictional name', 'Alex Example')}${choose('document-topic', 'Sample topic', ['Payment enquiry', 'Document request', 'Follow-up'])}${button('draft', 'Preview sample draft')}<p class="notice">Demonstration only. Not legal advice or a filing-ready document.</p>`,
          `<div class="document" id="draft-document"><span class="small">SAMPLE / NOT FOR FILING</span><h2>Draft preview</h2><div class="rule"></div><p id="draft-copy">Your structured answers will appear here.</p></div>`
        );
      $('#draft').onclick = () => {
        $('#draft-copy').textContent = `Subject: ${$('#document-topic').value}. This sample is prepared for ${$('#person').value.trim() || 'a fictional person'}. Please provide the relevant records so that the outstanding matter can be reviewed. No legal assertions or calculations are included.`;
      };
    },

    // --- 12. Freedoms AI ---
    'freedoms-ai'() {
      const samples = [
        ['Prepare the studio demo', 'Tomorrow, review the studio homepage. Then record the garment interaction. Send the draft to the team on Friday.', ['Review the studio homepage', 'Record the garment interaction', 'Share the draft on Friday']],
        ['A calmer morning', 'I need to pack my notebook tonight. Tomorrow I want to take a walk before I check my messages.', ['Pack the notebook tonight', 'Take a morning walk', 'Check messages afterwards']]
      ];
      area.innerHTML = title('From a thought to a next step.', 'Explore prepared extracts from two sample voice-note transcripts.') +
        layout(
          `${choose('transcript', 'Prerecorded sample', samples.map(x => x[0]))}<div id="transcript-copy" class="result"></div>${button('extract', 'Reveal prepared tasks')}<p class="small">Prepared sample output. No microphone, speech model or live AI request.</p>`,
          `<span class="small">ACTION ITEMS</span><div id="tasks">Choose a sample and reveal its prepared tasks.</div>`
        );
      const update = () => {
        $('#transcript-copy').textContent = samples[$('#transcript').selectedIndex][1];
        $('#tasks').textContent = 'Ready to reveal the prepared task list.';
      };
      $('#transcript').onchange = update;
      $('#extract').onclick = () => {
        $('#tasks').innerHTML = samples[$('#transcript').selectedIndex][2].map(x => `<label class="task"><input type="checkbox"><span>${x}</span></label>`).join('');
      };
      update();
    },

    // --- 13. Pause ---
    'pause'() {
      let seconds = 0, running = false, interval;
      area.innerHTML = title('Make room for one breath.', 'A short pacing interaction inspired by the Android product.') +
        layout(
          `<div class="visual"><div id="breath" class="breath"><b id="phase">Ready</b></div></div>`,
          `<div class="wrap">${button('breathe', 'Start interval')}${button('hold', 'Pause', 'quiet')}</div>${output('A 12-second sample interval.')}<p class="notice">Browser interaction only. No device interception, haptic control or health claims.</p>`
        );
      const render = () => {
        $('#phase').textContent = seconds === 12 ? 'Complete' : seconds < 4 ? 'Breathe in' : seconds < 8 ? 'Hold' : 'Breathe out';
        $('#breath').style.transform = `scale(${seconds < 4 ? 1 + seconds * .04 : seconds < 8 ? 1.16 : 1.16 - (seconds - 8) * .04})`;
        $('#result').textContent = `${seconds} / 12 seconds`;
      };
      const stop = () => { clearInterval(interval); interval = null; };
      const tick = () => {
        if (interval || !running || !visible) return;
        interval = setInterval(() => {
          seconds++;
          render();
          if (seconds >= 12) { running = false; stop(); $('#breathe').textContent = 'Start again'; }
        }, 1000);
      };
      $('#breathe').onclick = () => {
        if (seconds >= 12) seconds = 0;
        running = true;
        render();
        tick();
      };
      $('#hold').onclick = () => {
        running = false;
        stop();
        $('#result').textContent = `Paused at ${seconds} seconds.`;
      };
      visibilityHandler = () => { visible ? tick() : stop(); };
      cleanup = stop;
    },

    // --- 14. Bhoomiputra Foundation ---
    'bhoomiputra'() {
      const data = [
        ['Coastal programme', [['Sample contribution', '₹500'], ['Sample materials', '−₹200']], 'Community supplies and programme information.'],
        ['Sanitation programme', [['Sample contribution', '₹800'], ['Sample distribution', '−₹300']], 'Programme distribution and local coordination.']
      ];
      area.innerHTML = title('Make the programme inspectable.', 'Select a programme to explore its fictional activity ledger.') +
        layout(
          `${choose('programme', 'Sample programme', data.map(x => x[0]))}<p class="notice">Fictional ledger. No contributions are collected.</p>`,
          `<div class="program"><h2 id="programme-title"></h2><p id="programme-description"></p></div><div id="ledger"></div>`
        );
      const update = () => {
        const d = data[$('#programme').selectedIndex];
        $('#programme-title').textContent = d[0];
        $('#programme-description').textContent = d[2];
        $('#ledger').innerHTML = d[1].map(r => `<div class="feed-row"><span>${r[0]}</span><span>${r[1]}</span></div>`).join('');
      };
      $('#programme').onchange = update;
      update();
    },

    // --- 15. SafeSpot ---
    'safespot'() {
      area.innerHTML = title('Keep the source close to the result.', 'Inspect a fictional example with explicit gaps in the record.') +
        layout(
          `${choose('source', 'Fictional source', ['Example public record', 'Unavailable source', 'Clear session'])}<p class="notice">Alex Example is fictional. No person is searched, scored or evaluated.</p>`,
          `${output()}<div id="source-detail" class="document"></div>`
        );
      const update = () => {
        const i = $('#source').selectedIndex;
        $('#result').textContent = ['Sample record available. This is not an identity match.', 'This source has no available information in the sample.', 'The demonstration record has been cleared.'][i];
        $('#source-detail').innerHTML = i === 0
          ? '<h2>Example record</h2><div class="rule"></div><p>Name: Alex Example<br>Reference: DEMO-001<br>Source: fictional fixture<br>Status: requires interpretation</p>'
          : i === 1 ? '<h2>Information unavailable</h2><p>Absence of information is not a positive or negative finding.</p>'
          : '<h2>Session cleared</h2><p>Select the example record to explore again.</p>';
      };
      $('#source').onchange = update;
      update();
    },

    // --- 16. WESHUB ---
    'weshub'() {
      const flows = [
        ['Brand activation', ['Define the audience', 'Choose the experience', 'Review the project brief']],
        ['Franchise enquiry', ['Choose the market', 'Describe the operating model', 'Review the enquiry']],
        ['AI workflow', ['Describe a repeatable task', 'Identify inputs and outputs', 'Review a sample workflow']]
      ];
      let step = 0;
      area.innerHTML = title('One entrance. A relevant path.', 'Select an interest and follow a short, local enquiry pathway.') +
        layout(
          `${choose('interest', 'Area of interest', flows.map(x => x[0]))}<div class="wrap">${button('step-back', 'Previous', 'quiet')}${button('step-next', 'Next step')}</div>`,
          `<div id="step-track" class="step-track"></div><span class="small" id="step-label"></span><h2 id="step-title"></h2>${output()}`
        );
      const render = () => {
        $('#step-track').innerHTML = [0, 1, 2].map(n => `<span class="${n <= step ? 'done' : ''}"></span>`).join('');
        $('#step-label').textContent = `Step ${step + 1} of 3`;
        $('#step-title').textContent = flows[$('#interest').selectedIndex][1][step];
        $('#result').textContent = step === 2
          ? 'Sample pathway complete. No enquiry has been submitted.'
          : 'The next question follows the selected interest.';
        $('#step-back').disabled = step === 0;
        $('#step-next').disabled = step === 2;
      };
      $('#interest').onchange = () => { step = 0; render(); };
      $('#step-next').onclick = () => { step++; render(); };
      $('#step-back').onclick = () => { step--; render(); };
      render();
    },

    // --- 17. BUKL ---
    'bukl'() {
      area.innerHTML = title('Let the mechanism tell the story.', 'Explore a simplified friction-lock schematic.') +
        layout(
          `<div class="visual"><div id="belt" class="schematic"><div class="buckle"></div></div><span class="visual-caption">Explanatory schematic · not a physical simulation</span></div>`,
          `<label>Illustrative tension<input id="tension" type="range" min="0" max="100" value="15"></label>${output()}<p class="small">The schematic communicates an idea through movement. It does not model material forces or validate a manufactured mechanism.</p>`
        );
      const update = () => {
        const v = Number($('#tension').value);
        $('#belt').style.setProperty('--latch', (35 - v * .3) + 'deg');
        $('#belt').style.transform = `rotate(${-12 + v * .12}deg) scaleX(${1 + v * .001})`;
        $('#result').textContent = v < 50 ? 'Loose state - adjust the sample strap.' : 'Tension state - the schematic latch engages.';
      };
      $('#tension').oninput = update;
      update();
    },

    // --- 18. Solar Solutions ---
    'solar-solutions'() {
      area.innerHTML = title('Show the assumptions with the number.', 'An illustrative calculator with an editable reduction assumption.') +
        layout(
          `${field('bill', 'Sample monthly bill (₹)', 3000, 'number')}<label>Illustrative reduction (%)<input id="reduction" type="range" min="0" max="80" value="30"></label><p class="notice">Simple arithmetic only. Not an energy assessment, quotation or savings guarantee.</p>`,
          `<span class="small">ILLUSTRATIVE MONTHLY DIFFERENCE</span><div class="value" id="saving"></div>${output()}`
        );
      $('#bill').min = 0; $('#bill').max = 100000;
      const update = () => {
        const bill = Math.max(0, Math.min(100000, Number($('#bill').value) || 0));
        const percent = Number($('#reduction').value);
        $('#saving').textContent = '₹' + Math.round(bill * percent / 100).toLocaleString('en-IN');
        $('#result').textContent = `₹${bill.toLocaleString('en-IN')} × ${percent}% assumed reduction. Actual performance requires a site assessment.`;
      };
      $('#bill').oninput = update;
      $('#reduction').oninput = update;
      update();
    },

    // --- 19. Healthy Meals ---
    'healthy-meals'() {
      area.innerHTML = title('Start with the person’s context.', 'Preview a message that follows a selected meal preference.') +
        layout(
          `${choose('persona', 'Sample preference', ['Busy professional', 'High-protein preference', 'Vegetarian preference'])}${choose('frequency', 'Meal frequency', ['Weekdays', 'Three days a week', 'One trial meal'])}${button('compose', 'Preview conversation')}`,
          `${output('Choose a preference and preview the message.')}<p class="small">A local message preview. No WhatsApp account or network request.</p>`
        );
      $('#compose').onclick = () => {
        $('#result').textContent = `Hello! I’m interested in your ${$('#persona').value.toLowerCase()} options for ${$('#frequency').value.toLowerCase()}. Could you share the menu, ingredients and delivery availability?`;
      };
    },

    // --- 20. Zyron Tech (Walkthrough) ---
    'zyron-tech'() {
      const stages = [
        {
          title: 'Stage 1: Merchant Center Disapproval',
          desc: 'Missing mandatory variant attributes and unstructured product titles triggered feed rejection across 48 SKUs.',
          excerpt: 'Google Merchant Center Issue: Invalid product title & missing variant colour values'
        },
        {
          title: 'Stage 2: Title & Feed Restructuring',
          desc: 'Refactored titles into [Brand] + [Core Keyword] + [Variant Attributes] format and unified barcode MPNs.',
          excerpt: 'Feed Rule Applied: Output title format standardized across Google Shopping categories'
        },
        {
          title: 'Stage 3: Shopping Campaign Architecture',
          desc: 'Segmented products into High Margin, Velocity Movers, and Liquidation buckets to control CPC bidding.',
          excerpt: 'Campaign Hierarchy: Tiered budget allocation by inventory velocity'
        }
      ];
      area.innerHTML = title('Google Shopping feed walkthrough.', 'Inspect the diagnostic progression from feed disapproval to segmented structure.') +
        layout(
          `${choose('stage', 'Campaign progression', stages.map(s => s.title))}<div id="stage-detail" class="transcript-box"></div>${output('Select a stage to inspect the feed changes.')}`,
          `<span class="small">ARCHIVED AUDIT EXCERPT</span><div id="excerpt-box" class="document"><p id="excerpt-text"></p></div>`
        );
      const update = () => {
        const s = stages[$('#stage').selectedIndex];
        $('#stage-detail').textContent = s.desc;
        $('#excerpt-text').textContent = s.excerpt;
        $('#result').textContent = `Inspecting ${s.title}. Feed corrections resolved platform compliance.`;
      };
      $('#stage').onchange = update;
      update();
    },

    // --- 21. Luxury Spirits ---
    'luxury-spirits'() {
      const regions = [
        { name: 'Campaign Organisation', val: 'Single-keyword intent ad groups separating corporate gifting from collector editions.' },
        { name: 'Search Term Spend', val: 'High-intent exact match keywords filtered to prevent consumer mass-market queries.' },
        { name: 'Conversion Value', val: 'Tracked verified B2B quote inquiries rather than standard consumer cart adds.' }
      ];
      area.innerHTML = title('Google Ads search intent explorer.', 'Inspect the targeting structure and conversion values of the luxury spirits campaign.') +
        layout(
          `${choose('region', 'Report focus region', regions.map(r => r.name))}${button('inspect-region', 'Inspect metric rationale')}${output('Select a region to analyze.')}`,
          `<div class="preview-card"><span class="tag">Strategy Breakdown</span><h2 id="region-title">Campaign Strategy</h2><p id="region-desc"></p></div>`
        );
      $('#inspect-region').onclick = () => {
        const r = regions[$('#region').selectedIndex];
        $('#region-title').textContent = r.name;
        $('#region-desc').textContent = r.val;
        $('#result').textContent = `Auditing ${r.name}: strategy connects query intent directly to landing page copy.`;
      };
    },

    // --- 22. Zupee ---
    'zupee'() {
      const posts = [
        { type: 'Relatable Hook', note: 'Everyday competitive banter: "The friend who always changes the ludo rules."', cta: 'Download link in bio · Instant play' },
        { type: 'Dialect Comedy', note: 'Authentic local expressions: relatable regional characters highlighting lightning-fast withdrawals.', cta: 'Play live against real players' },
        { type: 'Rapid Challenge', note: 'Direct-to-camera wager format: simple puzzles highlighting skill over luck.', cta: 'Test your reaction speed now' }
      ];
      area.innerHTML = title('Campaign creative archive.', 'Explore sample social content hooks and formats developed for Zupee.') +
        layout(
          `${choose('post', 'Content treatment', posts.map(p => p.type))}${button('switch-post', 'Analyze creative breakdown')}${output('Select a post format.')}`,
          `<div class="preview-card"><span class="tag" id="post-tag">Hook Analysis</span><h2 id="post-title">Creative Framework</h2><p id="post-note"></p><p class="small" id="post-cta"></p></div>`
        );
      const update = () => {
        const p = posts[$('#post').selectedIndex];
        $('#post-tag').textContent = p.type;
        $('#post-title').textContent = p.type;
        $('#post-note').textContent = p.note;
        $('#post-cta').textContent = 'CTA: ' + p.cta;
        $('#result').textContent = `Analyzing ${p.type}: high-retention opening hooks engineered for short-form video.`;
      };
      $('#post').onchange = update;
      $('#switch-post').onclick = update;
      update();
    },

    // --- 23. D2C Fitness ---
    'd2c-fitness'() {
      const angles = [
        { angle: 'Morning Routine', hook: 'Wake up 15 minutes earlier without dreading the gym commute.', format: '15s Reel / Story' },
        { angle: 'Equipment Teardown', hook: 'Why compact home resistance bands fail at the anchor point.', format: '45s Educational Teardown' },
        { angle: 'Social Proof', hook: 'From zero pull-ups to 12 in 90 days: member journey.', format: 'Carousel Testimonial' }
      ];
      area.innerHTML = title('Creative testing framework.', 'Compare audience angles and testing formats across the fitness funnel.') +
        layout(
          `${choose('angle', 'Creative hypothesis', angles.map(a => a.angle))}${output('Select an angle to review test structure.')}`,
          `<div class="preview-card"><span class="tag" id="angle-tag">Test Card</span><h2 id="angle-hook"></h2><p id="angle-format"></p></div>`
        );
      const update = () => {
        const a = angles[$('#angle').selectedIndex];
        $('#angle-tag').textContent = a.angle;
        $('#angle-hook').textContent = a.hook;
        $('#angle-format').textContent = 'Target Format: ' + a.format;
        $('#result').textContent = `Testing hypothesis: "${a.angle}" isolates customer motivation before production spend.`;
      };
      $('#angle').onchange = update;
      update();
    },

    // --- 24. Shopify SaaS ---
    'shopify-saas'() {
      const lessons = [
        { topic: 'Cart Thresholds', detail: 'Why free shipping progress bars must calculate instantly without page reloads.' },
        { topic: 'Variant Clarity', detail: 'How out-of-stock sizes should display without confusing add-to-cart clicks.' },
        { topic: 'Mobile Thumb Zones', detail: 'Placing checkout buttons within the natural one-handed reach zone.' }
      ];
      area.innerHTML = title('E-commerce teardown curriculum.', 'Step through educational lessons developed for merchant storefront design.') +
        layout(
          `${choose('lesson', 'Teardown chapter', lessons.map(l => l.topic))}${output('Select a lesson.')}`,
          `<div class="preview-card"><span class="tag">Merchant Education</span><h2 id="lesson-topic"></h2><p id="lesson-detail"></p></div>`
        );
      const update = () => {
        const l = lessons[$('#lesson').selectedIndex];
        $('#lesson-topic').textContent = l.topic;
        $('#lesson-detail').textContent = l.detail;
        $('#result').textContent = `Lesson active: ${l.topic}. Educational content turns technical teardowns into client authority.`;
      };
      $('#lesson').onchange = update;
      update();
    },

    // --- 25. DealStrike (New #1) ---
    'dealstrike'() {
      const transcripts = [
        {
          lang: 'English recap',
          text: 'Met Rajesh Sharma at Sharma Distributors. Agreed on 50 cases for next month. Need PO signed by Thursday. High interest.',
          deal: '₹2,50,000',
          stage: 'PO Pending',
          task: 'Follow-up Thursday 2 PM',
          contact: 'Rajesh Sharma (Sharma Distributors)'
        },
        {
          lang: 'Hinglish audio',
          text: 'Kalyan Electronics ke saath meeting hui. 30 units display ke liye chahiye. Follow up Friday ko karna hai after 3 PM.',
          deal: '₹1,20,000',
          stage: 'Follow-up Scheduled',
          task: 'Friday after 3:00 PM',
          contact: 'Kalyan Electronics'
        },
        {
          lang: 'Ambiguous Contact',
          text: 'Spoke to Rajesh about the new inventory. Wants sample kit sent tomorrow.',
          deal: '₹45,000',
          stage: 'Sample Request',
          task: 'Send sample kit tomorrow',
          contact: 'Ambiguous: Multiple "Rajesh" in CRM'
        }
      ];

      area.innerHTML = title('Spoken notes to structured pipeline.', 'Select an audio transcript, resolve any contact ambiguity, and apply updates to the CRM.') +
        layout(
          `${choose('trans', 'Select call transcript', transcripts.map(t => t.lang))}
          <div id="trans-text" class="transcript-box"></div>
          <div id="ambiguity-wrap" hidden>
            ${choose('contact-choice', 'Resolve ambiguous contact', ['Rajesh Sharma (Apex Hardware)', 'Rajesh Gupta (Bhopal Electronics)'])}
          </div>
          <div class="wrap">${button('apply-crm', 'Apply updates to pipeline')}</div>
          ${output('Select a transcript to parse.')}`,
          `<span class="small">PROPOSED CRM LEAD UPDATES</span>
          <div class="crm-grid">
            <div class="crm-box"><h4>Deal Value</h4><p id="crm-deal">—</p></div>
            <div class="crm-box"><h4>Pipeline Stage</h4><p id="crm-stage">—</p></div>
            <div class="crm-box"><h4>Next Action</h4><p id="crm-task">—</p></div>
            <div class="crm-box"><h4>Contact</h4><p id="crm-contact">—</p></div>
          </div>
          <div class="rule"></div>
          <div id="pipeline-status" class="preview-card" style="min-height:140px">
            <span class="tag">DealStrike Telemetry</span>
            <h2>Pipeline State</h2>
            <p id="pipe-msg">Waiting for user extraction...</p>
          </div>`
        );

      const update = () => {
        const t = transcripts[$('#trans').selectedIndex];
        $('#trans-text').textContent = `"${t.text}"`;
        const isAmbiguous = t.lang === 'Ambiguous Contact';
        $('#ambiguity-wrap').hidden = !isAmbiguous;
        $('#crm-deal').textContent = t.deal;
        $('#crm-stage').textContent = t.stage;
        $('#crm-task').textContent = t.task;
        $('#crm-contact').textContent = isAmbiguous ? $('#contact-choice').value : t.contact;
        $('#result').textContent = `Parsed ${t.lang} in 0.8s. Review proposed updates before applying.`;
      };

      $('#trans').onchange = update;
      $('#contact-choice').onchange = () => {
        $('#crm-contact').textContent = $('#contact-choice').value;
      };
      $('#apply-crm').onclick = () => {
        const t = transcripts[$('#trans').selectedIndex];
        const contact = t.lang === 'Ambiguous Contact' ? $('#contact-choice').value : t.contact;
        $('#pipe-msg').textContent = `Successfully updated: ${contact} → Stage: ${t.stage} (${t.deal})`;
        $('#result').textContent = `Pipeline synchronized! Updated ${contact} with zero manual typing.`;
      };
      update();
    },

    // --- 26. BillFetch (New #2) ---
    'billfetch'() {
      const receipts = [
        { vendor: 'Bharat Petroleum (Fleet Fuel)', date: '2026-09-18', amount: '₹4,850.00', taxFlag: '12%', correctTax: '18%', category: 'Vehicle & Logistics' },
        { vendor: 'Chroma Electronics (Cables & Hub)', date: '2026-09-22', amount: '₹12,400.00', taxFlag: '5%', correctTax: '18%', category: 'Office Hardware' }
      ];
      area.innerHTML = title('Receipts to verified ledgers.', 'Inspect OCR extraction, correct flagged tax discrepancies, and approve.') +
        layout(
          `${choose('rcpt', 'Sample receipt', receipts.map(r => r.vendor))}
          <div class="document">
            <span class="small">THERMAL RECEIPT PREVIEW</span>
            <h2 id="rcpt-vendor"></h2>
            <p id="rcpt-meta"></p>
            <div class="rule"></div>
            <p>Subtotal: <strong id="rcpt-amt"></strong></p>
            <p>Tax Rate: <span id="rcpt-tax" class="flagged-field"></span> <span class="small">(Flagged: verify GST)</span></p>
          </div>
          ${output('Select a receipt.')}`,
          `<span class="small">VERIFICATION & EDIT</span>
          ${choose('tax-fix', 'Correct GST rate', ['18% (Standard GST)', '12% (Concessional)', '5% (Essential)'])}
          ${button('approve-bill', 'Approve & lock to ledger')}
          <div class="rule"></div>
          <table class="receipt-table">
            <thead><tr><th>Vendor</th><th>Date</th><th>GST</th><th>Total</th><th>Status</th></tr></thead>
            <tbody id="bill-rows">
              <tr><td>BPCL Fleet</td><td>18 Sep</td><td>18%</td><td>₹4,850</td><td><span class="tag">Pending</span></td></tr>
            </tbody>
          </table>`
        );

      const update = () => {
        const r = receipts[$('#rcpt').selectedIndex];
        $('#rcpt-vendor').textContent = r.vendor;
        $('#rcpt-meta').textContent = `Date: ${r.date} · Category: ${r.category}`;
        $('#rcpt-amt').textContent = r.amount;
        $('#rcpt-tax').textContent = r.taxFlag;
        $('#result').textContent = `Flagged tax anomaly on ${r.vendor}: OCR read ${r.taxFlag}. Please verify against GST certificate.`;
      };
      $('#rcpt').onchange = update;
      $('#approve-bill').onclick = () => {
        const r = receipts[$('#rcpt').selectedIndex];
        const fixedTax = $('#tax-fix').value.split(' ')[0];
        $('#rcpt-tax').className = 'good';
        $('#rcpt-tax').textContent = fixedTax;
        $('#bill-rows').innerHTML = `<tr><td>${r.vendor.split(' ')[0]}</td><td>${r.date.slice(5)}</td><td>${fixedTax}</td><td>${r.amount}</td><td><span class="tag" style="border-color:#10b981;color:#10b981">Approved</span></td></tr>`;
        $('#result').textContent = `Approved ${r.vendor} with corrected ${fixedTax} GST credit. Ready for Tally export.`;
      };
      update();
    },

    // --- 27. Phase 1 GTM Tracker (New #3) ---
    'gtm-tracker'() {
      area.innerHTML = title('Outbound telemetry against decision gates.', 'Simulate positive reply volumes to test campaign scale vs kill thresholds.') +
        layout(
          `${field('cohort', 'Cohort size (sent emails)', 250, 'number')}
          ${field('replies', 'Positive replies received', 2, 'number')}
          <p class="notice">Decision Gate Rule: Reply rate >= 3.0% → Scale campaign. Below 3.0% → Kill or rewrite angle.</p>
          ${output()}`,
          `<span class="small">EXPERIMENT SCOREBOARD</span>
          <div class="value" id="reply-rate">0.8%</div>
          <div class="rule"></div>
          <div class="preview-card" id="gate-card">
            <span class="tag" id="gate-tag">GATE EVALUATION</span>
            <h2 id="gate-verdict">KILL / REWRITE</h2>
            <p id="gate-reason">Current sample performance is below the 3.0% significance threshold.</p>
          </div>`
        );
      const update = () => {
        const c = Math.max(1, Number($('#cohort').value) || 250);
        const r = Math.max(0, Number($('#replies').value) || 0);
        const rate = (r / c) * 100;
        $('#reply-rate').textContent = rate.toFixed(1) + '%';
        const pass = rate >= 3.0;
        $('#gate-tag').textContent = pass ? 'THRESHOLD MET' : 'THRESHOLD FAILED';
        $('#gate-verdict').textContent = pass ? 'SCALE CAMPAIGN' : 'KILL / REVISE ANGLE';
        $('#gate-reason').textContent = pass
          ? `${rate.toFixed(1)}% reply rate exceeds 3.0% minimum threshold. Scale to 1,000-lead cohort.`
          : `${rate.toFixed(1)}% reply rate is below the 3.0% threshold. Do not waste further mailbox reputation.`;
        $('#result').textContent = `Cohort: ${c} sends | ${r} positive replies = ${rate.toFixed(1)}% signal rate.`;
      };
      $('#cohort').oninput = update;
      $('#replies').oninput = update;
      update();
    },

    // --- 28. MAG Swimwear (New #4) ---
    'mag-swimwear'() {
      const silhouettes = ['The Asymmetric One-Piece', 'The High-Waist Two-Piece', 'The Sculpted Maillot'];
      const fabrics = ['Matte Terracotta', 'Ribbed Ocean Noir', 'Sage Silk Lycra'];
      area.innerHTML = title('Restraint in luxury resortwear.', 'Select a silhouette and fabric swatch to inspect reservation details.') +
        layout(
          `${choose('sil', 'Silhouette', silhouettes)}${choose('fab', 'Fabric & Colour', fabrics)}${choose('sz', 'Size', ['XS · 32', 'S · 34', 'M · 36', 'L · 38'])}${button('reserve', 'Request 24-hr hold')}
          ${output('Select a garment to review hold details.')}`,
          `<div class="preview-card" style="background:#091a24">
            <span class="tag">MAG ARCHIVE RESERVATION</span>
            <h2 id="mag-name"></h2>
            <p id="mag-fab"></p>
            <div class="rule"></div>
            <p class="small" id="mag-status">Complimentary private courier fitting included with hold.</p>
          </div>`
        );
      const update = () => {
        $('#mag-name').textContent = $('#sil').value;
        $('#mag-fab').textContent = `${$('#fab').value} · Size ${$('#sz').value}`;
        $('#result').textContent = `Selected: ${$('#sil').value} in ${$('#fab').value}. Ready for concierge hold.`;
      };
      $('#sil').onchange = update;
      $('#fab').onchange = update;
      $('#sz').onchange = update;
      $('#reserve').onclick = () => {
        $('#result').textContent = `Hold confirmed for 24 hours: ${$('#sil').value} (${$('#sz').value}). Zero payment required.`;
      };
      update();
    },

    // --- 29. Machhli (New #5) ---
    'machhli'() {
      const items = {
        Swim: ['Kashmiri Print Monokini', 'Azure Blue Wave Bikini', 'Marigold Coral Halter'],
        Resort: ['Goa Sunset Silk Robe', 'Embroidered Linen Kaftan', 'Tiered Resort Trousers']
      };
      area.innerHTML = title('Tactile editorial lookbook.', 'Switch collections and open artisan fit specifications.') +
        layout(
          `<div class="direction-tabs">
            <button type="button" class="direction-tab active" data-col="Swim">Swim Collection</button>
            <button type="button" class="direction-tab" data-col="Resort">Resort Archive</button>
          </div>
          ${choose('look-item', 'Lookbook piece', items.Swim)}
          ${button('fit-guide', 'Open artisan fit & craft notes')}
          ${output('Explore lookbook piece.')}`,
          `<div class="preview-card" style="background:#260e17">
            <span class="tag" id="look-cat">Swim Collection</span>
            <h2 id="look-title"></h2>
            <p id="look-desc">100% regenerated Italian Lycra with hand-blocked coastal motifs.</p>
          </div>`
        );
      let curCol = 'Swim';
      const update = () => {
        const piece = $('#look-item').value;
        $('#look-cat').textContent = curCol + ' Collection';
        $('#look-title').textContent = piece;
        $('#result').textContent = `Viewing ${piece} from Machhli ${curCol} catalogue.`;
      };
      $$('.direction-tab').forEach(b => b.onclick = () => {
        $$('.direction-tab').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        curCol = b.dataset.col;
        $('#look-item').innerHTML = items[curCol].map(x => `<option>${x}</option>`).join('');
        update();
      });
      $('#look-item').onchange = update;
      $('#fit-guide').onclick = () => {
        $('#result').textContent = `Artisan Specs: Crafted with chlorine-resistant Econyl yarn and hand-stitched borders.`;
      };
      update();
    },

    // --- 30. NAKA (New #6) ---
    'naka'() {
      let days = [1, 1, 0, 1, 1, 0, 0]; // 1 = 8hr shift, 0 = off
      area.innerHTML = title('Shift calendar to net earnings.', 'Tap days to toggle shifts and adjust tips to recalculate take-home income.') +
        layout(
          `<span class="small">TAP DAY TO TOGGLE DUTY (MON–SUN)</span>
          <div class="duty-grid" id="duty-grid"></div>
          ${field('rate', 'Hourly wage (₹)', 220, 'number')}
          ${field('tips', 'Weekly cash tips (₹)', 1500, 'number')}
          ${output()}`,
          `<span class="small">PROJECTED TAKE-HOME EARNINGS</span>
          <div class="value" id="net-pay">₹0</div>
          <div class="rule"></div>
          <p id="duty-stats">0 hours logged across 0 shifts.</p>`
        );
      const render = () => {
        const dayNames = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
        $('#duty-grid').innerHTML = days.map((d, i) => `<div class="duty-cell ${d ? 'active' : ''}" data-day="${i}"><strong>${dayNames[i]}</strong><span>${d ? '8h' : 'Off'}</span></div>`).join('');
        const shifts = days.filter(Boolean).length;
        const hours = shifts * 8;
        const rate = Math.max(0, Number($('#rate').value) || 220);
        const tips = Math.max(0, Number($('#tips').value) || 0);
        const total = (hours * rate) + tips;
        $('#net-pay').textContent = '₹' + total.toLocaleString('en-IN');
        $('#duty-stats').textContent = `${shifts} active shifts (${hours} total hours) @ ₹${rate}/hr + ₹${tips.toLocaleString('en-IN')} tips.`;
        $('#result').textContent = `Recalculated: ${shifts} shifts scheduled. Net take-home: ₹${total.toLocaleString('en-IN')}.`;
      };
      $('#duty-grid').onclick = e => {
        const cell = e.target.closest('.duty-cell');
        if (!cell) return;
        const i = +cell.dataset.day;
        days[i] = days[i] ? 0 : 1;
        render();
      };
      $('#rate').oninput = render;
      $('#tips').oninput = render;
      render();
    },

    // --- 31. CODSURE (New #7) ---
    'codsure'() {
      const orders = [
        { id: 'ORD-9821', customer: 'Rahul Sharma · Thane', amt: '₹1,850', score: '88% Risk', reason: 'High Risk: Phone number unverified; address flagged across 3 logistics partners for repeated refusal.', status: 'Held' },
        { id: 'ORD-9822', customer: 'Priya Iyer · Bangalore', amt: '₹3,200', score: '12% Risk', reason: 'Low Risk: Address confirmed, previous pre-paid order delivered successfully.', status: 'Cleared' },
        { id: 'ORD-9823', customer: 'Amit Verma · Patna', amt: '₹950', score: '62% Risk', reason: 'Medium Risk: First-time customer, non-standard postal PIN code syntax.', status: 'Held' }
      ];
      area.innerHTML = title('Stop RTO fraud before dispatch.', 'Inspect held COD orders, review risk reasons, and simulate verification.') +
        layout(
          `${choose('order-sel', 'Flagged order queue', orders.map(o => `${o.id} - ${o.customer}`))}<div class="document"><h2 id="ord-id"></h2><p id="ord-reason"></p><div class="rule"></div><p id="ord-amt"></p></div>
          <div class="wrap">${button('btn-otp', 'Simulate WhatsApp OTP')}${button('btn-cancel', 'Cancel & Save Freight', 'quiet')}</div>
          ${output('Select an order.')}`,
          `<div class="preview-card"><span class="tag" id="ord-tag">Risk Engine</span><h2 id="ord-score"></h2><p id="ord-action">Awaiting verification</p></div>`
        );
      const update = () => {
        const o = orders[$('#order-sel').selectedIndex];
        $('#ord-id').textContent = `${o.id}: ${o.customer}`;
        $('#ord-reason').textContent = o.reason;
        $('#ord-amt').textContent = `Order Value: ${o.amt} · COD Payment`;
        $('#ord-score').textContent = o.score;
        $('#ord-tag').textContent = o.status.toUpperCase();
        $('#result').textContent = `Inspecting ${o.id}: ${o.score}. Verify customer intent before courier pickup.`;
      };
      $('#order-sel').onchange = update;
      $('#btn-otp').onclick = () => {
        const o = orders[$('#order-sel').selectedIndex];
        $('#ord-action').textContent = 'OTP Verified: Customer confirmed delivery on WhatsApp (+91 98201...).';
        $('#result').textContent = `Order ${o.id} confirmed! Address validated for dispatch.`;
      };
      $('#btn-cancel').onclick = () => {
        const o = orders[$('#order-sel').selectedIndex];
        $('#ord-action').textContent = 'Cancelled: Customer failed to confirm. Courier booking aborted.';
        $('#result').textContent = `Saved ₹180 RTO freight fee by intercepting ${o.id}.`;
      };
      update();
    },

    // --- 32. Jawaab Engine (New #8) ---
    'jawaab-engine'() {
      let timeline = [
        { time: '14:02:10', label: 'Missed Call Logged', detail: 'Inbound call from +91 98201... unanswered (mechanic on road)', state: 'done' },
        { time: '14:02:18', label: 'Instant Auto-Response Sent', detail: 'WhatsApp: "Hi! Saw we missed your call. Need car detailing or repair quote?"', state: 'done' },
        { time: '14:17:18', label: 'Scheduled 15-Min Reminder', detail: 'Automated nudge queued to fire if customer does not reply', state: 'pending' }
      ];
      area.innerHTML = title('Missed-call recovery timeline.', 'Trigger a sample missed-call flow, then simulate a customer reply that cancels pending follow-ups.') +
        layout(
          `<div class="wrap">${button('sim-reply', 'Simulate Customer Reply')}${button('reset-time', 'Trigger New Missed Call', 'quiet')}</div>
          <div class="rule"></div>
          <div id="timeline-list"></div>
          ${output('Timeline initialized: instant WhatsApp sent.')}`,
          `<div class="preview-card"><span class="tag">Engine State</span><h2 id="jawaab-status">Lead Engaged</h2><p id="jawaab-detail">Automated follow-up timer running (15m countdown).</p></div>`
        );
      const render = () => {
        $('#timeline-list').innerHTML = timeline.map(t => `<div class="timeline-item"><div class="timeline-dot">${t.state === 'done' ? '✓' : t.state === 'cancelled' ? '✕' : '○'}</div><div class="timeline-content"><h4>${t.label} · <span class="small">${t.time}</span></h4><p>${t.detail}</p></div></div>`).join('');
      };
      $('#sim-reply').onclick = () => {
        timeline[2] = { time: '14:05:32', label: 'Reminder Cancelled', detail: 'Customer replied: "Need quote for ceramic coating". Remaining timers cleared.', state: 'cancelled' };
        $('#jawaab-status').textContent = 'Reply Received';
        $('#jawaab-detail').textContent = 'Lead successfully recovered in 3m 14s. Remaining reminder sequence aborted.';
        $('#result').textContent = 'Customer reply received! Auto-cancellation prevented redundant follow-up messages.';
        render();
      };
      $('#reset-time').onclick = () => {
        timeline[2] = { time: '14:17:18', label: 'Scheduled 15-Min Reminder', detail: 'Automated nudge queued to fire if customer does not reply', state: 'pending' };
        $('#jawaab-status').textContent = 'Lead Engaged';
        $('#jawaab-detail').textContent = 'Automated follow-up timer running (15m countdown).';
        $('#result').textContent = 'New missed-call event logged. Instant auto-response dispatched.';
        render();
      };
      render();
    },

    // --- 33. Service Picker (New #9) ---
    'service-picker'() {
      const plans = {
        'Solo Founder': {
          '< 5 hours': { name: 'Async Forensic Audit', scope: '14-day technical audit & prioritized repair roadmap. Zero meeting overhead.', cost: '$1,000' },
          '10–20 hours': { name: 'Solo Build Sprint', scope: 'Complete 2-week storefront or web app delivery with weekly async reviews.', cost: '$2,500' }
        },
        'Growing Agency': {
          '< 5 hours': { name: 'White-Label Pipeline', scope: 'Automated voice-to-CRM or GTM scrapers deployed directly to client accounts.', cost: '$3,500' },
          '10–20 hours': { name: 'Dedicated Engineering Pod', scope: 'Full-stack technical execution partner for high-ticket client retainers.', cost: '$5,000' }
        }
      };
      area.innerHTML = title('Right-sized commercial scoping.', 'Match your team constraints and capacity to a concrete delivery scope.') +
        layout(
          `${choose('team-role', 'Organization type', ['Solo Founder', 'Growing Agency'])}${choose('team-hrs', 'Weekly time commitment', ['< 5 hours', '10–20 hours'])}${output('Select constraints.')}`,
          `<div class="preview-card"><span class="tag">Recommended Scope</span><h2 id="plan-name"></h2><p id="plan-scope"></p><div class="rule"></div><span class="value" id="plan-cost"></span></div>`
        );
      const update = () => {
        const role = $('#team-role').value, hrs = $('#team-hrs').value;
        const p = plans[role]?.[hrs] || plans['Solo Founder']['< 5 hours'];
        $('#plan-name').textContent = p.name;
        $('#plan-scope').textContent = p.scope;
        $('#plan-cost').textContent = p.cost;
        $('#result').textContent = `Matching scope for ${role} with ${hrs} availability: ${p.name}.`;
      };
      $('#team-role').onchange = update;
      $('#team-hrs').onchange = update;
      update();
    },

    // --- 34. The Message Tree (New #10) ---
    'message-tree'() {
      const branches = [
        {
          objection: '“We already use an all-in-one software (Mindbody / ZenPlanner).”',
          response: '“That software is built for member billing, not sales. When coaches have to fill out 10 form fields, they stop logging notes. What if they could just speak 1 sentence right after a session?”',
          next: 'Ask: “How many trial passes went cold last week because no one followed up?”'
        },
        {
          objection: '“Your price is higher than a generic freelancer.”',
          response: '“A freelancer writes code and hands you an invoice. We build the architecture, audit the database, and verify commercial outcomes. Which part of your project carries the biggest risk?”',
          next: 'Offer: “Let’s scope a small 14-day technical audit first so you can inspect our engineering standards.”'
        },
        {
          objection: '“We don’t have budget for new tech until next quarter.”',
          response: '“Understood. If you’re already bleeding 20% of your checkout conversions to cart latency, waiting 90 days costs more than the sprint. What is your current mobile drop-off rate?”',
          next: 'Action: Send 1-page forensic mobile checkout audit.'
        }
      ];
      area.innerHTML = title('Navigate objections without hesitation.', 'Select an objection to follow the structured conversational response path.') +
        layout(
          `${choose('obj-sel', 'Customer objection', branches.map(b => b.objection))}${output('Select an objection to reveal the response branch.')}`,
          `<div class="preview-card"><span class="tag">Recommended Response</span><h2 id="obj-head" style="font-size:20px;line-height:1.4"></h2><div class="rule"></div><p id="obj-next" style="color:var(--accent)"></p></div>`
        );
      const update = () => {
        const b = branches[$('#obj-sel').selectedIndex];
        $('#obj-head').textContent = b.response;
        $('#obj-next').textContent = 'Next conversational move: ' + b.next;
        $('#result').textContent = `Objection response loaded. Keep the conversation grounded in the prospect's operational pain.`;
      };
      $('#obj-sel').onchange = update;
      update();
    },

    // --- 35. Audit Generator (New #11) ---
    'audit-generator'() {
      area.innerHTML = title('One-page technical forensic audits.', 'Adjust store performance facts to generate an instant diagnostic sheet.') +
        layout(
          `${field('site-url', 'Storefront URL', 'luxury-apparel.com')}${field('speed', 'Mobile PageSpeed score (0–100)', 34, 'number')}${field('apps', 'Third-party app scripts', 22, 'number')}${output()}`,
          `<div class="document"><span class="small">FORENSIC TECHNICAL AUDIT SHEET</span><h2 id="audit-title"></h2><div class="rule"></div><div id="audit-findings"></div><div class="rule"></div><p id="audit-remedy" class="notice"></p></div>`
        );
      const update = () => {
        const url = $('#site-url').value.trim() || 'store.com';
        const s = Math.max(0, Math.min(100, Number($('#speed').value) || 34));
        const a = Math.max(0, Number($('#apps').value) || 22);
        $('#audit-title').textContent = `${url} · Diagnostic Findings`;
        $('#audit-findings').innerHTML = `<p><strong>Mobile Score:</strong> ${s}/100 (${s < 50 ? 'Severe Friction ⚠️' : 'Moderate'})</p><p><strong>Script Bloat:</strong> ${a} external JS tags blocking initial cart render.</p><p><strong>Checkout Latency:</strong> ~${(3.8 + (a * 0.12)).toFixed(1)}s redirect delay on mobile networks.</p>`;
        $('#audit-remedy').textContent = s < 50
          ? 'Recommendation: Quarantine non-essential tracking pixels; load theme drawer as pure Web Component to eliminate 2.4s render blocking.'
          : 'Recommendation: Minor script minification and pre-fetching of checkout assets.';
        $('#result').textContent = `Generated forensic sheet for ${url}: PageSpeed ${s}, ${a} active scripts.`;
      };
      $('#site-url').oninput = update;
      $('#speed').oninput = update;
      $('#apps').oninput = update;
      update();
    },

    // --- 36. 50-Buyer List Builder (New #12) ---
    'buyer-list-builder'() {
      const buyers = [
        { name: 'Dr. Pet Wellness Hub', cat: 'Pet Clinics', city: 'Mumbai', rev: '₹2.4 Cr', verified: true },
        { name: 'Canine Care Hospital', cat: 'Pet Clinics', city: 'Delhi', rev: '₹1.8 Cr', verified: true },
        { name: 'Apex Industrial Fasteners', cat: 'Distributors', city: 'Mumbai', rev: '₹8.5 Cr', verified: true },
        { name: 'Bhopal Agro Supplies', cat: 'Distributors', city: 'Bhopal', rev: '₹4.2 Cr', verified: true },
        { name: 'Metro Healthcare Supplies', cat: 'Medical Supplies', city: 'Delhi', rev: '₹6.1 Cr', verified: true }
      ];
      let shortlist = new Set();
      area.innerHTML = title('Curated B2B prospect search.', 'Filter verified distributor and clinic databases and build a contactable shortlist.') +
        layout(
          `${choose('cat-filter', 'Trade category', ['All Categories', 'Pet Clinics', 'Distributors', 'Medical Supplies'])}${choose('city-filter', 'Region', ['All Cities', 'Mumbai', 'Delhi', 'Bhopal'])}
          <table class="receipt-table">
            <thead><tr><th>Company</th><th>City</th><th>Revenue</th><th>Action</th></tr></thead>
            <tbody id="buyer-rows"></tbody>
          </table>`,
          `<div class="preview-card"><span class="tag">Active Shortlist</span><h2 id="short-count">0 shortlisted</h2><p id="short-names">Click "+ Add" on any record to build your exportable outreach list.</p></div>${output()}`
        );
      const render = () => {
        const c = $('#cat-filter').value, ci = $('#city-filter').value;
        const filtered = buyers.filter(b => (c === 'All Categories' || b.cat === c) && (ci === 'All Cities' || b.city === ci));
        $('#buyer-rows').innerHTML = filtered.map((b, i) => `<tr><td><strong>${b.name}</strong><br><span class="small">${b.cat}</span></td><td>${b.city}</td><td>${b.rev}</td><td><button type="button" class="quiet" data-add="${b.name}">${shortlist.has(b.name) ? '✓ Added' : '+ Add'}</button></td></tr>`).join('');
        $('#short-count').textContent = `${shortlist.size} company records`;
        $('#short-names').textContent = shortlist.size ? Array.from(shortlist).join(', ') : 'No companies added yet.';
        $('#result').textContent = `Showing ${filtered.length} verified trade records. ${shortlist.size} shortlisted.`;
      };
      $('#buyer-rows').onclick = e => {
        const btn = e.target.closest('[data-add]');
        if (!btn) return;
        const name = btn.dataset.add;
        shortlist.has(name) ? shortlist.delete(name) : shortlist.add(name);
        render();
      };
      $('#cat-filter').onchange = render;
      $('#city-filter').onchange = render;
      render();
    },

    // --- 37. Shortlist (New #13) ---
    'shortlist'() {
      area.innerHTML = title('Deterministic resume bullet checks.', 'Rewrite weak, passive resume bullets and watch deterministic linting rules turn green.') +
        layout(
          `<label>Resume bullet text<textarea id="bullet-input" rows="3">Managed the company social media accounts and helped increase audience engagement.</textarea></label>
          <div class="wrap">${button('sample-bullet', 'Use high-impact rewrite')}</div>
          ${output()}`,
          `<span class="small">DETERMINISTIC EVALUATION RULES</span>
          <div class="stack" id="rules-box"></div>`
        );
      const evaluate = () => {
        const text = $('#bullet-input').value.trim();
        const hasNumber = /\d+%?|\d+x|\$\d+|\₹\d+/.test(text);
        const hasActionVerb = /^(Directed|Built|Engineered|Scaled|Generated|Negotiated|Architected|Spearheaded)/i.test(text);
        const noPassive = !/(helped|worked on|assisted|responsible for|participated)/i.test(text);

        const rules = [
          { name: 'Strong Action Verb', pass: hasActionVerb, note: 'Lead with an active, decisive verb (e.g. Directed, Scaled, Engineered).' },
          { name: 'Quantifiable Metric', pass: hasNumber, note: 'Must include explicit numbers, percentages, or revenue figures.' },
          { name: 'Eliminate Passive Fillers', pass: noPassive, note: 'Avoid weak filler words like "helped", "assisted", or "worked on".' }
        ];

        $('#rules-box').innerHTML = rules.map(r => `<div class="rule-check ${r.pass ? 'rule-pass' : 'rule-fail'}"><div class="rule-icon">${r.pass ? '✓' : '✕'}</div><div><strong>${r.name}</strong><p class="small">${r.note}</p></div></div>`).join('');
        const passedAll = rules.every(r => r.pass);
        $('#result').textContent = passedAll ? 'All deterministic checks passed (100/100). High-impact bullet.' : 'Bullet requires revision: missing metrics or passive phrasing.';
      };
      $('#bullet-input').oninput = evaluate;
      $('#sample-bullet').onclick = () => {
        $('#bullet-input').value = 'Scaled B2B outbound campaign generating 42 qualified calls and ₹8.4L in verified pipeline.';
        evaluate();
      };
      evaluate();
    },

    // --- 38. Kirti Couture (New #14) ---
    'kirti-couture'() {
      const directions = [
        { name: 'Maison Kirti', era: 'Contemporary Architectural Couture', fab: 'Silk organza, structured corsetry, monochrome silhouette.', note: 'Minimalist high-fashion editorial direction with crisp typography.' },
        { name: 'Old British Clothes', era: 'Heritage Tailoring & Suiting', fab: 'Hand-woven Yorkshire tweed, horn buttons, Savile Row canvas.', note: 'Vintage Anglo-Indian bespoke tailoring lookbook.' },
        { name: 'Heirloom Archive', era: 'Vintage Zardozi Royal Archive', fab: 'Pure tissue silk, metallic gold bullion embroidery, antique dabka.', note: 'Curated royal preservation catalogue celebrating multi-generational craft.' }
      ];
      area.innerHTML = title('Three visual directions in heirloom luxury.', 'Switch between Maison, Old British tailoring, and the Heirloom archive.') +
        layout(
          `${choose('dir-sel', 'Select design direction', directions.map(d => d.name))}${button('inspect-craft', 'Inspect embroidery & material specs')}${output()}`,
          `<div class="preview-card" style="background:#1a1710;border-color:#d4af3740">
            <span class="tag" style="border-color:#d4af37;color:#d4af37" id="dir-era"></span>
            <h2 id="dir-title" style="color:#f5ebdc"></h2>
            <p id="dir-fab" style="color:#d1c4b2"></p>
            <div class="rule" style="border-color:#ffffff15"></div>
            <p class="small" id="dir-note"></p>
          </div>`
        );
      const update = () => {
        const d = directions[$('#dir-sel').selectedIndex];
        $('#dir-era').textContent = d.era;
        $('#dir-title').textContent = d.name;
        $('#dir-fab').textContent = d.fab;
        $('#dir-note').textContent = d.note;
        $('#result').textContent = `Direction active: ${d.name}. Showcasing ${d.era}.`;
      };
      $('#dir-sel').onchange = update;
      $('#inspect-craft').onclick = () => {
        const d = directions[$('#dir-sel').selectedIndex];
        $('#result').textContent = `Craftsmanship detail: ${d.fab}`;
      };
      update();
    },

    // --- 39. Payments Dashboard Study (New #15) ---
    'payments-dashboard-study'() {
      const txns = [
        { id: 'pay_N9921k', amt: '₹4,500.00', status: 'Captured', method: 'UPI · GooglePay', fee: '₹0.00', time: '14:22:04' },
        { id: 'pay_N9922k', amt: '₹18,000.00', status: 'Captured', method: 'Card · HDFC Visa', fee: '₹360.00', time: '12:15:30' },
        { id: 'pay_N9923k', amt: '₹2,200.00', status: 'Failed', method: 'Netbanking · SBI', fee: '₹0.00', time: '11:08:12' },
        { id: 'pay_N9924k', amt: '₹7,500.00', status: 'Refunded', method: 'UPI · PhonePe', fee: '₹0.00', time: '09:44:21' }
      ];
      area.innerHTML = title('Independent payments interface study.', 'Filter date ranges and transaction states to inspect fee deductions and settlement flows.') +
        layout(
          `${choose('status-filter', 'Transaction status', ['All Transactions', 'Captured', 'Failed', 'Refunded'])}
          <table class="receipt-table">
            <thead><tr><th>Txn ID</th><th>Method</th><th>Gross</th><th>Status</th></tr></thead>
            <tbody id="txn-rows"></tbody>
          </table>`,
          `<div class="preview-card"><span class="tag">Selected Transaction</span><h2 id="txn-head">Click a transaction</h2><p id="txn-detail">Select any row from the ledger to inspect fee breakdown.</p></div>${output()}`
        );
      const render = () => {
        const f = $('#status-filter').value;
        const filtered = txns.filter(t => f === 'All Transactions' || t.status === f);
        $('#txn-rows').innerHTML = filtered.map(t => `<tr data-id="${t.id}" style="cursor:pointer"><td><span class="mono">${t.id}</span></td><td>${t.method.split(' ')[0]}</td><td><strong>${t.amt}</strong></td><td><span class="tag" style="border-color:${t.status === 'Captured' ? '#10b981' : t.status === 'Failed' ? '#f43f5e' : '#eab308'}">${t.status}</span></td></tr>`).join('');
        $('#result').textContent = `Displaying ${filtered.length} transactions (${f}). Independent interface study.`;
      };
      $('#txn-rows').onclick = e => {
        const tr = e.target.closest('tr');
        if (!tr) return;
        const t = txns.find(x => x.id === tr.dataset.id);
        if (!t) return;
        $('#txn-head').textContent = `${t.amt} (${t.status})`;
        $('#txn-detail').innerHTML = `Transaction ID: <span class="mono">${t.id}</span><br>Payment Method: ${t.method}<br>Gateway Fee: ${t.fee}<br>Settlement Time: ${t.time}`;
        $('#result').textContent = `Inspecting ${t.id}: Net settled = ₹${(parseFloat(t.amt.replace(/[₹,]/g, '')) - parseFloat(t.fee.replace(/[₹,]/g, ''))).toLocaleString('en-IN')}`;
      };
      $('#status-filter').onchange = render;
      render();
    },

    // --- 40. DTC Creative OS (New #16) ---
    'dtc-creative-os'() {
      const briefs = {
        'Problem Agitation': { hook: '“If you have to shake your protein bottle for 2 minutes to break clumps, your shaker is broken.”', scenes: ['0-3s: Clumpy powder mess', '3-8s: Mechanism teardown', '8-15s: 1-click smooth drink'], cta: 'Order now with free replacement ball' },
        'Feature Teardown': { hook: '“We put 3 popular shakers in a hydraulic press to test lid leakage.”', scenes: ['0-4s: Pressure test machine', '4-10s: Competitor lid snaps', '10-18s: Our bottle seals shut'], cta: 'Get the spill-proof guarantee' }
      };
      area.innerHTML = title('Rapid ad brief & storyboard generator.', 'Select a messaging angle and format to generate a production-ready ad brief.') +
        layout(
          `${choose('angle-sel', 'Hook strategy', ['Problem Agitation', 'Feature Teardown'])}${choose('format-sel', 'Aspect ratio', ['9:16 Mobile Reel', '1:1 Square Feed'])}${output('Select creative parameters.')}`,
          `<div class="preview-card"><span class="tag" id="brief-tag">Creative Brief</span><h2 id="brief-hook" style="font-size:18px;line-height:1.4"></h2><div class="rule"></div><p id="brief-scenes" class="small"></p><p id="brief-cta" style="color:var(--accent);font-weight:bold"></p></div>`
        );
      const update = () => {
        const a = $('#angle-sel').value, fmt = $('#format-sel').value;
        const b = briefs[a] || briefs['Problem Agitation'];
        $('#brief-tag').textContent = `${a} · ${fmt}`;
        $('#brief-hook').textContent = b.hook;
        $('#brief-scenes').innerHTML = b.scenes.map(s => `• ${s}`).join('<br>');
        $('#brief-cta').textContent = 'CTA: ' + b.cta;
        $('#result').textContent = `Generated storyboard for ${a} (${fmt}). Ready for video editor handover.`;
      };
      $('#angle-sel').onchange = update;
      $('#format-sel').onchange = update;
      update();
    },

    // --- 41. Agency Follow-Up OS (New #17) ---
    'agency-followup-os'() {
      const leads = [
        { name: 'Samantha Yeager', co: 'TRVFIT Flint', stage: 'Follow-up 2 Due', days: 4, msg: 'Saw your TRVFIT setup in Flint - I put together a clean 45-second visual showing how the 1-tap claim flow works on gym floors. Happy to send the preview over.' },
        { name: 'Dave Miller', co: 'Apex Detailing', stage: 'Follow-up 3 Due', days: 7, msg: 'Quick check about your missed call recovery. Did you want to review the sample WhatsApp timeline or should we shelf this for now?' }
      ];
      area.innerHTML = title('Zero-drop prospect follow-up pipeline.', 'Surfaces who needs contact today paired with contextual follow-up copy.') +
        layout(
          `${choose('lead-sel', 'Active prospect', leads.map(l => `${l.name} (${l.co})`))}${button('mark-sent', 'Mark message as sent')}${output()}`,
          `<div class="document"><span class="small" id="lead-stage"></span><h2 id="lead-name"></h2><div class="rule"></div><p id="lead-msg" style="font-style:italic"></p></div>`
        );
      const update = () => {
        const l = leads[$('#lead-sel').selectedIndex];
        $('#lead-stage').textContent = `${l.stage} · Last contact ${l.days} days ago`;
        $('#lead-name').textContent = `${l.name} (${l.co})`;
        $('#lead-msg').textContent = `"${l.msg}"`;
        $('#result').textContent = `Follow-up ready for ${l.name}. 4th-grade reading level, zero buzzword friction.`;
      };
      $('#lead-sel').onchange = update;
      $('#mark-sent').onclick = () => {
        const l = leads[$('#lead-sel').selectedIndex];
        $('#result').textContent = `Follow-up sent to ${l.name}! Next check-in scheduled for 5 days.`;
      };
      update();
    },

    // --- 42. Small Creator Sponsorship OS (New #18) ---
    'creator-sponsorship-os'() {
      const sections = {
        'Media Kit': { head: 'Audience Demographics & Reach', body: '48.2K Subscribers · 6.4% Engagement Rate · Top audience: Software Engineers & Product Designers (India & US).' },
        'Rate Card': { head: 'Sponsorship Packages', body: 'Package A: 60s Dedicated Mid-Roll (₹45,000) · Package B: Integrated Mention + Newsletter (₹25,000).' },
        'Deliverables': { head: 'Production & Tracking Checklist', body: '7-day script approval window, dedicated tracking UTM parameter, 30-day analytics report submission.' }
      };
      area.innerHTML = title('Brand sponsorship pitch kit.', 'Switch between Media Kit, Rate Card, and Deliverables checklist.') +
        layout(
          `${choose('kit-sec', 'Kit section', Object.keys(sections))}${output('Select section.')}`,
          `<div class="preview-card"><span class="tag" id="kit-tag">Pitch Kit</span><h2 id="kit-head"></h2><p id="kit-body"></p></div>`
        );
      const update = () => {
        const s = sections[$('#kit-sec').value];
        $('#kit-tag').textContent = $('#kit-sec').value;
        $('#kit-head').textContent = s.head;
        $('#kit-body').textContent = s.body;
        $('#result').textContent = `Viewing ${$('#kit-sec').value}. Standardized rates protect creator value.`;
      };
      $('#kit-sec').onchange = update;
      update();
    }
  };

  $('#reset').addEventListener('click', init);
  const syncVisibility = () => {
    visible = parentVisible && !document.hidden;
    visibilityHandler();
    document.documentElement.classList.toggle('suspended', !visible);
  };
  window.addEventListener('message', ev => {
    if (ev.source !== parent || ev.data?.channel !== 'mindmaxing-demo' || ev.data.type !== 'visibility' || typeof ev.data.value !== 'boolean') return;
    parentVisible = ev.data.value;
    syncVisibility();
  });
  document.addEventListener('visibilitychange', syncVisibility);
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') send('close', true); });
  new ResizeObserver(height).observe(document.body);
  init();
})();
