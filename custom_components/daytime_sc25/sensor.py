"""Sensors for the daytime SC25."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import SC25ConfigEntry
from .api import CHANNELS
from .entity import SC25Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: SC25ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    count = entry.runtime_data.state.channel_count
    entities: list[SensorEntity] = [SC25TemperatureSensor(entry)]
    entities += [SC25OutputSensor(entry, index) for index in range(count)]
    entities += [
        SC25NextCloudSensor(entry),
        SC25FrameSensor(
            entry,
            "moon_phase_day",
            "MOON",
            "currentCycleDay",
            unit=UnitOfTime.DAYS,
            icon="mdi:moon-waxing-gibbous",
        ),
        SC25FrameSensor(
            entry,
            "moon_intensity",
            "MOON",
            "currentIntensity",
            unit=PERCENTAGE,
            icon="mdi:moon-full",
        ),
        SC25FrameSensor(
            entry, "acclimation_day", "ACCLIMATE", "currentAcclDay", icon="mdi:calendar-today"
        ),
        # Remaining light factor of today's acclimation step (100 = no dimming).
        SC25FrameSensor(
            entry,
            "acclimation_level",
            "ACCLIMATE",
            "currentAccReduction",
            unit=PERCENTAGE,
            icon="mdi:brightness-4",
            inactive=("acclActive", 100),
        ),
        SC25WifiSensor(entry),
    ]
    async_add_entities(entities)


class SC25TemperatureSensor(SC25Entity, SensorEntity):
    _attr_translation_key = "module_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "module_temperature")

    @property
    def native_value(self) -> float | None:
        return self.client.state.module_temperature


class SC25OutputSensor(SC25Entity, SensorEntity):
    """Live output of one channel, including effects such as clouds."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, entry: SC25ConfigEntry, index: int) -> None:
        super().__init__(entry, f"output_{CHANNELS[index]}")
        self._index = index
        self._attr_translation_key = f"output_{CHANNELS[index]}"

    @property
    def native_value(self) -> int:
        return self.client.state.current_values[self._index]


class SC25FrameSensor(SC25Entity, SensorEntity):
    """A numeric runtime value straight from a device frame."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry, key, frame, field, *, unit=None, icon=None, inactive=None) -> None:
        super().__init__(entry, key)
        self._frame, self._field = frame, field
        # (flag field, value): report value while the flag is off; the device
        # keeps computing the field even when the feature is disabled.
        self._inactive = inactive
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> float | None:
        frame = self.client.state.get(self._frame)
        if self._inactive and not frame.get(self._inactive[0]):
            return self._inactive[1] if frame else None
        value = frame.get(self._field)
        return value if isinstance(value, (int, float)) else None


class SC25NextCloudSensor(SC25Entity, SensorEntity):
    """Start of the next cloud; the device reports seconds since midnight."""

    _attr_translation_key = "next_cloud"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:weather-cloudy-clock"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "next_cloud")

    @property
    def native_value(self) -> datetime | None:
        cloud = self.client.state.get("CLOUD")
        seconds = cloud.get("nextCloudStart")
        if not cloud.get("cloudActive") or not isinstance(seconds, (int, float)):
            return None
        if seconds <= 0 or seconds >= 86400:  # none left today
            return None
        midnight = dt_util.start_of_local_day()
        return midnight + timedelta(seconds=int(seconds))


class SC25WifiSensor(SC25Entity, SensorEntity):
    """Joined WLAN with the controller's address (the password is never exposed)."""

    _attr_translation_key = "wifi_network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:wifi"

    def __init__(self, entry: SC25ConfigEntry) -> None:
        super().__init__(entry, "wifi_network")

    @property
    def native_value(self) -> str | None:
        return self.client.state.get("NET_ST").get("stSSID") or None

    @property
    def extra_state_attributes(self) -> dict:
        net = self.client.state.get("NET_ST")
        ip = net.get("ip")
        return {
            "ip_address": ".".join(str(p) for p in ip) if isinstance(ip, list) else None,
            "dhcp": bool(net.get("dhcp")) if "dhcp" in net else None,
        }
