"""Discover Yamaha Receivers in local network using SSDP"""

import logging
import re

from ucapi_framework import DiscoveredDevice
from ucapi_framework.discovery import SSDPDiscovery

_LOG = logging.getLogger("discover")


class YamahaReceiverDiscovery(SSDPDiscovery):
    """Discover Yamaha Receivers in local network using SSDP."""

    @staticmethod
    def is_yamaha_device(raw_device: dict) -> bool:
        """
        Filter to identify Yamaha AVR devices.

        :param raw_device: Raw SSDP device data
        :return: True if device is a Yamaha AVR
        """
        model_name = raw_device.get("x-modelname", "")
        # Check if model name contains Yamaha AVR patterns
        return bool(re.search(r"RX-|R-N", model_name))

    def parse_ssdp_device(self, raw_device: dict) -> DiscoveredDevice | None:
        """
        Parse raw SSDP device data into DiscoveredDevice.

        :param raw_device: Raw SSDP device data
        :return: DiscoveredDevice or None if parsing fails
        """
        try:
            # Extract IP address from location URL
            location = raw_device.get("location", "")
            match = re.search(r"http://([\d\.]+):", location)
            if not match:
                _LOG.debug("Could not extract IP from location: %s", location)
                return None

            ip_address = match.group(1)

            # Extract model name
            model_name = raw_device.get("x-modelname", "Unknown Yamaha AVR")
            # Clean up model name (remove anything after colon)
            model_name = model_name.split(":")[0]

            # Use model name + IP as identifier (or extract serial if available)
            # You might want to fetch more info from the device to get a real serial number
            identifier = f"yamaha_{ip_address.replace('.', '_')}"

            _LOG.info("Discovered Yamaha AVR: %s at %s", model_name, ip_address)

            return DiscoveredDevice(
                identifier=identifier,
                name=model_name,
                address=ip_address,
                extra_data={
                    "location": location,
                    "model_name": model_name,
                    "raw_data": raw_device,
                },
            )

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Failed to parse SSDP device: %s", err)
            return None
