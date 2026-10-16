# Contributing

Thanks for helping! Issues and pull requests are welcome.

## Before you start

- For larger changes, open an issue first so we can agree on the approach.
- The protocol is reverse engineered. If you find new behaviour, add it to
  [docs/protocol.md](docs/protocol.md) together with how you verified it.
- Never commit captures that contain your Wi-Fi or access-point password, MAC
  addresses or other personal data.

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
```

## Checks

All of these run in CI and must pass:

```bash
ruff check .
ruff format --check .
node --check custom_components/daytime_sc25/frontend/daytime-sc25-card.js
pytest
```

`pytest` runs against `tests/fake_sc25.py`. If you change how the integration
talks to the device, update the fake so it keeps matching the real controller,
and, if you have one, run the live test:

```bash
SC25_HOST=<ip> pytest tests/test_live.py
```

The live test switches modes, writes settings and favourites on the real
controller and restores them at the end. Timing-related bugs have shown up only
without debug logging, so run it a few times.

## Releases

1. Bump `version` in `manifest.json` and `CARD_VERSION` in the card, and add a
   section to `CHANGELOG.md`.
2. Merge to `main`, then tag: `git tag v0.4.0 && git push --tags`.
3. The release workflow checks that tag, manifest and card versions match and
   publishes the GitHub release that HACS installs from.
