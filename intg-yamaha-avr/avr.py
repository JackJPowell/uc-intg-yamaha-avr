"""
This module implements the Yamaha AVR communication of the Remote Two integration driver.

"""

import asyncio
import logging
from asyncio import AbstractEventLoop
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, ParamSpec, TypeVar

import aiohttp

from pyamaha import AsyncDevice, System, Zone
import config
from config import YamahaDevice
from pyee.asyncio import AsyncIOEventEmitter
from ucapi.media_player import Attributes as MediaAttr

_LOG = logging.getLogger(__name__)

BACKOFF_MAX = 30
BACKOFF_SEC = 2


class EVENTS(IntEnum):
    """Internal driver events."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRED = 3
    ERROR = 4
    UPDATE = 5


_YamahaAVRT = TypeVar("_YamahaAVRT", bound="YamahaAVR")
_P = ParamSpec("_P")


class PowerState(str, Enum):
    """Playback state for companion protocol."""

    OFF = "OFF"
    ON = "ON"
    STANDBY = "STANDBY"


class YamahaAVR:
    """Representing an Yamaha AVR Device."""

    def __init__(
        self, device: YamahaDevice, loop: AbstractEventLoop | None = None
    ) -> None:
        """Create instance."""
        self._loop: AbstractEventLoop = loop or asyncio.get_running_loop()
        self.events = AsyncIOEventEmitter(self._loop)
        self._is_on: bool = False
        self._is_connected: bool = False
        self._yamaha_avr: AsyncDevice | None = None
        self._device: YamahaDevice = device
        self._connect_task = None
        self._connection_attempts: int = 0
        self._polling = None
        self._poll_interval: int = 10
        self._state: PowerState | None = None
        self._source_list: list[str] = self._device.input_list or []
        self._volume_level: float = 0.0
        self._end_of_power_off: datetime | None = None
        self._end_of_power_on: datetime | None = None
        self._active_source: str = ""
        self._zone: str = "main"
        self._muted: bool = False
        self._sound_mode: str | None = None

    @property
    def device_config(self) -> YamahaDevice:
        """Return the device configuration."""
        return self._device

    @property
    def identifier(self) -> str:
        """Return the device identifier."""
        if not self._device.identifier:
            raise ValueError("Instance not initialized, no identifier available")
        return self._device.identifier

    @property
    def log_id(self) -> str:
        """Return a log identifier."""
        return self._device.name if self._device.name else self._device.identifier

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._device.name

    @property
    def address(self) -> str | None:
        """Return the optional device address."""
        return self._device.address

    @property
    def is_on(self) -> bool | None:
        """Whether the Yamaha AVR is on or off. Returns None if not connected."""
        return self._is_on

    @property
    def state(self) -> PowerState | None:
        """Return the device state."""
        if self.is_on:
            return PowerState.ON
        return PowerState.STANDBY

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
        return self._sound_mode if self._sound_mode else None

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

    async def connect(self) -> None:
        """Establish connection to the AVR."""
        if self._is_on:
            return

        _LOG.debug("[%s] Connecting to device", self.log_id)
        self.events.emit(EVENTS.CONNECTING, self._device.identifier)
        self._connect_task = asyncio.create_task(self._connect_setup())

    async def _connect_setup(self) -> None:
        try:
            alive = await self._connect()

            if alive is True:
                _LOG.debug("[%s] Device is alive", self.log_id)
                self._is_on = True
                self.events.emit(
                    EVENTS.UPDATE, self._device.identifier, {"state": PowerState.ON}
                )
            else:
                _LOG.debug("[%s] Device is not alive", self.log_id)
                self.events.emit(
                    EVENTS.UPDATE, self._device.identifier, {"state": PowerState.OFF}
                )
        except asyncio.CancelledError:
            pass
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Could not connect: %s", self.log_id, err)
        finally:
            _LOG.debug("[%s] Connect setup finished", self.log_id)

        self.events.emit(EVENTS.CONNECTED, self._device.identifier)
        _LOG.debug("[%s] Connected", self.log_id)

        await asyncio.sleep(1)
        await self._start_polling()
        await self._update_source_list()

    async def _connect(self) -> None:
        """Connect to the device."""
        _LOG.debug(
            "[%s] Connecting to TVWS device at IP address: %s",
            self.log_id,
            self.address,
        )
        async with aiohttp.ClientSession() as session:
            avr = AsyncDevice(session, self.address)
            res = await avr.request(Zone.get_status(self.zone))
            status = await res.json()
            self._is_on = status.get("power", "standby") == "on"

    async def _start_polling(self) -> None:
        if not self._polling:
            self._polling = self._loop.create_task(self._poll_worker())
            _LOG.debug("[%s] Polling started", self.log_id)

    async def _stop_polling(self) -> None:
        if self._polling:
            self._polling.cancel()
            self._polling = None
            _LOG.debug("[%s] Polling stopped", self.log_id)
        else:
            _LOG.debug("[%s] Polling was already stopped", self.log_id)

    async def _process_update(self, data: {}) -> None:  # pylint: disable=too-many-branches
        _LOG.debug("[%s] Process update", self.log_id)
        update = {}

        # We only update device state (playing, paused, etc) if the power state is On
        # otherwise we'll set the state to Off in the polling method
        self._state = data.device_state
        update["state"] = data.device_state

    async def _update_source_list(self) -> None:
        _LOG.debug("[%s] Updating app list", self.log_id)
        update = {}

        if self._source_list is None or len(self._source_list) == 0:
            _LOG.error("[%s] Unable to retrieve app list. Using default", self.log_id)
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
            update["source_list"] = self._source_list

        except Exception:  # pylint: disable=broad-exception-caught
            _LOG.exception("[%s] App list: protocol error", self.log_id)

        self.events.emit(EVENTS.UPDATE, self._device.identifier, update)

    async def send_command(
        self, command: str, group: str, *args: Any, **kwargs: Any
    ) -> str:
        """Send a command to the AVR."""
        update = {}
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
                            res = await avr.request(System.set_hdmi_out_1(True))
                        case "setHdmiOut2":
                            res = await avr.request(System.set_hdmi_out_2(True))
                case "zone":
                    zone = kwargs["zone"]  #  'main', 'zone2', 'zone3', 'zone4'
                    match command:
                        case "getStatus":
                            res = await avr.request(Zone.get_status(zone))
                        case "setPower":
                            power = kwargs["power"]  #  'on', 'standby', 'toggle'
                            res = await avr.request(Zone.set_power(zone, power))

                            if power == "toggle":
                                res = await avr.request(Zone.get_status(zone))
                                power = await res.json()["power"]

                            self._is_on = power == "on"
                            match power:
                                case "on":
                                    update["state"] = PowerState.ON
                                case "standby":
                                    update["state"] = PowerState.STANDBY
                        case "setSleep":
                            sleep = kwargs["sleep"]  # 0,30,60,90,120
                            res = await avr.request(Zone.set_sleep(zone, sleep))
                        case "setVolume":
                            volume = kwargs["volume"]  # up, down, level
                            step = int(self.device_config.volume_step) | 1
                            _LOG.debug(
                                "[%s] Volume command: %s Step: %s",
                                self.log_id,
                                volume,
                                step,
                            )
                            res = await avr.request(Zone.set_volume(zone, volume, step))
                        case "setMute":
                            mute = kwargs["mute"]  # True, False
                            if mute == "toggle":
                                # Toggle mute state
                                current_status = await avr.request(
                                    Zone.get_status(zone)
                                )
                                mute = not await current_status.json()["mute"]
                            res = await avr.request(Zone.set_mute(zone, mute))
                            self._muted = mute
                            update["muted"] = mute
                        case "setInput":
                            input_source = kwargs["input_source"]
                            input_source = input_source.lower()
                            res = await avr.request(
                                Zone.set_input(zone, input_source, mode=None)
                            )
                            self._active_source = input_source
                            update["source"] = input_source
                        case "setDirect":
                            res = await avr.request(Zone.set_direct(zone, True))
                            self._sound_mode = "Direct"
                            update["sound_mode"] = "Direct"
                        case "setPureDirect":
                            res = await avr.request(Zone.set_pure_direct(zone, True))
                            self._sound_mode = "Pure Direct"
                            update["sound_mode"] = "Pure Direct"
                        case "setClearVoice":
                            res = await avr.request(Zone.set_clear_voice(zone, True))
                            self._sound_mode = "Clear Voice"
                            update["sound_mode"] = "Clear Voice"

        self.events.emit(EVENTS.UPDATE, self._device.identifier, update)
        return res

    async def _poll_worker(self) -> None:
        await asyncio.sleep(1)
        while True:
            await self.get_status()
            await asyncio.sleep(10)

    async def get_status(self) -> str:
        """Return the status of the device."""
        update = {}
        async with aiohttp.ClientSession() as session:
            avr = AsyncDevice(session, self.address)
            res = await avr.request(Zone.get_status(self.zone))
            status = await res.json()
            self._is_on = status.get("power", "standby") == "on"

        if self._is_on:
            update["state"] = PowerState.ON
        else:
            update["state"] = PowerState.STANDBY
        self.events.emit(EVENTS.UPDATE, self._device.identifier, update)
