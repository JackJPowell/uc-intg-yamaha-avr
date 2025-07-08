"""
Remote entity functions.

:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

import ucapi
from config import YamahaDevice, create_entity_id
from ucapi import EntityTypes, Remote, StatusCodes, media_player
from ucapi.media_player import States as MediaStates
from ucapi.remote import Attributes, Commands, Features
from ucapi.remote import States as RemoteStates
from ucapi.ui import DeviceButtonMapping, Buttons
import avr
from const import SimpleCommands

_LOG = logging.getLogger(__name__)

YAMAHA_REMOTE_STATE_MAPPING = {
    MediaStates.UNKNOWN: RemoteStates.UNKNOWN,
    MediaStates.UNAVAILABLE: RemoteStates.UNAVAILABLE,
    MediaStates.OFF: RemoteStates.OFF,
    MediaStates.ON: RemoteStates.ON,
    MediaStates.STANDBY: RemoteStates.OFF,
}


class YamahaRemote(Remote):
    """Representation of a Yamaha AVR Remote entity."""

    def __init__(self, config_device: YamahaDevice, device: avr.YamahaAVR):
        """Initialize the class."""
        self._device: avr.YamahaAVR = device
        _LOG.debug("Yamaha AVR Remote init")
        entity_id = create_entity_id(config_device.identifier, EntityTypes.REMOTE)
        features = [Features.SEND_CMD, Features.ON_OFF, Features.TOGGLE]
        super().__init__(
            entity_id,
            f"{config_device.name} Remote",
            features,
            attributes={
                Attributes.STATE: device.state,
            },
            simple_commands=YAMAHA_REMOTE_SIMPLE_COMMANDS,
            button_mapping=YAMAHA_REMOTE_BUTTONS_MAPPING,
            ui_pages=YAMAHA_REMOTE_UI_PAGES,
            cmd_handler=self.command,
        )

    def get_int_param(self, param: str, params: dict[str, Any], default: int):
        """Get parameter in integer format."""
        try:
            value = params.get(param, default)
        except AttributeError:
            return default

        if isinstance(value, str) and len(value) > 0:
            return int(float(value))
        return default

    async def command(
        self, cmd_id: str, params: dict[str, Any] | None = None
    ) -> StatusCodes:
        """
        Remote entity command handler.

        Called by the integration-API if a command is sent to a configured remote entity.

        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command request
        """
        repeat = 1
        _LOG.info("Got %s command request: %s %s", self.id, cmd_id, params)

        if self._device is None:
            _LOG.warning("No Yamaha AVR instance for entity: %s", self.id)
            return StatusCodes.SERVICE_UNAVAILABLE

        if params:
            repeat = self.get_int_param("repeat", params, 1)

        for _i in range(0, repeat):
            await self.handle_command(cmd_id, params)
        return StatusCodes.OK

    async def handle_command(
        self, cmd_id: str, params: dict[str, Any] | None = None
    ) -> StatusCodes:
        """Handle command."""
        command = ""
        delay = 0

        if params:
            command = params.get("command", "")
            delay = self.get_int_param("delay", params, 0)

        if command == "":
            command = f"remote.{cmd_id}"

        _LOG.info("Got command request: %s %s", cmd_id, params if params else "")

        yamaha = self._device
        res = None
        try:
            if command == "remote.on":
                _LOG.debug("Sending ON command to AVR")
                res = await yamaha.send_command(
                    "setPower", group="zone", zone="main", power="on"
                )
            elif command == "remote.off":
                res = await yamaha.send_command(
                    "setPower", group="zone", zone="main", power="standby"
                )
            elif command == "remote.toggle":
                res = await yamaha.send_command(
                    "setPower", group="zone", zone="main", power="toggle"
                )
            elif cmd_id == Commands.SEND_CMD:
                match command:
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
                        await yamaha.send_command(
                            "setInput",
                            group="zone",
                            zone="main",
                            input_source=params.get("source"),
                        )
                    case media_player.Commands.SELECT_SOUND_MODE:
                        await yamaha.send_command(
                            "setSoundProgram",
                            group="zone",
                            zone="main",
                            sound_mode=params.get("sound_mode"),
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

            elif cmd_id == Commands.SEND_CMD_SEQUENCE:
                commands = params.get("sequence", [])
                res = StatusCodes.OK
                for command in commands:
                    res = await self.handle_command(
                        Commands.SEND_CMD, {"command": command, "params": params}
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
            else:
                return StatusCodes.NOT_IMPLEMENTED
            if delay > 0 and cmd_id != Commands.SEND_CMD_SEQUENCE:
                await asyncio.sleep(delay)
            return res
        except Exception as ex:  # pylint: disable=broad-except
            _LOG.error("Error executing remote command %s: %s", cmd_id, ex)
            return ucapi.StatusCodes.BAD_REQUEST
        return ucapi.StatusCodes.OK


YAMAHA_REMOTE_SIMPLE_COMMANDS = [
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
    SimpleCommands.NUMBER_ENTER.value,
    SimpleCommands.RETURN.value,
    SimpleCommands.OPTIONS.value,
]
YAMAHA_REMOTE_BUTTONS_MAPPING: [DeviceButtonMapping] = [
    {"button": Buttons.BACK, "short_press": {"cmd_id": media_player.Commands.BACK}},
    {"button": Buttons.HOME, "short_press": {"cmd_id": media_player.Commands.HOME}},
    {
        "button": Buttons.CHANNEL_DOWN,
        "short_press": {"cmd_id": media_player.Commands.CHANNEL_DOWN},
    },
    {
        "button": Buttons.DPAD_DOWN,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_DOWN},
    },
    {
        "button": Buttons.DPAD_LEFT,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_LEFT},
    },
    {
        "button": Buttons.DPAD_RIGHT,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_RIGHT},
    },
    {
        "button": Buttons.DPAD_MIDDLE,
        "short_press": {"cmd_id": media_player.Commands.CURSOR_ENTER},
    },
    {
        "button": Buttons.VOLUME_UP,
        "short_press": {"cmd_id": media_player.Commands.VOLUME_UP},
    },
    {
        "button": Buttons.VOLUME_DOWN,
        "short_press": {"cmd_id": media_player.Commands.VOLUME_DOWN},
    },
    {
        "button": Buttons.MUTE,
        "short_press": {"cmd_id": media_player.Commands.MUTE_TOGGLE},
    },
    {"button": Buttons.POWER, "short_press": {"cmd_id": media_player.Commands.TOGGLE}},
]

YAMAHA_REMOTE_UI_PAGES = [
    {
        "page_id": "yamaha_avr_commands",
        "name": "AVR commands",
        "grid": {"width": 4, "height": 7},
        "items": [
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.TOGGLE, "repeat": 1},
                },
                "icon": "uc:power-on",
                "location": {"x": 0, "y": 0},
                "size": {"height": 1, "width": 1},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.INFO, "repeat": 1},
                },
                "icon": "uc:info",
                "location": {"x": 1, "y": 0},
                "size": {"height": 1, "width": 1},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.SETTINGS, "repeat": 1},
                },
                "text": "Settings",
                "location": {"x": 2, "y": 0},
                "size": {"height": 1, "width": 2},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.MUTE_TOGGLE,
                        "repeat": 1,
                    },
                },
                "icon": "uc:mute",
                "location": {"x": 2, "y": 1},
                "size": {"height": 1, "width": 2},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SLEEP_OFF,
                        "repeat": 1,
                    },
                },
                "icon": "uc:coffee-pot",
                "location": {"x": 2, "y": 2},
                "size": {"height": 1, "width": 2},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.VOLUME_UP, "repeat": 1},
                },
                "icon": "uc:plus",
                "location": {"x": 0, "y": 1},
                "size": {"height": 1, "width": 1},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.VOLUME_DOWN,
                        "repeat": 1,
                    },
                },
                "icon": "uc:minus",
                "location": {"x": 0, "y": 2},
                "size": {"height": 1, "width": 1},
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SLEEP_30,
                        "repeat": 1,
                    },
                },
                "text": "30",
                "location": {"x": 0, "y": 3},
                "size": {"height": 1, "width": 1},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SLEEP_60,
                        "repeat": 1,
                    },
                },
                "text": "60",
                "location": {"x": 1, "y": 3},
                "size": {"height": 1, "width": 1},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SLEEP_90,
                        "repeat": 1,
                    },
                },
                "text": "90",
                "location": {"x": 2, "y": 3},
                "size": {"height": 1, "width": 1},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SLEEP_120,
                        "repeat": 1,
                    },
                },
                "text": "120",
                "location": {"x": 3, "y": 3},
                "size": {"height": 1, "width": 1},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.HDMI_OUTPUT_1,
                        "repeat": 1,
                    },
                },
                "text": "Output 1",
                "location": {"x": 0, "y": 4},
                "size": {"height": 1, "width": 2},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.HDMI_OUTPUT_2,
                        "repeat": 1,
                    },
                },
                "text": "Output 2",
                "location": {"x": 2, "y": 4},
                "size": {"height": 1, "width": 2},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SOUND_MODE_DIRECT,
                        "repeat": 1,
                    },
                },
                "text": "Direct",
                "location": {"x": 0, "y": 5},
                "size": {"height": 1, "width": 2},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SOUND_MODE_PURE,
                        "repeat": 1,
                    },
                },
                "text": "Pure",
                "location": {"x": 2, "y": 5},
                "size": {"height": 1, "width": 2},
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": SimpleCommands.SOUND_MODE_CLEAR_VOICE,
                        "repeat": 1,
                    },
                },
                "text": "Clear Voice",
                "location": {"x": 0, "y": 6},
                "size": {"height": 1, "width": 4},
                "type": "text",
            },
        ],
    },
    {
        "page_id": "TV numbers",
        "name": "TV numbers",
        "grid": {"height": 4, "width": 3},
        "items": [
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_1, "repeat": 1},
                },
                "location": {"x": 0, "y": 0},
                "size": {"height": 1, "width": 1},
                "text": "1",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_2, "repeat": 1},
                },
                "location": {"x": 1, "y": 0},
                "size": {"height": 1, "width": 1},
                "text": "2",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_3, "repeat": 1},
                },
                "location": {"x": 2, "y": 0},
                "size": {"height": 1, "width": 1},
                "text": "3",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_4, "repeat": 1},
                },
                "location": {"x": 0, "y": 1},
                "size": {"height": 1, "width": 1},
                "text": "4",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_5, "repeat": 1},
                },
                "location": {"x": 1, "y": 1},
                "size": {"height": 1, "width": 1},
                "text": "5",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_6, "repeat": 1},
                },
                "location": {"x": 2, "y": 1},
                "size": {"height": 1, "width": 1},
                "text": "6",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_7, "repeat": 1},
                },
                "location": {"x": 0, "y": 2},
                "size": {"height": 1, "width": 1},
                "text": "7",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_8, "repeat": 1},
                },
                "location": {"x": 1, "y": 2},
                "size": {"height": 1, "width": 1},
                "text": "8",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_9, "repeat": 1},
                },
                "location": {"x": 2, "y": 2},
                "size": {"height": 1, "width": 1},
                "text": "9",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.DIGIT_0, "repeat": 1},
                },
                "location": {"x": 1, "y": 3},
                "size": {"height": 1, "width": 1},
                "text": "0",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": SimpleCommands.NUMBER_ENTER, "repeat": 1},
                },
                "location": {"x": 2, "y": 3},
                "size": {"height": 1, "width": 1},
                "text": "OK",
                "type": "text",
            },
        ],
    },
    {
        "page_id": "TV direction pad",
        "name": "TV direction pad",
        "grid": {"height": 3, "width": 3},
        "items": [
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.BACK, "repeat": 1},
                },
                "location": {"x": 0, "y": 0},
                "size": {"height": 1, "width": 1},
                "icon": "uc:back",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.CURSOR_UP, "repeat": 1},
                },
                "location": {"x": 1, "y": 0},
                "size": {"height": 1, "width": 1},
                "icon": "uc:up-arrow",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.HOME, "repeat": 1},
                },
                "location": {"x": 2, "y": 0},
                "size": {"height": 1, "width": 1},
                "icon": "uc:home",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.CURSOR_LEFT,
                        "repeat": 1,
                    },
                },
                "location": {"x": 0, "y": 1},
                "size": {"height": 1, "width": 1},
                "icon": "uc:left-arrow",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.CURSOR_ENTER,
                        "repeat": 1,
                    },
                },
                "location": {"x": 1, "y": 1},
                "size": {"height": 1, "width": 1},
                "text": "OK",
                "type": "text",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.CURSOR_RIGHT,
                        "repeat": 1,
                    },
                },
                "location": {"x": 2, "y": 1},
                "size": {"height": 1, "width": 1},
                "icon": "uc:right-arrow",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.CURSOR_RIGHT,
                        "repeat": 1,
                    },
                },
                "location": {"x": 0, "y": 2},
                "size": {"height": 1, "width": 1},
                "icon": "uc:option",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {
                        "command": media_player.Commands.CURSOR_DOWN,
                        "repeat": 1,
                    },
                },
                "location": {"x": 1, "y": 2},
                "size": {"height": 1, "width": 1},
                "icon": "uc:down-arrow",
                "type": "icon",
            },
            {
                "command": {
                    "cmd_id": "remote.send",
                    "params": {"command": media_player.Commands.BACK, "repeat": 1},
                },
                "location": {"x": 2, "y": 2},
                "size": {"height": 1, "width": 1},
                "text": "Exit",
                "type": "text",
            },
        ],
    },
]
