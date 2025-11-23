#!/usr/bin/env python3
"""
This module implements a Remote Two integration driver for Apple TV devices.

:copyright: (c) 2023-2024 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import Any

import ucapi
from avr import YamahaAVR
from config import YamahaDevice, YamahaDeviceManager
from discover import YamahaReceiverDiscovery
from media_player import YamahaMediaPlayer
from remote import YamahaRemote
from setup import YamahaSetupFlow
from ucapi import media_player
from ucapi_framework import BaseIntegrationDriver

_LOG = logging.getLogger("driver")
_LOOP = asyncio.get_event_loop()


class YamahaIntegrationDriver(BaseIntegrationDriver[YamahaAVR, YamahaDevice]):
    """Yamaha AVR Integration Driver"""

    async def on_device_update(
        self, device_id: str, update: dict[str, Any] | None
    ) -> None:
        """
        Handle Yamaha AVR device state updates.

        :param device_id: Device identifier (account_id)
        :param update: Dictionary containing updated Yamaha AVR properties
        """
        if update is None:
            _LOG.warning("[%s] Received None update, skipping", device_id)
            return

        target_entity = None
        for identifier in self.get_entity_ids_for_device(device_id):
            attributes = {}
            configured_entity = self.api.available_entities.get(identifier)
            if configured_entity is None:
                _LOG.debug(
                    "[%s] Entity %s not in available entities, skipping update",
                    device_id,
                    identifier,
                )
                continue

            if isinstance(configured_entity, YamahaMediaPlayer):
                target_entity = self.api.available_entities.get(identifier)
            elif isinstance(configured_entity, YamahaRemote):
                target_entity = self.api.available_entities.get(identifier)

        if "state" in update:
            state = self.map_device_state(update["state"])
            attributes[ucapi.media_player.Attributes.STATE] = state

        if isinstance(configured_entity, YamahaMediaPlayer):
            if "source_list" in update:
                if media_player.Attributes.SOURCE_LIST in target_entity.attributes:
                    if len(
                        target_entity.attributes[media_player.Attributes.SOURCE_LIST]
                    ) != len(update["source_list"]):
                        attributes[media_player.Attributes.SOURCE_LIST] = update[
                            "source_list"
                        ]
                else:
                    attributes[media_player.Attributes.SOURCE_LIST] = update[
                        "source_list"
                    ]

            if "sound_mode_list" in update:
                if media_player.Attributes.SOUND_MODE_LIST in target_entity.attributes:
                    if len(
                        target_entity.attributes[
                            media_player.Attributes.SOUND_MODE_LIST
                        ]
                    ) != len(update["sound_mode_list"]):
                        attributes[media_player.Attributes.SOUND_MODE_LIST] = update[
                            "sound_mode_list"
                        ]
                else:
                    attributes[media_player.Attributes.SOUND_MODE_LIST] = update[
                        "sound_mode_list"
                    ]
            if "source" in update:
                attributes[media_player.Attributes.MEDIA_TITLE] = update["source"]

            if "volume" in update:
                if (
                    target_entity.attributes.get(media_player.Attributes.VOLUME, None)
                    != update["volume"]
                ):
                    attributes[media_player.Attributes.VOLUME] = update["volume"]

            if "muted" in update:
                if (
                    target_entity.attributes.get(media_player.Attributes.MUTED, None)
                    != update["muted"]
                ):
                    attributes[media_player.Attributes.MUTED] = update["muted"]

            if "sound_mode" in update:
                attributes[media_player.Attributes.MEDIA_ARTIST] = update["sound_mode"]

            if media_player.Attributes.STATE in attributes:
                if attributes[media_player.Attributes.STATE] in [
                    media_player.States.OFF,
                    media_player.States.STANDBY,
                ]:
                    attributes[media_player.Attributes.SOURCE] = ""
                    attributes[media_player.Attributes.VOLUME] = ""
                    attributes[media_player.Attributes.MUTED] = False
                    attributes[media_player.Attributes.SOUND_MODE] = ""
                    attributes[media_player.Attributes.MEDIA_ARTIST] = ""
                    attributes[media_player.Attributes.MEDIA_TITLE] = ""

        if attributes:
            if self.api.configured_entities.contains(identifier):
                self.api.configured_entities.update_attributes(identifier, attributes)
            else:
                self.api.available_entities.update_attributes(identifier, attributes)


async def main():
    """Start the Remote Two integration driver."""
    logging.basicConfig()

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("config").setLevel(level)
    logging.getLogger("discover").setLevel(level)
    logging.getLogger("setup").setLevel(level)

    driver = YamahaIntegrationDriver(
        loop=_LOOP,
        device_class=YamahaAVR,
        entity_classes=[YamahaMediaPlayer, YamahaRemote],
    )
    # Initialize configuration manager with device callbacks
    driver.config = YamahaDeviceManager(
        driver.api.config_dir_path, driver.on_device_added, driver.on_device_removed
    )

    # Load and register all configured devices
    loaded_devices = list(driver.config.all())
    _LOG.info("Loaded %d configured device(s)", len(loaded_devices))
    for device in loaded_devices:
        driver.add_configured_device(device, connect=False)

    # Initialize SSDP discovery for Yamaha AVRs
    discovery = YamahaReceiverDiscovery(
        timeout=2,
        search_target="urn:schemas-upnp-org:device:MediaRenderer:1",
        device_filter=YamahaReceiverDiscovery.is_yamaha_device,
    )
    setup_handler = YamahaSetupFlow.create_handler(driver.config, discovery)

    await driver.api.init("driver.json", setup_handler)


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
