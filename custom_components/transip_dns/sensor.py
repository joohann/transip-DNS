"""Sensor platform for the TransIP Dynamic DNS integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DOMAIN_NAME,
    CONF_RECORD_NAME,
    CONF_RECORD_TYPE,
    DOMAIN,
)
from .coordinator import TransipDnsCoordinator, _record_key


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for each configured DNS record plus the external IPs."""
    coordinator: TransipDnsCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        ExternalIpSensor(coordinator, entry, "ipv4"),
        ExternalIpSensor(coordinator, entry, "ipv6"),
        PreviousExternalIpSensor(coordinator, entry, "ipv4"),
        PreviousExternalIpSensor(coordinator, entry, "ipv6"),
    ]
    for rec in coordinator.records:
        entities.append(
            DnsRecordSensor(
                coordinator,
                entry,
                rec[CONF_DOMAIN_NAME],
                rec[CONF_RECORD_NAME],
                rec[CONF_RECORD_TYPE],
            )
        )
    async_add_entities(entities)


def _hub_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device representing the TransIP account itself (holds the IP sensors)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"TransIP DNS ({entry.data.get('login', entry.title)})",
        manufacturer="TransIP",
        entry_type=DeviceEntryType.SERVICE,
    )


def _domain_device_info(entry: ConfigEntry, domain: str) -> DeviceInfo:
    """Device representing a single managed domain - one row per domain."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{domain}")},
        name=domain,
        manufacturer="TransIP",
        model="Dynamic DNS domain",
        entry_type=DeviceEntryType.SERVICE,
        via_device=(DOMAIN, entry.entry_id),
    )


class ExternalIpSensor(CoordinatorEntity[TransipDnsCoordinator], SensorEntity):
    """Shows the last detected external IPv4/IPv6 address."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TransipDnsCoordinator, entry: ConfigEntry, ip_type: str
    ) -> None:
        super().__init__(coordinator)
        self._ip_type = ip_type
        self._attr_unique_id = f"{entry.entry_id}_{ip_type}"
        self._attr_name = "External IPv4" if ip_type == "ipv4" else "External IPv6"
        self._attr_icon = "mdi:ip-network"
        self._attr_device_info = _hub_device_info(entry)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._ip_type)

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "previous_ip": data.get(f"{self._ip_type}_previous"),
            "changed_at": data.get(f"{self._ip_type}_changed_at"),
        }


class PreviousExternalIpSensor(CoordinatorEntity[TransipDnsCoordinator], SensorEntity):
    """Shows the external IPv4/IPv6 address used before the last change."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TransipDnsCoordinator, entry: ConfigEntry, ip_type: str
    ) -> None:
        super().__init__(coordinator)
        self._ip_type = ip_type
        self._attr_unique_id = f"{entry.entry_id}_{ip_type}_previous"
        self._attr_name = (
            "Previous external IPv4" if ip_type == "ipv4" else "Previous external IPv6"
        )
        self._attr_icon = "mdi:ip-network-outline"
        self._attr_device_info = _hub_device_info(entry)

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        return data.get(f"{self._ip_type}_previous")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "current_ip": data.get(self._ip_type),
            "changed_at": data.get(f"{self._ip_type}_changed_at"),
        }


class DnsRecordSensor(CoordinatorEntity[TransipDnsCoordinator], SensorEntity):
    """Shows the current content and status of a single managed DNS record."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:dns"

    def __init__(
        self,
        coordinator: TransipDnsCoordinator,
        entry: ConfigEntry,
        domain: str,
        name: str,
        record_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._domain = domain
        self._name = name
        self._record_type = record_type
        self._key = _record_key(domain, name, record_type)
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_name = f"{name} ({record_type})" if name != "@" else record_type
        self._attr_device_info = _domain_device_info(entry, domain)

    @property
    def _record(self) -> dict | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("records", {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._record is not None

    @property
    def native_value(self) -> str | None:
        record = self._record
        return record.get("ip") if record else None

    @property
    def extra_state_attributes(self) -> dict:
        record = self._record or {}
        return {
            "domain": self._domain,
            "name": self._name,
            "type": self._record_type,
            "status": record.get("status"),
            "last_updated": record.get("last_updated"),
            "previous_ip": record.get("previous_ip"),
            "previous_changed_at": record.get("previous_changed_at"),
            "error": record.get("error"),
        }
