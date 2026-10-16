"""Firmware version and whether the vendor offers a newer one.

Installing is deliberately not supported: a failed flash can leave the
controller unreachable. Use the device web interface for updates.
"""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SC25ConfigEntry
from .entity import SC25Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SC25FirmwareUpdate(entry)])


def _first(value) -> str | None:
    return str(value[0]) if isinstance(value, list) and value else None


class SC25FirmwareUpdate(SC25Entity, UpdateEntity):
    _attr_translation_key = "firmware"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "firmware")

    @property
    def installed_version(self) -> str | None:
        return _first(self.client.state.get("USRDTA").get("revision"))

    @property
    def latest_version(self) -> str | None:
        return (
            _first(self.client.state.get("USRDTA").get("latestAvailableRevision"))
            or self.installed_version
        )

    @property
    def release_url(self) -> str:
        return f"http://{self.client.host}/"
