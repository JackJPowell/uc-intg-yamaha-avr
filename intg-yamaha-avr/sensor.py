"""
Sensor entity functions for the Yamaha AVR integration.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from const import YamahaConfig, SensorConfig
from avr import YamahaAVR
from ucapi import EntityTypes
from ucapi.sensor import Attributes, DeviceClasses, Sensor, States
from ucapi_framework import create_entity_id
from ucapi_framework.entity import Entity as FrameworkEntity

_LOG = logging.getLogger(__name__)


class YamahaSensor(Sensor, FrameworkEntity):
    """Representation of a Yamaha AVR Sensor entity."""

    def __init__(
        self,
        config_device: YamahaConfig,
        device: YamahaAVR,
        sensor_config: SensorConfig,
    ):
        """Initialize a Yamaha Sensor entity.

        Args:
            config_device: Device configuration
            device: YamahaAVR device instance
            sensor_config: SensorConfig dataclass with sensor metadata
        """
        self._device = device
        self._sensor_id = sensor_config.identifier

        # Set entity_id for FrameworkEntity mixin
        self._entity_id = create_entity_id(
            EntityTypes.SENSOR, config_device.identifier, sensor_config.identifier
        )

        attributes: dict[str, Any] = {
            Attributes.STATE: States.UNKNOWN,
            Attributes.VALUE: sensor_config.default,
        }

        if sensor_config.unit is not None:
            attributes[Attributes.UNIT] = sensor_config.unit

        _LOG.debug("Initializing sensor entity: %s", self._entity_id)

        super().__init__(
            identifier=self._entity_id,
            name=f"{sensor_config.name}",
            features=[],
            attributes=attributes,
            device_class=DeviceClasses.CUSTOM,
        )

    def refresh_state(self) -> None:
        """Refresh sensor state from device and update entity.

        This method is called by the device after updating sensor values.
        It retrieves the current attributes and uses entity.update() to
        notify the framework.
        """

        self.update(self._device.get_device_attributes(self.id))
