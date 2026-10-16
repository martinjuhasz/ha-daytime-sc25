"""Time-of-day settings (day start/end, midday dimming, moonlight window)."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity
from .settings import TIMES, Setting


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(SC25Time(entry, s) for s in TIMES)


class SC25Time(SC25Entity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: SC25ConfigEntry, setting: Setting) -> None:
        super().__init__(entry, setting.key)
        self._setting = setting
        self._attr_translation_key = setting.key
        self._attr_icon = setting.icon

    @property
    def native_value(self) -> time | None:
        minutes = self._setting.get(self.client.state)
        if minutes is None:
            return None
        minutes = max(0, min(1439, int(minutes)))
        return time(minutes // 60, minutes % 60)

    async def async_set_value(self, value: time) -> None:
        await self._run(self._setting.set(self.client, value.hour * 60 + value.minute))
