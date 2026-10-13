"""Sensors for contact sync and call history."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CALL_LOG_SENSOR_ENTRIES,
    DEFAULT_CALL_LOG_SENSOR_ENTRIES,
)
from .coordinator import GooglePhonebookCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    sensor_entries = int(
        entry.options.get(
            CONF_CALL_LOG_SENSOR_ENTRIES,
            DEFAULT_CALL_LOG_SENSOR_ENTRIES,
        )
    )
    async_add_entities(
        [
            ContactCountSensor(coordinator, entry.entry_id),
            LastSyncSensor(coordinator, entry.entry_id),
            CallLogCountSensor(
                coordinator,
                entry.entry_id,
                sensor_entries,
            ),
            MissedCallsSensor(coordinator, entry.entry_id),
            LastCallSensor(coordinator, entry.entry_id),
        ]
    )


class PhonebookBaseSensor(
    CoordinatorEntity[GooglePhonebookCoordinator],
    SensorEntity,
):
    def __init__(
        self,
        coordinator: GooglePhonebookCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id


class ContactCountSensor(PhonebookBaseSensor):
    _attr_name = "Google Phonebook Kontakte"
    _attr_icon = "mdi:contacts"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_contact_count"

    @property
    def native_value(self):
        return self.coordinator.data.contact_count if self.coordinator.data else 0


class LastSyncSensor(PhonebookBaseSensor):
    _attr_name = "Google Phonebook Letzte Synchronisierung"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_last_sync"

    @property
    def native_value(self):
        return self.coordinator.data.last_sync if self.coordinator.data else None


class CallLogCountSensor(PhonebookBaseSensor):
    _attr_name = "Google Phonebook Anrufprotokoll"
    _attr_icon = "mdi:phone-log"

    def __init__(self, coordinator, entry_id, sensor_entries):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_call_log"
        self._sensor_entries = sensor_entries

    @property
    def native_value(self):
        return len(self.coordinator.call_log.entries)

    @property
    def extra_state_attributes(self):
        if self._sensor_entries <= 0:
            return {}
        return {
            "calls": self.coordinator.call_log.entries[
                : self._sensor_entries
            ],
            "privacy_note": (
                "Call details in entity attributes may be recorded by "
                "Home Assistant Recorder."
            ),
        }


class MissedCallsSensor(PhonebookBaseSensor):
    _attr_name = "Google Phonebook Verpasste Anrufe"
    _attr_icon = "mdi:phone-missed"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_missed_calls"

    @property
    def native_value(self):
        return self.coordinator.call_log.unread_missed_count


class LastCallSensor(PhonebookBaseSensor):
    _attr_name = "Google Phonebook Letzter Anruf"
    _attr_icon = "mdi:phone"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_last_call"

    @property
    def native_value(self):
        entry = self.coordinator.call_log.last_entry
        if not entry:
            return "none"
        return entry.get("status", "unknown")

    @property
    def extra_state_attributes(self):
        return self.coordinator.call_log.last_entry or {}
