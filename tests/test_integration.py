"""Full integration test against the fake SC25 (no hardware needed)."""

from __future__ import annotations

import asyncio

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.daytime_sc25.const import DOMAIN

from .fake_sc25 import FakeSC25


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def fake(socket_enabled):
    device = FakeSC25()
    await device.start()
    yield device
    await device.stop()


@pytest.fixture
async def entry(hass: HomeAssistant, fake: FakeSC25):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: fake.host}
    )
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    yield entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def eid(hass, entry, platform, key) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.unique_id}_{key}")
    assert entity_id, f"{platform}.{key} missing"
    return entity_id


async def call(hass, domain, service, entity_id, **data):
    await hass.services.async_call(domain, service, {"entity_id": entity_id, **data}, blocking=True)
    await hass.async_block_till_done()


def state(hass, entity_id):
    return hass.states.get(entity_id).state


async def test_entities_created(hass: HomeAssistant, entry) -> None:
    ids = {s.entity_id for s in hass.states.async_all()}
    assert len([i for i in ids if i.startswith("number.")]) == 23
    assert len([i for i in ids if i.startswith("sensor.")]) == 11
    assert len([i for i in ids if i.startswith("time.")]) == 6
    assert len([i for i in ids if i.startswith("switch.")]) == 13
    assert state(hass, eid(hass, entry, "update", "firmware")) == "off"
    assert state(hass, eid(hass, entry, "text", "controller_name")) == "SC25_12345678"


async def test_daycycle_settings_rebuild_curve(hass, entry, fake) -> None:
    await call(hass, "time", "set_value", eid(hass, entry, "time", "day_start"), time="07:00:00")
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "sunrise_duration"), value=90
    )
    await call(hass, "number", "set_value", eid(hass, entry, "number", "day_intensity"), value=80)
    await call(hass, "switch", "turn_on", eid(hass, entry, "switch", "midday_dimming"))

    desc = fake.state["DSCRPTN"]["description"]
    assert "start:420;" in desc and "sunrise:90;" in desc and "intensity:80;" in desc
    assert "middayDimmingEnabled:true" in desc
    curve = fake.state["DYCL"]["configuration"]
    assert curve[:3] == [[0, 0, 0, 0, 0], [420, 0, 0, 0, 0], [510, 80, 80, 80, 80]]
    assert [675, 48, 48, 48, 48] in curve
    mode = hass.states.get(eid(hass, entry, "select", "mode"))
    assert mode.attributes["daycycle"] == curve
    assert mode.attributes["day_start"] == 420


async def test_invalid_daycycle_is_rejected(hass, entry, fake) -> None:
    from homeassistant.exceptions import ServiceValidationError

    before = fake.state["DYCL"]["configuration"]
    # 08:00-09:00 cannot hold 60 min sunrise plus 60 min sunset.
    with pytest.raises(ServiceValidationError):
        await call(hass, "time", "set_value", eid(hass, entry, "time", "day_end"), time="09:00:00")
    assert fake.sent("DYCL") == [] and fake.sent("DSCRPTN") == []
    assert fake.state["DYCL"]["configuration"] == before


async def test_channel_intensity_enables_individual(hass, entry, fake) -> None:
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "day_intensity_blue"), value=40
    )
    desc = fake.state["DSCRPTN"]["description"]
    assert "individual:true" in desc and "intensities:100,40,0,0" in desc
    assert fake.state["DYCL"]["configuration"][2] == [540, 100, 40, 0, 0]
    assert state(hass, eid(hass, entry, "switch", "individual_intensities")) == "on"


async def test_cloud_units(hass, entry, fake) -> None:
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "cloud_duration_min"), value=5
    )
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "cloud_strength_max"), value=70
    )
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "cloud_strength_min"), value=10
    )
    cloud = fake.state["CLOUD"]
    assert cloud["minDuration"] == 300  # seconds on the wire
    assert cloud["minIntensity"] == 30  # 100 - strength max
    assert cloud["maxIntensity"] == 90  # 100 - strength min
    assert state(hass, eid(hass, entry, "number", "cloud_strength_max")) == "70.0"
    # status fields are never written back
    assert not any("isCloudActive" in p for p in fake.sent("CLOUD"))


async def test_moon_settings(hass, entry, fake) -> None:
    await call(hass, "number", "set_value", eid(hass, entry, "number", "moon_max"), value=20)
    await call(hass, "switch", "turn_on", eid(hass, entry, "switch", "moon_blue"))
    await call(hass, "switch", "turn_on", eid(hass, entry, "switch", "moon_white"))
    await call(hass, "time", "set_value", eid(hass, entry, "time", "moon_start"), time="22:30:00")
    moon = fake.state["MOON"]
    assert moon["maxmoonlight"] == 20 and moon["color"] == "wb" and moon["moonStart"] == 1350
    assert state(hass, eid(hass, entry, "switch", "moon_blue")) == "on"


async def test_acclimation(hass, entry, fake) -> None:
    await call(hass, "switch", "turn_on", eid(hass, entry, "switch", "acclimation"))
    await call(hass, "switch", "turn_on", eid(hass, entry, "switch", "acclimation_pause"))
    await call(
        hass, "number", "set_value", eid(hass, entry, "number", "acclimation_days"), value=14
    )
    acc = fake.state["ACCLIMATE"]
    assert acc["acclActive"] == 1 and acc["pause"] == 1 and acc["duration"] == 14
    assert fake.sent("PAUSE_ACCLIMATION")[-1]["pause"] == 1


