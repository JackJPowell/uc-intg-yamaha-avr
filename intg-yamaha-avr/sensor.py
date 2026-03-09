"""
Sensor entity functions for the Yamaha AVR integration.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from const import YamahaConfig, SensorConfig
from avr import YamahaAVR
from ucapi import EntityTypes
from ucapi.sensor import Attributes, DeviceClasses, States
from ucapi_framework import create_entity_id
from ucapi_framework.entities import SensorEntity

_LOG = logging.getLogger(__name__)


class YamahaSensor(SensorEntity):
    """Representation of a Yamaha AVR Sensor entity."""

    def __init__(
        self,
        config_device: YamahaConfig,
        device: YamahaAVR,
        sensor_config: SensorConfig,
    ):
        """Initialize a Yamaha Sensor entity."""
        self._device = device
        self._sensor_id = sensor_config.identifier

        entity_id = create_entity_id(
            EntityTypes.SENSOR, config_device.identifier, sensor_config.identifier
        )

        attributes: dict[str, Any] = {
            Attributes.STATE: States.UNKNOWN,
            Attributes.VALUE: sensor_config.default,
        }

        if sensor_config.unit is not None:
            attributes[Attributes.UNIT] = sensor_config.unit

        _LOG.debug("Initializing sensor entity: %s", entity_id)

        super().__init__(
            identifier=entity_id,
            name=f"{sensor_config.name}",
            features=[],
            attributes=attributes,
            device_class=DeviceClasses.CUSTOM,
        )

        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        """Sync sensor state from device after push_update() or reconnect."""
        if self._device is None:
            self.set_unavailable()
            return

        attrs = self._device.get_sensor_attributes(
            self._device.identifier, self._sensor_id
        )
        if attrs is not None:
            self.update(attrs)
