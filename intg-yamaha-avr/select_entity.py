"""
Select entity functions for the Yamaha AVR integration.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

import ucapi
from avr import YamahaAVR
from const import YamahaConfig, SelectConfig
from ucapi import EntityTypes, StatusCodes
from ucapi.select import Attributes, Commands, States
from ucapi_framework import create_entity_id
from ucapi_framework.entities import SelectEntity

_LOG = logging.getLogger(__name__)


class YamahaSelect(SelectEntity):
    """Representation of a Yamaha AVR Select entity.

    The current option is never stored here — it lives in the matching
    SensorConfig.value on the device, ensuring sensors and selects that
    represent the same piece of data share a single source of truth.
    """

    def __init__(
        self,
        config_device: YamahaConfig,
        device: YamahaAVR,
        select_config: SelectConfig,
    ):
        """Initialize a Yamaha Select entity."""
        self._device = device
        self._select_id = select_config.identifier

        entity_id = create_entity_id(
            EntityTypes.SELECT, config_device.identifier, select_config.identifier
        )

        _LOG.debug("Initializing select entity: %s", entity_id)

        super().__init__(
            entity_id,
            select_config.name,
            attributes={
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.CURRENT_OPTION: "",
                Attributes.OPTIONS: select_config.options or [],
            },
            cmd_handler=self.select_cmd_handler,
        )

        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        """Sync select state from device after push_update() or reconnect."""
        if self._device is None:
            self.set_unavailable()
            return

        attrs = self._device.get_select_attributes(
            self._device.identifier, self._select_id
        )
        if attrs is not None:
            self.update(attrs)

    async def select_cmd_handler(
        self,
        _entity: Any,
        cmd_id: str,
        params: dict[str, Any] | None,
        _websocket: Any = None,
    ) -> StatusCodes:
        """Handle select entity commands."""
        _LOG.debug("[%s] Command: %s, params: %s", self._select_id, cmd_id, params)

        if self._device is None:
            return ucapi.StatusCodes.SERVICE_UNAVAILABLE

        match cmd_id:
            case Commands.SELECT_OPTION:
                if params and "option" in params:
                    return await self._select_option(params["option"])
                return StatusCodes.BAD_REQUEST

            case Commands.SELECT_FIRST:
                options = self.attributes.get(Attributes.OPTIONS, [])
                if options:
                    return await self._select_option(options[0])
                return StatusCodes.BAD_REQUEST

            case Commands.SELECT_LAST:
                options = self.attributes.get(Attributes.OPTIONS, [])
                if options:
                    return await self._select_option(options[-1])
                return StatusCodes.BAD_REQUEST

            case Commands.SELECT_NEXT:
                options = self.attributes.get(Attributes.OPTIONS, [])
                current = self.attributes.get(Attributes.CURRENT_OPTION, "")
                if options and current in options:
                    cycle = params.get("cycle", False) if params else False
                    idx = options.index(current)
                    if idx < len(options) - 1:
                        return await self._select_option(options[idx + 1])
                    elif cycle:
                        return await self._select_option(options[0])
                return StatusCodes.BAD_REQUEST

            case Commands.SELECT_PREVIOUS:
                options = self.attributes.get(Attributes.OPTIONS, [])
                current = self.attributes.get(Attributes.CURRENT_OPTION, "")
                if options and current in options:
                    cycle = params.get("cycle", False) if params else False
                    idx = options.index(current)
                    if idx > 0:
                        return await self._select_option(options[idx - 1])
                    elif cycle:
                        return await self._select_option(options[-1])
                return StatusCodes.BAD_REQUEST

            case _:
                _LOG.warning("[%s] Unknown command: %s", self._select_id, cmd_id)
                return StatusCodes.NOT_IMPLEMENTED

    async def _select_option(self, option: str) -> StatusCodes:
        """Send the selected option to the device."""
        _LOG.debug("[%s] Selecting option: %s", self._select_id, option)
        try:
            await self._device.send_command(
                "setSelect",
                group="zone",
                zone=self._device.zone,
                select_id=self._select_id,
                option=option,
            )
            _LOG.info("[%s] Successfully set to: %s", self._select_id, option)
            return StatusCodes.OK
        except (ValueError, Exception) as err:  # pylint: disable=broad-exception-caught
            _LOG.error(
                "[%s] Failed to select option '%s': %s",
                self._select_id,
                option,
                err,
            )
            return StatusCodes.SERVER_ERROR
