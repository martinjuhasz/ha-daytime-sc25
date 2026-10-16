"""Offline tests for the daycycle curve, checked against real device data."""

from __future__ import annotations

import pytest

from custom_components.daytime_sc25.daycycle import DaycycleSettings, build_curve

# Captured from the SC25 (firmware 10102) on 2026-10-16.
DEVICE_DSCRPTN = (
    "confId:10;expMode:false;start:480;end:1260;sunrise:60;sunset:60;intensity:100;"
    "individual:false;sunGlowEnabled:false;sunriseGlowDuration:30;sunriseGlowIntensity:1;"
    "sunsetGlowDuration:30;sunsetGlowIntensity:1;middayDimmingEnabled:false;"
    "middayDimmingStart:660;middayDimmingEnd:840;middayDimmingIntensity:60;"
    "intensities:100,0,0,0"
)
DEVICE_DYCL = [
    [0, 0, 0, 0, 0],
    [480, 0, 0, 0, 0],
    [540, 100, 100, 100, 100],
    [1200, 100, 100, 100, 100],
    [1260, 0, 0, 0, 0],
    [1440, 0, 0, 0, 0],
]


def test_round_trip_is_byte_identical() -> None:
    assert DaycycleSettings.parse(DEVICE_DSCRPTN).encode() == DEVICE_DSCRPTN


def test_device_curve_is_reproduced() -> None:
    assert build_curve(DaycycleSettings.parse(DEVICE_DSCRPTN)) == DEVICE_DYCL


def test_individual_intensities() -> None:
    s = DaycycleSettings(individual=True, intensities=(80, 40, 20, 0))
    assert build_curve(s)[2] == [540, 80, 40, 20, 0]


def test_unused_channels_are_zero() -> None:
    assert build_curve(DaycycleSettings(), channel_count=1)[2] == [540, 100, 0, 0, 0]


def test_midday_dimming() -> None:
    s = DaycycleSettings(intensity=80, midday_dimming=True)
    curve = build_curve(s)
    assert [660, 80, 80, 80, 80] in curve
    assert [675, 48, 48, 48, 48] in curve
    assert [825, 48, 48, 48, 48] in curve
    assert [840, 80, 80, 80, 80] in curve
    assert [r[0] for r in curve] == sorted(r[0] for r in curve)


def test_sun_glow_inserts_red_point() -> None:
    s = DaycycleSettings(sun_glow=True, sunrise_glow_intensity=3, sunset_glow_intensity=2)
    curve = build_curve(s)
    assert [495, 0, 0, 30, 0] in curve  # 480 + 30 // 2
    assert [1245, 0, 0, 20, 0] in curve  # 1260 - 30 // 2


def test_sun_glow_needs_red_channel() -> None:
    curve = build_curve(DaycycleSettings(sun_glow=True), channel_count=2)
    assert len(curve) == 6


@pytest.mark.parametrize(
    "changes",
    [{"start": 900, "end": 800}, {"sunrise": 400, "sunset": 400}],
)
def test_invalid_settings(changes) -> None:
    with pytest.raises(ValueError):
        build_curve(DaycycleSettings(**changes))
