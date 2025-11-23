"""
Configuration handling of the integration driver.

:copyright: (c) 2025 by Jack Powell.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from dataclasses import dataclass
from ucapi_framework import BaseDeviceManager

_LOG = logging.getLogger(__name__)


@dataclass
class YamahaDevice:
    """Yamaha device configuration."""

    identifier: str
    """Unique identifier of the device. (MAC Address)"""
    name: str
    """Friendly name of the device."""
    address: str
    """IP Address of device"""
    input_list: list[str] | None = None
    """List of inputs for the device, if available."""
    volume_step: str = "1"
    """Volume step for the device, default is 1. Can be set to '0.5' or '2'."""
    sound_modes: list[str] | None = None
    """List of sound modes for the device, if available."""


class YamahaDeviceManager(BaseDeviceManager[YamahaDevice]):
    """Configuration manager for Yamaha devices."""

    def deserialize_device(self, data: dict) -> YamahaDevice | None:
        """Deserialize Yamaha device from JSON."""
        try:
            return YamahaDevice(
                identifier=data["identifier"],
                name=data.get("name", "Yamaha Device"),
                address=data["address"],
                input_list=data.get("input_list"),
                volume_step=data.get("volume_step", "1"),
                sound_modes=data.get("sound_modes"),
            )
        except (KeyError, TypeError) as ex:
            _LOG.error("Failed to deserialize Yamaha device: %s", ex)
            return None
