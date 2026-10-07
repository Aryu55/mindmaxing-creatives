# Website verification — 27 September 2026

## Verified locally

- `npm test`: 5 tests passed. Covers static generation, 24 unique project routes/social metadata, public output isolation, deterministic demo allocation, retry/deduplication, cart boundaries, and mocked contact HTML escaping with project context.
- `tests/site-browser.cjs`: passed in headless Chrome. All 24 project routes load, their stated interaction works, and Reset restores the initial state.
- Browser checks cover 1440px desktop and every project/demo at 390px and 768px; no horizontal overflow. Desktop/mobile screenshots were inspected.
- Search/category URL state and Back navigation, old archive and homepage hash links, new-tab return-to-index, mobile navigation, reduced motion, expansion retaining state, and mocked contact success all passed.
- Resilience checks: no iframe before request; parent-origin readiness spoof ignored; simulated demo initialization failure restores the cover and retry succeeds; contact failure preserves the brief and context; JavaScript-disabled form submission uses POST without putting personal fields in its URL.
- No page exceptions or failed page assets in the normal browser journeys.
- Syntax checks and tracked-file whitespace checks passed.
- Independent code review found two issues (new-tab return navigation and native form GET fallback). Both were corrected and covered by the final browser run.

## After-dark revision verification

- Final `npm test`: all 5 tests pass.
- Final `tests/site-browser.cjs`: passes all 24 routes, interactions and resets at desktop, plus responsive checks for every project/demo at 390px and 768px.
- Additional assertions verify working homepage material changes via canvas pixels, project colour propagation into isolated frames, and garment pixels staying inside canvas bounds at 390/768/1440.
- Hero initialization failure leaves the close-up visible, disables unavailable swatches and preserves the project link. Demo timeout/retry and mocked contact recovery still pass.
- Reduced motion, keyboard material selection, image loading, URL filters/Back navigation, legacy links, contact context and expanded-demo state remain functional.
- Updated authoring previews/social images were regenerated. Photography uses reserved image dimensions and responsive 900px/2200px sources. No external image request is required at runtime.
- Homepage and Knittire screenshots were inspected at all three requested widths. The review is recorded in `design-qa.md`.
- New source files pass Node syntax checks. No page exceptions or failed resources were reported by the final browser run.

## Boundaries

This verifies the local website, not production deployment or live contact delivery. No real contact messages were sent. The contact API was mocked in tests; the preview returns an explanatory 503.

All sandboxes are labelled reconstructions with synthetic fixtures. Twelve projects include captured public interfaces; those captures do not establish client outcomes or code ownership. Saffron Origins was corrected to apparel and Janus to content queues after inspecting their public interfaces. No unsupported growth/performance figures are published as Mindmaxing results.

The deployment output is `dist/` (approximately 4.2 MB), generated from the allowlisted website assets/templates. Private repository material and the original unverified dossier are excluded. Existing contact function source remains outside the static output for Cloudflare Pages compilation.

No production release, commit or pull request was created. Work remains in the local `codex/demonstrable-studio` branch.
