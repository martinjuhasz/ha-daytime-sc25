# ha-daytime-sc25

Home Assistant custom integration (`custom_components/daytime_sc25`) for the
daytime Smart Control SC25 aquarium light controller, plus two Lovelace cards in
one JS file served by the integration. Published via HACS; users install from
GitHub releases.

Read [docs/protocol.md](docs/protocol.md) before touching `api.py`,
`daycycle.py` or `tests/fake_sc25.py`. Checks and the release flow are in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Where things live

- `api.py` – the only module that speaks the wire protocol: connection, state
  frames, commands with readback. Entities never build frames themselves.
- `daycycle.py` – easy-mode settings (`DSCRPTN`) and the curve (`DYCL`) the
  vendor app derives from them. Pure functions, no I/O.
- `settings.py` – declarative table of every number/time/switch setting
  (getter, setter, range). Wire unit conversions live here, nowhere else.
- `frontend/daytime-sc25-card.js` – both cards, no build step. The info card
  subclasses the control card.

## Protocol rules

The device acknowledges nothing and broadcasts everything, so every command
**reads back** and compares. Behaviour that broke real runs:

- The connect burst can arrive after replies to `GET_*`; its stale `CLOCK`
  then undoes a fresh mode change. Wait for the burst; request only as fallback.
- After a mode change the device pushes the *old* `CCV` a moment later. Let it
  settle before writing channel values, and verify the readback.
- `MODE_GUARD`: for 3 s after a `CCMODE` confirmation, a `CLOCK` reporting
  another mode is stale and ignored. Real device-side changes arrive as `CCMODE`.
- Frames with `from: USER` are other clients' echoes — drop them.
- Channels are always four, in order white, blue, red, green.

Timing bugs here vanish under debug logging. Reproduce them with the live test
run repeatedly **without** logging; `client.trace` keeps the last 200 frames.

## Cards

- HA swaps `window.customElements` for a scoped-registry polyfill during boot.
  A cached card can run first and land in the old registry, which shows as a
  permanent "Configuration error". The `register()` watcher re-registers a
  fresh subclass for 60 s — keep it.
- The card URL carries `?v=<mtime>` computed at HA startup: a changed card only
  reaches browsers after an HA restart.
- UI strings live in the card's `TEXT` table (de + en); keep both complete.

## Tests

- `tests/fake_sc25.py` is the stand-in controller. When you learn new device
  behaviour, teach the fake the same quirk and add a test that fails without
  the fix.
- `tests/test_live.py` runs only with `SC25_HOST` set and **changes the real
  controller** (mode, settings, favourites, name), restoring them at the end.
  Run it only when the user asks and the controller may be switched.

## Stable contracts

- Unique IDs are `<mac>_<key>`; renaming a key in `settings.py` or a platform
  orphans users' entities and automations.
- `strings.json` and `translations/en.json` are identical; `de.json` mirrors
  every key.
- Minimum Home Assistant version is set in `hacs.json`.

## Privacy

This repo is public. Test data, docs and screenshots use placeholders (MAC
`AA:BB:CC:DD:EE:01`, name `SC25_12345678`, IP `192.168.1.50`). Real MACs, device
names, IPs, SSIDs and the access-point password (`NET_AP.apPW`) never enter
code, logs or commits.

## Scope

Wi-Fi/AP setup, mesh pairing, factory reset and firmware flashing stay out on
purpose: a mistake there can leave the controller unreachable.

## Releases

`manifest.json` `version`, `CARD_VERSION` in the card and the git tag `vX.Y.Z`
must match, with a matching `CHANGELOG.md` section; the release workflow
refuses otherwise.
