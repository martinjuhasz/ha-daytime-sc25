"""Lights for the daytime SC25: the whole lamp plus one per colour channel."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .api import CHANNELS
from .entity import SC25Entity


def _to_percent(brightness: int) -> int:
    return max(1, round(brightness * 100 / 255))


def _to_brightness(percent: int) -> int:
    return round(percent * 255 / 100)


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    count = entry.runtime_data.state.channel_count
    entities: list[LightEntity] = [SC25MasterLight(entry)]
    entities += [SC25ChannelLight(entry, index) for index in range(count)]
    async_add_entities(entities)


class SC25MasterLight(SC25Entity, LightEntity):
    """All active channels together; brightness keeps the colour ratio."""

    _attr_name = None
    _attr_translation_key = "lamp"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "light")
        self._last_on: list[int] | None = None

    def _active_values(self) -> list[int]:
        count = self.client.state.channel_count
        return self.client.state.current_values[:count]

    @property
    def is_on(self) -> bool:
        return any(self._active_values())

    @property
    def brightness(self) -> int | None:
        values = self._active_values()
        return _to_brightness(max(values)) if any(values) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        count = self.client.state.channel_count
        values = self._active_values()
        if not any(values):
            values = self._last_on or [100] * count
        target = _to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else max(values)
        peak = max(values)
        scaled = [round(v * target / peak) for v in values]
        await self._run(self.client.set_channels(scaled, fallback_seconds=self.fallback_seconds))

    async def async_turn_off(self, **kwargs: Any) -> None:
        values = self._active_values()
        if any(values):
            self._last_on = values
        await self._run(
            self.client.set_channels([0, 0, 0, 0], fallback_seconds=self.fallback_seconds)
        )


class SC25ChannelLight(SC25Entity, LightEntity):
    """A single colour channel."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, entry: SC25ConfigEntry, index: int) -> None:
        super().__init__(entry, f"channel_{CHANNELS[index]}")
        self._index = index
        self._attr_translation_key = f"channel_{CHANNELS[index]}"
        self._last_on = 100

    @property
    def _value(self) -> int:
        return self.client.state.current_values[self._index]

    @property
    def is_on(self) -> bool:
        return self._value > 0

    @property
    def brightness(self) -> int | None:
        return _to_brightness(self._value) if self._value else None

    async def _set(self, percent: int) -> None:
        values = list(self.client.state.current_values)
        values[self._index] = percent
        await self._run(self.client.set_channels(values, fallback_seconds=self.fallback_seconds))

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            await self._set(_to_percent(kwargs[ATTR_BRIGHTNESS]))
        else:
            await self._set(self._value or self._last_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._value:
            self._last_on = self._value
        await self._set(0)
