"""
Select platform for FusionSolar App HA.

Working mode (signal 20002, gun dnId):
  0 = Normal charging
  1 = PV preferred (charge only when solar surplus is available)
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChargerCoordinator

_LOGGER = logging.getLogger(__name__)

WORKING_MODE_OPTIONS = ["Normal", "PV preferred"]
WORKING_MODE_TO_VALUE = {"Normal": "0", "PV preferred": "1"}
WORKING_MODE_FROM_VALUE = {"0": "Normal", "1": "PV preferred"}

SIGNAL_WORKING_MODE = 20002


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    charger: ChargerCoordinator = data["charger"]
    async_add_entities([WorkingModeSelect(charger)])


class WorkingModeSelect(CoordinatorEntity[ChargerCoordinator], SelectEntity):
    """Select entity for the charger working mode (Normal / PV preferred)."""

    _attr_has_entity_name = True
    _attr_name = "Working mode"
    _attr_icon = "mdi:solar-power"
    _attr_options = WORKING_MODE_OPTIONS

    def __init__(self, coordinator: ChargerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.dn_id}_charger_working_mode"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"charger_{self.coordinator.dn_id}")},
            name=self.coordinator.device_name,
            manufacturer="Huawei",
            model="FusionSolar EV Charger",
        )

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        raw = str(self.coordinator.data.get("working_mode", ""))
        return WORKING_MODE_FROM_VALUE.get(raw)

    async def async_select_option(self, option: str) -> None:
        value = WORKING_MODE_TO_VALUE.get(option)
        if value is None:
            _LOGGER.error("Unknown working mode option: %s", option)
            return

        _LOGGER.info(
            "Setting working mode to %s (value=%s) on gun dnId %s",
            option, value, self.coordinator.gun_dn_id,
        )

        success = await self.coordinator.api.set_config_signal(
            dn_id=self.coordinator.gun_dn_id,
            signal_id=SIGNAL_WORKING_MODE,
            value=value,
        )

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set working mode to %s", option)
