#!/usr/bin/env python3
"""
This module implements a Remote Two integration driver for Apple TV devices.

:copyright: (c) 2023-2024 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os

from avr import YamahaAVR
from const import YamahaConfig
from discover import YamahaReceiverDiscovery
from media_player import YamahaMediaPlayer
from remote import YamahaRemote
from setup import YamahaSetupFlow
from ucapi_framework import BaseConfigManager, BaseIntegrationDriver, get_config_path


async def main():
    """Start the Remote Two integration driver."""
    logging.basicConfig()

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("discover").setLevel(level)
    logging.getLogger("setup").setLevel(level)

    driver = BaseIntegrationDriver(
        device_class=YamahaAVR,
        entity_classes=[YamahaMediaPlayer, YamahaRemote],
    )

    driver.config_manager = BaseConfigManager(
        get_config_path(driver.api.config_dir_path),
        driver.on_device_added,
        driver.on_device_removed,
        config_class=YamahaConfig,
    )

    await driver.register_all_configured_devices()

    discovery = YamahaReceiverDiscovery(
        timeout=2,
        search_target="urn:schemas-upnp-org:device:MediaRenderer:1",
        device_filter=YamahaReceiverDiscovery.is_yamaha_device,
    )

    setup_handler = YamahaSetupFlow.create_handler(driver, discovery=discovery)
    await driver.api.init("driver.json", setup_handler)

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
