"""Selects for the daytime SC25: operating mode and light colour favourites."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import voluptuous as vol

from . import SC25ConfigEntry
from .api import FAVORITE_SLOTS, MODE_DAYCYCLE, MODE_MANUAL
from .button import run_preview
from .daycycle import level_at
from .entity import SC25Entity

OPTIONS = {"daycycle": MODE_DAYCYCLE, "manual": MODE_MANUAL}

SLOT = vol.All(vol.Coerce(int), vol.Range(min=1, max=FAVORITE_SLOTS))
PERCENT = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
MINUTE = vol.All(vol.Coerce(int), vol.Range(min=0, max=1440))


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SC25ModeSelect(entry), SC25FavoriteSelect(entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "save_favorite",
        {
            vol.Required("slot"): SLOT,
            vol.Required("name"): cv.string,
            vol.Optional("channels"): vol.All(cv.ensure_list, [PERCENT], vol.Length(max=4)),
        },
        "async_save_favorite",
    )
    platform.async_register_entity_service(
        "delete_favorite", {vol.Required("slot"): SLOT}, "async_delete_favorite"
    )
    platform.async_register_entity_service(
        "set_daycycle_curve",
        {
            vol.Required("points"): vol.All(
                cv.ensure_list,
                [vol.All(cv.ensure_list, [vol.Coerce(int)], vol.Length(min=2, max=5))],
                vol.Length(min=2, max=50),
            )
        },
        "async_set_daycycle_curve",
    )
    platform.async_register_entity_service(
        "preview_daycycle",
        {
            vol.Optional("seconds", default=80): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=600)
            ),
            vol.Optional("start", default=0): MINUTE,
            vol.Optional("end", default=1439): MINUTE,
        },
        "async_preview_daycycle",
    )


class SC25ModeSelect(SC25Entity, SelectEntity):
    _attr_translation_key = "mode"
    _attr_options = list(OPTIONS)

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "mode")

    @property
    def current_option(self) -> str | None:
        mode = self.client.state.mode
        for option, wire in OPTIONS.items():
            if wire == mode:
                return option
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Daycycle data for dashboards (e.g. the bundled card)."""
        state = self.client.state
        settings = state.daycycle_settings
        curve = state.daycycle
        clock = state.get("CLOCK")
        now = None
        if "hour" in clock and "min" in clock:
            now = int(clock["hour"]) * 60 + int(clock["min"])
        return {
            "daycycle": curve,
            "expert_mode": settings.expert_mode,
            "day_start": settings.start,
            "day_end": settings.end,
            "sunrise_minutes": settings.sunrise,
            "sunset_minutes": settings.sunset,
            "day_intensity": settings.intensity,
            "midday_dimming": settings.midday_dimming,
            "sun_glow": settings.sun_glow,
            "channel_count": state.channel_count,
            "programmed_levels": level_at(curve, now) if curve and now is not None else None,
            "manual_fallback_remaining": state.manual_remaining,
        }

    async def async_select_option(self, option: str) -> None:
        await self._run(
            self.client.set_mode(
                OPTIONS[option] == MODE_MANUAL, fallback_seconds=self.fallback_seconds
            )
        )

    async def async_set_daycycle_curve(self, points: list[list[int]]) -> None:
        await self._run(self.client.set_daycycle_curve(points))

    async def async_preview_daycycle(self, seconds: int, start: int, end: int) -> None:
        await run_preview(self, seconds, start, end)

    async def async_save_favorite(self, slot: int, name: str, channels=None) -> None:
        await self._run(self.client.save_favorite(slot, name, channels))

    async def async_delete_favorite(self, slot: int) -> None:
        await self._run(self.client.delete_favorite(slot))


class SC25FavoriteSelect(SC25Entity, SelectEntity):
    """Apply a stored light colour favourite (switches to manual mode)."""

    _attr_translation_key = "favorite"
    _attr_icon = "mdi:star-outline"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "favorite")

    def _slots(self) -> dict[str, dict[str, Any]]:
        slots = {}
        for i, fav in enumerate(self.client.state.favorites, start=1):
            if fav["name"] or any(fav["channels"]):
                slots[fav["name"] or f"Favorit {i}"] = {**fav, "slot": i}
        return slots

    @property
    def options(self) -> list[str]:
        return list(self._slots())

    @property
    def current_option(self) -> str | None:
        if self.client.state.mode != MODE_MANUAL:
            return None
        current = self.client.state.current_values
        for name, fav in self._slots().items():
            if fav["channels"] == current:
                return name
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "favorites": [
                {"slot": fav["slot"], "name": name, "channels": fav["channels"]}
                for name, fav in self._slots().items()
            ]
        }

    async def async_select_option(self, option: str) -> None:
        fav = self._slots()[option]
        await self._run(
            self.client.set_channels(fav["channels"], fallback_seconds=self.fallback_seconds)
        )

    async def async_save_favorite(self, slot: int, name: str, channels=None) -> None:
        await self._run(self.client.save_favorite(slot, name, channels))

    async def async_delete_favorite(self, slot: int) -> None:
        await self._run(self.client.delete_favorite(slot))

    async def async_set_daycycle_curve(self, points: list[list[int]]) -> None:
        await self._run(self.client.set_daycycle_curve(points))

    async def async_preview_daycycle(self, seconds: int, start: int, end: int) -> None:
        await run_preview(self, seconds, start, end)
