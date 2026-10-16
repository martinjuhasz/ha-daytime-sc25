"""Declarative list of the SC25 settings exposed as entities.

Each setting knows how to read its value from the client state and how to
write it back. Wire quirks (cloud units, inverted cloud intensity) live here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .api import CHANNELS, SC25Client, SC25State

Getter = Callable[[SC25State], Any]
Setter = Callable[[SC25Client, Any], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class Setting:
    key: str
    get: Getter
    set: Setter
    # Only created when the lamp has at least this many channels.
    min_channels: int = 1
    # number entities
    min: float = 0
    max: float = 100
    step: float = 1
    unit: str | None = None
    icon: str | None = None


def _frame(title: str, field: str) -> Getter:
    def get(state: SC25State) -> Any:
        return state.get(title).get(field)

    return get


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _daycycle(attr: str) -> Getter:
    return lambda state: getattr(state.daycycle_settings, attr)


def _set_daycycle(attr: str) -> Setter:
    return lambda client, value: client.set_daycycle_settings(**{attr: value})


def _day_intensity(index: int) -> Getter:
    return lambda state: state.daycycle_settings.intensities[index]


def _set_channel_intensity(index: int) -> Setter:
    async def setter(client: SC25Client, value: Any) -> None:
        intensities = list(client.state.daycycle_settings.intensities)
        intensities[index] = int(value)
        await client.set_daycycle_settings(individual=True, intensities=tuple(intensities))

    return setter


def _cloud_minutes(field: str) -> Getter:
    def get(state: SC25State) -> int | None:
        seconds = _int(state.get("CLOUD").get(field))
        return None if seconds is None else round(seconds / 60)

    return get


def _set_cloud_minutes(field: str) -> Setter:
    return lambda client, value: client.set_cloud(**{field: int(value) * 60})


def _cloud_strength(wire_field: str) -> Getter:
    # The wire stores the remaining light during a cloud, the UI its strength:
    # strength_min = 100 - wire.maxIntensity, strength_max = 100 - wire.minIntensity.
    def get(state: SC25State) -> int | None:
        value = _int(state.get("CLOUD").get(wire_field))
        return None if value is None else 100 - value

    return get


def _set_cloud_strength(wire_field: str) -> Setter:
    return lambda client, value: client.set_cloud(**{wire_field: 100 - int(value)})


async def _set_cloud_amount(client: SC25Client, value: Any) -> None:
    # The app caps clouds per day so they fit into the day at maximum length.
    max_minutes = max(1, round((_int(client.state.get("CLOUD").get("maxDuration")) or 60) / 60))
    await client.set_cloud(maxAmount=max(1, min(int(value), 1440 // max_minutes, 1500)))


def _moon_channel(channel: str) -> Getter:
    return lambda state: channel in state.moon_channels


def _set_moon_channel(channel: str) -> Setter:
    return lambda client, value: client.set_moon_channel(channel, bool(value))


def _flag(title: str, field: str) -> Getter:
    def get(state: SC25State) -> bool | None:
        value = _int(state.get(title).get(field))
        return None if value is None else bool(value)

    return get


# -- numbers -------------------------------------------------------------

NUMBERS: tuple[Setting, ...] = (
    Setting(
        key="sunrise_duration",
        get=_daycycle("sunrise"),
        set=_set_daycycle("sunrise"),
        max=360,
        step=5,
        unit="min",
        icon="mdi:weather-sunset-up",
    ),
    Setting(
        key="sunset_duration",
        get=_daycycle("sunset"),
        set=_set_daycycle("sunset"),
        max=360,
        step=5,
        unit="min",
        icon="mdi:weather-sunset-down",
    ),
    Setting(
        key="day_intensity",
        get=_daycycle("intensity"),
        set=_set_daycycle("intensity"),
        unit="%",
        icon="mdi:brightness-6",
    ),
    *(
        Setting(
            key=f"day_intensity_{ch}",
            min_channels=i + 1,
            get=_day_intensity(i),
            set=_set_channel_intensity(i),
            unit="%",
            icon="mdi:brightness-percent",
        )
        for i, ch in enumerate(CHANNELS)
    ),
    Setting(
        key="midday_intensity",
        get=_daycycle("midday_intensity"),
        set=_set_daycycle("midday_intensity"),
        unit="%",
        icon="mdi:weather-sunny-off",
    ),
    Setting(
        key="sunrise_glow_duration",
        get=_daycycle("sunrise_glow_duration"),
        set=_set_daycycle("sunrise_glow_duration"),
        min_channels=3,
        max=180,
        step=5,
        unit="min",
        icon="mdi:weather-sunset-up",
    ),
    Setting(
        key="sunrise_glow_intensity",
        get=_daycycle("sunrise_glow_intensity"),
        set=_set_daycycle("sunrise_glow_intensity"),
        min_channels=3,
        max=5,
        icon="mdi:fire",
    ),
    Setting(
        key="sunset_glow_duration",
        get=_daycycle("sunset_glow_duration"),
        set=_set_daycycle("sunset_glow_duration"),
        min_channels=3,
        max=180,
        step=5,
        unit="min",
        icon="mdi:weather-sunset-down",
    ),
    Setting(
        key="sunset_glow_intensity",
        get=_daycycle("sunset_glow_intensity"),
        set=_set_daycycle("sunset_glow_intensity"),
        min_channels=3,
        max=5,
        icon="mdi:fire",
    ),
    Setting(
        key="moon_max",
        get=_frame("MOON", "maxmoonlight"),
        set=lambda c, v: c.set_moon(maxmoonlight=int(v)),
        unit="%",
        icon="mdi:moon-full",
    ),
    Setting(
        key="moon_min",
        get=_frame("MOON", "minmoonlight"),
        set=lambda c, v: c.set_moon(minmoonlight=int(v)),
        unit="%",
        icon="mdi:moon-new",
    ),
    Setting(
        key="cloud_probability",
        get=_frame("CLOUD", "probability"),
        set=lambda c, v: c.set_cloud(probability=int(v)),
        unit="%",
        icon="mdi:dice-multiple",
    ),
    Setting(
        key="cloud_max_per_day",
        get=_frame("CLOUD", "maxAmount"),
        set=_set_cloud_amount,
        min=1,
        max=1500,
        icon="mdi:weather-cloudy",
    ),
    Setting(
        key="cloud_strength_min",
        get=_cloud_strength("maxIntensity"),
        set=_set_cloud_strength("maxIntensity"),
        unit="%",
        icon="mdi:weather-partly-cloudy",
    ),
    Setting(
        key="cloud_strength_max",
        get=_cloud_strength("minIntensity"),
        set=_set_cloud_strength("minIntensity"),
        unit="%",
        icon="mdi:weather-cloudy",
    ),
    Setting(
        key="cloud_duration_min",
        get=_cloud_minutes("minDuration"),
        set=_set_cloud_minutes("minDuration"),
        min=1,
        max=120,
        unit="min",
        icon="mdi:timer-sand",
    ),
    Setting(
        key="cloud_duration_max",
        get=_cloud_minutes("maxDuration"),
        set=_set_cloud_minutes("maxDuration"),
        min=1,
        max=120,
        unit="min",
        icon="mdi:timer-sand-complete",
    ),
    Setting(
        key="acclimation_days",
        get=_frame("ACCLIMATE", "duration"),
        set=lambda c, v: c.set_acclimation(duration=int(v)),
        min=1,
        max=90,
        unit="d",
        icon="mdi:calendar-range",
    ),
    Setting(
        key="acclimation_reduction",
        get=_frame("ACCLIMATE", "intensityReduction"),
        set=lambda c, v: c.set_acclimation(intensityReduction=int(v)),
        unit="%",
        icon="mdi:brightness-4",
    ),
    Setting(
        key="acclimation_current_day",
        get=_frame("ACCLIMATE", "currentAcclDay"),
        set=lambda c, v: c.set_acclimation(currentAcclDay=int(v)),
        min=1,
        max=90,
        icon="mdi:calendar-today",
    ),
)

# -- times (minutes of day) ------------------------------------------------

TIMES: tuple[Setting, ...] = (
    Setting(
        key="day_start",
        get=_daycycle("start"),
        set=_set_daycycle("start"),
        icon="mdi:weather-sunset-up",
    ),
    Setting(
        key="day_end",
        get=_daycycle("end"),
        set=_set_daycycle("end"),
        icon="mdi:weather-sunset-down",
    ),
    Setting(
        key="midday_start",
        get=_daycycle("midday_start"),
        set=_set_daycycle("midday_start"),
        icon="mdi:clock-start",
    ),
    Setting(
        key="midday_end",
        get=_daycycle("midday_end"),
        set=_set_daycycle("midday_end"),
        icon="mdi:clock-end",
    ),
    Setting(
        key="moon_start",
        get=_frame("MOON", "moonStart"),
        set=lambda c, v: c.set_moon(moonStart=int(v)),
        icon="mdi:moon-waxing-crescent",
    ),
    Setting(
        key="moon_end",
        get=_frame("MOON", "moonEnd"),
        set=lambda c, v: c.set_moon(moonEnd=int(v)),
        icon="mdi:moon-waning-crescent",
    ),
)

# -- switches --------------------------------------------------------------

EFFECT_SWITCHES: tuple[Setting, ...] = (
    Setting(
        key="moonlight",
        get=_flag("MOON", "moonlightActive"),
        set=lambda c, v: c.set_moonlight(bool(v)),
        icon="mdi:weather-night",
    ),
    Setting(
        key="clouds",
        get=_flag("CLOUD", "cloudActive"),
        set=lambda c, v: c.set_clouds(bool(v)),
        icon="mdi:weather-cloudy",
    ),
)

CONFIG_SWITCHES: tuple[Setting, ...] = (
    Setting(
        key="acclimation",
        get=_flag("ACCLIMATE", "acclActive"),
        set=lambda c, v: c.set_acclimation_active(bool(v)),
        icon="mdi:fishbowl-outline",
    ),
    Setting(
        key="acclimation_pause",
        get=_flag("ACCLIMATE", "pause"),
        set=lambda c, v: c.set_acclimation_paused(bool(v)),
        icon="mdi:pause-circle-outline",
    ),
    Setting(
        key="moon_cycle",
        get=_flag("MOON", "moonlightCycle"),
        set=lambda c, v: c.set_moon(moonlightCycle=1 if v else 0),
        icon="mdi:moon-waning-gibbous",
    ),
    Setting(
        key="moon_individual_times",
        get=_flag("MOON", "individualTimes"),
        set=lambda c, v: c.set_moon(individualTimes=1 if v else 0),
        icon="mdi:clock-edit-outline",
    ),
    *(
        Setting(
            key=f"moon_{ch}",
            get=_moon_channel(ch),
            set=_set_moon_channel(ch),
            min_channels=i + 1,
            icon="mdi:moon-full",
        )
        for i, ch in enumerate(CHANNELS)
    ),
    Setting(
        key="individual_intensities",
        get=_daycycle("individual"),
        set=lambda c, v: c.set_daycycle_settings(individual=bool(v)),
        icon="mdi:palette",
    ),
    Setting(
        key="sun_glow",
        get=_daycycle("sun_glow"),
        set=lambda c, v: c.set_daycycle_settings(sun_glow=bool(v)),
        min_channels=3,
        icon="mdi:weather-sunset",
    ),
    Setting(
        key="midday_dimming",
        get=_daycycle("midday_dimming"),
        set=lambda c, v: c.set_daycycle_settings(midday_dimming=bool(v)),
        icon="mdi:weather-sunny-off",
    ),
)
