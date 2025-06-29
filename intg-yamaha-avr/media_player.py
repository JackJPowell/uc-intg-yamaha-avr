"""
Media-player entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any
import asyncio
import ucapi
import ucapi.api as uc

import avr
from config import YamahaDevice, create_entity_id
from const import SimpleCommands
from ucapi import MediaPlayer, media_player, EntityTypes
from ucapi.media_player import DeviceClasses, Attributes

_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)

_LOG = logging.getLogger(__name__)
api = uc.IntegrationAPI(_LOOP)
_configured_devices: dict[str, avr.YamahaAVR] = {}

features = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.HOME,
    media_player.Features.DPAD,
    media_player.Features.SELECT_SOURCE,
    media_player.Features.MENU,
    media_player.Features.NUMPAD,
    media_player.Features.INFO,
    media_player.Features.SETTINGS,
]


class YamahaMediaPlayer(MediaPlayer):
    """Representation of a Yamaha MediaPlayer entity."""

    def __init__(self, config_device: YamahaDevice, device: avr.YamahaAVR):
        """Initialize the class."""
        self._device = device
        _LOG.debug("Yamaha AVR Media Player init")
        entity_id = create_entity_id(config_device.identifier, EntityTypes.MEDIA_PLAYER)
        self.config = config_device

        super().__init__(
            entity_id,
            config_device.name,
            features,
            attributes={
                Attributes.STATE: device.state,
                Attributes.SOURCE: device.source if device.source else "",
                Attributes.SOURCE_LIST: device.source_list,
            },
            device_class=DeviceClasses.TV,
            options={
                media_player.Options.SIMPLE_COMMANDS: [
                    SimpleCommands.EXIT.value,
                    SimpleCommands.SLEEP.value,
                    SimpleCommands.HDMI_OUTPUT_1.value,
                    SimpleCommands.HDMI_OUTPUT_2.value,
                    SimpleCommands.SOUND_MODE_DIRECT.value,
                    SimpleCommands.SOUND_MODE_PURE.value,
                    SimpleCommands.SOUND_MODE_CLEAR_VOICE.value,
                ],
            },
            cmd_handler=self.media_player_cmd_handler,
        )

    # pylint: disable=too-many-statements
    async def media_player_cmd_handler(
        self, entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> ucapi.StatusCodes:
        """
        Media-player entity command handler.

        Called by the integration-API if a command is sent to a configured media-player entity.

        :param entity: media-player entity
        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command. StatusCodes.OK if the command succeeded.
        """
        _LOG.info(
            "Got %s command request: %s %s", entity.id, cmd_id, params if params else ""
        )

        avr = self._device
        zone = self._device.zone
        # ir_code = _get_cmd_param("ir_code", "")

        try:
            match cmd_id:
                case media_player.Commands.ON:
                    _LOG.debug("Sending ON command to AVR")
                    res = await avr.send_command(
                        "setPower", group="zone", zone="main", power="on"
                    )
                case media_player.Commands.OFF:
                    res = await avr.send_command(
                        "setPower", group="zone", zone="main", power="off"
                    )
                case media_player.Commands.TOGGLE:
                    res = await avr.send_command(
                        "setPower", group="zone", zone="main", power="toggle"
                    )
                case media_player.Commands.VOLUME_UP:
                    res = await avr.send_command(
                        "setVolume", group="zone", zone="main", volume="up"
                    )
                case media_player.Commands.VOLUME_DOWN:
                    res = await avr.send_command(
                        "setVolume", group="zone", zone="main", volume="down"
                    )
                case media_player.Commands.MUTE_TOGGLE:  # TODO mute status
                    res = await avr.send_command(
                        "setMute", group="zone", zone="main", mute=True
                    )
                case (
                    media_player.Commands.CURSOR_UP
                    | media_player.Commands.CURSOR_DOWN
                    | media_player.Commands.CURSOR_LEFT
                    | media_player.Commands.CURSOR_RIGHT
                    | media_player.Commands.CURSOR_ENTER
                    | media_player.Commands.BACK
                    | media_player.Commands.DIGIT_0
                    | media_player.Commands.DIGIT_1
                    | media_player.Commands.DIGIT_2
                    | media_player.Commands.DIGIT_3
                    | media_player.Commands.DIGIT_4
                    | media_player.Commands.DIGIT_5
                    | media_player.Commands.DIGIT_6
                    | media_player.Commands.DIGIT_7
                    | media_player.Commands.DIGIT_8
                    | media_player.Commands.DIGIT_9
                    | media_player.Commands.HOME
                    | media_player.Commands.MENU
                    | media_player.Commands.INFO
                    | media_player.Commands.GUIDE
                    | media_player.Commands.BACK
                    | media_player.Commands.SETTINGS
                ):
                    # res = await avr.send_command("sendIrCode", ir_code)
                    pass
                case media_player.Commands.SELECT_SOURCE:
                    await avr.send_command("setInput", zone, params.get("source"))
                # --- simple commands ---
                case SimpleCommands.EXIT.value:
                    # res = await avr.send_command("sendIrCode", ir_code)
                    pass
                case SimpleCommands.SLEEP.value:  # TODO sleep time
                    res = await avr.send_command("setSleep", zone, 60)
                case SimpleCommands.HDMI_OUTPUT_1.value:
                    res = await avr.send_command("setHdmiOut1")
                case SimpleCommands.HDMI_OUTPUT_2.value:
                    res = await avr.send_command("setHdmiOut2")
                case SimpleCommands.SOUND_MODE_DIRECT.value:
                    res = await avr.send_command("setDirect")
                case SimpleCommands.SOUND_MODE_PURE.value:
                    res = await avr.send_command("setPure")
                case SimpleCommands.SOUND_MODE_CLEAR_VOICE.value:
                    res = await avr.send_command("setClearVoice")

        except Exception as ex:  # pylint: disable=broad-except
            _LOG.error("Error executing command %s: %s", cmd_id, ex)
            return ucapi.StatusCodes.TIMEOUT
        return ucapi.StatusCodes.OK


def _get_cmd_param(name: str, params: dict[str, Any] | None) -> str | bool | None:
    if params is None:
        return None
    return params.get(name)
