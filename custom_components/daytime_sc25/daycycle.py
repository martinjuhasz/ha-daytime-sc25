"""Daycycle easy-mode settings and the curve the vendor app derives from them.

The controller stores two things: ``DSCRPTN``, a ``key:value;...`` string with
the easy-mode settings, and ``DYCL``, the curve it actually plays as
``[minute, white, blue, red, green]`` rows. The app recomputes the curve from
the settings on every save; ``build_curve`` reproduces that computation
(template "Standard", confId 10) so both stay consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from itertools import pairwise
from typing import Any

MINUTES_PER_DAY = 1440
MIDDAY_TRANSITION = 15
RED = 2  # protocol index of the red channel, used by the sun glow


def _bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1")


# DSCRPTN wire key -> (DaycycleSettings attribute, parser), in wire order.
_WIRE = {
    "confId": ("conf_id", int),
    "expMode": ("expert_mode", _bool),
    "start": ("start", int),
    "end": ("end", int),
    "sunrise": ("sunrise", int),
    "sunset": ("sunset", int),
    "intensity": ("intensity", int),
    "individual": ("individual", _bool),
    "sunGlowEnabled": ("sun_glow", _bool),
    "sunriseGlowDuration": ("sunrise_glow_duration", int),
    "sunriseGlowIntensity": ("sunrise_glow_intensity", int),
    "sunsetGlowDuration": ("sunset_glow_duration", int),
    "sunsetGlowIntensity": ("sunset_glow_intensity", int),
    "middayDimmingEnabled": ("midday_dimming", _bool),
    "middayDimmingStart": ("midday_start", int),
    "middayDimmingEnd": ("midday_end", int),
    "middayDimmingIntensity": ("midday_intensity", int),
}


@dataclass(frozen=True)
class DaycycleSettings:
    """Easy-mode settings as stored in ``DSCRPTN``. Times are minutes of day."""

    conf_id: int = 10
    expert_mode: bool = False
    start: int = 480
    end: int = 1260
    sunrise: int = 60
    sunset: int = 60
    intensity: int = 100
    individual: bool = False
    intensities: tuple[int, int, int, int] = (100, 100, 100, 100)
    sun_glow: bool = False
    sunrise_glow_duration: int = 30
    sunrise_glow_intensity: int = 1
    sunset_glow_duration: int = 30
    sunset_glow_intensity: int = 1
    midday_dimming: bool = False
    midday_start: int = 660
    midday_end: int = 840
    midday_intensity: int = 60

    @classmethod
    def parse(cls, text: str | None) -> DaycycleSettings:
        values: dict[str, Any] = {}
        for part in (text or "").split(";"):
            if ":" not in part:
                continue
            key, raw = part.split(":", 1)
            if key == "intensities":
                try:
                    nums = [int(v) for v in raw.split(",") if v.strip()]
                except ValueError:
                    continue
                values["intensities"] = tuple([*nums, 0, 0, 0, 0][:4])
            elif key in _WIRE:
                attr, parser = _WIRE[key]
                try:
                    values[attr] = parser(raw)
                except ValueError:
                    continue
        return cls(**values)

    def encode(self) -> str:
        """Serialise in the exact key order the vendor app writes."""
        parts = []
        for key, (attr, parser) in _WIRE.items():
            value = getattr(self, attr)
            parts.append(f"{key}:{str(value).lower() if parser is _bool else value}")
        parts.append("intensities:" + ",".join(str(v) for v in self.intensities))
        return ";".join(parts)

    def with_changes(self, **changes: Any) -> DaycycleSettings:
        return replace(self, **changes)

    def validate(self) -> None:
        """Raise ValueError if the settings cannot form a curve."""
        if not 0 <= self.start < self.end <= MINUTES_PER_DAY - 1:
            raise ValueError("Der Tag muss nach dem Beginn enden.")
        if self.sunrise < 0 or self.sunset < 0:
            raise ValueError("Dauer darf nicht negativ sein.")
        if self.start + self.sunrise > self.end - self.sunset:
            raise ValueError("Sonnenaufgang und -untergang sind zusammen länger als der Tag.")
        if self.midday_dimming and not self.midday_start < self.midday_end:
            raise ValueError("Die Mittagsabsenkung muss nach ihrem Beginn enden.")


def _interpolate(curve: list[list[int]], minute: int) -> list[int]:
    for row in curve:
        if row[0] == minute:
            return list(row)
    if minute <= curve[0][0]:
        return [minute, *curve[0][1:]]
    for prev, nxt in pairwise(curve):
        if nxt[0] >= minute:
            span = nxt[0] - prev[0]
            ratio = 0 if span == 0 else (minute - prev[0]) / span
            return [
                minute,
                *(round(a + (b - a) * ratio) for a, b in zip(prev[1:], nxt[1:], strict=True)),
            ]
    return [minute, *curve[-1][1:]]


def _upsert(curve: list[list[int]], row: list[int]) -> None:
    for i, existing in enumerate(curve):
        if existing[0] == row[0]:
            curve[i] = row
            return
        if existing[0] > row[0]:
            curve.insert(i, row)
            return
    curve.append(row)


def _glow_level(level: int) -> int:
    # The UI slider goes 0-5; each step is 10 % red.
    if level <= 0:
        return 0
    return 10 * level if level <= 5 else min(100, level)


def build_curve(settings: DaycycleSettings, channel_count: int = 4) -> list[list[int]]:
    """Compute the ``DYCL`` rows for easy-mode ``settings``."""
    settings.validate()
    s = settings
    levels = [
        (s.intensities[i] if s.individual else s.intensity) if i < channel_count else 0
        for i in range(4)
    ]
    zero = [0, 0, 0, 0]
    curve = [
        [0, *zero],
        [s.start, *zero],
        [s.start + s.sunrise, *levels],
        [s.end - s.sunset, *levels],
        [s.end, *zero],
        [MINUTES_PER_DAY, *zero],
    ]

    if s.midday_dimming and s.midday_end > s.midday_start:
        base = [list(r) for r in curve]
        start = max(0, min(MINUTES_PER_DAY - 1, s.midday_start))
        end = max(0, min(MINUTES_PER_DAY - 1, s.midday_end))
        transition = max(0, min(MIDDAY_TRANSITION, (end - start) // 2))
        factor = max(0, min(100, s.midday_intensity)) / 100

        def scaled(minute: int) -> list[int]:
            row = _interpolate(base, minute)
            return [row[0], *(round(v * factor) for v in row[1:])]

        _upsert(curve, _interpolate(base, start))
        _upsert(curve, scaled(start + transition))
        if end - transition > start + transition:
            _upsert(curve, scaled(end - transition))
        _upsert(curve, _interpolate(base, end))

    if s.sun_glow and channel_count > RED:
        for edge_start, edge_end, duration, level, at in (
            (
                s.start,
                s.start + s.sunrise,
                min(s.sunrise_glow_duration, s.sunrise),
                s.sunrise_glow_intensity,
                lambda d: s.start + d // 2,
            ),
            (
                s.end - s.sunset,
                s.end,
                min(s.sunset_glow_duration, s.sunset),
                s.sunset_glow_intensity,
                lambda d: s.end - d // 2,
            ),
        ):
            minute = at(max(0, duration))
            if edge_start < minute < edge_end:
                row = [minute, 0, 0, 0, 0]
                row[RED + 1] = _glow_level(level)
                _upsert(curve, row)

    return curve


def level_at(curve: list[list[int]], minute: float) -> list[int]:
    """Programmed channel levels at ``minute`` (linear interpolation)."""
    if not curve:
        return [0, 0, 0, 0]
    return _interpolate(curve, int(minute))[1:5]


SETTINGS_FIELDS = tuple(f.name for f in fields(DaycycleSettings))
