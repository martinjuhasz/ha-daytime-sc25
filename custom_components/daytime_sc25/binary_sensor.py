"""Binary sensors: cloud passing."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SC25CloudPassing(entry)])


class SC25CloudPassing(SC25Entity, BinarySensorEntity):
    _attr_translation_key = "cloud_passing"
    _attr_icon = "mdi:weather-cloudy-clock"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "cloud_passing")

    @property
    def is_on(self) -> bool | None:
        value = self.client.state.get("CLOUD").get("isCloudActive")
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict:
        cloud = self.client.state.get("CLOUD")
        return {
            "remaining_seconds": cloud.get("cloudRemaining")
            if cloud.get("isCloudActive")
            else None,
            "light_level": cloud.get("cloudCurrentIntensity"),
        }
