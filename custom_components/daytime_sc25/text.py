"""Controller name."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SC25NameText(entry)])


class SC25NameText(SC25Entity, TextEntity):
    _attr_translation_key = "controller_name"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = 32
    _attr_icon = "mdi:rename"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "controller_name")

    @property
    def native_value(self) -> str | None:
        return self.client.state.get("USRDTA").get("name")

    async def async_set_value(self, value: str) -> None:
        await self._run(self.client.set_name(value))