async def test_favorites(hass, entry, fake) -> None:
    fav = eid(hass, entry, "select", "favorite")
    lamp = eid(hass, entry, "light", "light")
    await call(hass, "light", "turn_on", lamp, brightness_pct=60)
    await hass.services.async_call(
        DOMAIN, "save_favorite", {"entity_id": fav, "slot": 3, "name": "Abend"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN,
        "save_favorite",
        {"entity_id": fav, "slot": 1, "name": "Blau", "channels": [0, 80, 0, 10]},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert fake.state["SCNR"]["scenarios"][2] == {
        "name": "Abend",
        "icon": "",
        "channels": [60, 60, 60, 60],
    }
    assert hass.states.get(fav).attributes["options"] == ["Blau", "Abend"]
    assert state(hass, fav) == "Abend"  # current output matches

    await call(hass, "select", "select_option", fav, option="Blau")
    assert fake.state["CCV"]["currentValues"] == [0, 80, 0, 10]
    assert state(hass, fav) == "Blau"

    await hass.services.async_call(
        DOMAIN, "delete_favorite", {"entity_id": fav, "slot": 3}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(fav).attributes["options"] == ["Blau"]


async def test_expert_curve_service(hass, entry, fake) -> None:
    mode = eid(hass, entry, "select", "mode")
    points = [[0, 0, 0, 0, 0], [600, 50, 60, 70, 80], [1440, 0, 0, 0, 0]]
    await hass.services.async_call(
        DOMAIN, "set_daycycle_curve", {"entity_id": mode, "points": points}, blocking=True
    )
    await hass.async_block_till_done()
    assert fake.state["DYCL"]["configuration"] == points
    assert "expMode:true" in fake.state["DSCRPTN"]["description"]
    assert hass.states.get(mode).attributes["expert_mode"] is True


async def test_name_clock_preview(hass, entry, fake) -> None:
    await call(
        hass, "text", "set_value", eid(hass, entry, "text", "controller_name"), value="Becken"
    )
    assert fake.state["USRDTA"]["name"] == "Becken"
    await call(hass, "button", "press", eid(hass, entry, "button", "sync_clock"))
    clock = fake.sent("CLOCK")[-1]
    assert {"year", "month", "day", "hour", "min", "sec"} <= clock.keys()
    await hass.services.async_call(
        DOMAIN,
        "preview_daycycle",
        {"entity_id": eid(hass, entry, "select", "mode"), "seconds": 10},
        blocking=True,
    )
    await asyncio.sleep(0.2)  # fire-and-forget command, no readback
    prev = fake.sent("PREV-CRV")[-1]
    assert prev["previewTime"] == 10 and prev["startTime"] == 0 and prev["endTime"] == 1439


async def test_status_sensors(hass, entry, fake) -> None:
    assert state(hass, eid(hass, entry, "sensor", "moon_phase_day")) == "19.7"
    assert state(hass, eid(hass, entry, "binary_sensor", "cloud_passing")) == "off"
    assert state(hass, eid(hass, entry, "sensor", "next_cloud")) == "unknown"
    fake.state["CLOUD"].update(cloudActive=1, nextCloudStart=3600 * 14)
    await entry.runtime_data.request_and_wait("GET_CLOUD", "CLOUD")
    await hass.async_block_till_done()
    from homeassistant.util import dt as dt_util

    next_cloud = dt_util.parse_datetime(state(hass, eid(hass, entry, "sensor", "next_cloud")))
    assert dt_util.as_local(next_cloud).hour == 14


async def test_info_sensors(hass, entry, fake) -> None:
    wifi = hass.states.get(eid(hass, entry, "sensor", "wifi_network"))
    assert wifi.attributes["ip_address"] == "192.168.1.50"
    assert "stPW" not in wifi.attributes and "apPW" not in str(wifi.attributes)
    fake.state["ACCLIMATE"]["currentAccReduction"] = 50  # device computes it even when off
    await entry.runtime_data.request_and_wait("GET_ACCL", "ACCLIMATE")
    await hass.async_block_till_done()
    assert state(hass, eid(hass, entry, "sensor", "acclimation_level")) == "100"
    mode = hass.states.get(eid(hass, entry, "select", "mode"))
    assert mode.attributes["programmed_levels"] == [0, 0, 0, 0]  # fake clock: 00:15


async def test_card_is_served(hass, entry, hass_client) -> None:
    client = await hass_client()
    resp = await client.get("/daytime_sc25/daytime-sc25-card.js")
    assert resp.status == 200
    text = await resp.text()
    assert "daytime-sc25-card" in text and "daytime-sc25-info-card" in text


async def test_stale_clock_does_not_undo_mode_change(hass, entry, fake) -> None:
    lamp = eid(hass, entry, "light", "light")
    mode = eid(hass, entry, "select", "mode")
    await call(hass, "light", "turn_on", lamp, brightness_pct=40)
    assert state(hass, mode) == "manual"
    # A CLOCK reply generated before the switch arrives late.
    stale = {**fake.frame("CLOCK"), "mode": "DAYCL_MODE"}
    for key in ("duration", "fallbackActive", "remaining"):
        stale.pop(key, None)
    await fake._broadcast(stale)
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    assert state(hass, mode) == "manual"
    # A real device-side change (CCMODE, e.g. the manual-mode fallback) still applies.
    fake.state["CLOCK"]["mode"] = "DAYCL_MODE"
    await fake._broadcast(fake._mode_frame())
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    assert state(hass, mode) == "daycycle"
