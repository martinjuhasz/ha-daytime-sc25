"""Number entities for the SC25 settings (daycycle, moonlight, clouds, acclimation)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity
from .settings import NUMBERS, Setting


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    count = entry.runtime_data.state.channel_count
    async_add_entities(SC25Number(entry, s) for s in NUMBERS if s.min_channels <= count)


class SC25Number(SC25Entity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: SC25ConfigEntry, setting: Setting) -> None:
        super().__init__(entry, setting.key)
        self._setting = setting
        self._attr_translation_key = setting.key
        self._attr_native_min_value = setting.min
        self._attr_native_max_value = setting.max
        self._attr_native_step = setting.step
        self._attr_native_unit_of_measurement = setting.unit
        self._attr_icon = setting.icon

    @property
    def native_value(self) -> float | None:
        value = self._setting.get(self.client.state)
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._run(self._setting.set(self.client, round(value)))
