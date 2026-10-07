# Colour and Life After Dark — design review

Reviewed locally on 27 September 2026.

## Reference and interpretation

The approved Lerone Pieters Manhattan photograph is the atmospheric reference, not a pixel-perfect page mockup. The implementation keeps its cold architecture, amber light and red movement. The desktop crop leaves the clock and street visible between the headline and garment. Mobile uses the portrait composition, with the headline followed by the demonstration.

Source, photographer and licence are retained in `site/assets/atmosphere/ATTRIBUTION.md`. Photography is not presented as a studio location or client project.

## Visual checks

- Homepage and Knittire inspected at 390, 768 and 1440 CSS pixels. Images are saved beside this report as `night-home-{width}.png` and `night-knittire-{width}.png`.
- Instrument Sans, the agreed headline and direct service description remain readable against a directional overlay. Amber, red and cold blue are retained in the photographic scene.
- Translucency is concentrated in navigation and the featured garment surface. Explanatory copy uses quiet, solid surfaces.
- The homepage garment changes immediately from the three labelled swatches. The project link remains available when WebGL initialization is unavailable.
- Knittire's cover now shows the garment close-up rather than a screenshot of controls. The larger model is framed without clipped shoulders at all checked widths.
- Six selected work entries retain authentic project captures where available. Their thumbnails are larger than the previous version.
- Each case study supplies its own colour token to the surrounding page and isolated demo. Saffron Origins, ABX Engine and Glaze were additionally inspected for warm, blue and lavender treatments. Outputs are larger; form controls no longer stretch into tall grid rows.
- Keyboard focus and Space activation were checked on the material controls; expanded demos retain state and their close control. Reduced motion keeps controls functional while removing atmosphere movement and spatial transitions.

## Corrections made during review

1. The enlarged garment initially clipped at tablet width. Its camera scale now accounts for both width and height, with rendered-pixel bounds checked in the browser suite.
2. Grid stretching made some demo buttons abnormally tall. Panels now align their content at its natural height.
3. The original thumbnail assertion assumed every lazy image loaded before scrolling. The test now scrolls to and decodes each thumbnail, retaining native lazy loading.
4. Project colour tokens are generated from the same public records for both pages and sandbox frames.
5. Hidden garment renderers pause resize redraws. The iframe combines parent visibility and document visibility before resuming activity.

## Remaining boundaries

The garment is an explicitly labelled procedural demonstration model. It is not the client's production model or a textile simulation. Screenshots and sample interactions do not establish production performance or client outcomes. No frame-rate, Core Web Vitals or conversion guarantee is claimed.

This is the local build. No production deployment or real contact submission was performed.
