# Mindmaxing Studio website

The current website is generated from `projects.mjs` and `templates.mjs`. The older root HTML files and `public/` directory are legacy material and are **not** the deployment source.

## Develop and build

- `npm run dev` builds the website and serves `dist/` on port 3000. Set `PORT=3001` if needed.
- `npm run build` produces the website-only `dist/` directory. It never copies the repository as a whole.
- `npm test` runs build, data, demo-logic and contact-function checks.
- `npm run test:browser` builds and checks routes, interactions and responsive layouts in headless Chrome. Install Playwright first, or expose an existing installation through `NODE_PATH`.

The simple local preview deliberately returns an explanatory 503 for contact submission. It cannot send email. The existing Cloudflare Pages function handles production contact delivery through `RESEND_API_KEY`; local/browser tests mock that service.

## Authoring projects

`projects.mjs` is the public editorial layer. Original unverified records remain in the root `case-studies-data.js` and are not shipped to the browser. Do not copy numerical claims from those records into the public layer without source evidence.

Each public record provides a stable slug, plain-language summary, contribution, demonstration instruction, engineering explanation and limitations. The build emits a full HTML page at `/case-studies/{slug}` with its own metadata and social image. Links from the former `.html#slug` archive still resolve.

Original public captures are in `assets/projects/`. Demo previews are in `assets/previews/` and represent the functional reconstruction, not the original application. Social cards are in `assets/social/`. Optional `node scripts/render-site-media.cjs` regenerates previews and social cards against a running preview (default port 3001); it requires Playwright and Sharp. These are authoring dependencies only. The normal build has no image-tool or browser dependency.

## Demo boundaries

All 24 records have small local demonstrations or guided creative reconstructions. They run in an opaque-origin iframe with only `allow-scripts`. They cannot access the parent DOM, send network requests, navigate the parent, submit payments or contact anyone. CSP blocks network connections and form submission.

Parent messages accept only the active iframe's `contentWindow` with opaque origin `null`. The child validates `event.source === parent`. Recognised events are readiness, bounded frame height, visibility and Escape-to-close. Unknown messages are ignored. Expansion changes the existing frame's presentation without moving or reloading it, retaining demo state.

The WebGL garment is a new procedural demonstration model. Voice extraction is a prepared transcript walkthrough. Legal/property/identity examples use fictional fixtures and do not perform searches or generate actionable advice. No reconstructed demonstration is presented as original production source.

## Release

Cloudflare Pages is configured to publish `dist/`. The contact function remains in `functions/api/contact.js`, outside the static output. `npm run deploy` is a separate explicit release action; it has not been run as part of implementation.

Keep the existing service secret and verify the contact sender configuration in the deployment environment before expecting live delivery. The local test results do not establish that production credentials work.

## After-dark presentation

The homepage photograph is served locally in 900px and 2200px WebP variants. Photographer/source/licence details live in `assets/atmosphere/ATTRIBUTION.md`. Crop and directional overlays are controlled in `studio.css`.

`hero-preview.js` lazily imports the shared procedural garment renderer while the opening is visible. Swatches redraw on input; there is no render loop. Fine-pointer depth is bounded, and reduced motion disables it. If the renderer fails, the close-up image and project link remain available.

The build generates `demos/theme.css` from each public project's `accent`. Keep those colour choices in `projects.mjs`; no additional frame messaging or permissions are needed. `site/review/design-qa.md` records the visual checks.
