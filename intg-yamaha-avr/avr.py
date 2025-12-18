"""
This module implements the Yamaha AVR communication of the Remote Two integration driver.

"""

import asyncio
import logging
from asyncio import AbstractEventLoop
from enum import StrEnum
from typing import Any

import aiohttp
from const import YamahaConfig
from pyamaha import AsyncDevice, System, Tuner, Zone, NetUSB
from ucapi import EntityTypes
from ucapi.media_player import Attributes as MediaAttr
from ucapi_framework import StatelessHTTPDevice, create_entity_id
from ucapi_framework.device import DeviceEvents

_LOG = logging.getLogger(__name__)


class PowerState(StrEnum):
    """Playback state for companion protocol."""

    OFF = "OFF"
    ON = "ON"
    STANDBY = "STANDBY"


class YamahaAVR(StatelessHTTPDevice):
    """Representing an Yamaha AVR Device."""

    def __init__(
        self,
        device_config: YamahaConfig,
        loop: AbstractEventLoop | None = None,
        config_manager=None,
    ) -> None:
        """Create instance."""
        super().__init__(device_config, loop, config_manager=config_manager)
        self._yamaha_avr: AsyncDevice | None = None
        self._connection_attempts: int = 0
        self._state: PowerState = PowerState.OFF
        self._source_list: list[str] = self._device_config.input_list or []
        self._volume_level: float = 0.0
        self._min_volume_level: int = 0
        self._max_volume_level: int = 161
        self._active_source: str = ""
        self._active_source_text: str = ""
        self._zone: str = "main"
        self._muted: bool = False
        self._sound_mode: str = ""
        self._sound_mode_list: list[str] = self._device_config.sound_modes or []
        self._speaker_pattern_count: int = 4
        self._features: dict = {}
        self._volume_mode: str = ""

    @property
    def identifier(self) -> str:
        """Return the device identifier."""
        if not self._device_config.identifier:
            raise ValueError("Instance not initialized, no identifier available")
        return self._device_config.identifier

    @property
    def log_id(self) -> str:
        """Return a log identifier."""
        return (
            self._device_config.name
            if self._device_config.name
            else self._device_config.identifier
        )

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._device_config.name

    @property
    def address(self) -> str | None:
        """Return the optional device address."""
        return self._device_config.address

    @property
    def state(self) -> PowerState | None:
        """Return the device state."""
        return self._state.upper()

    @property
    def source_list(self) -> list[str]:
        """Return a list of available input sources."""
        return sorted(self._source_list)

    @property
    def source(self) -> str:
        """Return the current input source."""
        return self._active_source

    @property
    def zone(self) -> str:
        """Return the current zone."""
        return self._zone

    @property
    def muted(self) -> bool:
        """Return whether the device is muted."""
        return self._muted

    @property
    def sound_mode(self) -> str | None:
        """Return the current sound mode."""
        return self._sound_mode if self._sound_mode else ""

    @property
    def speaker_pattern_count(self) -> int:
        """Return the number of available speaker patterns."""
        return self._speaker_pattern_count

    @property
    def attributes(self) -> dict[str, any]:
        """Return the device attributes."""
        updated_data = {
            MediaAttr.STATE: self.state,
        }
        if self.source_list:
            updated_data[MediaAttr.SOURCE_LIST] = self.source_list
        if self.source:
            updated_data[MediaAttr.SOURCE] = self.source
        return updated_data

    @property
    def sound_mode_list(self) -> list[str]:
        """Return the list of available sound modes."""
        return sorted(self._sound_mode_list) if self._sound_mode_list else []

    @property
    def volume(self) -> float:
        """Return the current volume level."""
        return self._volume_level

    async def verify_connection(self) -> None:
        """
        Verify the device connection.

        Makes a simple status request to verify device is reachable.
        Raises exception if connection fails.
        """
        _LOG.debug(
            "[%s] Verifying connection to Yamaha AVR at IP address: %s",
            self.log_id,
            self.address,
        )
        async with aiohttp.ClientSession() as session:
            avr = AsyncDevice(session, self.address)
            res = await avr.request(Zone.get_status(self.zone))
            status = await res.json()
            self._state = status.get("power", PowerState.OFF)
            _LOG.debug("[%s] Device state: %s", self.log_id, self._state)

    async def connect(self) -> None:
        """Establish connection to the AVR."""
        # Use the base class connect which calls verify_connection
        await super().connect()
        # After connection is verified, update attributes
        await self._update_attributes()

    async def _update_attributes(self) -> None:
        _LOG.debug("[%s] Updating attributes", self.log_id)
        update = {}

        async with aiohttp.ClientSession() as session:
            try:
                avr = AsyncDevice(session, self.address)
                status = await avr.request(Zone.get_status(zone=self.zone))
                status = await status.json()
                self._state = status.get("power", PowerState.OFF)
                self._muted = status.get("mute", False)
                self._active_source = status.get("input", "")
                self._active_source_text = status.get("input_text", "")
                self._sound_mode = status.get("sound_program", None)
                self._volume_level = status.get("volume", 0.0)

                # Safely extract nested actual_volume data
                actual_volume = status.get("actual_volume", {})
                if actual_volume and isinstance(actual_volume, dict):
                    self._volume_mode = actual_volume.get("mode", "")

                self._features = await avr.request(System.get_features())
                self._features = await self._features.json()
                self._speaker_pattern_count = self._features.get("system", {}).get(
                    "speaker_pattern_count", 0
                )

                try:
                    range_steps = next(
                        zone["range_step"]
                        for zone in self._features["zone"]
                        if zone["id"] == "main"
                    )
                    self._sound_mode_list = next(
                        zone["sound_program_list"]
                        for zone in self._features["zone"]
                        if zone["id"] == "main"
                    )

                    self._min_volume_level, self._max_volume_level = next(
                        (item["min"], item["max"])
                        for item in range_steps
                        if item["id"] == "volume"
                    )
                except (StopIteration, KeyError) as err:
                    _LOG.warning(
                        "[%s] Failed to extract volume range: %s", self.log_id, err
                    )

            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.error("[%s] Error retrieving status: %s", self.log_id, err)

        if not self._source_list:
            _LOG.warning("[%s] No input list configured, using defaults", self.log_id)
            self._source_list = [
                "tuner",
                "hdmi1",
                "hdmi2",
                "hdmi3",
                "hdmi4",
                "hdmi5",
                "hdmi6",
                "hdmi7",
                "av1",
                "av2",
                "av3",
                "tv",
                "audio1",
                "audio2",
                "audio3",
                "audio4",
                "phono",
            ]

        try:
            update[MediaAttr.STATE] = self.state

            source_text = self.source.upper()
            if self._active_source_text:
                source_text = self._active_source_text
            update[MediaAttr.SOURCE] = source_text
            update[MediaAttr.MUTED] = self.muted
            update[MediaAttr.SOURCE_LIST] = self.source_list
            update[MediaAttr.SOUND_MODE] = self.sound_mode
            update[MediaAttr.SOUND_MODE_LIST] = self.sound_mode_list
            update[MediaAttr.VOLUME] = self.volume

        except Exception:  # pylint: disable=broad-exception-caught
            _LOG.exception("[%s] App list: protocol error", self.log_id)

        self.events.emit(
            DeviceEvents.UPDATE,
            create_entity_id(EntityTypes.MEDIA_PLAYER, self.identifier),
            update,
        )

    async def send_command(
        self, command: str, group: str, *args: Any, **kwargs: Any
    ) -> str:
        """Send a command to the AVR."""
        update = {}
        res = None
        try:
            async with aiohttp.ClientSession() as session:
                avr = AsyncDevice(session, self.address)
                _LOG.debug(
                    "[%s] Sending command: %s, group: %s, args: %s, kwargs: %s",
                    self.log_id,
                    command,
                    group,
                    args,
                    kwargs,
                )
                match group:
                    case "system":
                        match command:
                            case "getDeviceInfo":
                                res = await avr.request(System.get_device_info())
                            case "getFeatures":
                                res = await avr.request(System.get_features())
                            case "getNetworkStatus":
                                res = await avr.request(System.get_network_status())
                            case "getFuncStatus":
                                res = await avr.request(System.get_func_status())
                            case "sendIrCode":
                                code = kwargs.get("code", "")
                                res = await avr.request(System.send_ir_code(code))
                            case "setHdmiOut1":
                                enabled = kwargs.get("enabled", True)
                                res = await avr.request(System.set_hdmi_out_1(enabled))
                            case "setHdmiOut2":
                                enabled = kwargs.get("enabled", True)
                                res = await avr.request(System.set_hdmi_out_2(enabled))
                            case "setSpeakerPattern":
                                pattern = kwargs.get("pattern")
                                if pattern is None:
                                    _LOG.error(
                                        "[%s] Missing 'pattern' parameter for setSpeakerPattern",
                                        self.log_id,
                                    )
                                    raise ValueError(
                                        "Missing required parameter 'pattern'"
                                    )
                                res = await avr.request(
                                    System.set_speaker_pattern(int(pattern))
                                )
                    case "zone":
                        zone = kwargs.get("zone")
                        if zone is None:
                            _LOG.error(
                                "[%s] Missing 'zone' parameter for zone command",
                                self.log_id,
                            )
                            raise ValueError("Missing required parameter 'zone'")
                        match command:
                            case "getStatus":
                                res = await avr.request(Zone.get_status(zone))
                            case "setPower":
                                power = kwargs["power"]  #  'on', 'standby', 'toggle'
                                res = await avr.request(Zone.set_power(zone, power))

                                match power:
                                    case "on":
                                        update[MediaAttr.STATE] = PowerState.ON
                                    case "standby":
                                        update[MediaAttr.STATE] = PowerState.STANDBY
                            case "setSleep":
                                sleep = int(kwargs["sleep"])  # 0,30,60,90,120
                                res = await avr.request(Zone.set_sleep(zone, sleep))
                            case "setVolume":
                                volume, step = self._calculate_volume(kwargs)
                                res = await avr.request(
                                    Zone.set_volume(zone, volume, int(step))
                                )
                                await asyncio.sleep(0.1)
                                res = await avr.request(Zone.get_status(self.zone))
                                status = await res.json()

                                # Safely extract volume value
                                actual_volume = status.get("actual_volume", {})
                                if actual_volume and isinstance(actual_volume, dict):
                                    self._volume_level = actual_volume.get("value", 0.0)

                                update[MediaAttr.VOLUME] = self.volume
                            case "setMute":
                                mute = kwargs["mute"]  # True, False
                                if mute == "toggle":
                                    # Toggle mute state
                                    current_status = await avr.request(
                                        Zone.get_status(zone)
                                    )
                                    current_status = await current_status.json()
                                    mute = not current_status["mute"]
                                res = await avr.request(Zone.set_mute(zone, mute))
                                self._muted = mute
                                update[MediaAttr.MUTED] = mute
                            case "controlCursor":
                                cursor = kwargs["cursor"]
                                res = await avr.request(
                                    Zone.control_cursor(zone, cursor)
                                )
                            case "controlMenu":
                                menu = kwargs["menu"]
                                res = await avr.request(Zone.control_menu(zone, menu))
                            case "setInput":
                                input_source = kwargs["input_source"]
                                input_source = input_source.lower()
                                res = await avr.request(
                                    Zone.set_input(zone, input_source, mode=None)
                                )
                                self._active_source = input_source

                                await asyncio.sleep(0.1)
                                res = await avr.request(Zone.get_status(self.zone))
                                status = await res.json()

                                self._active_source_text = input_source
                                if (
                                    status.get("input") == input_source
                                ):  # We have the new source
                                    self._active_source_text = status.get("input_text")

                                update[MediaAttr.SOURCE] = self._active_source_text
                            case "setSoundMode":
                                sound_mode = kwargs["sound_mode"]
                                sound_mode = sound_mode.lower()
                                res = await avr.request(
                                    Zone.set_sound_program(zone, sound_mode)
                                )
                                self._sound_mode = sound_mode
                                update[MediaAttr.SOUND_MODE] = sound_mode
                            case "setDirect":
                                res = await avr.request(Zone.set_direct(zone, "True"))
                                self._sound_mode = "Direct"
                                update[MediaAttr.SOUND_MODE] = "Direct"
                            case "setPureDirect":
                                res = await avr.request(
                                    Zone.set_pure_direct(zone, "True")
                                )
                                self._sound_mode = "Pure Direct"
                                update[MediaAttr.SOUND_MODE] = "Pure Direct"
                            case "setClearVoice":
                                res = await avr.request(
                                    Zone.set_clear_voice(zone, "True")
                                )
                                self._sound_mode = "Clear Voice"
                                update[MediaAttr.SOUND_MODE] = "Clear Voice"
                            case "setSurroundAI":
                                enabled = kwargs["enabled"]  # True, False
                                res = await avr.request(
                                    Zone.set_surround_ai(zone, enable=enabled)
                                )
                            case "setScene":
                                scene = int(kwargs["scene"])  # 1..8
                                res = await avr.request(Zone.set_scene(zone, scene))
                    case "tuner":
                        zone = kwargs.get("zone", "main")
                        match command:
                            case "recallPreset":
                                band = kwargs.get("band")
                                num = kwargs.get("num")
                                if band is None or num is None:
                                    _LOG.error(
                                        "[%s] Missing 'band' or 'num' parameter for recallPreset",
                                        self.log_id,
                                    )
                                    raise ValueError(
                                        "Missing required parameters 'band' and 'num'"
                                    )
                                res = await avr.request(
                                    Tuner.recall_preset(
                                        zone=zone, band=band, num=int(num)
                                    )
                                )
                            case "switchPreset":
                                direction = kwargs.get("direction")
                                if direction is None:
                                    _LOG.error(
                                        "[%s] Missing 'direction' parameter for switchPreset",
                                        self.log_id,
                                    )
                                    raise ValueError(
                                        "Missing required parameter 'direction'"
                                    )
                                res = await avr.request(Tuner.switch_preset(direction))
                    case "netusb":
                        zone = kwargs.get("zone", "main")
                        match command:
                            case "recallPreset":
                                num = kwargs.get("num")
                                if num is None:
                                    _LOG.error(
                                        "[%s] Missing 'num' parameter for recallPreset",
                                        self.log_id,
                                    )
                                    raise ValueError(
                                        "Missing required parameters 'band' and 'num'"
                                    )
                                res = await avr.request(
                                    NetUSB.recall_preset(zone=zone, num=int(num))
                                )

            self.events.emit(
                DeviceEvents.UPDATE,
                create_entity_id(EntityTypes.MEDIA_PLAYER, self.identifier),
                update,
            )
            return res
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOG.error(
                "[%s] Network error sending command %s: %s",
                self.log_id,
                command,
                err,
            )
            raise
        except ValueError as err:
            _LOG.error(
                "[%s] Invalid parameter for command %s: %s",
                self.log_id,
                command,
                err,
            )
            raise
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error(
                "[%s] Unexpected error sending command %s: %s",
                self.log_id,
                command,
                err,
            )
            raise

    def _calculate_volume(self, kwargs: dict[str, Any]) -> tuple:
        volume = kwargs.get("volume", None)  # up, down, level
        volume_level = kwargs.get("volume_level", None)
        step = float(self.device_config.volume_step)

        if step < 1:
            step = 1
        else:
            step = step * 2

        if volume_level is not None:
            try:
                volume_level = int((161 * float(volume_level) / 100))
            except ValueError:
                volume_level = 0

            volume = volume_level
            step = 1

        _LOG.debug(
            "[%s] Volume command: %s Step: %s",
            self.log_id,
            volume,
            step,
        )
        return volume, step
