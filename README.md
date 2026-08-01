# 🚀 Mindmaxing Creatives — Product Studio Portfolio

> **"We notice problems and then go build the thing."**

**Mindmaxing Creatives** is an independent product studio based in India. This repository contains the flagship interactive web experience for **[mindmaxing.one](https://mindmaxing.one)** — showcasing 11 active products, custom 3D shaders, an interactive Resend-powered contact lead engine, and a dedicated founder showcase for **Aryan**.

---

## 🌐 Live URLs

- **Official Domain**: [https://mindmaxing.one](https://mindmaxing.one)
- **Cloudflare Pages Production**: [https://mindmaxing-creatives.pages.dev](https://mindmaxing-creatives.pages.dev)
- **GitHub Repository**: [https://github.com/Aryu55/mindmaxing-creatives](https://github.com/Aryu55/mindmaxing-creatives)

---

## ⚡ Key Highlights & Features

- **Interactive 3D WebGL Background Shaders**: Custom Three.js liquid FBM noise field that dynamically shifts ambient gradient palettes as you scroll through products.
- **3D Morphing Glass/Metal Orb**: Real-time vertex displacement shader reacting to cursor position and scroll depth.
- **GSAP Panel & Typography Reveals**: Fluid scroll-triggered line reveals and panel transitions matching high-end design aesthetics.
- **Resend-Powered Serverless Lead Engine**: Integrated glassmorphism contact modal that POSTs lead inquiries directly to Cloudflare Pages Serverless Function (`/functions/api/contact.js`) which proxies secure emails to `mindmaxxxing@gmail.com` via Resend API.
- **Meet the Founder Showcase**: Dedicated section spotlighting founder **Aryan**, highlighting key achievements (4 profitable AI products, Fortune 500 training, ₹20 Cr+ alumni earnings in 2025, 1:1 C-suite consulting).
- **100% Mobile Optimized**: Responsive fluid typography (`clamp()`), automatic rail index collapsing on mobile viewports, touch-friendly bottom-sheet lead modal with iOS 16px auto-zoom prevention.
- **11 Active Showcase Products**:
  1. **SafeSpot** (`trysafespot.com`): Pre-date verification & background safety checking engine.
  2. **Hisaab** (`hisaab-lilac-rho.vercel.app`): Employment FnF legal notice & Labour Commissioner pack builder.
  3. **Before Token** (`before-token.vercel.app`): Real estate brochure vs MahaRERA registry risk screener.
  4. **Freedoms AI** (`freedoms.ai/join`): Voice capture & nightly memory pass AI journaling assistant.
  5. **BUKL** (`bukl.co`): Ultralight friction-lock belt direct-to-consumer storefront.
  6. **Xalt Watches** (`xaltwatches.com`): Swiss luxury timepiece storefront with bilingual Gulf checkout.
  7. **Manifest** (`manifest.leblessed.com/lp01`): Direct response book funnel & conversion engine.
  8. **WhatsApp Autopilot** (`whisper-buddy-21.mindmaxing.workers.dev`): 5-stage automated webinar attendance & support bot.
  9. **Glaze** (`getglaze.in`): Anonymous peer feedback loop app.
  10. **Pause**: Native Android distraction blocker built for habit change.
  11. **Janus** (`janus-engine.vercel.app`): Multi-business content command centre and DM pipeline.

---

## 🛠️ Architecture & Tech Stack

- **Core**: HTML5, Vanilla JavaScript (ESNext), Three.js (r128), GSAP (3.12.5)
- **Design & Styling**: Custom Dark Glassmorphism Design System, Fluid Typography (`clamp()`), Custom SVG Chevron Select Dropdowns, HSL Tailored Palettes
- **Serverless Edge Backend**: Cloudflare Pages Functions (`/functions/api/contact.js`)
- **Transactional Email**: Resend API (`api.resend.com/emails`)
- **Hosting & Infrastructure**: Cloudflare Pages, Cloudflare DNS (`mindmaxing.one`)

---

## 📜 Full Changelog & Evolution History

### v1.4.0 (2026-08-01)
- 🚀 **GitHub Repository Launch**: Published open-source project to `Aryu55/mindmaxing-creatives`.
- 💵 **USD Budget Selection Dropdown**: Converted budget field to a styled dark glass `<select>` dropdown ranging from `$1,000` up to `$20,000+`. Replaced en-dashes with clean hyphens.
- 🔒 **Privacy Protection Update**: Removed raw email address display from the lead submission success banner to prevent UI email harvesting.

### v1.3.0 (2026-08-01)
- 👤 **"Meet Aryan" Founder Section**: Built a dark glass profile section showcasing Aryan's photo, bio, and key achievements (4 profitable AI products, Fortune 500 advisory, ₹20 Cr+ alumni earnings in 2025).
- 🖼️ **Icon & Favicon Fix**: Updated `favicon.ico`, `favicon.png`, and `apple-touch-icon.png` with the official 500x500 1:1 red & black MindMaxing logo icon with `?v=3` cache-busting headers.

### v1.2.0 (2026-08-01)
- 📱 **Mobile Layout & Typography Optimization**: Fixed top margin alignment on mobile headers. Set fluid typography scaling (`clamp(36px, 9.5vw, 56px)`). Auto-collapsed sidebar rail index on mobile screens for 100% full-width showcase cards.
- ⚡ **Global Event Delegation Fix**: Resolved `support.js` React template mounting issue by implementing top-level event delegation (`document.addEventListener('click')`) and global `window.openContactModal(e)` trigger.
- 🔍 **DevTools Console Diagnostics**: Added `[Mindmaxing]` log prefixes across all modal triggers and API fetch payloads for instant debugging.

### v1.1.0 (2026-08-01)
- 📩 **Resend Lead Modal Integration**: Embedded glassmorphism modal with inputs for Name, Email, Phone, Budget, and Problem details.
- ⚡ **Cloudflare Pages Serverless Function**: Created `/functions/api/contact.js` proxying inquiries to `mindmaxxxing@gmail.com` via Resend API (`re_gn3FwoXw...`).
- 🗑️ **Product Lineup Cleanup**: Removed RoofHero, cleanly renumbering the showcase to 11 active live products.
- 🌐 **Custom Domain Integration**: Attached `mindmaxing.one` and `www.mindmaxing.one` via Cloudflare REST API & CNAME routing.

### v1.0.0 (2026-08-01)
- Initial release of the Mindmaxing Creatives interactive 3D WebGL product studio portfolio.

---

## 🛠️ Local Development & Deployment

### 1. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 2. Deploy to Cloudflare Pages
```bash
npm run deploy
```
or via Wrangler CLI:
```bash
npx wrangler pages deploy . --project-name mindmaxing-creatives
```

---

## 📬 Contact & Enquiries

- **Lead Form**: [https://mindmaxing.one/#contact](https://mindmaxing.one/#contact)
- **Target Recipient**: `mindmaxxxing@gmail.com`
