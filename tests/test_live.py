"""Live test against a real SC25, run inside the Home Assistant test harness.

    SC25_HOST=192.168.1.50 pytest tests/test_live.py

Changes mode and channel values on the device and returns it to the daycycle
at the end. Effect switches are toggled and switched back off.
"""

from __future__ import annotations

import asyncio
import os

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
import pytest
import pytest_socket

from custom_components.daytime_sc25.api import _is_status_field
from custom_components.daytime_sc25.const import CONF_MANUAL_FALLBACK, DOMAIN

HOST = os.environ.get("SC25_HOST")

pytestmark = pytest.mark.skipif(not HOST, reason="SC25_HOST not set")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def allow_sc25_host(socket_enabled):
    # The HA test plugin restricts sockets to 127.0.0.1 before fixtures run.
    pytest_socket.socket_allow_hosts(["127.0.0.1", HOST], allow_unix_socket=True)
    yield


def _eid(hass: HomeAssistant, entry, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.unique_id}_{key}")
    assert entity_id, f"{platform} {key} missing"
    return entity_id


async def _call(hass: HomeAssistant, domain: str, service: str, entity_id: str, **data):
    await hass.services.async_call(domain, service, {"entity_id": entity_id, **data}, blocking=True)
    await hass.async_block_till_done()


def _outputs(hass: HomeAssistant, entry) -> list[int]:
    return [
        int(hass.states.get(_eid(hass, entry, "sensor", f"output_{c}")).state)
        for c in ("white", "blue", "red", "green")
    ]


