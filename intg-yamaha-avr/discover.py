"""Discover Yamaha Receivers in local network using SSDP"""

import logging
from dataclasses import dataclass
import re
from ssdpy import SSDPClient


_LOG = logging.getLogger("discover")  # avoid having __main__ in log messages


@dataclass
class YamahaReceiverDetails:
    """Class to hold details about Yamaha Receiver discovered via SSDP"""

    modelname: str = None
    ip_address: str = None


class YamahaReceiverDiscovery:
    """Class to discover Yamaha Receivers in local network using SSDP"""

    def __init__(self):
        self.receivers: list[YamahaReceiverDetails] = []

    def __repr__(self):
        return f"YamahaReceiverDiscovery(receivers={self.receivers})"

    def discover(self, timeout=2) -> list[YamahaReceiverDetails]:
        """Crude SSDP discovery. Returns a list of RxvDetails objects
        with data about Yamaha Receivers in local network"""
        client = SSDPClient(timeout=timeout)
        devices = client.m_search("ssdp:all")

        receiver: YamahaReceiverDetails = YamahaReceiverDetails()
        media_renderers = [
            device
            for device in devices
            if device.get("st") == "urn:schemas-upnp-org:device:MediaRenderer:1"
        ]

        for device in media_renderers:
            _LOG.debug("Found device: %s", device)
            match = re.search(r"http://([\d\.]+):", device.get("location", ""))
            receiver.ip_address = match.group(1) if match else None
            if not receiver.ip_address:
                continue
            match = re.search(r"RX-|R-N", device.get("x-modelname", ""))
            if not match:
                continue
            receiver.modelname = device.get("x-modelname").split(":")[0]
            _LOG.info("%s - %s", device["location"], device.get("x-modelname"))
            self.receivers.append(receiver)
            receiver = YamahaReceiverDetails()

        return self.receivers
