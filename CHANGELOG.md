# Changelog


## 1.1.0

### Marketplace / CI preparation fixes (before first release)

- Load the real HA network component and preflight its HTTP/DNS client before the config flow in the smoke test; addresses the reported `KeyError: network`.

- Initialize the Home Assistant integration loader and base registries/helpers before component setup in the real-HA smoke test; fixes the reported bootstrap `KeyError: integrations`.

- Pin GitHub runners to Ubuntu 24.04; use stable Python 3.14 patches with a minimum-version check (3.14.2).
- Update checkout and setup-python actions to v7 / Node 24.
- Move the editable SVG icon to assets/icon.svg; keep only supported PNG brand images.
- Guard brand file names and CI runner configuration in repository checks.
- Correct stale README version text and document the required manual GitHub topics, old-file deletion and catalog submission.

- Add all 19 screenshot entities with the exact requested enabled/disabled defaults.
- Add a published-tariff forecast sensor with upcoming prices as structured attributes.
- Add tomorrow's average, continuous cheap/expensive 2/4-hour windows and memberships.
- Add 10/25/50-percent cheap/expensive price-slot groups, including tied prices.
- Use one coherent coordinator snapshot at minute/tariff/window boundaries.
- Expose local evaluation time and API-attempt time separately from successful API updates.
- Prevent duplicate/late clock callbacks and stale error reporting for queued refresh clicks.
- Replace the banner with bright sunshine, solar house, yellow export arrow, chart and pylons; no battery.
- Preserve existing entity unique IDs and user activation choices.
- Extend offline regression tests and the real-HA CI smoke test.

Prepared update; live HA, Hassfest and Marketplace CI validation still required before release.


## 1.0.0

- Initial BKW dynamic feed-in API implementation.
- Twelve-hour API polling, local minute/interval updates and Swiss-day rollover.
- Current price, complete-day weighted average/min/max, next actual price change.
- Two threshold binary sensors, two persistent number controls and refresh button.
- API-update diagnostic and downloadable diagnostics.
- German/English UI, original local brand assets and Marketplace metadata.
- Unit tests, Home Assistant smoke test, Hassfest and Marketplace validation workflows.

Prepared version; publish only after GitHub checks and real installation tests pass.
Known limitation: twelve-hour polling cannot guarantee uninterrupted future data coverage.
