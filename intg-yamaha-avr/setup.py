"""
Setup flow for Yamaha AVR Remote integration.

:copyright: (c) 2023-2024 by Jack Powell
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import aiohttp
from const import YamahaConfig
from pyamaha import AsyncDevice, System, Zone
from ucapi import IntegrationSetupError, RequestUserInput, SetupError
from ucapi_framework import BaseSetupFlow

_LOG = logging.getLogger(__name__)


class YamahaSetupFlow(BaseSetupFlow[YamahaConfig]):
    """
    Setup flow for Yamaha AVR integration.

    Handles Yamaha AVR configuration through SSDP discovery or manual entry.
    """

    def get_manual_entry_form(self) -> RequestUserInput:
        """
        Get the manual entry form for Yamaha AVR setup.

        :return: RequestUserInput for manual entry
        """
        return RequestUserInput(
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
                    "id": "address",
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
                {
                    "id": "volume_mode_info",
                    "label": {
                        "en": "Volume Mode",
                    },
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "To use R3 slider for volume, you must select Absolute. "
                                    "Otherwise, choose the option that matches your receiver."
                                ),
                            }
                        }
                    },
                },
                {
                    "field": {
                        "dropdown": {
                            "value": "",
                            "items": [
                                {
                                    "id": "",
                                    "label": {"en": "Auto-detect from receiver"},
                                },
                                {"id": "relative", "label": {"en": "Relative"}},
                                {"id": "absolute", "label": {"en": "Absolute"}},
                            ],
                        }
                    },
                    "id": "volume_mode",
                    "label": {
                        "en": "Volume Mode",
                    },
                },
            ],
        )

    def get_additional_discovery_fields(self) -> list[dict]:
        """
        Return additional fields for discovery-based setup.

        :return: List of dictionaries defining additional fields
        """
        return [
            {
                "field": {"text": {"value": "1"}},
                "id": "step",
                "label": {
                    "en": "Volume Step",
                },
            },
            {
                "id": "volume_mode_info",
                "label": {
                    "en": "Volume Mode",
                },
                "field": {
                    "label": {
                        "value": {
                            "en": (
                                "To use R3 slider for volume, you must select Absolute. "
                                "Otherwise, choose the option that matches your receiver."
                            ),
                        }
                    }
                },
            },
            {
                "field": {
                    "dropdown": {
                        "value": "",
                        "items": [
                            {"id": "", "label": {"en": "Auto-detect from receiver"}},
                            {"id": "relative", "label": {"en": "Relative"}},
                            {"id": "absolute", "label": {"en": "Absolute"}},
                        ],
                    }
                },
                "id": "volume_mode",
                "label": {
                    "en": "Volume Mode",
                },
            },
        ]

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> YamahaConfig | SetupError | RequestUserInput:
        """
        Helper method to create device configuration from IP address.

        :param input_values: Dictionary containing 'address' (device IP address)
        and 'step' (volume step size).
        :return: Yamaha device configuration
        :raises IntegrationSetupError: If device setup fails
        """
        address = input_values.get("address")
        step = input_values.get("step", "1")
        volume_mode = input_values.get("volume_mode", "")
        if not address:
            return self.get_manual_entry_form()
        _LOG.debug("Connecting to Yamaha AVR at %s", address)

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=2)
            ) as client:
                dev = AsyncDevice(client, address)
                res = await dev.request(System.get_device_info())
                data = await res.json()
                res = await dev.request(System.get_features())
                features = await res.json()
                res = await dev.request(Zone.get_status("main"))
                status = await res.json()

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

            # If volume_mode is not selected, detect from API
            if not volume_mode:
                # Check actual_volume.mode from status response
                # "db" = relative, "numeric" = absolute
                actual_volume = status.get("actual_volume", {})
                actual_volume_mode = actual_volume.get("mode", "")

                if actual_volume_mode == "numeric":
                    volume_mode = "absolute"
                elif actual_volume_mode == "db":
                    volume_mode = "relative"
                else:
                    # Default to relative if we can't determine
                    volume_mode = "relative"

                _LOG.debug(
                    "Auto-detected volume mode: %s (actual_volume.mode: %s)",
                    volume_mode,
                    actual_volume_mode,
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
                return SetupError(IntegrationSetupError.OTHER)

            # if we are adding a new device: make sure it's not already configured
            if self._add_mode and self.config.contains(device_id):
                _LOG.warning(
                    "Device %s already configured, skipping",
                    data.get("model_name"),
                )
                return SetupError(IntegrationSetupError.OTHER)

            return YamahaConfig(
                identifier=device_id,
                name=data.get("model_name"),
                address=address,
                volume_step=step,
                volume_mode=volume_mode,
                input_list=input_list,
                sound_modes=sound_modes,
            )

        except aiohttp.ClientError as err:
            _LOG.error("Connection error to Yamaha AVR at %s: %s", address, err)
            return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
        except Exception as err:  # pylint: disable=broad-except
            _LOG.error("Setup error for Yamaha AVR at %s: %s", address, err)
            return SetupError(IntegrationSetupError.OTHER)