async def test_live(hass: HomeAssistant) -> None:
    # --- config flow ------------------------------------------------------
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert entry.unique_id and ":" in entry.unique_id

    # Duplicate setup is rejected.
    dup = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    dup = await hass.config_entries.flow.async_configure(dup["flow_id"], {CONF_HOST: HOST})
    assert dup["type"] is FlowResultType.ABORT and dup["reason"] == "already_configured"

    lamp = _eid(hass, entry, "light", "light")
    blue = _eid(hass, entry, "light", "channel_blue")
    mode = _eid(hass, entry, "select", "mode")
    moon = _eid(hass, entry, "switch", "moonlight")
    clouds = _eid(hass, entry, "switch", "clouds")
    temp = _eid(hass, entry, "sensor", "module_temperature")
    print("entities:", sorted(s.entity_id for s in hass.states.async_all()))

    assert hass.states.get(mode).state in ("daycycle", "manual")
    assert float(hass.states.get(temp).state) > 0
    attrs = hass.states.get(mode).attributes
    assert len(attrs["daycycle"]) >= 2 and len(attrs["daycycle"][0]) == 5
    assert attrs["channel_count"] == 4 and "day_start" in attrs

    try:
        # --- master light -------------------------------------------------
        await _call(hass, "light", "turn_on", lamp, brightness_pct=50)
        if hass.states.get(mode).state != "manual":
            t0 = entry.runtime_data.trace[0][0]
            for t, d, f in entry.runtime_data.trace:
                if "USRDTA" not in f and "DYCL" not in f:
                    print(f"{t - t0:7.3f} {d} {f[:170]}")
        assert hass.states.get(mode).state == "manual"
        assert _outputs(hass, entry) == [50, 50, 50, 50]
        assert hass.states.get(lamp).state == "on"
        assert hass.states.get(lamp).attributes["brightness"] == 128

        # --- single channel -----------------------------------------------
        await _call(hass, "light", "turn_on", blue, brightness_pct=30)
        assert _outputs(hass, entry) == [50, 30, 50, 50]

        # Master brightness keeps the colour ratio.
        await _call(hass, "light", "turn_on", lamp, brightness_pct=100)
        assert _outputs(hass, entry) == [100, 60, 100, 100]

        # Off and on again restores the previous mix.
        await _call(hass, "light", "turn_off", lamp)
        assert _outputs(hass, entry) == [0, 0, 0, 0]
        assert hass.states.get(lamp).state == "off"
        await _call(hass, "light", "turn_on", lamp)
        assert _outputs(hass, entry) == [100, 60, 100, 100]

        # Values stay put (no late stale push from the device).
        await asyncio.sleep(3)
        assert _outputs(hass, entry) == [100, 60, 100, 100]

        # --- effects --------------------------------------------------------
        for switch in (moon, clouds):
            await _call(hass, "switch", "turn_on", switch)
            assert hass.states.get(switch).state == "on"
            await _call(hass, "switch", "turn_off", switch)
            assert hass.states.get(switch).state == "off"

        # --- back to daycycle ------------------------------------------------
        await _call(hass, "select", "select_option", mode, option="daycycle")
        assert hass.states.get(mode).state == "daycycle"

        # --- options: automatic fallback ----------------------------------
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_MANUAL_FALLBACK: 2}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.state is config_entries.ConfigEntryState.LOADED
        lamp = _eid(hass, entry, "light", "light")
        await _call(hass, "light", "turn_on", lamp, brightness_pct=20)
        clock = entry.runtime_data.state.get("CLOCK")
        assert clock.get("fallbackActive") is True and clock.get("duration") == 120
    finally:
        await _call(hass, "select", "select_option", mode, option="daycycle")
        assert hass.states.get(mode).state == "daycycle"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_live_settings(hass: HomeAssistant) -> None:
    """Every new setting entity against the real device, then restore."""
    import copy

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    client = entry.runtime_data
    st = client.state
    await client.request_and_wait("GET_SCNR", "SCNR")
    backup = {
        t: copy.deepcopy(st.get(t))
        for t in ("MOON", "CLOUD", "ACCLIMATE", "DSCRPTN", "DYCL", "SCNR", "USRDTA")
    }
    e = lambda p, k: _eid(hass, entry, p, k)  # noqa: E731
    try:
        await _call(hass, "time", "set_value", e("time", "day_start"), time="07:30:00")
        await _call(hass, "number", "set_value", e("number", "sunrise_duration"), value=45)
        await _call(hass, "switch", "turn_on", e("switch", "sun_glow"))
        await _call(hass, "number", "set_value", e("number", "sunrise_glow_intensity"), value=3)
        s = st.daycycle_settings
        assert (s.start, s.sunrise, s.sun_glow, s.sunrise_glow_intensity) == (450, 45, True, 3)
        assert [465, 0, 0, 30, 0] in st.daycycle  # glow point read back from device
        assert hass.states.get(e("time", "day_start")).state == "07:30:00"

        await _call(hass, "number", "set_value", e("number", "cloud_strength_max"), value=70)
        await _call(hass, "number", "set_value", e("number", "cloud_duration_max"), value=20)
        assert st.get("CLOUD")["minIntensity"] == 30 and st.get("CLOUD")["maxDuration"] == 1200

        await _call(hass, "switch", "turn_on", e("switch", "moon_blue"))
        await _call(hass, "number", "set_value", e("number", "moon_max"), value=22)
        assert "blue" in st.moon_channels and st.get("MOON")["maxmoonlight"] == 22

        await _call(hass, "number", "set_value", e("number", "acclimation_days"), value=12)
        await _call(hass, "switch", "turn_on", e("switch", "acclimation_pause"))
        assert st.get("ACCLIMATE")["duration"] == 12 and st.get("ACCLIMATE")["pause"] == 1

        fav = e("select", "favorite")
        await hass.services.async_call(
            DOMAIN,
            "save_favorite",
            {"entity_id": fav, "slot": 10, "name": "HA Live", "channels": [5, 15, 25, 35]},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert "HA Live" in hass.states.get(fav).attributes["options"]
        await _call(hass, "select", "select_option", fav, option="HA Live")
        assert st.current_values == [5, 15, 25, 35] and st.mode == "MAN_MODE"
        assert hass.states.get(fav).state == "HA Live"

        await _call(hass, "text", "set_value", e("text", "controller_name"), value="SC25 HA Live")
        assert st.get("USRDTA")["name"] == "SC25 HA Live"
        await _call(hass, "button", "press", e("button", "sync_clock"))
        assert st.get("CLOCK").get("valid") == 1
    finally:

        async def put(title, request, body, to="ALL-LIGHTS"):
            await client.send({**body, "title": title, "to": to, "from": "USER"})
            await asyncio.sleep(0.8)
            await client.request_and_wait(request, title)

        def strip(frame, title):
            return {
                k: v
                for k, v in frame.items()
                if k not in ("title", "from", "to") and not _is_status_field(title, k)
            }

        for title, request in (
            ("MOON", "GET_MOON"),
            ("CLOUD", "GET_CLOUD"),
            ("ACCLIMATE", "GET_ACCL"),
        ):
            await put(title, request, strip(backup[title], title))
        await put("DSCRPTN", "GET_DSCRPTN", {"description": backup["DSCRPTN"]["description"]})
        await put("DYCL", "GET_DYCL", {"configuration": backup["DYCL"]["configuration"]})
        await put("SCNR", "GET_SCNR", {"scenarios": backup["SCNR"]["scenarios"]}, to="ALL")
        await put("USRDTA", "GET_USRDTA", {"name": backup["USRDTA"]["name"]})
        await client.set_mode(False)
        for title in ("MOON", "CLOUD", "ACCLIMATE", "DSCRPTN", "DYCL", "SCNR"):
            assert strip(st.get(title), title) == strip(backup[title], title), title
        assert st.get("USRDTA")["name"] == backup["USRDTA"]["name"]
        assert st.mode == "DAYCL_MODE"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
