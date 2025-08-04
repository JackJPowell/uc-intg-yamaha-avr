"""
Media-player entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any
import asyncio
import ucapi
import ucapi.api as uc
import re

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
    media_player.Features.VOLUME,
    media_player.Features.SELECT_SOUND_MODE,
]


class YamahaMediaPlayer(MediaPlayer):
    """Representation of a Yamaha MediaPlayer entity."""

    def __init__(self, config_device: YamahaDevice, device: avr.YamahaAVR):
        """Initialize the class."""
        self._device = device
        _LOG.debug("Yamaha AVR Media Player init")
        entity_id = create_entity_id(config_device.identifier, EntityTypes.MEDIA_PLAYER)
        self.config = config_device
        self.options = [
            SimpleCommands.SLEEP_OFF.value,
            SimpleCommands.SLEEP_30.value,
            SimpleCommands.SLEEP_60.value,
            SimpleCommands.SLEEP_90.value,
            SimpleCommands.SLEEP_120.value,
            SimpleCommands.HDMI_OUTPUT_1.value,
            SimpleCommands.HDMI_OUTPUT_2.value,
            SimpleCommands.SOUND_MODE_DIRECT.value,
            SimpleCommands.SOUND_MODE_PURE.value,
            SimpleCommands.SOUND_MODE_CLEAR_VOICE.value,
            SimpleCommands.OPTIONS.value,
        ]
        if self._device.speaker_pattern_count > 0:
            for pattern in range(self._device.speaker_pattern_count):
                self.options.extend([f"SPEAKER_PATTERN_{pattern + 1}"])

        super().__init__(
            entity_id,
            config_device.name,
            features,
            attributes={
                Attributes.STATE: device.state,
                Attributes.SOURCE: device.source if device.source else "",
                Attributes.SOURCE_LIST: device.source_list,
                Attributes.MUTED: device.muted,
                Attributes.SOUND_MODE: device.sound_mode if device.sound_mode else "",
                Attributes.SOUND_MODE_LIST: device.sound_mode_list
                if device.sound_mode_list
                else [],
                Attributes.VOLUME: device.volume,
            },
            device_class=DeviceClasses.RECEIVER,
            options={media_player.Options.SIMPLE_COMMANDS: self.options},
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
        pattern = 0
        res = None

        yamaha = self._device

        if re.match("SPEAKER_PATTERN", cmd_id):
            pattern = cmd_id.split("_")[-1]
            cmd_id = "SPEAKER_PATTERN"

        try:
            match cmd_id:
                case media_player.Commands.ON:
                    _LOG.debug("Sending ON command to AVR")
                    res = await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="on"
                    )
                case media_player.Commands.OFF:
                    res = await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="standby"
                    )
                case media_player.Commands.TOGGLE:
                    res = await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="toggle"
                    )
                case media_player.Commands.VOLUME_UP:
                    res = await yamaha.send_command(
                        "setVolume", group="zone", zone="main", volume="up"
                    )
                case media_player.Commands.VOLUME_DOWN:
                    res = await yamaha.send_command(
                        "setVolume", group="zone", zone="main", volume="down"
                    )
                case media_player.Commands.VOLUME:
                    volume_level = params.get("volume")
                    res = await yamaha.send_command(
                        "setVolume",
                        group="zone",
                        zone="main",
                        volume_level=volume_level,
                    )
                case media_player.Commands.MUTE:
                    res = await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute=True
                    )
                case media_player.Commands.UNMUTE:
                    res = await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute=False
                    )
                case media_player.Commands.MUTE_TOGGLE:
                    res = await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute="toggle"
                    )
                case media_player.Commands.CURSOR_UP:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="up"
                    )
                case media_player.Commands.CURSOR_DOWN:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="down"
                    )
                case media_player.Commands.CURSOR_LEFT:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="left"
                    )
                case media_player.Commands.CURSOR_RIGHT:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="right"
                    )
                case media_player.Commands.CURSOR_ENTER:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="select"
                    )
                case media_player.Commands.BACK | SimpleCommands.RETURN.value:
                    res = await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="return"
                    )
                case media_player.Commands.INFO:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="display"
                    )
                case media_player.Commands.SETTINGS:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="on_screen"
                    )
                case media_player.Commands.HOME:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="home"
                    )
                case media_player.Commands.FUNCTION_RED:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="red"
                    )
                case media_player.Commands.FUNCTION_GREEN:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="green"
                    )
                case media_player.Commands.FUNCTION_YELLOW:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="yellow"
                    )
                case media_player.Commands.FUNCTION_BLUE:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="blue"
                    )
                case media_player.Commands.SELECT_SOURCE:
                    res = await yamaha.send_command(
                        "setInput",
                        group="zone",
                        zone="main",
                        input_source=params.get("source"),
                    )
                case media_player.Commands.SELECT_SOUND_MODE:
                    res = await yamaha.send_command(
                        "setSoundProgram",
                        group="zone",
                        zone="main",
                        sound_mode=params.get("mode"),
                    )
                # --- simple commands ---
                case SimpleCommands.SLEEP_OFF.value:
                    res = await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="0"
                    )
                case SimpleCommands.SLEEP_30.value:
                    res = await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="30"
                    )
                case SimpleCommands.SLEEP_60.value:
                    res = await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="60"
                    )
                case SimpleCommands.SLEEP_90.value:
                    res = await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="90"
                    )
                case SimpleCommands.SLEEP_120.value:
                    res = await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="120"
                    )
                case SimpleCommands.HDMI_OUTPUT_1.value:
                    res = await yamaha.send_command(
                        "setHdmiOut1", group="zone", zone="main"
                    )
                case SimpleCommands.HDMI_OUTPUT_2.value:
                    res = await yamaha.send_command(
                        "setHdmiOut2", group="zone", zone="main"
                    )
                case SimpleCommands.SOUND_MODE_DIRECT.value:
                    res = await yamaha.send_command(
                        "setDirect", group="zone", zone="main"
                    )
                case SimpleCommands.SOUND_MODE_PURE.value:
                    res = await yamaha.send_command(
                        "setPure", group="zone", zone="main"
                    )
                case SimpleCommands.SOUND_MODE_CLEAR_VOICE.value:
                    res = await yamaha.send_command(
                        "setClearVoice", group="zone", zone="main"
                    )
                case SimpleCommands.OPTIONS.value:
                    res = await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="option"
                    )
                case "SPEAKER_PATTERN":
                    if int(pattern) > 0:
                        res = await yamaha.send_command(
                            "setSpeakerPattern", group="system", pattern=pattern
                        )
                    else:
                        return ucapi.StatusCodes.BAD_REQUEST
                    pattern = 0

        except Exception as ex:  # pylint: disable=broad-except
            _LOG.error("Error executing command %s: %s", cmd_id, ex)
            return ucapi.StatusCodes.BAD_REQUEST
        return ucapi.StatusCodes.OK


def _get_cmd_param(name: str, params: dict[str, Any] | None) -> str | bool | None:
    if params is None:
        return None
    return params.get(name)
