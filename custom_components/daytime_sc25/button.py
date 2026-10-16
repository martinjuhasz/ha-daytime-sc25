"""Buttons: daycycle preview and clock sync."""

from __future__ import annotations

import asyncio
import time

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import SC25ConfigEntry
from .api import MODE_MANUAL
from .entity import SC25Entity

PREVIEW_SECONDS = 80  # the vendor app's default


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SC25PreviewButton(entry), SC25SyncClockButton(entry)])


async def run_preview(
    entity: SC25Entity, seconds: int = PREVIEW_SECONDS, start: int = 0, end: int = 1439
) -> None:
    """Play the daycycle in fast motion, then restore the previous mode."""
    client = entity.client
    manual = client.state.mode == MODE_MANUAL
    started = time.monotonic()
    await entity._run(client.preview_daycycle(seconds=seconds, start=start, end=end))

    async def restore() -> None:
        await asyncio.sleep(seconds + 2)
        # A light or mode command in the meantime already ended the preview.
        if client.available and client.last_command_at < started:
            # The vendor app ends a preview by re-sending the mode.
            await client.set_mode(manual, fallback_seconds=entity.fallback_seconds)

    entity.hass.async_create_background_task(restore(), "sc25 preview restore")


class SC25PreviewButton(SC25Entity, ButtonEntity):
    _attr_translation_key = "preview_daycycle"
    _attr_icon = "mdi:play-speed"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "preview_daycycle")

    async def async_press(self) -> None:
        await run_preview(self)


class SC25SyncClockButton(SC25Entity, ButtonEntity):
    _attr_translation_key = "sync_clock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "sync_clock")

    async def async_press(self) -> None:
        await self._run(self.client.sync_clock(dt_util.now()))
