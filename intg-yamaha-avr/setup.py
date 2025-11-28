"""
Setup flow for Yamaha AVR Remote integration.

:copyright: (c) 2023-2024 by Jack Powell
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import aiohttp
from const import YamahaDevice
from pyamaha import AsyncDevice, System
from ucapi import IntegrationSetupError, RequestUserInput
from ucapi_framework import BaseSetupFlow

_LOG = logging.getLogger(__name__)

_MANUAL_INPUT_SCHEMA = RequestUserInput(
    {"en": "Yamaha AVR Setup"},
    [
        {
            "id": "info",
            "label": {
                "en": "Setup Information",
            },
            "field": {
                "label": {
                    "value": {
                        "en": (
                            "Please supply the following settings for your Yamaha AVR."
                        ),
                    }
                }
            },
        },
        {
            "field": {"text": {"value": ""}},
            "id": "ip",
            "label": {
                "en": "IP Address",
            },
        },
        {
            "field": {"text": {"value": "1"}},
            "id": "step",
            "label": {
                "en": "Volume Step",
            },
        },
    ],
)


class YamahaSetupFlow(BaseSetupFlow[YamahaDevice]):
    """
    Setup flow for Yamaha AVR integration.

    Handles Yamaha AVR configuration through SSDP discovery or manual entry.
    """

    async def create_device_from_discovery(
        self, device_id: str, additional_data: dict[str, Any]
    ) -> YamahaDevice:
        """
        Create Yamaha device configuration from discovered device.

        :param device_id: Discovered device identifier
        :param additional_data: Additional user input data (e.g., volume step)
        :return: Yamaha device configuration
        :raises IntegrationSetupError: If device setup fails
        """
        # Look up the discovered device using the framework's helper
        discovered = self.get_discovered_devices(device_id)

        if not discovered:
            _LOG.error("Discovered device %s not found", device_id)
            raise IntegrationSetupError("Device not found")

        ip = discovered.address
        step = additional_data.get("step", "1")

        return await self._create_device_from_ip(ip, step)

    async def create_device_from_manual_entry(
        self, input_values: dict[str, Any]
    ) -> YamahaDevice | RequestUserInput:
        """
        Create Yamaha device configuration from manual entry.

        :param input_values: User input containing 'ip' and 'volume_step'
        :return: Yamaha device configuration or RequestUserInput to re-display form
        """
        ip = input_values.get("ip", "").strip()
        step = input_values.get("step", "1")

        if not ip:
            # Re-display the form if IP is missing
            _LOG.warning("IP address is required, re-displaying form")
            return _MANUAL_INPUT_SCHEMA

        return await self._create_device_from_ip(ip, step)

    async def _create_device_from_ip(self, ip: str, volume_step: str) -> YamahaDevice:
        """
        Helper method to create device configuration from IP address.

        :param ip: Device IP address
        :param volume_step: Volume step size
        :return: Yamaha device configuration
        :raises IntegrationSetupError: If device setup fails
        """
        _LOG.debug("Connecting to Yamaha AVR at %s", ip)

        try:
            async with aiohttp.ClientSession(conn_timeout=2) as client:
                dev = AsyncDevice(client, ip)
                res = await dev.request(System.get_device_info())
                data = await res.json()
                res = await dev.request(System.get_features())
                features = await res.json()

            input_list = next(
                (
                    zone.get("input_list", [])
                    for zone in features["zone"]
                    if zone["id"] == "main"
                ),
                [],
            )
            sound_modes = next(
                (
                    zone.get("sound_mode_list", [])
                    for zone in features["zone"]
                    if zone["id"] == "main"
                ),
                [],
            )

            _LOG.debug("Yamaha AVR input list: %s", input_list)
            _LOG.debug("Yamaha AVR sound modes: %s", sound_modes)
            _LOG.debug("Yamaha AVR device info: %s", data)

            device_id = data.get("serial_number", data.get("device_id"))
            if not device_id:
                device_id = data.get("model_name", None)
            if not device_id:
                _LOG.error(
                    "Could not determine device identifier from response: %s", data
                )
                raise IntegrationSetupError("Could not determine device identifier")

            # if we are adding a new device: make sure it's not already configured
            if self._add_mode and self.config.contains(device_id):
                _LOG.warning(
                    "Device %s already configured, skipping",
                    data.get("model_name"),
                )
                raise IntegrationSetupError("Device already configured")

            return YamahaDevice(
                identifier=device_id,
                name=data.get("model_name"),
                address=ip,
                volume_step=volume_step,
                input_list=input_list,
                sound_modes=sound_modes,
            )

        except aiohttp.ClientError as err:
            _LOG.error("Connection error to Yamaha AVR at %s: %s", ip, err)
            raise IntegrationSetupError("Could not connect to device") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOG.error("Setup error for Yamaha AVR at %s: %s", ip, err)
            raise IntegrationSetupError("Device setup failed") from err

    def get_manual_entry_form(self) -> RequestUserInput:
        """
        Get the manual entry form for Yamaha AVR setup.

        :return: RequestUserInput for manual entry
        """
        return _MANUAL_INPUT_SCHEMA
