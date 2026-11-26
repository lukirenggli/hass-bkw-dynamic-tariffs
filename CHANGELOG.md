# Changelog

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
