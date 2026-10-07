// Public editorial catalogue.
// Named records decoupled from legacy unverified datasets.
// Deliberately excludes unsubstantiated revenue, ROAS, and performance figures.

export const categories = {
  commerce: 'Commerce',
  interactive: 'Interactive experiences',
  motion: '3D Motion & Animation',
  software: 'Software',
  growth: 'Marketing & growth'
};

export const rawProjects = [
  // --- 1. Knittire ---
  {
    slug: 'knittire-3d',
    title: 'Knittire',
    category: 'interactive',
    heading: 'A garment. Every possibility.',
    summary: 'A material configurator that makes a complex product easy to explore.',
    contribution: 'Storefront architecture & interactive product experience',
    instruction: 'Change the fabric. Turn the garment.',
    problem: 'Product choices are difficult to explain through static swatches alone. A useful configuration experience needs to connect the visible garment to a clear set of selections.',
    approach: 'Keep material, view and configuration summary in one state model. The demonstration uses an explicitly identified procedural 3D garment; production models and manufacturing integrations are separate.',
    tradeoff: 'A lightweight demonstration loads quickly, but cannot reproduce the physical drape of a real textile.',
    disciplines: 'materials / interaction / configuration',
    accent: '#b3d9c5',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'reconstruction', source: 'Procedural WebGL garment configuration study' }
  },

  // --- 2. Saffron Origins ---
  {
    slug: 'saffron-origins',
    title: 'Saffron Origins',
    category: 'commerce',
    heading: 'Culture, carried into commerce.',
    summary: 'An apparel storefront with product choices that stay clear from selection to cart.',
    contribution: 'Storefront design & engineering',
    instruction: 'Choose a colour. Find your fit.',
    problem: 'Apparel shoppers need to understand the selected size, colour and quantity before adding a product to their cart.',
    approach: 'Keep product options and the cart summary in the same state model. The reconstruction uses a sample tee and shows unavailable combinations as an explicit state.',
    tradeoff: 'The current public store sells apparel. This demonstration uses sample inventory; production availability must be checked against Shopify.',
    disciplines: 'commerce / product options / cart',
    accent: '#db9d64',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://saffronorigins.com',
    evidence: { type: 'production', source: 'Production Shopify storefront architecture' }
  },

  // --- 3. ABX Engine ---
  {
    slug: 'abx-engine',
    title: 'ABX Engine',
    category: 'software',
    heading: 'Small experiments. Clear decisions.',
    summary: 'A look inside consistent visitor assignment for storefront experiments.',
    contribution: 'Product architecture & experiment tooling',
    instruction: 'Try a visitor ID. Then try it again.',
    problem: 'An experiment becomes difficult to interpret when a returning visitor sees a different variant unexpectedly.',
    approach: 'Derive a stable assignment from a visitor identifier and show the assigned treatment. This small reconstruction demonstrates allocation, not a production analytics service.',
    tradeoff: 'Stable allocation alone does not establish statistical significance or experiment validity.',
    disciplines: 'allocation / state / experimentation',
    accent: '#aabce4',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://abx-liard.vercel.app',
    evidence: { type: 'prototype', source: 'Deterministic hash-bucket test utility' }
  },

  // --- 4. WhatsApp Autopilot ---
  {
    slug: 'whatsapp-autopilot',
    title: 'WhatsApp Autopilot',
    category: 'software',
    heading: 'The right message. Once.',
    summary: 'An event-driven notification workflow, made visible.',
    contribution: 'Automation design & workflow engineering',
    instruction: 'Run an event. Test a retry.',
    problem: 'Notifications need to survive temporary failures without sending the same message twice.',
    approach: 'Separate event receipt, scheduling and delivery state. A sample event identifier makes repeated submissions identifiable; retrying a failed step resumes the demonstration.',
    tradeoff: 'A local simulation cannot reproduce provider limits or delivery guarantees. No messages leave this demo.',
    disciplines: 'events / retries / deduplication',
    accent: '#9dcdb6',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'reconstruction', source: 'Idempotent webhook queue simulation' }
  },

  // --- 5. Glaze ---
  {
    slug: 'glaze',
    title: 'Glaze',
    category: 'software',
    heading: 'A little space for honest feedback.',
    summary: 'A simple feedback interface built around a shareable identity.',
    contribution: 'Product design & web application engineering',
    instruction: 'Leave a sample note.',
    problem: 'A feedback tool should get out of the way between a person sharing a link and someone leaving a response.',
    approach: 'Keep input, validation and the resulting feed close together. The demonstration maintains fictional feedback only for the current session.',
    tradeoff: 'Anonymous input requires abuse controls in production. This sandbox is not a public collection service.',
    disciplines: 'forms / state / feedback',
    accent: '#c2abd7',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://getglaze.in',
    evidence: { type: 'production', source: 'Public web application deployment' }
  },

  // --- 6. Before Token ---
  {
    slug: 'before-token',
    title: 'Before Token',
    category: 'software',
    heading: 'Read between the documents.',
    summary: 'A document comparison workflow that makes discrepancies easier to inspect.',
    contribution: 'Document workflow & interface engineering',
    instruction: 'Compare two sample records.',
    problem: 'Marketing material and source records can describe the same project differently. A reviewer needs to see the source of each difference.',
    approach: 'Present fields side by side and flag discrepancies without concealing the original values. The sandbox uses fixed, fictional documents.',
    tradeoff: 'A field mismatch is a reason to investigate, not a legal conclusion. No regulatory database is queried here.',
    disciplines: 'documents / comparison / provenance',
    accent: '#b4c3d3',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://before-token.vercel.app',
    evidence: { type: 'prototype', source: 'Property specification comparison interface' }
  },

  // --- 7. Manifest ---
  {
    slug: 'manifest',
    title: 'Manifest',
    category: 'commerce',
    heading: 'An offer that stays understandable.',
    summary: 'Offer selection and order summaries in a focused purchase journey.',
    contribution: 'Landing-page & purchase-flow engineering',
    instruction: 'Switch the sample offer.',
    problem: 'Changing bundles can make it difficult to understand what is included and how the total changes.',
    approach: 'Keep the selected offer and its itemised summary in sync. The demonstration updates local sample amounts without entering a payment flow.',
    tradeoff: 'Production pricing must be validated by the commerce backend. Browser totals are not a payment authority.',
    disciplines: 'offers / totals / purchase flow',
    accent: '#d5b38d',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'reconstruction', source: 'Direct-response single-product purchase flow' }
  },

  // --- 8. Shopify CRO ---
  {
    slug: 'shopify-cro',
    title: 'Storefront interactions',
    category: 'commerce',
    heading: 'The details between browse and buy.',
    summary: 'A focused exploration of cart quantities and shipping thresholds.',
    contribution: 'Storefront interaction engineering',
    instruction: 'Change the cart quantity.',
    problem: 'Cart interactions should explain quantity, cost and shipping changes without making shoppers reconstruct the calculation.',
    approach: 'Derive the total and shipping progress from the same cart state. Keep the user in context when an item changes.',
    tradeoff: 'The sandbox uses fixed sample prices. Production inventory, taxes and shipping rules belong to the store backend.',
    disciplines: 'cart / derived state / feedback',
    accent: '#d6b291',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'reconstruction', source: 'Progressive cart drawer threshold logic' }
  },

  // --- 9. Xalt Watches ---
  {
    slug: 'xalt-watches',
    title: 'Xalt Watches',
    category: 'commerce',
    heading: 'Closer to the detail.',
    summary: 'Product inspection and bidirectional layouts for a watch storefront.',
    contribution: 'Commerce interface & localisation',
    instruction: 'Explore the dial. Switch direction.',
    problem: 'A detail-led product needs room for inspection; a multilingual store also needs a layout that respects reading direction.',
    approach: 'Demonstrate product zoom and direction-aware interface positioning as independent controls. The sample dial is illustrative.',
    tradeoff: 'A layout-direction switch is not a complete translation or localisation audit.',
    disciplines: 'product detail / zoom / RTL',
    accent: '#d1c29e',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'reconstruction', source: 'Bilingual luxury horology storefront prototype' }
  },

  // --- 10. Zyron Tech (Marketing) ---
  {
    slug: 'zyron-tech',
    title: 'Zyron Tech',
    category: 'growth',
    heading: 'Make the product feed legible.',
    summary: 'A guided look at product-feed review and Shopping campaign structure.',
    contribution: 'Google Shopping feed architecture & campaign strategy',
    instruction: 'Inspect a sample feed entry.',
    problem: 'Incomplete product specifications and unstructured titles trigger Google Merchant Center disapprovals and drain Shopping ad efficiency.',
    approach: 'Restructure variant attributes, standardise titles, and segment product feeds by margin and inventory velocity.',
    tradeoff: 'These illustrative checks demonstrate methodology. Actual platform eligibility requires Google Merchant Center audit.',
    disciplines: 'feed architecture / google shopping / merchant center',
    accent: '#aebedb',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign walkthrough · sample data',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Google Merchant Center feed resolution records' }
  },

  // --- 11. Luxury Spirits (Marketing) ---
  {
    slug: 'luxury-spirits',
    title: 'Luxury Spirits',
    category: 'growth',
    heading: 'Different intent. Different message.',
    summary: 'A comparison of product messaging for distinct buying situations.',
    contribution: 'Google Ads search architecture & copy strategy',
    instruction: 'Switch the buying occasion.',
    problem: 'A collector seeking rare bottles and a corporate procurement officer purchasing bulk gifts require completely distinct value propositions.',
    approach: 'Pair each search intent with tailored ad copy, dedicated landing pages, and targeted conversion actions.',
    tradeoff: 'Copy comparisons demonstrate strategic thinking, not verified conversion metrics or profit figures.',
    disciplines: 'intent segmentation / search copy / landing pages',
    accent: '#ca9e82',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign creative archive',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Google Ads campaign search term breakdown' }
  },

  // --- 12. Zupee (Marketing) ---
  {
    slug: 'zupee',
    title: 'Zupee',
    category: 'growth',
    heading: 'Make the idea worth stopping for.',
    summary: 'An interactive breakdown of short-form content approaches.',
    contribution: 'Social creative strategy & campaign production',
    instruction: 'Compare two content treatments.',
    problem: 'Product announcements often fail to engage audiences unless anchored to relatable cultural references and tight opening hooks.',
    approach: 'Develop high-retention short-form scripts, meme formats, and character-driven gaming scenarios for mobile feeds.',
    tradeoff: 'Sample concepts are explanatory reconstructions and static frames. No video streaming or live engagement metrics.',
    disciplines: 'creative strategy / cultural hooks / short-form',
    accent: '#d5c48d',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign creative archive',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Organic social campaign creative assets' }
  },

  // --- 13. D2C Fitness (Marketing) ---
  {
    slug: 'd2c-fitness',
    title: 'D2C Fitness',
    category: 'growth',
    heading: 'One product. Several ways in.',
    summary: 'Creative approaches organised by the question a customer is asking.',
    contribution: 'Creative testing matrix & performance copy',
    instruction: 'Choose a creative angle.',
    problem: 'Highlighting product specifications alone fails to convert customers across varied fitness levels and living spaces.',
    approach: 'Systematically test pain-point hooks against routine-based messaging and visual teardowns.',
    tradeoff: 'The demonstration illustrates messaging strategy and makes no medical, fitness, or conversion claims.',
    disciplines: 'creative testing / copy angles / audience context',
    accent: '#b9c89e',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign creative archive',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Meta performance ad creative frameworks' }
  },

  // --- 14. Solar Solutions (Marketing) ---
  {
    slug: 'solar-solutions',
    title: 'Solar Solutions',
    category: 'growth',
    heading: 'Make the calculation tangible.',
    summary: 'An illustrative savings calculator inside a lead journey.',
    contribution: 'Meta campaign strategy & lead qualification funnel',
    instruction: 'Adjust the sample inputs.',
    problem: 'High-ticket residential solar purchases stall when homeowners find savings estimates opaque or confusing.',
    approach: 'Build an interactive estimation flow directly into the ad destination to qualify homeowner roof viability and power consumption.',
    tradeoff: 'Simple arithmetic only. Not an engineering site survey, formal quotation, or solar power guarantee.',
    disciplines: 'meta campaigns / calculator funnel / qualification',
    accent: '#d7c89b',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign walkthrough · sample data',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Meta lead generation campaign flows' }
  },

  // --- 15. Healthy Meals (Marketing) ---
  {
    slug: 'healthy-meals',
    title: 'Healthy Meals',
    category: 'growth',
    heading: 'A more relevant first conversation.',
    summary: 'A persona-led message builder for a meal-service journey.',
    contribution: 'Persona segmentation & WhatsApp onboarding copy',
    instruction: 'Choose a meal preference.',
    problem: 'Meal subscription services experience high drop-off when prospective subscribers receive generic dietary menus.',
    approach: 'Route incoming inquiries to persona-specific meal previews based on dietary restrictions and delivery frequency.',
    tradeoff: 'Interactive preview only. Does not dispatch live WhatsApp messages or provide nutritional advice.',
    disciplines: 'personas / onboarding flow / messaging copy',
    accent: '#9bbf9b',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign creative archive',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'Subscription brand onboarding journeys' }
  },

  // --- 16. Shopify SaaS (Marketing) ---
  {
    slug: 'shopify-saas',
    title: 'Shopify education',
    category: 'growth',
    heading: 'Turn a teardown into a useful lesson.',
    summary: 'An interactive walkthrough of a storefront education concept.',
    contribution: 'Content design & technical teardown publishing',
    instruction: 'Step through the teardown.',
    problem: 'E-commerce merchants tune out theoretical design advice unless observations are tied to concrete storefront details.',
    approach: 'Produce annotated visual teardowns breaking down checkout friction, mobile ergonomics, and cart velocity.',
    tradeoff: 'Illustrative educational teardown demonstrating editorial style rather than measured merchant results.',
    disciplines: 'editorial design / teardowns / educational content',
    accent: '#abc5bb',
    caseStudyType: 'marketing',
    showcaseMode: 'Campaign creative archive',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'campaign_archive', source: 'E-commerce technical advisory graphics' }
  },

  // --- 17. BUKL (Marketing / Product Storytelling) ---
  {
    slug: 'bukl',
    title: 'BUKL',
    category: 'growth',
    heading: 'Understand it through movement.',
    summary: 'A product explanation for a friction-lock belt.',
    contribution: 'Product storytelling & launch campaign creative',
    instruction: 'Explore the product mechanism.',
    problem: 'An unfamiliar mechanical belt closure is hard to explain through static photos alone without customer confusion.',
    approach: 'Combine interactive tension schematics with product narrative to highlight durability and effortless adjustment.',
    tradeoff: 'The schematic is an explanatory model, not a manufacturing CAD file or physical simulation.',
    disciplines: 'product narrative / launch creative / interactive',
    accent: '#bdb5a0',
    caseStudyType: 'marketing',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio collaboration',
    liveUrl: null,
    evidence: { type: 'production', source: 'Direct-to-consumer product launch materials' }
  },

  // --- 18. Janus ---
  {
    slug: 'janus',
    title: 'Janus',
    category: 'software',
    heading: 'Keep the next action visible.',
    summary: 'A content-production workspace with visible queues and review states.',
    contribution: 'Workflow architecture & application engineering',
    instruction: 'Move a sample job through the queue.',
    problem: 'Content production teams get bottlenecked when asset generation, caption approval, and publishing states blur together.',
    approach: 'Design an explicit job pipeline where media moves strictly from queued to in-progress to approved.',
    tradeoff: 'Client-side simulation. Does not connect to live Instagram or TikTok APIs.',
    disciplines: 'queues / state machines / content ops',
    accent: '#a6b6cf',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://saas-instagram-dm-automations-three.vercel.app',
    evidence: { type: 'production', source: 'Janus AI content automation platform' }
  },

  // --- 19. SafeSpot ---
  {
    slug: 'safespot',
    title: 'SafeSpot',
    category: 'software',
    heading: 'Show the source. Keep the context.',
    summary: 'A fictional-record interface for inspecting information and its limitations.',
    contribution: 'Research workflow & product interface',
    instruction: 'Explore a fictional record.',
    problem: 'Aggregated safety databases often present confidence scores while obscuring missing or unverified source records.',
    approach: 'Expose explicit provenance tags and gap disclosures directly alongside person and location entities.',
    tradeoff: 'All records are synthetic fixtures. SafeSpot does not query government databases or evaluate real individuals.',
    disciplines: 'data provenance / research / disclosure',
    accent: '#b8b9d5',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'prototype', source: 'Compliance entity verification interface' }
  },

  // --- 20. Hisaab ---
  {
    slug: 'hisaab',
    title: 'Hisaab',
    category: 'software',
    heading: 'From questions to a structured draft.',
    summary: 'A guided questionnaire and sample document preview.',
    contribution: 'Questionnaire & document workflow engineering',
    instruction: 'Complete a sample questionnaire.',
    problem: 'Small business owners struggle to draft formal commercial notices without expensive preliminary consultation.',
    approach: 'Structure intake into simple multi-step questions and compile responses into clean, standardized document previews.',
    tradeoff: 'Sample draft generator only. Not legal advice and does not produce court-admissible pleadings.',
    disciplines: 'intake flows / document assembly / form logic',
    accent: '#c9bfa8',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://hisaab-lilac-rho.vercel.app',
    evidence: { type: 'production', source: 'Commercial notice drafting utility' }
  },

  // --- 21. Bhoomiputra Foundation ---
  {
    slug: 'bhoomiputra',
    title: 'Bhoomiputra Foundation',
    category: 'software',
    heading: 'Give the work a visible home.',
    summary: 'A programme-led community platform and sample contribution ledger.',
    contribution: 'Community platform design & engineering',
    instruction: 'Explore a programme and sample ledger.',
    problem: 'Grassroots community foundations need transparent expenditure records to build enduring donor trust.',
    approach: 'Organise grassroots initiatives into inspectable programme ledgers with line-item disbursement breakdowns.',
    tradeoff: 'Demonstration transactions are synthetic. No real donations or payments are processed.',
    disciplines: 'community ledgers / civic tech / transparency',
    accent: '#adbfa6',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'production', source: 'Community foundation portal and ledger' }
  },

  // --- 22. Freedoms AI ---
  {
    slug: 'freedoms-ai',
    title: 'Freedoms AI',
    category: 'software',
    heading: 'A thought becomes a next step.',
    summary: 'A guided example of organising a voice note into actionable information.',
    contribution: 'Product interface & automation workflow',
    instruction: 'Turn a sample transcript into tasks.',
    problem: 'Spoken voice memos often mix random stream-of-consciousness thoughts with genuine time-sensitive commitments.',
    approach: 'Filter conversational noise to extract structured action items and deadlines into an actionable checklist.',
    tradeoff: 'Prepared sample extracts only. No live Whisper or OpenAI speech model queries.',
    disciplines: 'voice extraction / task breakdown / mobile UX',
    accent: '#b8aed0',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'prototype', source: 'Voice transcript parsing workflow' }
  },

  // --- 23. WESHUB ---
  {
    slug: 'weshub',
    title: 'WESHUB',
    category: 'interactive',
    heading: 'Different ventures. One clear entrance.',
    summary: 'A guided interface across a multi-venture platform.',
    contribution: 'Web experience & workflow design',
    instruction: 'Follow a sample enquiry path.',
    problem: 'Corporate holding platforms confuse visitors when diverse services are lumped together without guided routing.',
    approach: 'Present an interactive branch selector that routes inquiries directly to the relevant operating division.',
    tradeoff: 'Interactive preview only. Stops at sample confirmation without CRM submission.',
    disciplines: 'guided navigation / routing / multi-brand',
    accent: '#aebbd2',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'production', source: 'Multi-venture enterprise hub portal' }
  },

  // --- 24. Pause ---
  {
    slug: 'pause',
    title: 'Pause',
    category: 'software',
    heading: 'A moment before the next tap.',
    summary: 'A browser interpretation of a deliberate pause interaction.',
    contribution: 'Android product & interaction engineering',
    instruction: 'Start a short breathing interval.',
    problem: 'Compulsive phone habits occur before the prefrontal cortex can register deliberate intentionality.',
    approach: 'Introduce a deliberate, visual pacing breath before opening selected applications.',
    tradeoff: 'Browser animation only. Does not demonstrate native Android Accessibility Service interception.',
    disciplines: 'behavioral design / Android / pacing',
    accent: '#c6b2a5',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: null,
    evidence: { type: 'production', source: 'Android digital wellness application' }
  },

  // --- 25. DealStrike (New #1) ---
  {
    slug: 'dealstrike',
    title: 'DealStrike',
    category: 'software',
    heading: 'Voice to CRM on the road.',
    summary: 'A voice intelligence CRM built for field sales reps and Indian B2B distributor networks.',
    contribution: 'Product architecture, voice-to-CRM pipeline & mobile frontend',
    instruction: 'Choose a voice transcript. Inspect and apply CRM updates.',
    problem: 'B2B field sales reps talk on the phone all day but despise filling out 15 form fields on a laptop CRM. Notes get lost, follow-ups slip, and founders remain blind.',
    approach: 'Parse English and Hinglish phone recordings to extract deal values, pipeline stage updates, and next actions with zero manual typing.',
    tradeoff: 'Demonstration runs deterministic extraction on sample transcripts. No live microphone or proprietary telephony API connected.',
    disciplines: 'voice CRM / Hinglish NLP / field sales',
    accent: '#10b981',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://trydealstrike.com',
    evidence: { type: 'production', source: 'Production landing page and mobile web app' }
  },

  // --- 26. BillFetch (New #2) ---
  {
    slug: 'billfetch',
    title: 'BillFetch',
    category: 'software',
    heading: 'Receipts to clean ledgers.',
    summary: 'Automated receipt parsing, vendor categorization, and tax expense extraction for Indian businesses.',
    contribution: 'OCR data pipeline, verification UI & document reconciliation',
    instruction: 'Select a receipt. Correct flagged fields and approve.',
    problem: 'Small business owners drown in physical thermal receipts and WhatsApp bills. Manual data entry produces accounting errors and missed GST input tax credits.',
    approach: 'Pair thermal receipt OCR with an editable verification table that flags ambiguous tax and total fields for 1-click human sign-off.',
    tradeoff: 'Runs against synthetic sample invoices and receipts. Does not connect to live Tally or Zoho Books APIs.',
    disciplines: 'OCR extraction / GST bookkeeping / document UI',
    accent: '#84cc16',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://trybillfetch.com',
    evidence: { type: 'production', source: 'Production landing page and accounting pipeline' }
  },

  // --- 27. Phase 1 GTM Tracker (New #3) ---
  {
    slug: 'gtm-tracker',
    title: 'Phase 1 GTM Tracker',
    category: 'software',
    heading: 'Outbound signals against real thresholds.',
    summary: 'A disciplined B2B outbound campaign experiment scoreboard with explicit decision gates.',
    contribution: 'GTM dashboard engineering & hypothesis tracking logic',
    instruction: 'Adjust reply numbers. Compare with decision thresholds.',
    problem: 'Founders burn cash on cold outreach by changing copy daily without statistical thresholds, mistaking noise for market signals.',
    approach: 'Track cohort volumes, positive reply rates, and pipeline generation against explicit kill-or-scale decision rules.',
    tradeoff: 'Fictional campaign numbers. Private operational data and client email logs remain excluded.',
    disciplines: 'GTM telemetry / decision models / B2B data',
    accent: '#6366f1',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://phase-1-gtm-tracker.vercel.app',
    evidence: { type: 'production', source: 'Deployed GTM experimental tracking dashboard' }
  },

  // --- 28. MAG Swimwear (New #4) ---
  {
    slug: 'mag-swimwear',
    title: 'MAG Swimwear',
    category: 'commerce',
    heading: 'Restraint in luxury resortwear.',
    summary: 'An architectural storefront and private reservation experience for high-end swimwear.',
    contribution: 'Storefront engineering, product photography layout & reservation state',
    instruction: 'Select a silhouette and fabric. View reservation summary.',
    problem: 'Luxury resortwear demands spacious editorial pacing without the noisy clutter of mass-market e-commerce discounts.',
    approach: 'Combine full-bleed imagery, typography, and an interactive size/swatch reservation summary that protects brand prestige.',
    tradeoff: 'Reservation simulation only. No live merchant payment gateway is processed.',
    disciplines: 'luxury commerce / editorial layout / reservation flow',
    accent: '#0284c7',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://mag-eta.vercel.app',
    evidence: { type: 'production', source: 'Deployed luxury swimwear storefront' }
  },

  // --- 29. Machhli (New #5) ---
  {
    slug: 'machhli',
    title: 'Machhli',
    category: 'commerce',
    heading: 'Vibrant coastal editorial lookbook.',
    summary: 'A colourful, tactile digital catalogue and fit guide for contemporary resort collections.',
    contribution: 'Editorial web design, responsive lookbook & catalogue architecture',
    instruction: 'Toggle between collections. Inspect garment details.',
    problem: 'Boutique fashion labels struggle when standard e-commerce templates drain their print collections of character and story.',
    approach: 'Build an interactive lookbook that transitions smoothly between Swim and Resort lines with integrated fit context.',
    tradeoff: 'Catalogue and lookbook study. Direct checkout and inventory feeds are mocked.',
    disciplines: 'lookbook design / responsive editorial / apparel UI',
    accent: '#f43f5e',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://machhli.vercel.app',
    evidence: { type: 'production', source: 'Deployed contemporary resortwear catalogue' }
  },

  // --- 30. NAKA (New #6) ---
  {
    slug: 'naka',
    title: 'NAKA',
    category: 'software',
    heading: 'Shift hours to take-home earnings.',
    summary: 'A mobile duty calendar and income calculator designed for hospitality and gig shift workers.',
    contribution: 'Mobile web application, calendar logic & earnings arithmetic',
    instruction: 'Toggle shift duties and tips. View net earnings update.',
    problem: 'Shift workers juggle split shifts, variable hourly rates, and cash tips across multiple venues with zero reliable income visibility.',
    approach: 'Create a dead-simple, 1-tap mobile duty calendar that instantly tallies hours, overtime, and tip distributions.',
    tradeoff: 'Local arithmetic demonstration. No employer payroll integration or tax liability computation.',
    disciplines: 'shift scheduling / mobile app / earnings logic',
    accent: '#eab308',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://naka-theta.vercel.app',
    evidence: { type: 'production', source: 'Deployed mobile duty and earnings tracker' }
  },

  // --- 31. CODSURE (New #7) ---
  {
    slug: 'codsure',
    title: 'CODSURE',
    category: 'software',
    heading: 'Stop RTO fraud before dispatch.',
    summary: 'A Cash-on-Delivery risk engine and order verification workflow for Indian direct-to-consumer brands.',
    contribution: 'Risk decision rules, verification queue & merchant dashboard',
    instruction: 'Inspect a flagged order. Simulate verification or cancellation.',
    problem: 'Return-to-Origin (RTO) shipping fees kill Indian e-commerce margins when fake or impulsive COD orders are dispatched blindly.',
    approach: 'Score incoming orders against historical address validity and buyer patterns, holding suspicious shipments for automated verification.',
    tradeoff: 'Demonstration uses synthetic order fixtures. Live courier NDR and logistics APIs remain disconnected.',
    disciplines: 'fraud scoring / COD verification / merchant ops',
    accent: '#f97316',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://codsure.vercel.app',
    evidence: { type: 'production', source: 'Deployed COD verification platform' }
  },

  // --- 32. Jawaab Engine (New #8) ---
  {
    slug: 'jawaab-engine',
    title: 'Jawaab Engine',
    category: 'software',
    heading: 'Never lose a missed phone enquiry.',
    summary: 'A missed-call auto-responder and conversation recovery timeline for Indian service businesses.',
    contribution: 'State machine architecture, timeline UI & webhook recovery',
    instruction: 'Trigger a missed call. Advance time or simulate a customer reply.',
    problem: 'Local service businesses miss up to 40% of inbound customer calls when busy on the job, losing high-intent leads to competitors.',
    approach: 'Instantly fire a contextual WhatsApp message upon a missed call, maintaining a cancelable reminder timeline until the prospect replies.',
    tradeoff: 'Simulated telephony timeline. No live Twilio, Exotel, or Meta WhatsApp Business API tokens.',
    disciplines: 'telephony hooks / auto-response / state cancellation',
    accent: '#22c55e',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://whatsapp-jawaab.vercel.app',
    evidence: { type: 'production', source: 'Deployed missed-call WhatsApp workflow' }
  },

  // --- 33. Service Picker (New #9) ---
  {
    slug: 'service-picker',
    title: 'Service Picker',
    category: 'software',
    heading: 'Right-sized service intake.',
    summary: 'A guided commercial intake wizard that matches client team size and constraints to clear delivery scopes.',
    contribution: 'Intake flow engineering, recommendation logic & scope breakdown',
    instruction: 'Select team role and available hours. Inspect recommended plan.',
    problem: 'Agencies waste dozens of hours on discovery calls with early-stage founders who cannot afford or manage an enterprise sprint.',
    approach: 'A 2-step decision wizard that assesses founder capacity and outputs an appropriate scope with transparent trade-offs.',
    tradeoff: 'Client-side recommendation model. Does not submit proposals or process retainer contracts.',
    disciplines: 'guided intake / decision trees / commercial scoping',
    accent: '#8b5cf6',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://service-picker.vercel.app',
    evidence: { type: 'production', source: 'Deployed client scoping wizard' }
  },

  // --- 34. The Message Tree (New #10) ---
  {
    slug: 'message-tree',
    title: 'The Message Tree',
    category: 'software',
    heading: 'Navigate objections without hesitation.',
    summary: 'A visual branching sales conversation map and objection-handling training tool for SDRs.',
    contribution: 'Tree navigation UI, graph state & sales copy structuring',
    instruction: 'Select an objection. Follow the branch to the next response.',
    problem: 'Junior sales reps freeze when prospects raise pricing, timing, or competitor objections, losing deal momentum.',
    approach: 'Organise battle-tested objection responses into an interactive visual node tree with clear conversational branches.',
    tradeoff: 'Interactive reference map. Does not record live sales audio or evaluate spoken speech.',
    disciplines: 'graph navigation / sales training / objection mapping',
    accent: '#38bdf8',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://message-tree-app.vercel.app',
    evidence: { type: 'production', source: 'Deployed conversation tree application' }
  },

  // --- 35. Audit Generator (New #11) ---
  {
    slug: 'audit-generator',
    title: 'Audit Generator',
    category: 'software',
    heading: 'One-page technical forensic audits.',
    summary: 'A technical storefront audit generator that compiles page speed, cart bloat, and script latency into actionable sheets.',
    contribution: 'Automated audit engine, diagnostic scoring & report layout',
    instruction: 'Modify store metrics. Inspect the generated audit score.',
    problem: 'Generic agency audit decks are bloated 40-page PDF fluff that merchants never read and engineers cannot action.',
    approach: 'Condense performance, script latency, and cart friction into a single dense, factual 1-page diagnostic sheet.',
    tradeoff: 'Interactive demonstration based on sample store facts. Live Chrome Lighthouse API calls are mocked.',
    disciplines: 'performance diagnostics / report layout / CRO auditing',
    accent: '#ec4899',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://audit-generator-saas.vercel.app',
    evidence: { type: 'production', source: 'Deployed technical audit generator platform' }
  },

  // --- 36. 50-Buyer List Builder (New #12) ---
  {
    slug: 'buyer-list-builder',
    title: '50-Buyer List Builder',
    category: 'software',
    heading: 'Curated prospect discovery.',
    summary: 'A targeted B2B prospect search and shortlist utility for specialized regional distributor databases.',
    contribution: 'Search filter architecture, table performance & shortlist state',
    instruction: 'Filter by trade category and region. Add records to shortlist.',
    problem: 'Sales teams waste hours scraping unverified directory trash instead of contacting verified, active trade buyers.',
    approach: 'Provide instant categorical and geographic filtering over structured trade datasets with 1-click list building.',
    tradeoff: 'Operates over synthetic directory fixtures. No background scraping or live Hunter email verification.',
    disciplines: 'data filtering / list building / B2B prospecting',
    accent: '#14b8a6',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://list-builder-app.vercel.app',
    evidence: { type: 'production', source: 'Deployed distributor database builder' }
  },

  // --- 37. Shortlist (New #13) ---
  {
    slug: 'shortlist',
    title: 'Shortlist',
    category: 'software',
    heading: 'Deterministic resume bullet evaluation.',
    summary: 'An automated resume rule checker that catches passive verbs, missing metrics, and vague claims.',
    contribution: 'Deterministic linting rules, interactive editor & scoring UI',
    instruction: 'Rewrite a weak resume bullet. Watch the rule re-evaluate.',
    problem: 'Job seekers write fluffy, passive bullets like "managed marketing" that get ignored by hiring managers.',
    approach: 'Run deterministic regex and action-verb checks that demand explicit numbers, business impact, and active phrasing.',
    tradeoff: 'Rule-based deterministic linting. Makes no subjective hiring guarantees or ATS ranking promises.',
    disciplines: 'resume linting / deterministic rules / interactive feedback',
    accent: '#a855f7',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://shortlist-sable-zeta.vercel.app',
    evidence: { type: 'production', source: 'Deployed resume optimization platform' }
  },

  // --- 38. Kirti Couture (New #14 - Grouped 4 Deployments) ---
  {
    slug: 'kirti-couture',
    title: 'Kirti Couture',
    category: 'commerce',
    heading: 'Three visual directions in heirloom luxury.',
    summary: 'A unified luxury showcase uniting Maison Kirti, Old British heritage tailoring, and the Heirloom archive.',
    contribution: 'Multi-theme storefront architecture, heritage lookbook & archival UI',
    instruction: 'Switch between the 3 design directions. Inspect garment craft.',
    problem: 'A heritage couture house with bespoke, archival, and bridal lines needed distinct visual vocabularies without fracturing brand equity.',
    approach: 'Unite three design explorations (Maison modernism, Old British tailoring, and Heirloom cataloguing) into one interactive archive.',
    tradeoff: 'Interactive design study. E-commerce purchasing and custom bespoke booking remain in private preview.',
    disciplines: 'luxury couture / multi-theme architecture / fashion archive',
    accent: '#d4af37',
    caseStudyType: 'engineering',
    showcaseMode: 'Interface study',
    status: 'Studio project',
    liveUrl: 'https://maison-kriti.vercel.app',
    evidence: { type: 'production', source: 'Four deployed fashion storefront variations' }
  },

  // --- 39. Payments Dashboard Study (New #15) ---
  {
    slug: 'payments-dashboard-study',
    title: 'Payments Dashboard',
    category: 'software',
    heading: 'Independent payments interface study.',
    summary: 'A dense, keyboard-accessible payment transaction ledger and settlement inspector.',
    contribution: 'Financial UI architecture, date-range filtering & modal states',
    instruction: 'Filter transactions by date and status. Inspect payment details.',
    problem: 'Financial merchant dashboards often suffer from laggy tables, obscure status codes, and difficult reconciliation flows.',
    approach: 'Build a high-density, low-latency transaction ledger with instant status filtering and clean fee transparency.',
    tradeoff: 'Independent interface study inspired by Razorpay. Not an official Razorpay product or client engagement.',
    disciplines: 'fintech UI / transaction tables / financial reconciliation',
    accent: '#0ea5e9',
    caseStudyType: 'engineering',
    showcaseMode: 'Interface study',
    status: 'Studio project',
    liveUrl: 'https://razorpay-vercel-five.vercel.app',
    evidence: { type: 'prototype', source: 'Independent fintech transaction dashboard' }
  },

  // --- 40. DTC Creative OS (New #16) ---
  {
    slug: 'dtc-creative-os',
    title: 'DTC Creative OS',
    category: 'interactive',
    heading: 'Rapid ad brief and storyboard kit.',
    summary: 'A modular creative system for generating high-converting direct-to-consumer ad briefs and visual storyboards.',
    contribution: 'Creative system design, storyboard UI & angle generation',
    instruction: 'Choose an angle and video format. View storyboard breakdown.',
    problem: 'Growth teams waste days briefing video editors with vague instructions, resulting in off-brand, un-engaging creatives.',
    approach: 'Standardize creative briefs into concrete hook angles, visual scene requirements, and on-screen caption storyboards.',
    tradeoff: 'Client-side brief generation template. Does not run automated video rendering pipelines.',
    disciplines: 'creative brief / storyboards / direct response',
    accent: '#f59e0b',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://focused-tesla.vercel.app',
    evidence: { type: 'production', source: 'Deployed DTC creative brief system' }
  },

  // --- 41. Agency Follow-Up OS (New #17) ---
  {
    slug: 'agency-followup-os',
    title: 'Agency Follow-Up OS',
    category: 'software',
    heading: 'Zero-drop prospect follow-up pipeline.',
    summary: 'A lightweight, zero-bloat sales follow-up tracker designed for boutique agencies.',
    contribution: 'Pipeline UI, date scheduling & copy templating',
    instruction: 'Set follow-up dates. Inspect suggested message copy.',
    problem: 'Agencies lose 60% of interested leads simply because founders forget to send the third and fourth follow-up message.',
    approach: 'A streamlined queue that surfaces exactly who needs contact today, paired with contextual, pre-written follow-up templates.',
    tradeoff: 'Private beta prototype. Operates in local browser storage without sending live emails.',
    disciplines: 'sales pipeline / follow-up automation / agency ops',
    accent: '#06b6d4',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://agency-followup-os.vercel.app',
    evidence: { type: 'production', source: 'Deployed agency follow-up workflow' }
  },

  // --- 42. Small Creator Sponsorship OS (New #18) ---
  {
    slug: 'creator-sponsorship-os',
    title: 'Creator Sponsorship OS',
    category: 'software',
    heading: 'Brand sponsorship pitch kits.',
    summary: 'A professional media kit, rate card, and deliverable manager for independent creators.',
    contribution: 'Media kit design, rate calculators & deliverable checklists',
    instruction: 'Switch between Media Kit, Pitch Deck, and Deliverables.',
    problem: 'Niche creators undercharge or lose brand deals because their media kits look amateurish or lack clear deliverable specs.',
    approach: 'Package audience demographics, engagement ratios, and clear bundle tiers into an executive brand-facing kit.',
    tradeoff: 'Interactive template preview. Does not pull live YouTube/Instagram metrics or guarantee brand deals.',
    disciplines: 'creator economy / media kit / rate negotiation',
    accent: '#84cc16',
    caseStudyType: 'engineering',
    showcaseMode: 'Interactive reconstruction · sample data',
    status: 'Studio project',
    liveUrl: 'https://small-creator-sponsorship-os.vercel.app',
    evidence: { type: 'production', source: 'Deployed creator sponsorship media kit platform' }
  },

  // --- 43. Fevicol Bonding Tweet ---
  {
    slug: 'fevicol-bonding-tweet',
    title: 'Fevicol · The Bonding Tweet',
    category: 'motion',
    heading: 'When a tycoon tweets, a legacy brand responds.',
    summary: 'Topical commercial motion film turning Harsh Goenka’s viral bonding tweet into an iconic brand moment.',
    contribution: 'Rahul Saranya · Motion Direction & 2D/3D Animation',
    instruction: 'Watch the topical brand response film.',
    problem: 'Harsh Goenka tweeted a provocative question to millions: "What is better for bonding - fevicol or alcohol?" Fevicol needed a swift, witty, high-production animated social film before the cultural news cycle shifted.',
    approach: 'Crafted kinetic typography, floating social engagement reactions, and the signature Pidilite elephant iconography to deliver the punchline: "Depends on whether you want to bond for an evening or for life!"',
    tradeoff: 'Topical humor requires fast turnaround over complex 3D simulations. Kinetic 2.5D staging ensured the response shipped within hours of the original tweet.',
    disciplines: 'topical advertising / kinetic typography / motion graphics',
    accent: '#3b82f6',
    caseStudyType: 'motion',
    aspectRatio: '16:9',
    formatLabel: '16:9 Widescreen Film',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/fevicol-bonding-tweet.mp4',
    poster: '/assets/motion/fevicol-bonding-tweet.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Topical broadcast social campaign' }
  },

  // --- 44. Britannia Coffee Cracker ---
  {
    slug: 'britannia-coffee-cracker',
    title: 'Britannia · First Coffee Cracker',
    category: 'motion',
    heading: 'Karan Johar x Coffee Cracker: celebrity energy in motion.',
    summary: 'Commercial launch film and campaign case study introducing India’s first coffee cracker with pop-art motion design.',
    contribution: 'Rahul Saranya · Motion Graphics & Visual Direction',
    instruction: 'Watch the commercial launch film.',
    problem: 'Launching an entirely new snack category (coffee crackers) requires high-voltage visual identity that breaks standard FMCG biscuit advertising cliches.',
    approach: 'Combined Karan Johar celebrity footage with bold pop-art graphic overlays, coffee swirl visual effects, and kinetic typography that establishes "India’s First Coffee Cracker" across digital and broadcast channels.',
    tradeoff: 'Celebrity visual pacing must feel editorial rather than traditional TVC. High-tempo cut transitions and vibrant color blocking keep viewer retention high.',
    disciplines: 'commercial campaign / celebrity motion / broadcast graphics',
    accent: '#ea580c',
    caseStudyType: 'motion',
    aspectRatio: '16:9',
    formatLabel: '16:9 Widescreen Film',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/britannia-coffee-cracker.mp4',
    poster: '/assets/motion/britannia-coffee-cracker.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'National launch campaign film' }
  },

  // --- 45. MotoGP Bharat Racing ---
  {
    slug: 'motogp-bharat-racing',
    title: 'MotoGP Bharat · Wild Ride',
    category: 'motion',
    heading: 'Cockpit POV at 300 km/h: racing velocity on screen.',
    summary: 'High-octane commercial teaser for MotoGP Bharat on BookMyShow, simulating cockpit perspective and electric racetrack speed.',
    contribution: 'Rahul Saranya · 3D Motion Design & VFX',
    instruction: 'Watch the high-speed teaser.',
    problem: 'Promoting premier international motorcycle racing in India demanded visceral adrenaline that makes viewers feel the raw physics of MotoGP.',
    approach: 'Modeled a first-person cockpit camera view with dynamic asphalt blur, reactive lightning VFX, digital speedometer telemetry, and high-impact typographic locks: "GET READY FOR A WILD RIDE."',
    tradeoff: 'POV racing simulation required aggressive camera shake and motion blur, tuned precisely so text remains readable at mobile viewport speeds.',
    disciplines: '3D simulation / sports marketing / motion teaser',
    accent: '#10b981',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Teaser',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/motogp-bharat-racing.mp4',
    poster: '/assets/motion/motogp-bharat-racing.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'MotoGP Bharat digital launch teaser' }
  },

  // --- 46. ITC Fiama Charcoal Gel Bar ---
  {
    slug: 'fiama-charcoal-gel-bar',
    title: 'ITC Fiama · Charcoal Gel Bar',
    category: 'motion',
    heading: 'Activated charcoal in cinematic 3D space.',
    summary: 'Sensory 3D product commercial showcasing the texture, translucency, and grapefruit freshness of the Fiama gel bar.',
    contribution: 'Rahul Saranya · 3D Product Animation & Lighting',
    instruction: 'Watch the 3D product visual.',
    problem: 'Soap and gel bar commercials struggle to convey skin feel and cleansing power without looking generic.',
    approach: 'Constructed an atmospheric dark-slate studio setting with 3D product rendering, subsurface scattering, ambient charcoal smoke, and floating citrus accents to highlight body, face, and hair versatility.',
    tradeoff: 'Photorealistic gel bar lighting required precise refractive shaders to capture the glitter particulate inside the bar without slowing render times.',
    disciplines: '3D product visualization / CGI / look development',
    accent: '#64748b',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Visual',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/fiama-charcoal-gel-bar.mp4',
    poster: '/assets/motion/fiama-charcoal-gel-bar.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'ITC Fiama commercial product visual' }
  },

  // --- 47. Cuticura Original Bloom ---
  {
    slug: 'cuticura-original-bloom',
    title: 'Cuticura · Original Bloom',
    category: 'motion',
    heading: 'Floral botanical elegance in slow motion.',
    summary: 'Product-centric 3D motion reel highlighting botanical freshness, chamomile petals, and sunlit studio staging.',
    contribution: 'Rahul Saranya · 3D Motion & Visual Direction',
    instruction: 'Watch the vertical commercial reel.',
    problem: 'Personal care talc packaging needs to look modern, refreshing, and premium on vertical social feeds.',
    approach: 'Designed warm studio lighting with floating daisy and chamomile botanical elements in zero-gravity orbit around the bottle, synchronizing bottle rotation with typographic claims.',
    tradeoff: 'Petal physics had to feel organic and gentle rather than aggressive, requiring custom particle turbulence fields.',
    disciplines: 'commercial reel / botanical 3D / social campaign',
    accent: '#f59e0b',
    caseStudyType: 'motion',
    aspectRatio: '9:16',
    formatLabel: '9:16 Vertical Reel',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/cuticura-original-bloom.mp4',
    poster: '/assets/motion/cuticura-original-bloom.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Cuticura product reel' }
  },

  // --- 48. Paw Patrol India Launch ---
  {
    slug: 'paw-patrol-india-launch',
    title: 'Paw Patrol · The Mighty Movie',
    category: 'motion',
    heading: 'Nickelodeon superhero pups over Indian skies.',
    summary: 'Official character motion graphics and promotional pre-buzz animation for the theatrical release in India.',
    contribution: 'Rahul Saranya · Character Motion & Compositing',
    instruction: 'Watch the theatrical promo.',
    problem: 'Introducing global Nickelodeon character properties to Indian family audiences for BookMyShow theatrical booking.',
    approach: 'Composited official Paramount and Spin Master 3D character badge shields (Chase, Skye, Marshall, Rubble, Rocky, Zuma) into iconic Indian landmark backdrops with cinematic lens flares and sound design.',
    tradeoff: 'Strict brand guidelines on character likeness meant focusing on badge transition dynamics and dynamic camera zooms rather than altering character rigs.',
    disciplines: 'character motion / entertainment marketing / compositing',
    accent: '#3b82f6',
    caseStudyType: 'motion',
    aspectRatio: '9:16',
    formatLabel: '9:16 Vertical Reel',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/paw-patrol-india-launch.mp4',
    poster: '/assets/motion/paw-patrol-india-launch.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Theatrical release promotional animation' }
  },

  // --- 49. Akasa Air Destinations ---
  {
    slug: 'akasa-air-destinations',
    title: 'Akasa Air · Bucket List Flight',
    category: 'motion',
    heading: 'Wanderlust in motion: flying to Agartala.',
    summary: 'Kinetic travel reel for Akasa Air highlighting northeast Indian destinations with bespoke brand motion transitions.',
    contribution: 'Rahul Saranya · Motion Design & Reel Direction',
    instruction: 'Watch the travel reel.',
    problem: 'Airlines often use generic stock flight footage that fails to build brand recognition for newly opened regional flight routes.',
    approach: 'Created an illustrative travel diary aesthetic incorporating Akasa’s iconic orange-and-purple swoosh curves, custom vector stamps, and landmark reveals featuring Agartala’s Ujjayanta Palace.',
    tradeoff: 'Blends documentary photography with vector motion accents, balancing brand identity against destination beauty.',
    disciplines: 'airline branding / kinetic reel / travel design',
    accent: '#f97316',
    caseStudyType: 'motion',
    aspectRatio: '9:16',
    formatLabel: '9:16 Vertical Reel',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/akasa-air-destinations.mp4',
    poster: '/assets/motion/akasa-air-destinations.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Akasa Air destination campaign' }
  },

  // --- 50. Garnier Men AcnoFight ---
  {
    slug: 'garnier-men-acnofight',
    title: 'Garnier Men · AcnoFight Flash',
    category: 'motion',
    heading: 'Lightning speed: germ elimination in a flash.',
    summary: 'High-energy electrical VFX animation demonstrating deep-cleansing speed for Garnier Men AcnoFight.',
    contribution: 'Rahul Saranya · Motion Graphics & Visual Effects',
    instruction: 'Watch the VFX social spot.',
    problem: 'Men’s grooming digital ads require immediate 1-second hooks to prevent scroll-past on social feeds.',
    approach: 'Engineered high-voltage neon electrical arc simulations, dynamic floor crack displacement, and fast-paced graphic speed lines to dramatize rapid germ defense.',
    tradeoff: 'Intense VFX can overpower product readability. Framed product pack in high-contrast rim lighting to maintain brand salience throughout the explosion.',
    disciplines: 'VFX / electrical simulation / grooming commercial',
    accent: '#84cc16',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Visual',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/garnier-men-acnofight.mp4',
    poster: '/assets/motion/garnier-men-acnofight.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Garnier Men commercial spot' }
  },

  // --- 51. Cuticura Diana Perfume ---
  {
    slug: 'cuticura-diana-perfume',
    title: 'Cuticura Diana · Smart Perfume',
    category: 'motion',
    heading: 'Sensory blue orchid bloom in 3D.',
    summary: 'Commercial perfume visualization featuring blue orchids, atmospheric morning light, and micro-particle burst effects.',
    contribution: 'Rahul Saranya · 3D Product Staging & Animation',
    instruction: 'Watch the 3D fragrance showcase.',
    problem: 'Body perfumes rely heavily on invisible sensory qualities that must be translated visually on screen.',
    approach: 'Surrounded the 3D Cuticura Diana perfume can with blossoming royal blue orchids, soft cloud fog, and swirling mist particles that visually communicate the "Smart Perfume Burst" formula.',
    tradeoff: 'Color palette needed strict restraint to stay cool and ethereal while keeping the metallic blue cap punchy.',
    disciplines: '3D fragrance visualization / particle simulation / cosmetic CGI',
    accent: '#2563eb',
    caseStudyType: 'motion',
    aspectRatio: '9:16',
    formatLabel: '9:16 Vertical Reel',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/cuticura-diana-perfume.mp4',
    poster: '/assets/motion/cuticura-diana-perfume.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Cuticura Diana fragrance launch' }
  },

  // --- 52. Cuticura Lavender Mist ---
  {
    slug: 'cuticura-lavender-mist',
    title: 'Cuticura · Lavender Mist',
    category: 'motion',
    heading: 'Deep velvet purple: lavender freshness in motion.',
    summary: 'Lush social animation capturing the lavender fragrance profile with floating floral botanical bursts.',
    contribution: 'Rahul Saranya · Motion Graphics & Product Animation',
    instruction: 'Watch the lavender animation.',
    problem: 'Talc advertising can feel old-fashioned without modern motion styling and vibrant color harmony.',
    approach: 'Staged the lavender bottle against an intense ultraviolet ambient glow, animating floating blossoms, sunscreen benefit highlights, and glittering powder mist.',
    tradeoff: 'Optimized as an ultra-smooth looping asset for social feed autoplay.',
    disciplines: 'social advertising / botanical loop / product animation',
    accent: '#8b5cf6',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Visual',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/cuticura-lavender-mist.mp4',
    poster: '/assets/motion/cuticura-lavender-mist.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Cuticura social animation' }
  },

  // --- 53. Park Avenue Misty Trail ---
  {
    slug: 'park-avenue-misty-trail',
    title: 'Park Avenue · Misty Trail',
    category: 'motion',
    heading: 'Unlock the forest freshness.',
    summary: 'Commercial product spot for Raymond’s Park Avenue Naturel collection featuring mist vortexes and lighting accents.',
    contribution: 'Rahul Saranya · 3D Motion & Lighting',
    instruction: 'Watch the deodorant commercial.',
    problem: 'Communicating pure natural essential oils in an aerosol deodorant without losing masculine premium appeal.',
    approach: 'Created an icy forest atmosphere with swirling volumetric mist, metallic foil shaders on the bottle typography, and golden particle sparkles reflecting essential oil purity.',
    tradeoff: 'Focused camera orbit on the embossed Naturel badge to anchor commercial credibility.',
    disciplines: '3D cosmetic rendering / particle effects / brand advertising',
    accent: '#0284c7',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Visual',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/park-avenue-misty-trail.mp4',
    poster: '/assets/motion/park-avenue-misty-trail.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Park Avenue commercial spot' }
  },

  // --- 54. Britannia Smiles End Slate ---
  {
    slug: 'britannia-smiles-end-slate',
    title: 'Britannia · Smiles TVC End Slate',
    category: 'motion',
    heading: 'Good Day, Bourbon & Jim Jam: national TVC end slate.',
    summary: 'Stop-motion style 3D biscuit physics and kinetic typography for Britannia’s flagship national television campaign.',
    contribution: 'Rahul Saranya · Broadcast Motion Graphics',
    instruction: 'Watch the TVC end slate.',
    problem: 'TVC end slates have exactly 3 to 4 seconds to resolve brand identity and display multiple product SKUs without clutter.',
    approach: 'Modeled playful 3D rotating biscuits (Bourbon, Good Day, Little Hearts, Jim Jam) around kinetic "BRITANNIA SMILES" typography with cheerful pop-art accents.',
    tradeoff: 'Precision timing required every biscuit to land on its exact beat to synchronize with the iconic Britannia sonic mnemonic.',
    disciplines: 'broadcast design / TVC end slate / 3D product motion',
    accent: '#f43f5e',
    caseStudyType: 'motion',
    aspectRatio: '16:9',
    formatLabel: '16:9 TVC End Slate',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/britannia-smiles-end-slate.mp4',
    poster: '/assets/motion/britannia-smiles-end-slate.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'National television broadcast end slate' }
  },

  // --- 55. Britannia Gifting End Slate ---
  {
    slug: 'britannia-gifting-end-slate',
    title: 'Britannia · No Better Gift',
    category: 'motion',
    heading: 'Festive biscuit gifting: 3D typography and confection motion.',
    summary: 'National festival television commercial end slate celebrating festive gifting with volumetric extruded letterforms.',
    contribution: 'Rahul Saranya · 3D Motion Typography',
    instruction: 'Watch the festive TVC slate.',
    problem: 'Festive campaigns require warmth, celebration, and premium packaging presentation under tight broadcast timing.',
    approach: 'Rendered volumetric 3D extruded "NO BETTER GIFT" typography with striped drop shadows and joyful orbiting biscuits in warm pastel confectionery tones.',
    tradeoff: 'Kept typography bold and central so broadcast TV viewing on small screens remains legible.',
    disciplines: '3D typography / broadcast motion / festive advertising',
    accent: '#f472b6',
    caseStudyType: 'motion',
    aspectRatio: '16:9',
    formatLabel: '16:9 Festive TVC Slate',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/britannia-gifting-end-slate.mp4',
    poster: '/assets/motion/britannia-gifting-end-slate.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Festive television broadcast end slate' }
  },

  // --- 56. Britannia Bourbon Qatar ---
  {
    slug: 'britannia-bourbon-qatar',
    title: 'Britannia Bourbon · Road to Qatar',
    category: 'motion',
    heading: 'Football fever meets chocolate biscuits.',
    summary: 'Case study motion graphic documentation for the Britannia Bourbon Football Contest sending winning teams to Qatar.',
    contribution: 'Rahul Saranya · Motion Graphics & Case Study Design',
    instruction: 'Watch the campaign case study.',
    problem: 'Documenting a complex multi-city on-ground and digital consumer activation for marketing industry award submissions.',
    approach: 'Structured fast-paced screen motion combining contest mechanics, stadium graphics, winner celebrations, and on-pack QR promotions into a concise narrative.',
    tradeoff: 'Balances consumer enthusiasm with marketing metrics, keeping pacing dynamic throughout.',
    disciplines: 'case study film / sports activation / brand motion',
    accent: '#9333ea',
    caseStudyType: 'motion',
    aspectRatio: '16:9',
    formatLabel: '16:9 Award Case Study',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/britannia-bourbon-qatar.mp4',
    poster: '/assets/motion/britannia-bourbon-qatar.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'Industry award case study film' }
  },

  // --- 57. RISE Global MBA Promo ---
  {
    slug: 'rise-gmba-promo',
    title: 'RISE · Global MBA Explainer',
    category: 'motion',
    heading: 'Modern executive education in crisp vector motion.',
    summary: 'Educational promotional film translating executive curriculum, global networking, and career mobility into kinetic design.',
    contribution: 'Rahul Saranya · Motion Design & Art Direction',
    instruction: 'Watch the course promotional film.',
    problem: 'Higher education promo videos frequently rely on dry slide lectures or cheesy stock corporate footage.',
    approach: 'Built a clean, contemporary motion design system with flat-vector geometric transitions, rotating 3D globes, and clear typographic pacing for career milestones.',
    tradeoff: 'Prioritized informational clarity and sophisticated pacing over flashy distraction.',
    disciplines: 'explainer animation / edtech marketing / vector motion',
    accent: '#3b82f6',
    caseStudyType: 'motion',
    aspectRatio: '1:1',
    formatLabel: '1:1 Square Visual',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/rise-gmba-promo.mp4',
    poster: '/assets/motion/rise-gmba-promo.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'EdTech executive course promo' }
  },

  // --- 58. RIO Heavy Flow Animation ---
  {
    slug: 'rio-heavy-flow-animation',
    title: 'RIO · Heavy Flow Empathy',
    category: 'motion',
    heading: 'Breaking taboos with warm character animation.',
    summary: 'Empathetic 2D character animation addressing heavy flow and period cramps with warmth, humor, and dignity.',
    contribution: 'Rahul Saranya · 2D Character Animation & Motion',
    instruction: 'Watch the 2D character film.',
    problem: 'Feminine hygiene advertising has historically used clinical blue liquid and sterile tropes that fail to reflect the real physical pain and fatigue women experience.',
    approach: 'Developed relatable 2D character animation illustrating the physical exhaustion of period cramps through an affectionate pink elephant metaphor, creating an honest dialogue about heavy flow pads.',
    tradeoff: 'Character design required careful emotional nuance so humor feels supportive rather than flippant.',
    disciplines: '2D character animation / empathy-led advertising / social film',
    accent: '#e11d48',
    caseStudyType: 'motion',
    aspectRatio: '9:16',
    formatLabel: '9:16 Vertical Reel',
    showcaseMode: 'Commercial motion · Final render',
    status: 'Commercial client work',
    videoSrc: '/assets/motion/rio-heavy-flow-animation.mp4',
    poster: '/assets/motion/rio-heavy-flow-animation.jpg',
    liveUrl: null,
    evidence: { type: 'commercial', source: 'RIO social character animation campaign' }
  }
];

export const projects = rawProjects.map((p, i) => ({
  ...p,
  number: String(i + 1).padStart(2, '0'),
  publicationStatus: 'published',
  demo: `/demos/index.html?project=${p.slug}`,
  socialImage: p.caseStudyType === 'motion' ? p.poster : `/assets/social/${p.slug}.jpg`
}));

// Engineering showcase row for the homepage
export const featuredEngineering = ['dealstrike', 'billfetch', 'knittire-3d'].map(slug =>
  projects.find(p => p.slug === slug)
);

// Motion & 3D animation showcase row for the homepage
export const featuredMotion = ['fevicol-bonding-tweet', 'britannia-coffee-cracker', 'motogp-bharat-racing'].map(slug =>
  projects.find(p => p.slug === slug)
);

// Marketing showcase row for the homepage
export const featuredMarketing = ['zupee', 'zyron-tech', 'bukl'].map(slug =>
  projects.find(p => p.slug === slug)
);

// Legacy featured array compatibility
export const featured = featuredEngineering;

