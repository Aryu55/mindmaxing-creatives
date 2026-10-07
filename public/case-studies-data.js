export const CASE_STUDIES = [
  // -------------------------------------------------------------
  // SECTION 1: SHOPIFY DTC, CUSTOM CRO & 3D WEBGL STORES
  // -------------------------------------------------------------
  {
    slug: "saffron-origins",
    num: "01 / Client DTC",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live Store",
    title: "Saffron Origins",
    tagline: "Pure Kashmiri luxury storefront engineered with native Liquid purity verification, batch origin tracing, and zero third-party app bloat.",
    heroMetrics: [
      { val: "1.1s", lbl: "Mobile LCP", sub: "Down from 4.6s baseline", accent: true },
      { val: "+28%", lbl: "Mobile CVR Lift", sub: "Cold traffic checkout lift", accent: false },
      { val: "-$250/mo", lbl: "App Fees Saved", sub: "100% native Liquid architecture", accent: false }
    ],
    pitch: "Pure Kashmiri luxury storefront engineered with native Liquid purity verification, batch origin tracing, and zero third-party app bloat.",
    problem: "High-ticket luxury saffron buyers face deep skepticism regarding adulteration and authenticity. The previous theme was bloated with 9 separate third-party Shopify apps (reviews, upsells, trust badges, batch certificates), inflating mobile page load to 4.6 seconds on 4G networks and causing a 68% mobile drop-off rate on cold traffic.",
    solution: "Stripped out every single recurring app subscription. Hand-coded custom Shopify Liquid templates with an interactive laboratory purity verification engine where customers enter their batch number directly on the PDP to inspect certificate metadata. Engineered a slide-out cart drawer with native bundle upsells and optimized critical CSS delivery.",
    results: [
      "Mobile Largest Contentful Paint (LCP) reduced from 4.6s down to 1.1s (-76% latency).",
      "Mobile checkout conversion rate surged by +28% within 45 days of deployment.",
      "Eliminated $250/month in recurring third-party SaaS app subscriptions permanently.",
      "Zero layout shifts (CLS: 0.00) across all mobile device screen sizes."
    ],
    techStack: ["Native Shopify Liquid", "Custom Cart Drawer", "Batch Traceability Engine", "Tailwind CSS", "Zero-App Architecture"],
    liveUrl: "https://www.saffronorigins.com",
    liveUrlText: "Visit Saffron Origins &rarr;"
  },
  {
    slug: "abx-engine",
    num: "02 / Proprietary Tooling",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live Preview",
    title: "ABX Engine: Zero-Bloat A/B Testing",
    tagline: "Proprietary Shopify A/B testing suite with sub-50ms anti-flicker CSS masking, deterministic hash bucketing, and ad-source attribution.",
    heroMetrics: [
      { val: "< 4KB", lbl: "Engine Payload", sub: "95% lighter than VWO/Google Optimize", accent: true },
      { val: "0ms", lbl: "Layout Flicker", sub: "Sub-50ms CSS anti-flicker mask", accent: false },
      { val: "99%", lbl: "Statistical Rigor", sub: "Two-tailed Z-score calculation", accent: false }
    ],
    pitch: "Proprietary Shopify A/B testing suite with sub-50ms anti-flicker CSS masking, deterministic visitor hash bucketing, and ad-source attribution.",
    problem: "Mainstream A/B testing tools (VWO, Convert, Google Optimize) inject 80KB–200KB of blocking JavaScript into Shopify storefronts. This creates catastrophic layout flashing (CLS) and delays mobile paint times by 800ms+, skewing conversion experiments and penalizing Google SEO rankings.",
    solution: "Engineered a native Shopify Remix + Polaris application with a proprietary sub-4KB client-side execution script. Implemented deterministic visitor bucketing via Web Crypto SHA-256 hashing stored in localStorage, sub-50ms anti-flicker CSS opacity masking, and direct Meta/Google UTM campaign attribution tracking.",
    results: [
      "Ultra-lean <4KB client bundle with zero third-party telemetry overhead.",
      "Completely eliminated page flicker and layout shift on split variant switches.",
      "Built-in Bayesian and two-tailed Z-score confidence calculations directly in the merchant admin.",
      "Seamless variant split testing without changing Shopify product URLs or breaking canonical tags."
    ],
    techStack: ["Shopify Remix", "Polaris UI", "Web Crypto API", "Z-Test Stats Engine", "Prisma ORM"],
    liveUrl: "https://abx-liard.vercel.app/app",
    liveUrlText: "Explore ABX Engine &rarr;"
  },
  {
    slug: "knittire-3d",
    num: "03 / 3D Commerce",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live Architecture",
    title: "Knittire 3D Customizer",
    tagline: "Mobile-first Three.js 3D garment customizer with instant shader fabric switching and automated webhook pipelines generating B2B WhatsApp tech packs.",
    heroMetrics: [
      { val: "60 FPS", lbl: "Mobile 3D", sub: "Flawless Three.js shader rendering", accent: true },
      { val: "14 hrs", lbl: "Saved Weekly", sub: "Automated factory tech packs", accent: false },
      { val: "0.00", lbl: "Layout Shift", sub: "Seamless viewport integration", accent: false }
    ],
    pitch: "Mobile-first Three.js 3D garment customizer with instant shader fabric switching and automated webhook pipelines generating B2B WhatsApp tech packs.",
    problem: "B2B and custom luxury garment manufacturing suffers from high sampling return rates and endless manual sales consultations. Clients cannot accurately visualize collar styles, fabric weaves, and fit before placing custom orders, burning 14+ hours of manual designer labor per week.",
    solution: "Architected a mobile-first WebGL Three.js 3D viewer featuring procedural PBR fabric shaders, normal-mapped textile textures, and instant lighting controls. Connected order completions to automated serverless webhooks that render structured PDF factory tech packs and dispatch them directly to production WhatsApp groups.",
    results: [
      "Maintains a locked 60 FPS frame rate on standard mobile devices without battery drain.",
      "Automated factory spec sheet generation saving 14+ hours of manual CAD preparation every week.",
      "Drastically slashed customer sampling revision rounds from an average of 4 iterations down to 1.",
      "Zero layout shifts across all desktop, tablet, and mobile viewports."
    ],
    techStack: ["Three.js", "WebGL PBR Shaders", "GLTF Optimization", "WhatsApp API Webhooks", "Node.js Serverless"],
    liveUrl: "https://knittireglobal.com",
    liveUrlText: "Visit Knittire 3D &rarr;"
  },
  {
    slug: "manifest",
    num: "04 / Direct Response",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live Sales Engine",
    title: "Manifest",
    tagline: "Direct-response sales funnel with dynamic offer stacking, instant client-side coupon validation, and frictionless single-step checkout.",
    heroMetrics: [
      { val: "< 1.2s", lbl: "Checkout Speed", sub: "Single-page headless flow", accent: true },
      { val: "4.2%", lbl: "Cold Traffic CVR", sub: "High-ticket conversion rate", accent: false },
      { val: "31%", lbl: "Order Bump Take", sub: "Dynamic bundle upgrade adoption", accent: false }
    ],
    pitch: "Direct-response sales funnel with dynamic offer stacking, instant client-side coupon validation, and frictionless single-step checkout.",
    problem: "Cold paid ad traffic dropping off precipitously due to multi-step Shopify checkouts, slow coupon code validation, and a lack of visual urgency and dynamic offer stacking on mobile devices.",
    solution: "Engineered a dedicated high-velocity direct-response funnel featuring an instant single-page checkout, dynamic price ladders (₹197 / ₹999), instant client-side discount calculations, and integrated one-click Razorpay payment flows.",
    results: [
      "Sub-1.2s checkout rendering on standard Indian 4G mobile connections.",
      "Cold traffic conversion rate stabilized above 4.2% across paid Meta ad cohorts.",
      "31% order bump adoption on entry-level digital offerings."
    ],
    techStack: ["Direct-Response UX", "Single-Page Checkout", "Dynamic Pricing Engine", "Razorpay Payment API"],
    liveUrl: "https://manifest.leblessed.com/lp01",
    liveUrlText: "Visit Manifest Funnel &rarr;"
  },
  {
    slug: "shopify-cro",
    num: "05 / E-Commerce CRO",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live CRO",
    title: "Shopify Storefront Redesign & CRO",
    tagline: "Mobile-first UX re-architecture: custom variant pills, countdown shipping timers, social proof badges, and sticky cart drawer.",
    heroMetrics: [
      { val: "+34%", lbl: "Mobile CVR", sub: "Verified 30-day conversion lift", accent: true },
      { val: "+18%", lbl: "AOV Increase", sub: "Slide-out cart drawer cross-sells", accent: false },
      { val: "+22%", lbl: "ATC Velocity", sub: "Sticky mobile buy button", accent: false }
    ],
    pitch: "Mobile-first UX re-architecture: custom variant pills, countdown shipping timers, social proof badges, and sticky cart drawer.",
    problem: "High mobile paid traffic arriving on product pages but failing to add to cart due to buried buy buttons, confusing variant selectors, and missing real-time shipping guarantees.",
    solution: "Executed a comprehensive mobile PDP redesign: sticky bottom Add-to-Cart bar triggering on scroll, visual size/color swatches, delivery urgency countdown timers, and an automated free-shipping progress meter built into the cart drawer.",
    results: [
      "+34% increase in mobile purchase conversion rate within 30 days.",
      "+18% average order value (AOV) expansion driven by intelligent in-drawer product recommendations.",
      "Reduced mobile cart abandonment rate by 19%."
    ],
    techStack: ["Shopify Liquid", "Mobile CRO Engineering", "In-Drawer Upsells", "Dynamic Free-Shipping Thresholds"],
    liveUrl: "./index.html#contact",
    liveUrlText: "Request CRO Audit &rarr;"
  },
  {
    slug: "xalt-watches",
    num: "06 / Luxury Commerce",
    category: "shopify",
    categoryLabel: "Shopify DTC & CRO",
    badge: "Live Store",
    title: "Xalt Watches",
    tagline: "High-contrast luxury timepiece storefront with macro dial rendering, bilingual English/Arabic UI, and localized Gulf payment gateways.",
    heroMetrics: [
      { val: "1.4s", lbl: "GCC Load Time", sub: "Sub-1.5s in UAE & Saudi Arabia", accent: true },
      { val: "EN+AR", lbl: "Bilingual UI", sub: "Flawless RTL layout engine", accent: false },
      { val: "< 2%", lbl: "Return Rate", sub: "Macro dial rendering accuracy", accent: false }
    ],
    pitch: "High-contrast luxury timepiece storefront with macro dial rendering, bilingual English/Arabic UI, and localized Gulf payment gateways.",
    problem: "Luxury watches demand extreme visual detail to justify $500+ price points, but high-res watch photography causes massive latency across Middle Eastern mobile networks, driving abandonment.",
    solution: "Engineered high-performance WebP macro tile rendering with progressive zoom, bilingual RTL/LTR layout switching for English and Arabic shoppers, and localized GCC payment gateways (Tabby/Tamara installment checkout).",
    results: [
      "Sub-1.5s mobile page load across Saudi Arabia and UAE mobile networks.",
      "High-resolution dial inspection with zero layout lag or canvas stutter.",
      "Successful market entry with return rates remaining under 2%."
    ],
    techStack: ["Shopify Liquid", "RTL Arabic Layouts", "Macro Dial Zoom", "GCC Payment Integrations"],
    liveUrl: "https://xaltwatches.com/",
    liveUrlText: "Visit Xalt Watches &rarr;"
  },

  // -------------------------------------------------------------
  // SECTION 2: PERFORMANCE MARKETING & BRAND GROWTH (HIMANSHU)
  // -------------------------------------------------------------
  {
    slug: "zyron-tech",
    num: "07 / Performance Marketing",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Electronics D2C",
    title: "Zyron Tech: 4.6X ROAS on Google",
    tagline: "Recovered suspended Merchant Center and restructured Shopping & PMax campaigns into tier-1 high-intent keywords in the Australia market.",
    heroMetrics: [
      { val: "4.6X", lbl: "Verified ROAS", sub: "462% return on ad spend", accent: true },
      { val: "$10,000", lbl: "Monthly Spend", sub: "Scaled profitably in Australia", accent: false },
      { val: "72 hrs", lbl: "Suspension Fix", sub: "Complete Merchant Center recovery", accent: false }
    ],
    pitch: "Recovered suspended Merchant Center and restructured Shopping & PMax campaigns into tier-1 high-intent keywords in the Australia market.",
    problem: "Zyron Tech faced an unexpected Google Merchant Center account suspension for 'Misrepresentation', instantly halting all Google Shopping sales for their consumer electronics brand.",
    solution: "Conducted an urgent compliance audit of storefront policies, structured data, and inventory feeds to get the account reinstated in 72 hours. Restructured Shopping and Performance Max campaigns into high-intent keyword tiers with aggressive negative keyword sculpts.",
    results: [
      "Full Google Merchant Center reinstatement in under 72 hours.",
      "Achieved a sustained 462% (4.6X) ROAS on a $10,000/month advertising budget.",
      "Turned Google Shopping into their highest-margin acquisition channel in Australia."
    ],
    techStack: ["Google Merchant Center Recovery", "Performance Max (PMax)", "Negative Keyword Sculpting", "Shopify Feed Optimization"],
    image: "./growth_assets/hw_zyron.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Discuss Ad Strategy &rarr;"
  },
  {
    slug: "luxury-spirits",
    num: "08 / Performance Marketing",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Luxury Spirits",
    title: "Luxury Spirits: $238K at 9X ROAS",
    tagline: "Tightly controlled Google Search intent funnels targeting corporate gifting and rare whiskey searches on $26k total ad spend.",
    heroMetrics: [
      { val: "$238K", lbl: "Verified Revenue", sub: "$238,021 total revenue generated", accent: true },
      { val: "9.09X", lbl: "Google ROAS", sub: "9X return on ad spend", accent: true },
      { val: "893", lbl: "High-AOV Orders", sub: "Corporate & collector gifting", accent: false }
    ],
    pitch: "Tightly controlled Google Search intent funnels targeting corporate gifting and rare whiskey searches on $26k total ad spend.",
    problem: "Alcohol advertising is strictly regulated, with high CPCs and strict policy constraints. Broad-match keywords were burning ad budget on low-margin cocktail recipe queries.",
    solution: "Engineered laser-targeted Google Search intent funnels focusing exclusively on high-AOV corporate gifting, rare scotch collector sets, and custom corporate packages with bespoke landing page copy.",
    results: [
      "Generated $238,021 in verified revenue on a total spend of only $26,170.",
      "Delivered a sustained 9.09X ROAS across 893 premium corporate transactions.",
      "Strict compliance adherence with zero policy strikes or merchant warnings."
    ],
    techStack: ["Google Search Ads", "High-Ticket Gifting Funnels", "Conversion Copywriting", "Policy-Compliant Tracking"],
    image: "./growth_assets/hw_alcohol.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Scale High-Ticket Ads &rarr;"
  },
  {
    slug: "zupee",
    num: "09 / Gaming & App Growth",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Viral Social",
    title: "Zupee: 117K Follower Growth",
    tagline: "Pivoted corporate announcements into viral meme-style creative and rapid short-form video reels tapping into Indian pop culture humor.",
    heroMetrics: [
      { val: "+117K", lbl: "Follower Growth", sub: "Scaled from 66K to 183K", accent: true },
      { val: "< 6 Mo", lbl: "Time Horizon", sub: "High-velocity production", accent: false },
      { val: "Millions", lbl: "Organic Views", sub: "Zero media spend boost", accent: false }
    ],
    pitch: "Pivoted corporate announcements into viral meme-style creative and rapid short-form video reels tapping into Indian pop culture humor.",
    problem: "Leading real-money skill gaming app Zupee struggled with traditional corporate social posting, resulting in stagnant follower numbers and high cost-per-install rates.",
    solution: "Completely restructured the social content engine: transformed dry product updates into viral pop-culture meme reels, situational gaming comedy skits, and relatable relatable shorts.",
    results: [
      "Exploded social audience from 66K to 183,000+ organic followers in under 6 months.",
      "Generated tens of millions of organic views, drastically lowering blended CPI.",
      "Positioned Zupee as the most culturally resonant casual gaming brand in India."
    ],
    techStack: ["Viral Meme Strategy", "Short-Form Video Production", "Pop Culture Storytelling", "Organic Community Growth"],
    image: "./growth_assets/hw_zupee.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Deploy Meme Engine &rarr;"
  },
  {
    slug: "d2c-fitness",
    num: "10 / Performance Marketing",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Fitness Apparel",
    title: "D2C Fitness: 5+ ROAS Scaling",
    tagline: "Deployed 20+ short-form UGC video hooks focusing on real transformations, direct problem-solution storytelling, and instant bundle offers.",
    heroMetrics: [
      { val: "5.0+", lbl: "Sustained ROAS", sub: "Consistent profitability baseline", accent: true },
      { val: "3.5X", lbl: "Ad Spend Scale", sub: "Scaled daily spend safely", accent: false },
      { val: "90 Days", lbl: "Sprint Duration", sub: "Rapid creative iteration", accent: false }
    ],
    pitch: "Deployed 20+ short-form UGC video hooks focusing on real transformations, direct problem-solution storytelling, and instant bundle offers.",
    problem: "Severe creative fatigue on Meta Ads. The brand was unable to scale spend past $150/day without ROAS dropping below breakeven (1.8X).",
    solution: "Designed and tested 20+ authentic short-form UGC video hooks addressing specific body insecurity transformations, combined with automated bundle offers on product landing pages.",
    results: [
      "Scaled Meta ad spend 3.5X while maintaining an extraordinary 5.0+ ROAS baseline.",
      "Identified 3 'forever evergreen' video creative angles that survived multiple iOS algorithm updates.",
      "Increased blended store AOV by 24% via multi-item bundle landing pages."
    ],
    techStack: ["Meta Direct Response Ads", "UGC Video Strategy", "Creative Testing Matrix", "Bundle Economics"],
    image: "./growth_assets/hw_fitness.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Scale Meta Ads &rarr;"
  },
  {
    slug: "solar-solutions",
    num: "11 / High-Ticket Lead Gen",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Clean Energy B2B",
    title: "Solar Solutions: 80% CAC Drop",
    tagline: "Hyper-localized lead capture funnels with an instant solar savings calculator and aggressive negative keyword lists filtering out wasted clicks.",
    heroMetrics: [
      { val: "-80%", lbl: "Cost Per Lead", sub: "Massive acquisition cost drop", accent: true },
      { val: "74%", lbl: "Lead Quality", sub: "Verified property owners", accent: false },
      { val: "$12k/mo", lbl: "Ad Waste Saved", sub: "Negative keyword filtering", accent: false }
    ],
    pitch: "Hyper-localized lead capture funnels with an instant solar savings calculator and aggressive negative keyword lists filtering out wasted clicks.",
    problem: "Solar keyword bids were exceeding $25/click on Google, with over 75% of incoming inquiries coming from unqualified renters who could not install rooftop solar.",
    solution: "Engineered an interactive solar roof savings calculator landing page with pre-qualifying address and bill inputs, paired with negative keyword lists filtering out DIY and renter searches.",
    results: [
      "Reduced customer acquisition cost (CAC) by 80% within 60 days.",
      "Pre-qualified lead appointment show-up rate increased from 22% to 74%.",
      "Eliminated over $12,000/month in wasted commercial search clicks."
    ],
    techStack: ["Google Search Ads", "Interactive Savings Calculator", "Local Lead Funnels", "Address Verification APIs"],
    image: "./growth_assets/hw_solar.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Cut Lead Costs &rarr;"
  },
  {
    slug: "healthy-meals",
    num: "12 / Local & Subscription",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Food & Beverage",
    title: "Healthy Meals: +40% Lead Volume",
    tagline: "Deployed 15+ variations of diet hooks (Keto, High Protein, Busy Professional) with localized CTAs and instant WhatsApp booking on the exact same budget.",
    heroMetrics: [
      { val: "+40%", lbl: "Lead Volume", sub: "More subscription customers", accent: true },
      { val: "$0", lbl: "Extra Ad Spend", sub: "Optimized existing budget", accent: false },
      { val: "60%", lbl: "WhatsApp Close", sub: "Frictionless direct checkout", accent: false }
    ],
    pitch: "Deployed 15+ variations of diet hooks (Keto, High Protein, Busy Professional) with localized CTAs and instant WhatsApp booking on the exact same budget.",
    problem: "Generic healthy eating ads blended in with hundreds of competitors, creating customer acquisition plateaus and slow form-fill responses.",
    solution: "Split marketing angles into 15+ hyper-specific diet personas (Keto, High-Protein, Corporate Overtime) and routed ad clicks directly to pre-filled WhatsApp conversations.",
    results: [
      "+40% increase in weekly meal subscription orders on the exact same advertising budget.",
      "60% of new inquiries converted into paid subscribers within WhatsApp chat.",
      "Zero customer drop-off on slow traditional website contact forms."
    ],
    techStack: ["Meta Persona Ads", "WhatsApp Direct Funnels", "Diet Segment Hooks", "Hyper-Local Targeting"],
    image: "./growth_assets/hw_healthy.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Launch Direct Funnel &rarr;"
  },
  {
    slug: "shopify-saas",
    num: "13 / B2B SaaS Growth",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Shopify Ecosystem",
    title: "Shopify SaaS: +380% Inbound",
    tagline: "Engineered educational carousel infographics, case breakdowns, and interactive merchant teardowns driving organic app installs.",
    heroMetrics: [
      { val: "+380%", lbl: "Inbound Installs", sub: "Organic app store installs", accent: true },
      { val: "+100%", lbl: "Social Engagement", sub: "Merchant-targeted content", accent: false },
      { val: "+40%", lbl: "Bio CTR", sub: "Direct app store clicks", accent: false }
    ],
    pitch: "Engineered educational carousel infographics, case breakdowns, and interactive merchant teardowns driving organic app installs.",
    problem: "B2B Shopify App Store app struggling with exorbitant Google Search ad costs ($8+/click) and zero organic social distribution.",
    solution: "Created a high-authority educational carousel engine breaking down technical Shopify mistakes, checkout latency benchmarks, and mobile CRO teardowns for merchants.",
    results: [
      "+380% surge in organic Shopify App Store installs in 90 days.",
      "+40% increase in bio-link click-through rate to the listing page.",
      "Established founder as a go-to technical authority in the Shopify developer space."
    ],
    techStack: ["B2B SaaS Content Engine", "Ecom Teardown Carousels", "Organic App Distribution", "Shopify Merchant Network"],
    image: "./growth_assets/hw_saas.jpg",
    liveUrl: "./index.html#contact",
    liveUrlText: "Scale SaaS Inbound &rarr;"
  },
  {
    slug: "bukl",
    num: "14 / DTC Hardware Launch",
    category: "growth",
    categoryLabel: "Performance & ROAS",
    badge: "Kickstarter",
    title: "BUKL: Friction-Lock Belt",
    tagline: "Minimalist Kickstarter launch architecture and direct-to-consumer store for Traverse, an ultralight friction-lock belt with zero mechanical parts.",
    heroMetrics: [
      { val: "100%", lbl: "Funded", sub: "Successfully funded on Kickstarter", accent: true },
      { val: "0", lbl: "Moving Parts", sub: "Friction-lock mechanical design", accent: false },
      { val: "Direct", lbl: "To Consumer", sub: "Seamless transition to Shopify", accent: false }
    ],
    pitch: "Minimalist Kickstarter launch architecture and direct-to-consumer store for Traverse, an ultralight friction-lock belt with zero mechanical parts.",
    problem: "Launching a radical hardware innovation (a belt with zero holes, pins, or moving parts) required overcoming intense buyer skepticism before production.",
    solution: "Engineered high-contrast CAD visual demonstrations, video scripts, and a minimalist Kickstarter launch architecture that transitioned smoothly into a direct-to-consumer store.",
    results: [
      "Achieved 100% Kickstarter funding goal within the target campaign window.",
      "Established clean direct-to-consumer global fulfillment pipeline.",
      "Zero product warranty returns due to pure friction-lock physical engineering."
    ],
    techStack: ["Kickstarter Architecture", "Industrial CAD Visuals", "Hardware DTC Storefront", "Pre-Order Systems"],
    liveUrl: "https://bukl.co/",
    liveUrlText: "Visit BUKL &rarr;"
  },

  // -------------------------------------------------------------
  // SECTION 3: PROPRIETARY SOFTWARE & AUTOMATIONS
  // -------------------------------------------------------------
  {
    slug: "whatsapp-autopilot",
    num: "15 / Automation Engine",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Production",
    title: "WhatsApp Autopilot",
    tagline: "Automated WhatsApp notification pipeline sending dynamic calendar links, countdown triggers, and Zoom access tokens via verified webhooks.",
    heroMetrics: [
      { val: "+42%", lbl: "Live Show-Up", sub: "Webinar & sales call attendance", accent: true },
      { val: "70%", lbl: "Attendance Rate", sub: "Up from 28% email baseline", accent: false },
      { val: "0 mins", lbl: "Manual Work", sub: "100% automated webhook flow", accent: false }
    ],
    pitch: "Automated WhatsApp notification pipeline sending dynamic calendar links, countdown triggers, and Zoom access tokens via verified webhooks.",
    problem: "Sales call and webinar attendance collapsed below 30% due to spam-filtered calendar invites and unread email reminders.",
    solution: "Engineered an autonomous notification server using the official WhatsApp Business Cloud API. Listens to CRM webhooks, schedules timed countdown triggers, and delivers one-click Zoom access links.",
    results: [
      "Live call and webinar show-up rate surged from 28% to 70% (+42% lift).",
      "Completely eliminated manual sales rep reminder messaging.",
      "100% compliance with WhatsApp Business messaging policies and zero account bans."
    ],
    techStack: ["WhatsApp Cloud API", "FastAPI / Node.js", "CRM Webhooks", "Zoom API Automation"],
    liveUrl: "./index.html#contact",
    liveUrlText: "Deploy WhatsApp Pipeline &rarr;"
  },
  {
    slug: "glaze",
    num: "16 / Consumer Web Product",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live Product",
    title: "Glaze",
    tagline: "Frictionless candid feedback tool: enter name, generate personal link, share anywhere, read unfiltered submissions in clean card feeds.",
    heroMetrics: [
      { val: "10,000+", lbl: "Submissions", sub: "Candid anonymous messages", accent: true },
      { val: "1 Wknd", lbl: "Build Time", sub: "High-velocity MVP execution", accent: false },
      { val: "0-Auth", lbl: "Friction", sub: "Zero-login recipient onboarding", accent: false }
    ],
    pitch: "Frictionless candid feedback tool: enter name, generate personal link, share anywhere, read unfiltered submissions in clean card feeds.",
    problem: "Traditional survey and feedback tools require account creation, password resets, and complex form steps, killing social viral loops.",
    solution: "Built an ultra-lean viral web application: users enter their name, get a persistent link instantly, share it to Instagram or Twitter, and view anonymous feedback in a real-time card deck.",
    results: [
      "Engineered, tested, and deployed to production in a single weekend.",
      "Crossed 10,000+ authentic submissions organically without ad spend.",
      "Sub-200ms API response time under concurrent traffic spikes."
    ],
    techStack: ["Next.js App Router", "Supabase Realtime", "TailwindCSS", "Vercel Edge Network"],
    liveUrl: "https://getglaze.in",
    liveUrlText: "Open Glaze &rarr;"
  },
  {
    slug: "janus",
    num: "17 / Studio Infrastructure",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Internal System",
    title: "Janus",
    tagline: "Unified studio command center combining multi-account social scheduling, Instagram DM automation, and central lead dispatching.",
    heroMetrics: [
      { val: "18 hrs", lbl: "Saved Weekly", sub: "Automated administrative labor", accent: true },
      { val: "5", lbl: "Domains Managed", sub: "Central transactional control", accent: false },
      { val: "< 2 min", lbl: "Lead Routing", sub: "Zero delayed prospect responses", accent: false }
    ],
    pitch: "Unified studio command center combining multi-account social scheduling, Instagram DM automation, and central lead dispatching.",
    problem: "Managing client projects, social media distribution across multiple handles, and inbound prospect inquiries across 6 fragmented dashboards wasted 18+ hours per week.",
    solution: "Architected a unified studio command dashboard combining social publishing queues, Meta Graph API DM automation, and a transactional SQLite CRM with real-time lead dispatching.",
    results: [
      "Automated 18 hours per week of studio administrative friction.",
      "Single-pane view of all outbound mailboxes, domain health scores, and client leads.",
      "Instant routing of qualified client requests directly to founder devices."
    ],
    techStack: ["Next.js App Router", "Meta Graph API", "SQLite WAL CRM", "Python Automation Daemons"],
    liveUrl: "https://janus-engine.vercel.app",
    liveUrlText: "Open Janus &rarr;"
  },
  {
    slug: "safespot",
    num: "18 / Background Intelligence",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live App",
    title: "SafeSpot",
    tagline: "Pre-date background engine querying court records, public registries, and social profiles with automatic on-device data destruction.",
    heroMetrics: [
      { val: "0 Days", lbl: "Data Retention", sub: "Zero cloud privacy footprint", accent: true },
      { val: "< 3.2s", lbl: "Query Speed", sub: "Real-time registry compilation", accent: false },
      { val: "100%", lbl: "Client Privacy", sub: "On-device cryptographic purge", accent: false }
    ],
    pitch: "Pre-date background engine querying court records, public registries, and social profiles with automatic on-device data destruction.",
    problem: "Dating safety apps store sensitive background queries in centralized databases, leaving users vulnerable to catastrophic data leaks and privacy extortion.",
    solution: "Engineered a zero-footprint background check engine that queries public court registries and criminal databases, generates an instant safety scorecard, and permanently purges query history on-device.",
    results: [
      "Guaranteed on-device privacy with zero centralized database query storage.",
      "Delivered real-time court record aggregation in under 3.2 seconds.",
      "High user trust adoption due to absolute cryptographic zero-footprint architecture."
    ],
    techStack: ["Next.js", "Public Court APIs", "Client-Side Cryptography", "TailwindCSS"],
    liveUrl: "https://trysafespot.com",
    liveUrlText: "Visit SafeSpot &rarr;"
  },
  {
    slug: "hisaab",
    num: "19 / LegalTech Recovery",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live Platform",
    title: "Hisaab",
    tagline: "10-question questionnaire generator that outputs an escalating 5-document recovery pack: legal demand notice, Labour Commissioner draft, and gratuity math.",
    heroMetrics: [
      { val: "₹1.84 Cr+", lbl: "Claims Computed", sub: "Verified legal salary recovery", accent: true },
      { val: "< 4 min", lbl: "Turnaround", sub: "Instant 5-document pack generation", accent: false },
      { val: "5 Docs", lbl: "Legal Pack", sub: "Notice, labour draft, interest math", accent: false }
    ],
    pitch: "10-question questionnaire generator that outputs an escalating 5-document recovery pack: legal demand notice, Labour Commissioner draft, and gratuity math.",
    problem: "Unpaid tech employees and agency contractors in India face astronomical advocate retainers just to calculate statutory interest, gratuity, and draft formal legal demand notices.",
    solution: "Built a 10-question smart legal wizard that models Indian Labour Code statutory interest and gratuity mathematics, automatically compiling an escalating 5-document legal recovery packet ready for court filing.",
    results: [
      "Computed over ₹1.84 Crores in legitimate unpaid salary and contractor claims.",
      "Reduced legal notice drafting time from 5 days down to under 4 minutes.",
      "Helped dozens of distressed tech workers recover withheld dues without advocate fees."
    ],
    techStack: ["React", "PDF Generation Engine", "Indian Labour Code Math", "TailwindCSS"],
    liveUrl: "https://hisaab-lilac-rho.vercel.app",
    liveUrlText: "Visit Hisaab &rarr;"
  },
  {
    slug: "before-token",
    num: "20 / Real Estate Compliance",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live Scanner",
    title: "Before Token",
    tagline: "Automated verification scanner matching builder marketing brochures directly against MahaRERA regulatory filings and NCLT insolvency databases.",
    heroMetrics: [
      { val: "14", lbl: "Stalled Scans", sub: "Insolvent projects flagged", accent: true },
      { val: "< 15s", lbl: "Scan Time", sub: "Automated RERA regulatory check", accent: false },
      { val: "100%", lbl: "Independent", sub: "Zero builder sponsorship bias", accent: false }
    ],
    pitch: "Automated verification scanner matching builder marketing brochures directly against MahaRERA regulatory filings and NCLT insolvency databases.",
    problem: "Home buyers in Mumbai and Pune lose life savings in non-refundable token deposits to stalled projects whose active litigation and NCLT insolvencies are hidden by sales agents.",
    solution: "Constructed an automated regulatory scanner that parses builder marketing brochures, queries MahaRERA public filings, and cross-references active NCLT insolvency records in real time.",
    results: [
      "Successfully flagged 14 stalled residential projects before prospective buyers paid token deposits.",
      "Automated cross-referencing across 3 separate government compliance portals.",
      "Average comprehensive scan completed in under 15 seconds."
    ],
    techStack: ["FastAPI", "Playwright Web Scraping", "Next.js", "RERA Document Parser"],
    liveUrl: "https://before-token.vercel.app",
    liveUrlText: "Visit Before Token &rarr;"
  },
  {
    slug: "bhoomiputra",
    num: "21 / Civic & Agritech",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Client Work",
    title: "Bhoomiputra Foundation",
    tagline: "Full digital platform and collective hub featuring Coastal Rise (direct catch), Project Red Dot® (sanitation), and transparent micro-donations.",
    heroMetrics: [
      { val: "-45%", lbl: "Middleman Cut", sub: "Direct catch to residential kitchens", accent: true },
      { val: "3", lbl: "Initiatives", sub: "Coastal, Red Dot, Education", accent: false },
      { val: "500+", lbl: "Member Cards", sub: "Digital verified membership", accent: false }
    ],
    pitch: "Full digital platform and collective hub featuring Coastal Rise (direct catch), Project Red Dot® (sanitation), and transparent micro-donations.",
    problem: "Artisanal coastal fishermen lose up to 70% of catch value to predatory middlemen, while local foundation donors have zero visibility into charity allocation.",
    solution: "Engineered a comprehensive community hub: Coastal Rise (direct-to-consumer catch logistics), Project Red Dot (sanitation initiatives), and dynamic transparent donor ledgers.",
    results: [
      "Connected artisanal fishing collectives directly to urban communities, cutting middleman markups by 45%.",
      "Issued 500+ digital membership passes with verified community benefits.",
      "Full transparency on community micro-donations and coastal welfare funds."
    ],
    techStack: ["Lovable Web Engine", "Supabase Backend", "Razorpay Payment Gateway", "TailwindCSS"],
    liveUrl: "https://bhoomi-roots-foundation.lovable.app/",
    liveUrlText: "Visit Bhoomiputra &rarr;"
  },
  {
    slug: "freedoms-ai",
    num: "22 / Voice AI & Productivity",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live Platform",
    title: "Freedoms AI",
    tagline: "Voice-first mental clarity system: automated audio transcription, underlying intent extraction, cross-note linking, and nightly task passes.",
    heroMetrics: [
      { val: "12,000+", lbl: "Memos Processed", sub: "Automated voice-to-task pipeline", accent: true },
      { val: "98%", lbl: "Accuracy", sub: "Whisper speech transcription", accent: false },
      { val: "< 1.8s", lbl: "Latency", sub: "Real-time task categorization", accent: false }
    ],
    pitch: "Voice-first mental clarity system: automated audio transcription, underlying intent extraction, cross-note linking, and nightly task passes.",
    problem: "Founders and executives record dozens of unstructured voice memos each week that end up lost in phone recorder apps, leading to forgotten action items.",
    solution: "Built a voice-first mental operating system: record voice streams on mobile or desktop, transcribe with Whisper AI, automatically extract action items, and link related thoughts across notes.",
    results: [
      "Processed over 12,000 voice memos in private beta with a 98% transcription accuracy rate.",
      "Delivers automated nightly briefing passes summarizing daily voice captures into actionable tasks.",
      "Sub-1.8s transcription and intent categorization latency."
    ],
    techStack: ["Whisper AI", "LLM Structured Parsing", "Next.js", "FastAPI", "iOS Web Companion"],
    liveUrl: "https://freedoms.ai/join",
    liveUrlText: "Visit Freedoms AI &rarr;"
  },
  {
    slug: "weshub",
    num: "23 / Creator Platform",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Live Platform",
    title: "WESHUB",
    tagline: "Interactive multi-engine platform showcasing brand activations, international franchise expansion into India, and enterprise AI workflows.",
    heroMetrics: [
      { val: "3", lbl: "Business Verticals", sub: "Retail, media & AI integration", accent: true },
      { val: "100%", lbl: "Automated Leads", sub: "Franchise partner dispatch", accent: false },
      { val: "60 FPS", lbl: "Transitions", sub: "Ultra-smooth interactive presentation", accent: false }
    ],
    pitch: "Interactive multi-engine platform showcasing brand activations, international franchise expansion into India, and enterprise AI workflows.",
    problem: "Global retail and media franchise groups struggle to present diverse multi-brand assets and franchise investment terms through static corporate slide decks.",
    solution: "Designed and built an interactive flagship platform presenting 3 business verticals, automated franchise investor lead capture, and live demonstrations of enterprise AI brand workflows.",
    results: [
      "Deployed as the central presentation platform for global retail franchise negotiations in India.",
      "100% automated franchise lead routing directly to executive deal leads.",
      "Maintains 60 FPS visual transitions across modern desktop and mobile browsers."
    ],
    techStack: ["Interactive UI Engine", "Dynamic CMS", "TailwindCSS", "Cloudflare CDN"],
    liveUrl: "https://weshub.lovable.app",
    liveUrlText: "Visit WESHUB &rarr;"
  },
  {
    slug: "pause",
    num: "24 / Digital Wellbeing",
    category: "software",
    categoryLabel: "Software & Automations",
    badge: "Android App",
    title: "Pause",
    tagline: "Android application intercepting the physical impulse of phone unlocking and compulsive app opening using haptic delays and breath pacing.",
    heroMetrics: [
      { val: "-40%", lbl: "Screen Time", sub: "Verified reduction in phone pickups", accent: true },
      { val: "3s", lbl: "Breath Delay", sub: "Haptic sensory interruption", accent: false },
      { val: "0 Cloud", lbl: "Tracking", sub: "100% private on-device execution", accent: false }
    ],
    pitch: "Android application intercepting the physical impulse of phone unlocking and compulsive app opening using haptic delays and breath pacing.",
    problem: "Traditional screen-time limiters are easy to override with a single tap, failing to break the subconscious physical loop of compulsive phone unlocking.",
    solution: "Engineered a native Android application that intercepts device unlocks, introducing a mandatory 3-second haptic breath pacing delay before granting screen access.",
    results: [
      "Reduced compulsive phone unlock frequency by -40% across verified pilot testing.",
      "Zero battery drain via lightweight Android native accessibility hooks.",
      "Completely private execution with zero telemetry data leaving the device."
    ],
    techStack: ["Android Native (Kotlin)", "Accessibility Services", "Haptic Hardware APIs", "Zero-Telemetry Architecture"],
    liveUrl: "mailto:mindmaxxxing@gmail.com?subject=Pause%20access",
    liveUrlText: "Request Pause Access &rarr;"
  },
  {
      "slug": "fevicol-bonding-tweet",
      "num": "25 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Fevicol: The Bonding Tweet",
      "tagline": "Topical commercial motion film turning Harsh Goenka viral bonding tweet into an iconic brand moment.",
      "heroMetrics": [
          {
              "val": "Topical",
              "lbl": "Response Format",
              "sub": "Rapid turnaround delivery",
              "accent": true
          },
          {
              "val": "2D + 3D",
              "lbl": "Motion Stack",
              "sub": "Kinetic typography & asset staging",
              "accent": false
          },
          {
              "val": "National",
              "lbl": "Campaign Reach",
              "sub": "Pidilite brand engagement",
              "accent": false
          }
      ],
      "pitch": "Topical commercial motion film turning Harsh Goenka viral bonding tweet into an iconic brand moment.",
      "problem": "Harsh Goenka tweeted a provocative question to millions: \"What is better for bonding - fevicol or alcohol?\" Fevicol needed a swift, witty, high-production animated social film before the cultural news cycle shifted.",
      "solution": "Rahul Saranya directed and animated kinetic typography, floating social engagement reactions, and the signature Pidilite elephant iconography to deliver the punchline: \"Depends on whether you want to bond for an evening or for life!\"",
      "results": [
          "Topical brand response film conceived, animated, and delivered within the live cultural news cycle.",
          "High social engagement across Twitter, LinkedIn, and Instagram.",
          "Seamless blend of kinetic 2.5D typography and Pidilite elephant heritage animation."
      ],
      "techStack": [
          "After Effects",
          "Cinema 4D",
          "Kinetic Typography",
          "2.5D Compositing"
      ],
      "liveUrl": "/case-studies/fevicol-bonding-tweet",
      "liveUrlText": "Watch Fevicol Film &rarr;"
  },
  {
      "slug": "britannia-coffee-cracker",
      "num": "26 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Britannia: First Coffee Cracker",
      "tagline": "Commercial launch film and campaign case study introducing India first coffee cracker with Karan Johar.",
      "heroMetrics": [
          {
              "val": "Celebrity",
              "lbl": "Talent Feature",
              "sub": "Karan Johar launch spot",
              "accent": true
          },
          {
              "val": "4K / 60p",
              "lbl": "Master Delivery",
              "sub": "Broadcast TVC & digital cutdowns",
              "accent": false
          },
          {
              "val": "Pop Art",
              "lbl": "Visual Identity",
              "sub": "Kinetic typography overlays",
              "accent": false
          }
      ],
      "pitch": "Commercial launch film and campaign case study introducing India first coffee cracker with Karan Johar.",
      "problem": "Launching an entirely new snack category (coffee crackers) requires high-voltage visual identity that breaks standard FMCG biscuit advertising cliches.",
      "solution": "Combined Karan Johar celebrity footage with bold pop-art graphic overlays, coffee swirl visual effects, and kinetic typography that establishes \"India First Coffee Cracker\" across digital and broadcast channels.",
      "results": [
          "Comprehensive broadcast and digital campaign graphics delivered across national networks.",
          "Distinctive pop-art coffee aesthetic separating Coffee Cracker from legacy biscuit lines.",
          "Award-winning case study documentation of the national launch."
      ],
      "techStack": [
          "After Effects",
          "Premiere Pro",
          "Volumetric Shaders",
          "Broadcast Graphics"
      ],
      "liveUrl": "/case-studies/britannia-coffee-cracker",
      "liveUrlText": "Watch Britannia Launch &rarr;"
  },
  {
      "slug": "motogp-bharat-racing",
      "num": "27 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "MotoGP Bharat: Wild Ride",
      "tagline": "High-octane commercial teaser for MotoGP Bharat on BookMyShow, simulating cockpit perspective and electric racetrack speed.",
      "heroMetrics": [
          {
              "val": "POV Sim",
              "lbl": "Camera Rig",
              "sub": "300 km/h cockpit perspective",
              "accent": true
          },
          {
              "val": "VFX",
              "lbl": "Lightning Effects",
              "sub": "Electric speed lines & asphalt blur",
              "accent": false
          },
          {
              "val": "National",
              "lbl": "Ticketing Campaign",
              "sub": "BookMyShow exclusive launch",
              "accent": false
          }
      ],
      "pitch": "High-octane commercial teaser for MotoGP Bharat on BookMyShow, simulating cockpit perspective and electric racetrack speed.",
      "problem": "Promoting premier international motorcycle racing in India demanded visceral adrenaline that makes viewers feel the raw physics of MotoGP.",
      "solution": "Modeled a first-person cockpit camera view with dynamic asphalt blur, reactive lightning VFX, digital speedometer telemetry, and high-impact typographic locks: \"GET READY FOR A WILD RIDE.\"",
      "results": [
          "High-impact social teaser generating widespread fan excitement for the inaugural MotoGP Bharat race.",
          "Seamless integration of BookMyShow ticketing CTAs within the adrenaline-charged edit.",
          "Visceral first-person racing camera mechanics."
      ],
      "techStack": [
          "Cinema 4D",
          "After Effects",
          "Electrical VFX",
          "Speedometer Telemetry"
      ],
      "liveUrl": "/case-studies/motogp-bharat-racing",
      "liveUrlText": "Watch MotoGP Teaser &rarr;"
  },
  {
      "slug": "fiama-charcoal-gel-bar",
      "num": "28 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "ITC Fiama: Charcoal Gel Bar",
      "tagline": "Sensory 3D product commercial showcasing the texture, translucency, and grapefruit freshness of the Fiama gel bar.",
      "heroMetrics": [
          {
              "val": "3D CGI",
              "lbl": "Pack Modeling",
              "sub": "Subsurface scattering & sparkle particles",
              "accent": true
          },
          {
              "val": "Zero Gravity",
              "lbl": "Staging",
              "sub": "Floating charcoal & citrus elements",
              "accent": false
          },
          {
              "val": "Commercial",
              "lbl": "Digital Asset",
              "sub": "ITC Fiama brand spot",
              "accent": false
          }
      ],
      "pitch": "Sensory 3D product commercial showcasing the texture, translucency, and grapefruit freshness of the Fiama gel bar.",
      "problem": "Soap and gel bar commercials struggle to convey skin feel and cleansing power without looking generic.",
      "solution": "Constructed an atmospheric dark-slate studio setting with 3D product rendering, subsurface scattering, ambient charcoal smoke, and floating citrus accents to highlight body, face, and hair versatility.",
      "results": [
          "Photorealistic 3D product asset capturing the translucent glitter particulate of the gel bar.",
          "Atmospheric lighting and color balance highlighting activated charcoal purification.",
          "High social feed retention with zero-gravity product staging."
      ],
      "techStack": [
          "Cinema 4D",
          "Octane / Redshift",
          "Subsurface Scattering",
          "Particle Systems"
      ],
      "liveUrl": "/case-studies/fiama-charcoal-gel-bar",
      "liveUrlText": "Watch Fiama Spot &rarr;"
  },
  {
      "slug": "cuticura-original-bloom",
      "num": "29 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Cuticura: Original Bloom",
      "tagline": "Product-centric 3D motion reel highlighting botanical freshness, chamomile petals, and sunlit studio staging.",
      "heroMetrics": [
          {
              "val": "9:16",
              "lbl": "Vertical Format",
              "sub": "Native Instagram reel optimization",
              "accent": true
          },
          {
              "val": "Botanical",
              "lbl": "Particle Physics",
              "sub": "Slow-motion chamomile flower petals",
              "accent": false
          },
          {
              "val": "FMCG",
              "lbl": "Brand Campaign",
              "sub": "Cholayil Cuticura portfolio",
              "accent": false
          }
      ],
      "pitch": "Product-centric 3D motion reel highlighting botanical freshness, chamomile petals, and sunlit studio staging.",
      "problem": "Personal care talc packaging needs to look modern, refreshing, and premium on vertical social feeds.",
      "solution": "Designed warm studio lighting with floating daisy and chamomile botanical elements in zero-gravity orbit around the bottle, synchronizing bottle rotation with typographic claims.",
      "results": [
          "Warm summer aesthetic elevating traditional talc into a contemporary beauty staple.",
          "Micro-fluid camera orbits around bottle packaging geometry.",
          "Optimized for rapid mobile feed ingestion."
      ],
      "techStack": [
          "Cinema 4D",
          "After Effects",
          "Botanical Shaders",
          "Camera Tracking"
      ],
      "liveUrl": "/case-studies/cuticura-original-bloom",
      "liveUrlText": "Watch Cuticura Reel &rarr;"
  },
  {
      "slug": "paw-patrol-india-launch",
      "num": "30 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Paw Patrol: The Mighty Movie",
      "tagline": "Official character motion graphics and promotional pre-buzz animation for the theatrical release in India.",
      "heroMetrics": [
          {
              "val": "Nickelodeon",
              "lbl": "Licensed IP",
              "sub": "Official Paramount character badges",
              "accent": true
          },
          {
              "val": "Compositing",
              "lbl": "Environment",
              "sub": "India Gate twilight staging",
              "accent": false
          },
          {
              "val": "Theatrical",
              "lbl": "Pre-Buzz",
              "sub": "BookMyShow movie promotion",
              "accent": false
          }
      ],
      "pitch": "Official character motion graphics and promotional pre-buzz animation for the theatrical release in India.",
      "problem": "Introducing global Nickelodeon character properties to Indian family audiences for BookMyShow theatrical booking.",
      "solution": "Composited official Paramount and Spin Master 3D character badge shields (Chase, Skye, Marshall, Rubble, Rocky, Zuma) into iconic Indian landmark backdrops with cinematic lens flares and sound design.",
      "results": [
          "High-energy pre-buzz animation driving early ticketing curiosity among parents and children.",
          "Flawless IP brand consistency adhering to international theatrical guidelines.",
          "Dynamic multi-character shield choreography."
      ],
      "techStack": [
          "After Effects",
          "Paramount Character Assets",
          "Lens Flare Compositing",
          "Sound Design"
      ],
      "liveUrl": "/case-studies/paw-patrol-india-launch",
      "liveUrlText": "Watch Paw Patrol Promo &rarr;"
  },
  {
      "slug": "akasa-air-destinations",
      "num": "31 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Akasa Air: Bucket List Flight",
      "tagline": "Kinetic travel reel for Akasa Air highlighting northeast Indian destinations with bespoke brand motion transitions.",
      "heroMetrics": [
          {
              "val": "Aviation",
              "lbl": "Brand Identity",
              "sub": "Signature Akasa orange & purple curves",
              "accent": true
          },
          {
              "val": "Kinetic",
              "lbl": "Transitions",
              "sub": "Vector passport stamps & palace reveal",
              "accent": false
          },
          {
              "val": "Route Launch",
              "lbl": "Campaign Goal",
              "sub": "Agartala flight connectivity",
              "accent": false
          }
      ],
      "pitch": "Kinetic travel reel for Akasa Air highlighting northeast Indian destinations with bespoke brand motion transitions.",
      "problem": "Airlines often use generic stock flight footage that fails to build brand recognition for newly opened regional flight routes.",
      "solution": "Created an illustrative travel diary aesthetic incorporating Akasa iconic orange-and-purple swoosh curves, custom vector stamps, and landmark reveals featuring Agartala Ujjayanta Palace.",
      "results": [
          "Vibrant travel reel establishing Akasa Air as the premier airline for exploring Northeast India.",
          "Custom vector transition curves mirroring Akasa livery identity.",
          "High viewer completion rates across travel enthusiast cohorts."
      ],
      "techStack": [
          "After Effects",
          "Vector Motion Design",
          "Travel Graphics",
          "Branded Color Grading"
      ],
      "liveUrl": "/case-studies/akasa-air-destinations",
      "liveUrlText": "Watch Akasa Air Reel &rarr;"
  },
  {
      "slug": "garnier-men-acnofight",
      "num": "32 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Garnier Men: AcnoFight Flash",
      "tagline": "High-energy electrical VFX animation demonstrating deep-cleansing speed for Garnier Men AcnoFight.",
      "heroMetrics": [
          {
              "val": "Electric VFX",
              "lbl": "Simulation",
              "sub": "Neon lightning arcs & impact cracks",
              "accent": true
          },
          {
              "val": "Speed Pacing",
              "lbl": "Duration",
              "sub": "8-second high-velocity social spot",
              "accent": false
          },
          {
              "val": "Grooming",
              "lbl": "Category",
              "sub": "L Oreal / Garnier Men",
              "accent": false
          }
      ],
      "pitch": "High-energy electrical VFX animation demonstrating deep-cleansing speed for Garnier Men AcnoFight.",
      "problem": "Men grooming digital ads require immediate 1-second hooks to prevent scroll-past on social feeds.",
      "solution": "Engineered high-voltage neon electrical arc simulations, dynamic floor crack displacement, and fast-paced graphic speed lines to dramatize rapid germ defense.",
      "results": [
          "Stop-the-scroll lightning animation capturing male audience attention instantly.",
          "High-contrast rim lighting maintaining product recognition amidst intense VFX.",
          "Clear typographic hierarchy reinforcing 99.9% germ elimination."
      ],
      "techStack": [
          "After Effects",
          "Electrical Simulations",
          "Trapcode Particular",
          "Impact Sound Design"
      ],
      "liveUrl": "/case-studies/garnier-men-acnofight",
      "liveUrlText": "Watch Garnier Spot &rarr;"
  },
  {
      "slug": "cuticura-diana-perfume",
      "num": "33 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Cuticura Diana: Smart Perfume",
      "tagline": "Commercial perfume visualization featuring blue orchids, atmospheric morning light, and micro-particle burst effects.",
      "heroMetrics": [
          {
              "val": "Cosmetic CGI",
              "lbl": "Rendering",
              "sub": "Metallic blue cap & satin body shaders",
              "accent": true
          },
          {
              "val": "Atmosphere",
              "lbl": "Lighting",
              "sub": "Morning cloud fog & botanical orchids",
              "accent": false
          },
          {
              "val": "Fragrance",
              "lbl": "Campaign",
              "sub": "Diana body perfume launch",
              "accent": false
          }
      ],
      "pitch": "Commercial perfume visualization featuring blue orchids, atmospheric morning light, and micro-particle burst effects.",
      "problem": "Body perfumes rely heavily on invisible sensory qualities that must be translated visually on screen.",
      "solution": "Surrounded the 3D Cuticura Diana perfume can with blossoming royal blue orchids, soft cloud fog, and swirling mist particles that visually communicate the \"Smart Perfume Burst\" formula.",
      "results": [
          "Ethereal visual mood translating scent freshness into vivid screen imagery.",
          "Precise material shaders differentiating metallic luster from label textures.",
          "High conversion on digital beauty storefront placements."
      ],
      "techStack": [
          "Cinema 4D",
          "Redshift",
          "Micro-Particle Simulations",
          "Botanical 3D"
      ],
      "liveUrl": "/case-studies/cuticura-diana-perfume",
      "liveUrlText": "Watch Perfume Visual &rarr;"
  },
  {
      "slug": "cuticura-lavender-mist",
      "num": "34 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Cuticura: Lavender Mist",
      "tagline": "Lush social animation capturing the lavender fragrance profile with floating floral botanical bursts.",
      "heroMetrics": [
          {
              "val": "Looping",
              "lbl": "Animation Style",
              "sub": "Seamless social loop mechanics",
              "accent": true
          },
          {
              "val": "Botanical",
              "lbl": "Staging",
              "sub": "Floating lavender blossoms & powder mist",
              "accent": false
          },
          {
              "val": "Personal Care",
              "lbl": "Category",
              "sub": "Refreshing talc line promotion",
              "accent": false
          }
      ],
      "pitch": "Lush social animation capturing the lavender fragrance profile with floating floral botanical bursts.",
      "problem": "Talc advertising can feel old-fashioned without modern motion styling and vibrant color harmony.",
      "solution": "Staged the lavender bottle against an intense ultraviolet ambient glow, animating floating blossoms, sunscreen benefit highlights, and glittering powder mist.",
      "results": [
          "Hypnotic social looping asset driving continuous replays.",
          "Modernized brand perception across young female demographic targets.",
          "Clear packaging hierarchy showcasing UV sunscreen benefits."
      ],
      "techStack": [
          "Cinema 4D",
          "After Effects",
          "Lighting Design",
          "Botanical Compositing"
      ],
      "liveUrl": "/case-studies/cuticura-lavender-mist",
      "liveUrlText": "Watch Lavender Loop &rarr;"
  },
  {
      "slug": "park-avenue-misty-trail",
      "num": "35 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Park Avenue: Misty Trail",
      "tagline": "Commercial product spot for Raymond Park Avenue Naturel collection featuring mist vortexes and lighting accents.",
      "heroMetrics": [
          {
              "val": "Essential Oils",
              "lbl": "Theme",
              "sub": "100% natural oil spark simulation",
              "accent": true
          },
          {
              "val": "Volumetric",
              "lbl": "Mist FX",
              "sub": "Deep forest swirl & particle fields",
              "accent": false
          },
          {
              "val": "Men Grooming",
              "lbl": "Category",
              "sub": "Raymond Park Avenue line",
              "accent": false
          }
      ],
      "pitch": "Commercial product spot for Raymond Park Avenue Naturel collection featuring mist vortexes and lighting accents.",
      "problem": "Communicating pure natural essential oils in an aerosol deodorant without losing masculine premium appeal.",
      "solution": "Created an icy forest atmosphere with swirling volumetric mist, metallic foil shaders on the bottle typography, and golden particle sparkles reflecting essential oil purity.",
      "results": [
          "Masculine premium visual language combining forest organic freshness with sleek aerosol engineering.",
          "Embossed packaging typography brought to life with dynamic specular reflections.",
          "National social deployment across luxury grooming channels."
      ],
      "techStack": [
          "Cinema 4D",
          "Volumetric Fog",
          "Specular Reflection Maps",
          "Particle Flow"
      ],
      "liveUrl": "/case-studies/park-avenue-misty-trail",
      "liveUrlText": "Watch Park Avenue Spot &rarr;"
  },
  {
      "slug": "britannia-smiles-end-slate",
      "num": "36 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Britannia: Smiles TVC End Slate",
      "tagline": "Stop-motion style 3D biscuit physics and kinetic typography for Britannia flagship national television campaign.",
      "heroMetrics": [
          {
              "val": "Broadcast TVC",
              "lbl": "Format",
              "sub": "National television end card",
              "accent": true
          },
          {
              "val": "Multi-SKU",
              "lbl": "Product Staging",
              "sub": "Good Day, Bourbon, Jim Jam, Little Hearts",
              "accent": false
          },
          {
              "val": "Mnemonic Sync",
              "lbl": "Audio Alignment",
              "sub": "Ting-ting-ti-ting sonic beat lock",
              "accent": false
          }
      ],
      "pitch": "Stop-motion style 3D biscuit physics and kinetic typography for Britannia flagship national television campaign.",
      "problem": "TVC end slates have exactly 3 to 4 seconds to resolve brand identity and display multiple product SKUs without clutter.",
      "solution": "Modeled playful 3D rotating biscuits (Bourbon, Good Day, Little Hearts, Jim Jam) around kinetic \"BRITANNIA SMILES\" typography with cheerful pop-art accents.",
      "results": [
          "Aired across national television networks reaching hundreds of millions of households.",
          "Precise rhythm matching the iconic Britannia audio mnemonic signature.",
          "Harmonious showcase of four flagship biscuit SKUs within a single 3-second frame."
      ],
      "techStack": [
          "Cinema 4D",
          "After Effects",
          "Stop-Motion Rigging",
          "Broadcast Color Standards"
      ],
      "liveUrl": "/case-studies/britannia-smiles-end-slate",
      "liveUrlText": "Watch Smiles End Slate &rarr;"
  },
  {
      "slug": "britannia-gifting-end-slate",
      "num": "37 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Britannia: No Better Gift",
      "tagline": "National festival television commercial end slate celebrating festive gifting with volumetric extruded letterforms.",
      "heroMetrics": [
          {
              "val": "Festive TVC",
              "lbl": "Season",
              "sub": "National holiday gifting campaign",
              "accent": true
          },
          {
              "val": "3D Type",
              "lbl": "Typography",
              "sub": "Volumetric extruded letterforms",
              "accent": false
          },
          {
              "val": "Confectionery",
              "lbl": "Palette",
              "sub": "Warm pastel celebratory tones",
              "accent": false
          }
      ],
      "pitch": "National festival television commercial end slate celebrating festive gifting with volumetric extruded letterforms.",
      "problem": "Festive campaigns require warmth, celebration, and premium packaging presentation under tight broadcast timing.",
      "solution": "Rendered volumetric 3D extruded \"NO BETTER GIFT\" typography with striped drop shadows and joyful orbiting biscuits in warm pastel confectionery tones.",
      "results": [
          "National festive television broadcast presence during peak holiday sales quarters.",
          "Volumetric typography ensuring legibility across small television sets and mobile screens.",
          "Celebratory biscuit motion emphasizing sharing and connection."
      ],
      "techStack": [
          "Cinema 4D",
          "Extruded Type Engine",
          "After Effects",
          "Festive Lighting"
      ],
      "liveUrl": "/case-studies/britannia-gifting-end-slate",
      "liveUrlText": "Watch Gifting Slate &rarr;"
  },
  {
      "slug": "britannia-bourbon-qatar",
      "num": "38 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "Britannia Bourbon: Road to Qatar",
      "tagline": "Case study motion graphic documentation for the Britannia Bourbon Football Contest sending winning teams to Qatar.",
      "heroMetrics": [
          {
              "val": "FIFA World Cup",
              "lbl": "Cultural Event",
              "sub": "5 teams won tickets to Qatar",
              "accent": true
          },
          {
              "val": "Case Study",
              "lbl": "Format",
              "sub": "Industry award submission documentation",
              "accent": false
          },
          {
              "val": "Bourbon",
              "lbl": "Brand Lead",
              "sub": "Youth football engagement",
              "accent": false
          }
      ],
      "pitch": "Case study motion graphic documentation for the Britannia Bourbon Football Contest sending winning teams to Qatar.",
      "problem": "Documenting a complex multi-city on-ground and digital consumer activation for marketing industry award submissions.",
      "solution": "Structured fast-paced screen motion combining contest mechanics, stadium graphics, winner celebrations, and on-pack QR promotions into a concise narrative.",
      "results": [
          "Award-winning case study documentation winning creative agency accolades.",
          "Dynamic synthesis of live activation footage, on-pack design, and social metrics.",
          "Energetic athletic pacing reflecting the spirit of World Cup football."
      ],
      "techStack": [
          "After Effects",
          "Premiere Pro",
          "Infographic Animation",
          "Case Study Structuring"
      ],
      "liveUrl": "/case-studies/britannia-bourbon-qatar",
      "liveUrlText": "Watch Qatar Case Study &rarr;"
  },
  {
      "slug": "rise-gmba-promo",
      "num": "39 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "RISE: Global MBA Explainer",
      "tagline": "Educational promotional film translating executive curriculum, global networking, and career mobility into kinetic design.",
      "heroMetrics": [
          {
              "val": "EdTech",
              "lbl": "Vertical",
              "sub": "Executive business education",
              "accent": true
          },
          {
              "val": "Vector 3D",
              "lbl": "Visual Language",
              "sub": "Interactive globe & milestone tracks",
              "accent": false
          },
          {
              "val": "Lead Gen",
              "lbl": "Objective",
              "sub": "GMBA student enrollment conversion",
              "accent": false
          }
      ],
      "pitch": "Educational promotional film translating executive curriculum, global networking, and career mobility into kinetic design.",
      "problem": "Higher education promo videos frequently rely on dry slide lectures or cheesy stock corporate footage.",
      "solution": "Built a clean, contemporary motion design system with flat-vector geometric transitions, rotating 3D globes, and clear typographic pacing for career milestones.",
      "results": [
          "High conversion digital ad performance across LinkedIn and executive education platforms.",
          "Modern visual treatment positioning RISE as a premier next-gen learning institution.",
          "Complex curriculum architecture explained in under 30 seconds."
      ],
      "techStack": [
          "After Effects",
          "Vector Motion Design",
          "3D Globe Mapping",
          "Typographic Pacing"
      ],
      "liveUrl": "/case-studies/rise-gmba-promo",
      "liveUrlText": "Watch RISE Promo &rarr;"
  },
  {
      "slug": "rio-heavy-flow-animation",
      "num": "40 / Commercial Motion",
      "category": "motion",
      "categoryLabel": "3D Animation & Motion",
      "badge": "Commercial Client Work",
      "title": "RIO: Heavy Flow Empathy",
      "tagline": "Empathetic 2D character animation addressing heavy flow and period cramps with warmth, humor, and dignity.",
      "heroMetrics": [
          {
              "val": "Character Ani",
              "lbl": "Discipline",
              "sub": "Frame-by-frame character emotion",
              "accent": true
          },
          {
              "val": "Empathy Lead",
              "lbl": "Message",
              "sub": "Honest depiction of physical cramp pain",
              "accent": false
          },
          {
              "val": "Social Viral",
              "lbl": "Format",
              "sub": "Nobel Hygiene / RIO Pads campaign",
              "accent": false
          }
      ],
      "pitch": "Empathetic 2D character animation addressing heavy flow and period cramps with warmth, humor, and dignity.",
      "problem": "Feminine hygiene advertising has historically used clinical blue liquid and sterile tropes that fail to reflect the real physical pain and fatigue women experience.",
      "solution": "Developed relatable 2D character animation illustrating the physical exhaustion of period cramps through an affectionate pink elephant metaphor, creating an honest dialogue about heavy flow pads.",
      "results": [
          "Empathetic character storytelling celebrated by consumers and industry creative circles.",
          "Honest physical representation of period exhaustion without clinical euphemisms.",
          "High organic sharing and comment engagement on women social channels."
      ],
      "techStack": [
          "2D Character Animation",
          "Frame-by-Frame Illustration",
          "After Effects",
          "Visual Storyboarding"
      ],
      "liveUrl": "/case-studies/rio-heavy-flow-animation",
      "liveUrlText": "Watch RIO Film &rarr;"
  }
];
