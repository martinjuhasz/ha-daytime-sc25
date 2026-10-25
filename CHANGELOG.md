# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning](https://semver.org/).

## [0.3.6] - 2026-10-25

### Changed

- Info card: the light badge is the same round, glowing orb as on the control
  card, and next to it only the brightness is shown – no colour name or hex
  value. The scheduled line shows just the planned level.

## [0.3.5] - 2026-10-24

### Fixed

- Cards: entity names, attributes and entity ids from the card configuration
  are HTML-escaped before rendering, so markup in a friendly name no longer
  ends up in the dashboard.

### Changed

- README: installation leads with searching for the integration in HACS.

## [0.3.4] - 2026-10-16

### Changed

- Info card: sunrise and sunset are marked above the 24 h light band with
  their configured time ranges.

## [0.3.3] - 2026-10-16

First public release.

### Added

- Local push integration for the daytime Smart Control SC25 over its WebSocket
  API, set up from the UI.
- Lamp light (keeps the colour ratio when dimming) and one light per colour channel.
- Mode select (daycycle / manual) with optional automatic return to the daycycle.
- Colour favourites: apply via select, `save_favorite` / `delete_favorite` services.
- Daycycle settings as entities (day start/end, sunrise/sunset, brightness,
  per-colour brightness, midday dimming, sunrise/sunset glow), computed exactly
  like the vendor app; `set_daycycle_curve` for free-form curves; fast-motion preview.
- Moonlight, clouds and acclimation: on/off plus all settings.
- Status: live output per channel, module temperature, cloud passing / next
  cloud, moon phase, acclimation progress, Wi-Fi and IP, firmware update notice.
- Two Lovelace cards served by the integration: a control card with settings
  and a compact info card with the mixed colour and a 24 h light band.
