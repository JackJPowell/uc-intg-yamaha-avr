"""
Media-player entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
import re
from typing import Any

from avr import YamahaAVR
import ucapi
from const import SimpleCommands, YamahaConfig
from ucapi import EntityTypes, MediaPlayer, media_player
from ucapi.media_player import Attributes, DeviceClasses
from ucapi_framework import create_entity_id
from ucapi_framework.entity import Entity as FrameworkEntity

_LOG = logging.getLogger(__name__)

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


class YamahaMediaPlayer(MediaPlayer, FrameworkEntity):
    """Representation of a Yamaha MediaPlayer entity."""

    def __init__(self, config_device: YamahaConfig, device: YamahaAVR):
        """Initialize the class."""
        self._device = device
        _LOG.debug("Yamaha AVR Media Player init")
        self._entity_id = create_entity_id(
            EntityTypes.MEDIA_PLAYER, config_device.identifier
        )

        self.config = config_device
        self.options = [cmd.value for cmd in SimpleCommands]
        if self._device.speaker_pattern_count > 0:
            for pattern in range(self._device.speaker_pattern_count):
                self.options.extend([f"SPEAKER_PATTERN_{pattern + 1}"])

        super().__init__(
            self._entity_id,
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
                Attributes.VOLUME: device.volume_percent,
            },
            device_class=DeviceClasses.RECEIVER,
            options={media_player.Options.SIMPLE_COMMANDS: self.options},
            cmd_handler=self.media_player_cmd_handler,  # type: ignore[arg-type]
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
        scene_id = 1
        state_changed = False  # Track if command changes device state

        yamaha = self._device

        if re.match("SPEAKER_PATTERN", cmd_id):
            pattern = cmd_id.split("_")[-1]
            cmd_id = "SPEAKER_PATTERN"

        if re.match("SCENE", cmd_id, re.IGNORECASE):
            scene_id = cmd_id.split(" ")[-1]
            cmd_id = "SCENE"

        try:
            match cmd_id:
                case media_player.Commands.ON:
                    _LOG.debug("Sending ON command to AVR")
                    await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="on"
                    )
                    state_changed = True
                case media_player.Commands.OFF:
                    await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="standby"
                    )
                    state_changed = True
                case media_player.Commands.TOGGLE:
                    await yamaha.send_command(
                        "setPower", group="zone", zone="main", power="toggle"
                    )
                    state_changed = True
                case media_player.Commands.VOLUME_UP:
                    await yamaha.send_command(
                        "setVolume", group="zone", zone="main", volume="up"
                    )
                    state_changed = True
                case media_player.Commands.VOLUME_DOWN:
                    await yamaha.send_command(
                        "setVolume", group="zone", zone="main", volume="down"
                    )
                    state_changed = True
                case media_player.Commands.VOLUME:
                    volume_level = params.get("volume") if params else None
                    await yamaha.send_command(
                        "setVolume",
                        group="zone",
                        zone="main",
                        volume_level=volume_level,
                    )
                    state_changed = True
                case media_player.Commands.MUTE:
                    await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute=True
                    )
                    state_changed = True
                case media_player.Commands.UNMUTE:
                    await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute=False
                    )
                    state_changed = True
                case media_player.Commands.MUTE_TOGGLE:
                    await yamaha.send_command(
                        "setMute", group="zone", zone="main", mute="toggle"
                    )
                    state_changed = True
                case media_player.Commands.CURSOR_UP:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="up"
                    )
                case media_player.Commands.CURSOR_DOWN:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="down"
                    )
                case media_player.Commands.CURSOR_LEFT:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="left"
                    )
                case media_player.Commands.CURSOR_RIGHT:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="right"
                    )
                case media_player.Commands.CURSOR_ENTER:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="select"
                    )
                case media_player.Commands.BACK | SimpleCommands.RETURN.value:
                    await yamaha.send_command(
                        "controlCursor", group="zone", zone="main", cursor="return"
                    )
                case media_player.Commands.INFO:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="display"
                    )
                case media_player.Commands.SETTINGS:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="on_screen"
                    )
                case media_player.Commands.HOME:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="home"
                    )
                case media_player.Commands.FUNCTION_RED:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="red"
                    )
                case media_player.Commands.FUNCTION_GREEN:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="green"
                    )
                case media_player.Commands.FUNCTION_YELLOW:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="yellow"
                    )
                case media_player.Commands.FUNCTION_BLUE:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="blue"
                    )
                case media_player.Commands.SELECT_SOURCE:
                    await yamaha.send_command(
                        "setInput",
                        group="zone",
                        zone="main",
                        input_source=params.get("source") if params else None,
                    )
                    state_changed = True
                case media_player.Commands.SELECT_SOUND_MODE:
                    await yamaha.send_command(
                        "setSoundMode",
                        group="zone",
                        zone="main",
                        sound_mode=params.get("mode") if params else None,
                    )
                    state_changed = True
                # --- simple commands ---
                case SimpleCommands.SLEEP_OFF.value:
                    await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="0"
                    )
                    state_changed = True
                case SimpleCommands.SLEEP_30.value:
                    await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="30"
                    )
                    state_changed = True
                case SimpleCommands.SLEEP_60.value:
                    await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="60"
                    )
                    state_changed = True
                case SimpleCommands.SLEEP_90.value:
                    await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="90"
                    )
                    state_changed = True
                case SimpleCommands.SLEEP_120.value:
                    await yamaha.send_command(
                        "setSleep", group="zone", zone="main", sleep="120"
                    )
                    state_changed = True
                case SimpleCommands.HDMI_OUTPUT_1_ON.value:
                    await yamaha.send_command(
                        "setHdmiOut1", group="system", enabled=True
                    )
                    state_changed = True
                case SimpleCommands.HDMI_OUTPUT_1_OFF.value:
                    await yamaha.send_command(
                        "setHdmiOut1", group="system", enabled=False
                    )
                    state_changed = True
                case SimpleCommands.HDMI_OUTPUT_2_ON.value:
                    await yamaha.send_command(
                        "setHdmiOut2", group="system", enabled=True
                    )
                    state_changed = True
                case SimpleCommands.HDMI_OUTPUT_2_OFF.value:
                    await yamaha.send_command(
                        "setHdmiOut2", group="system", enabled=False
                    )
                    state_changed = True
                case SimpleCommands.SOUND_MODE_DIRECT.value:
                    await yamaha.send_command("setDirect", group="zone", zone="main")
                    state_changed = True
                case SimpleCommands.SOUND_MODE_PURE.value:
                    await yamaha.send_command(
                        "setPureDirect", group="zone", zone="main"
                    )
                    state_changed = True
                case SimpleCommands.SOUND_MODE_CLEAR_VOICE.value:
                    await yamaha.send_command(
                        "setClearVoice", group="zone", zone="main"
                    )
                    state_changed = True
                case SimpleCommands.OPTIONS.value:
                    await yamaha.send_command(
                        "controlMenu", group="zone", zone="main", menu="option"
                    )
                case "SCENE":
                    if int(scene_id) in range(1, 10):
                        await yamaha.send_command(
                            "setScene", group="zone", zone="main", scene=scene_id
                        )
                    else:
                        return ucapi.StatusCodes.BAD_REQUEST
                case "SPEAKER_PATTERN":
                    if int(pattern) > 0:
                        await yamaha.send_command(
                            "setSpeakerPattern", group="system", pattern=pattern
                        )
                    else:
                        return ucapi.StatusCodes.BAD_REQUEST
                case (
                    SimpleCommands.SURROUND_AI_ON.value | SimpleCommands.SURROUND_AI_ON
                ):
                    await yamaha.send_command(
                        "setSurroundAI", group="zone", zone="main", enabled="True"
                    )
                    state_changed = True
                case (
                    SimpleCommands.SURROUND_AI_OFF.value
                    | SimpleCommands.SURROUND_AI_OFF
                ):
                    await yamaha.send_command(
                        "setSurroundAI", group="zone", zone="main", enabled="False"
                    )
                    state_changed = True
                case (
                    SimpleCommands.FM_1.value
                    | SimpleCommands.FM_2.value
                    | SimpleCommands.FM_3.value
                    | SimpleCommands.FM_4.value
                    | SimpleCommands.FM_5.value
                    | SimpleCommands.FM_6.value
                    | SimpleCommands.FM_7.value
                    | SimpleCommands.FM_8.value
                    | SimpleCommands.FM_9.value
                    | SimpleCommands.FM_10.value
                ):
                    # Extract the preset number from the command (e.g., "FM 5" -> 5)
                    preset_num = cmd_id.split()[-1]
                    await yamaha.send_command(
                        "recallPreset",
                        group="tuner",
                        band="fm",
                        num=preset_num,
                        zone="main",
                    )
                case (
                    SimpleCommands.DAB_1.value
                    | SimpleCommands.DAB_2.value
                    | SimpleCommands.DAB_3.value
                    | SimpleCommands.DAB_4.value
                    | SimpleCommands.DAB_5.value
                    | SimpleCommands.DAB_6.value
                    | SimpleCommands.DAB_7.value
                    | SimpleCommands.DAB_8.value
                    | SimpleCommands.DAB_9.value
                    | SimpleCommands.DAB_10.value
                ):
                    # Extract the preset number from the command (e.g., "DAB 5" -> 5)
                    preset_num = cmd_id.split()[-1]
                    await yamaha.send_command(
                        "recallPreset",
                        group="tuner",
                        band="dab",
                        num=preset_num,
                        zone="main",
                    )
                case SimpleCommands.TUNER_NEXT.value:
                    await yamaha.send_command(
                        "switchPreset", group="tuner", direction="next"
                    )
                case SimpleCommands.TUNER_PREV.value:
                    await yamaha.send_command(
                        "switchPreset", group="tuner", direction="previous"
                    )
                case (
                    SimpleCommands.NETUSB_1.value
                    | SimpleCommands.NETUSB_2.value
                    | SimpleCommands.NETUSB_3.value
                    | SimpleCommands.NETUSB_4.value
                    | SimpleCommands.NETUSB_5.value
                    | SimpleCommands.NETUSB_6.value
                    | SimpleCommands.NETUSB_7.value
                    | SimpleCommands.NETUSB_8.value
                    | SimpleCommands.NETUSB_9.value
                    | SimpleCommands.NETUSB_10.value
                ):
                    # Extract the preset number from the command (e.g., "Net/USB 5" -> 5)
                    preset_num = cmd_id.split()[-1]
                    await yamaha.send_command(
                        "recallPreset",
                        group="netusb",
                        num=preset_num,
                        zone="main",
                    )

        except Exception as ex:  # pylint: disable=broad-except
            _LOG.error("Error executing command %s: %s", cmd_id, ex)
            return ucapi.StatusCodes.BAD_REQUEST

        # Update entity state if command changed device state
        # FrameworkEntity.update() calls get_device_attributes() to retrieve updated attributes
        if state_changed and isinstance(entity, FrameworkEntity):
            self.update(yamaha.attributes)

        return ucapi.StatusCodes.OK
