"""Switches for the SC25: effects and on/off settings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity
from .settings import CONFIG_SWITCHES, EFFECT_SWITCHES, Setting


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    count = entry.runtime_data.state.channel_count
    entities = [SC25Switch(entry, s, None) for s in EFFECT_SWITCHES]
    entities += [
        SC25Switch(entry, s, EntityCategory.CONFIG)
        for s in CONFIG_SWITCHES
        if s.min_channels <= count
    ]
    async_add_entities(entities)


class SC25Switch(SC25Entity, SwitchEntity):
    def __init__(
        self,
        entry: SC25ConfigEntry,
        setting: Setting,
        category: EntityCategory | None,
    ) -> None:
        super().__init__(entry, setting.key)
        self._setting = setting
        self._attr_translation_key = setting.key
        self._attr_entity_category = category
        self._attr_icon = setting.icon

    @property
    def is_on(self) -> bool | None:
        value = self._setting.get(self.client.state)
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._run(self._setting.set(self.client, True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._run(self._setting.set(self.client, False))
