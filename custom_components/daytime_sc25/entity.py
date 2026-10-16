"""Base entity for the daytime SC25."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import Entity

from .api import SC25Client, SC25Error
from .const import CONF_MANUAL_FALLBACK, DOMAIN, MANUFACTURER, MODEL


class SC25Entity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str) -> None:
        self._entry = entry
        self.client: SC25Client = entry.runtime_data
        state = self.client.state
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{key}"
        mac = state.mac
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            connections={(CONNECTION_NETWORK_MAC, format_mac(mac))} if mac else set(),
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
            sw_version=state.revision,
            configuration_url=f"http://{self.client.host}/",
        )

    @property
    def available(self) -> bool:
        return self.client.available

    @property
    def fallback_seconds(self) -> int | None:
        minutes = int(self._entry.options.get(CONF_MANUAL_FALLBACK, 0) or 0)
        return minutes * 60 if minutes > 0 else None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_listener(self.async_write_ha_state))

    async def _run(self, action: Awaitable[None]) -> None:
        """Run a device command, turning failures into HA errors."""
        try:
            await action
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except SC25Error as err:
            raise HomeAssistantError(str(err)) from err
