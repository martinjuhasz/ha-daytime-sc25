# daytime Smart Control SC25 – protocol notes

The SC25 has no public API documentation. Everything below was worked out from
the device's own web app (served by the controller, firmware **10102**) and
verified against a real controller. It is the reference for
`custom_components/daytime_sc25/api.py` and `daycycle.py`.

The SC25 is the successor of the SC20; the SC20 protocol was documented
independently by [dc0sk/daytime](https://github.com/dc0sk/daytime) and most of
it carries over. Differences are marked **SC25**.

## Transport

- `ws://<controller>/ws`, WebSocket sub-protocol `arduino`.
- JSON text frames. A frame is either one object or an **array of objects**.
- No authentication of any kind. Anyone on the network can control the device.
- Every frame has a `title`. Requests carry `"from": "USER"` and a target in
  `to`: `MASTER` for reads, `ALL-LIGHTS` for commands (mesh broadcast).
- Every frame the controller sends is **broadcast to all connected clients**,
  including other clients' commands (echoed with `from: USER`). Clients must
  drop frames with `from: USER`. Several clients (Home Assistant, the vendor web
  app) can be connected at the same time.
- The device occasionally sends `{"title":"REQ_KEEP_ALIVE","to":"ALL"}`. The
  vendor app does not answer it; connections stay open without a reply.

## Connect

On connect the controller pushes its full state unprompted, as two arrays:

```text
[USRDTA, MAX_CHANNEL_VALUES, CLOCK, NET_ST, NET_AP, MESH_NETWORK]
[CCV, MOON, CLOUD, ACCLIMATE, DSCRPTN, DYCL, SCNR]
```

**Pitfall:** replies to `GET_*` requests sent right after connecting can
overtake this burst. The burst's `CLOCK` then arrives *after* a mode change made
in the meantime and still carries the old mode. Wait for the burst and only
request state as a fallback.

`NET_AP.apPW` contains the access-point password (base64). Do not store or log it.

## Reads

| Request (`to: MASTER`) | Reply |
|---|---|
| `GET_USRDTA` | `USRDTA` – name, `channelCount`, `revision`, `latestAvailableRevision`, `moduleTemp`, `mode` |
| `GET_CLOCK` | `CLOCK` – local time, `mode`, and in manual mode `duration`, `fallbackActive`, `remaining` |
| `REQ_CCV` | `CCV` – live output `currentValues: [w, b, r, g]` including effects |
| `GET_DSCRPTN` / `GET_DYCL` | daycycle settings / curve (see below) |
| `GET_MOON` / `GET_CLOUD` / `GET_ACCL` | effect settings plus runtime status |
| `GET_SCNR` | `SCNR` – 10 colour favourites |
| `GET_NET_ST` | `NET_ST` – `stSSID`, `ip`, `dhcp` (`stPW` is only `"Yes"`) |
| `GET_CCMODE` (`to: ALL-LIGHTS`) | `CCMODE` – current mode |

Writes are **never acknowledged**. Read back after writing; the vendor app waits
about 700 ms before reading settings back.

## Channels (SC25)

Channel arrays always have **four** entries in protocol order
**white, blue, red, green**, integer percent 0–100 — regardless of the lamp. The
number of channels actually used is `USRDTA.channelCount`; a one-channel lamp
uses white only, two channels white + blue, three white + blue + red.

## Modes

```json
{"title": "MAN_MODE", "to": "ALL-LIGHTS", "from": "USER", "duration": 300, "fallbackActive": false}
{"title": "DAYCL_MODE", "to": "ALL-LIGHTS", "from": "USER"}
{"title": "CCV-SL", "to": "ALL-LIGHTS", "from": "USER", "currentValues": [80, 100, 20, 10]}
```

- **SC25:** `MAN_MODE` takes `duration` (60–86400 s) and `fallbackActive`. With
  `fallbackActive: true` the controller returns to the daycycle by itself and
  announces it with `CCMODE` + `CCV`. The vendor app enables this by default
  with 300 s.
- `CCV-SL` only has an effect in manual mode.
- After a mode change the device pushes `CCV` again a little later with the
  *old* values. Wait ~0.5 s before writing new values, and verify the readback.
- A `GET_CCMODE` reply can still show the previous mode right after a switch;
  retry until it matches.

## Daycycle

Two frames describe the schedule:

- `DSCRPTN.description` – the vendor app's easy-mode settings as a
  `key:value;…` string:

  ```text
  confId:10;expMode:false;start:480;end:1260;sunrise:60;sunset:60;intensity:100;
  individual:false;sunGlowEnabled:false;sunriseGlowDuration:30;sunriseGlowIntensity:1;
  sunsetGlowDuration:30;sunsetGlowIntensity:1;middayDimmingEnabled:false;
  middayDimmingStart:660;middayDimmingEnd:840;middayDimmingIntensity:60;intensities:100,0,0,0
  ```

  Times are minutes of the day. `sunGlow*` and `middayDimming*` are **SC25**.

- `DYCL.configuration` – the curve the controller actually plays, rows of
  `[minute, w, b, r, g]` from minute 0 to 1440, linearly interpolated.

The app recomputes the curve from the settings on every save and sends both
frames. `daycycle.build_curve` reproduces that computation for template
`confId 10`:

1. Base curve: dark until `start`, ramp to the day level by `start + sunrise`,
   hold until `end - sunset`, dark at `end`. The day level is `intensity` for
   all channels, or `intensities[i]` per channel when `individual` is true.
2. Midday dimming: insert the interpolated points at `start` and `end`, and
   points scaled by `middayDimmingIntensity` % at `start + 15` and `end - 15`.
3. Sunrise/sunset glow (only with a red channel): insert a red-only point at
   `start + glowDuration // 2` and `end - glowDuration // 2`. The glow level
   slider goes 0–5; each step is 10 % red.

With `expMode:true` the curve was edited point by point; easy-mode settings no
longer describe it.

Preview: `{"title":"PREV-CRV","to":"ALL","previewTime":80,"startTime":0,"endTime":1439}`
plays the curve in fast motion and sends `PREV` frames with the play time. Any
mode command stops the preview.

## Effects

Settings are written by sending the whole frame back with changed fields
(runtime status fields removed):

| Frame | Settings | Runtime status (read-only) |
|---|---|---|
| `MOON` | `moonlightActive`, `maxmoonlight`, `minmoonlight`, `moonlightCycle`, `color` (channel letters, e.g. `"wb"`), `individualTimes`, `moonStart`, `moonEnd` | `currentCycleDay` (0–29.5), `currentIntensity` |
| `CLOUD` | `cloudActive`, `probability`, `maxAmount`, `minIntensity`, `maxIntensity`, `minDuration`, `maxDuration`, `mode` | `isCloudActive`, `cloudRemaining` (s), `cloudCurrentIntensity`, `nextCloudStart` (s since midnight, ≥ 86400 = none today), `nextCloudDuration` |
| `ACCLIMATE` | `acclActive`, `duration` (days), `intensityReduction`, `currentAcclDay`, `pause` | `currentAccReduction` (remaining light %, also computed while inactive) |

Cloud wire quirks: durations are **seconds** (the UI shows minutes), and the
intensities are inverted *and* swapped: UI cloud strength
`min = 100 - maxIntensity`, `max = 100 - minIntensity`.

Pause acclimation: `{"title":"PAUSE_ACCLIMATION","to":"ALL-LIGHTS","pause":1}`.

## Favourites (SCNR, SC25)

```json
{"title": "SCNR", "to": "ALL", "from": "USER",
 "scenarios": [{"name": "Evening", "icon": "", "channels": [40, 10, 90, 5]}, …]}
```

Exactly 10 slots; empty slots have an empty name and zero channels. Applying a
favourite means switching to manual mode and sending its channels with `CCV-SL`.

## Device

- Rename: `{"title":"USRDTA","to":"<mac>","name":"…"}`.
- Set clock: `CLOCK` with `year`, `month` (1-based), `day`, `hour`, `min`, `sec`
  in local time. The web app adds 1 to the JavaScript month before sending.

## Deliberately not used

Network setup (`NET_ST`/`NET_AP` writes, scans), mesh pairing, `RESET_TO_DEFAULT`
and firmware updates (`START_FOTA`, `/update`). A mistake there can leave the
controller unreachable; use the vendor web app.
