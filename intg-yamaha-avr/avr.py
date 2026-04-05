"""
This module implements the Yamaha AVR communication of the Remote Two integration driver.

"""

import asyncio
import logging
from asyncio import AbstractEventLoop
from typing import Any

import aiohttp
from const import YamahaConfig, SENSORS, SELECTS, SensorConfig, SelectConfig
from pyamaha import AsyncDevice, System, Tuner, Zone, NetUSB
from ucapi import media_player
from ucapi.select import States as SelectStates
from ucapi.sensor import States as SensorStates
from ucapi_framework import StatelessHTTPDevice, BaseIntegrationDriver
from ucapi_framework.helpers import (
    MediaPlayerAttributes,
    RemoteAttributes,
    SensorAttributes,
    SelectAttributes,
)

_LOG = logging.getLogger(__name__)


class YamahaAVR(StatelessHTTPDevice):
    """Representing an Yamaha AVR Device."""

    def __init__(
        self,
        device_config: YamahaConfig,
        loop: AbstractEventLoop | None = None,
        config_manager=None,
        driver: BaseIntegrationDriver | None = None,
    ) -> None:
        """Create instance."""
        super().__init__(
            device_config, loop, config_manager=config_manager, driver=driver
        )
        self._yamaha_avr: AsyncDevice | None = None
        self._connection_attempts: int = 0
        self._source_list: list[str] = self._device_config.input_list or []
        self._sound_mode_list: list[str] = self._device_config.sound_modes or []
        self._min_volume_level: int = 0
        self._max_volume_level: int = 161
        self._zone: str = "main"
        self._speaker_pattern_count: int = 4
        self._features: dict = {}
        self._actual_volume: dict = {}
        self._volume_level: int = 0  # Internal volume (0-161)

        # Sensor storage — keyed by sensor identifier.
        # SensorConfig.value is the single source of truth shared with select entities.
        self.sensors: dict[str, SensorConfig] = {s.identifier: s for s in SENSORS}

        # Select storage — keyed by select identifier (same as sensor identifier).
        # SelectConfig.options is populated at runtime from System.get_features().
        # The current value is read from self.sensors[identifier].value, not stored here.
        self.selects: dict[str, SelectConfig] = {s.identifier: s for s in SELECTS}

        # Shared device state — single source of truth for all entity types.
        # Entities read from these properties; no per-entity copies are maintained.
        self._state: media_player.States = media_player.States.UNKNOWN
        self._source: str | None = None
        self._muted: bool = False
        self._sound_mode: str | None = None

    # ── Identity / config properties ─────────────────────────────────────────

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

    # ── Shared state properties ───────────────────────────────────────────────

    @property
    def state(self) -> media_player.States:
        """Return the current device power/play state."""
        return self._state if self._state else media_player.States.UNKNOWN

    @property
    def source_list(self) -> list[str]:
        """Return a list of available input sources."""
        return sorted(self._source_list)

    @property
    def source(self) -> str:
        """Return the current input source."""
        return self._source if self._source else ""

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
        return self._sound_mode

    @property
    def speaker_pattern_count(self) -> int:
        """Return the number of available speaker patterns."""
        return self._speaker_pattern_count

    @property
    def sound_mode_list(self) -> list[str]:
        """Return the list of available sound modes."""
        return sorted(self._sound_mode_list) if self._sound_mode_list else []

    @property
    def volume(self) -> float:
        """Return the current volume level (raw device value)."""
        return self._actual_volume.get("value", 0.0)

    @property
    def volume_percent(self) -> int:
        """Return the current volume as a percentage (0-100) for the remote UI slider."""
        percentage = int((self._volume_level / self.max_volume) * 100)
        return max(0, min(100, percentage))

    def get_display_volume(self) -> int:
        """Return volume in the format specified by user's volume_mode config."""
        user_mode = self._device_config.volume_mode
        actual_mode = self._actual_volume.get("mode", "db")
        actual_value = self._actual_volume.get("value", 0.0)

        if user_mode == "absolute":
            if actual_mode == "numeric":
                return int(actual_value)
            else:
                return int(actual_value + 80.5)
        else:
            if actual_mode == "db":
                return int(actual_value)
            else:
                return int(actual_value - 80.5)

    @property
    def volume_mode(self) -> str:
        """Return the volume mode (db or numeric)."""
        return self._actual_volume.get("mode", "db")

    @property
    def max_volume(self) -> int:
        """Return the maximum volume level."""
        return self._max_volume_level if self._max_volume_level > 0 else 161

    # ── Typed attribute accessors (coordinator pattern) ───────────────────────
    # Each entity type reads from the shared device state.
    # Accessors construct the appropriate dataclass on the fly.

    def get_media_player_attributes(
        self, device_id: str
    ) -> MediaPlayerAttributes | None:
        """Return current MediaPlayer attributes for the given device."""
        if device_id != self.identifier:
            return None
        return MediaPlayerAttributes(
            STATE=self._state,
            SOURCE=self._source,
            SOURCE_LIST=self._source_list,
            MUTED=self._muted,
            SOUND_MODE=self._sound_mode,
            SOUND_MODE_LIST=self._sound_mode_list,
            VOLUME=self.get_display_volume(),
        )

    def get_remote_attributes(self, device_id: str) -> RemoteAttributes | None:
        """Return current Remote attributes for the given device.

        Note: the Remote entity maps device.state to remote.States itself via
        map_entity_states(), so this accessor does not need to carry a state.
        """
        if device_id != self.identifier:
            return None
        return RemoteAttributes(STATE=None)

    def get_sensor_attributes(
        self, device_id: str, sensor_id: str
    ) -> SensorAttributes | None:
        """Return current Sensor attributes for the given sensor on the device."""
        if device_id != self.identifier:
            return None
        return self._sensor_attributes(sensor_id)

    def get_select_attributes(
        self, device_id: str, select_id: str
    ) -> SelectAttributes | None:
        """Return current Select attributes for the given select on the device.

        The current option is read from the shared SensorConfig.value so that
        sensors and selects representing the same data never duplicate state.
        """
        if device_id != self.identifier:
            return None
        select_cfg = self.selects.get(select_id)
        if not select_cfg:
            return None
        # Value lives in the matching SensorConfig — single source of truth.
        sensor_cfg = self.sensors.get(select_id)
        current_value = sensor_cfg.value if sensor_cfg else None
        select_state = (
            SelectStates.ON
            if self._state == media_player.States.ON
            else SelectStates.UNAVAILABLE
        )
        return SelectAttributes(
            STATE=select_state,
            CURRENT_OPTION=str(current_value) if current_value is not None else "",
            OPTIONS=select_cfg.options or [],
        )

    # ── Connection / update lifecycle ─────────────────────────────────────────

    def _session(self) -> aiohttp.ClientSession:
        """Return a ClientSession with force_close=True.

        Using force_close prevents aiohttp from pooling TCP connections across
        requests.  Without it, keep-alive connections are left open when the
        session context-manager exits and aiohttp emits "Unclosed connection"
        warnings on the event loop.
        """
        connector = aiohttp.TCPConnector(force_close=True)
        return aiohttp.ClientSession(connector=connector)

    async def verify_connection(self) -> None:
        """Verify the device connection."""
        _LOG.debug(
            "[%s] Verifying connection to Yamaha AVR at IP address: %s",
            self.log_id,
            self.address,
        )
        async with self._session() as session:
            avr = AsyncDevice(session, self.address)
            await avr.request(Zone.get_status(self.zone))
            _LOG.debug("[%s] Device connection verified", self.log_id)

    async def connect(self) -> bool:
        """Establish connection to the AVR."""
        result = await super().connect()
        if result:
            await self._update_attributes()
        return result

    async def _update_attributes(self) -> None:
        _LOG.debug("[%s] Updating attributes", self.log_id)
        status: dict = {}

        async with self._session() as session:
            try:
                avr = AsyncDevice(session, self.address)
                status_res = await avr.request(Zone.get_status(zone=self.zone))
                status = await status_res.json()

                # Update shared state from status response
                power_str = status.get("power", "off").lower()
                if power_str == "on":
                    self._state = media_player.States.ON
                elif power_str == "standby":
                    self._state = media_player.States.STANDBY
                else:
                    self._state = media_player.States.OFF

                self._muted = status.get("mute", False)
                active_source_text = status.get("input_text", "")
                if not active_source_text:
                    active_source_text = status.get("input", "")
                self._source = active_source_text if active_source_text else ""
                self._sound_mode = status.get("sound_program", None)

                self._actual_volume = status.get("actual_volume", {})
                self._volume_level = status.get("volume", 0)

                features_res = await avr.request(System.get_features())
                self._features = await features_res.json()
                self._speaker_pattern_count = self._features.get("system", {}).get(
                    "speaker_pattern_count", 0
                )

                try:
                    main_zone = next(
                        zone for zone in self._features["zone"] if zone["id"] == "main"
                    )
                    range_steps = main_zone["range_step"]
                    self._sound_mode_list = main_zone.get("sound_program_list", [])
                    self._min_volume_level, self._max_volume_level = next(
                        (item["min"], item["max"])
                        for item in range_steps
                        if item["id"] == "volume"
                    )
                    # Populate select options from the zone features dict.
                    # Only keys present in the actual features response are used,
                    # so selects not supported by this receiver get empty options.
                    # "prev", "next", "toggle" are navigation-only entries that
                    # cannot be set directly and must be excluded from options.
                    _NAV_ONLY = {"prev", "next", "toggle"}
                    for select_cfg in self.selects.values():
                        if select_cfg.features_zone_key:
                            opts = main_zone.get(select_cfg.features_zone_key)
                            if opts:
                                select_cfg.options = [
                                    str(o) for o in opts if str(o) not in _NAV_ONLY
                                ]
                                _LOG.debug(
                                    "[%s] Select '%s' options loaded: %s",
                                    self.log_id,
                                    select_cfg.identifier,
                                    select_cfg.options,
                                )
                except (StopIteration, KeyError) as err:
                    _LOG.warning(
                        "[%s] Failed to extract features: %s", self.log_id, err
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

        if status:
            self._update_sensors_from_status(status)

        # Notify all subscribed entities of the updated state
        self.push_update()

    # ── Command dispatch ──────────────────────────────────────────────────────

    async def send_command(
        self, command: str, group: str, *args: Any, **kwargs: Any
    ) -> str:
        """Send a command to the AVR."""
        res: str = ""
        try:
            async with self._session() as session:
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
                                res = await avr.request(System.set_hdmi_out_1("True"))
                            case "setHdmiOut2":
                                res = await avr.request(System.set_hdmi_out_2("True"))
                            case "setSpeakerPattern":
                                pattern = kwargs.get("pattern")
                                if pattern is None:
                                    raise ValueError(
                                        "Missing required parameter 'pattern'"
                                    )
                                res = await avr.request(
                                    System.set_speaker_pattern(int(pattern))
                                )

                    case "zone":
                        zone = kwargs.get("zone")
                        if zone is None:
                            raise ValueError("Missing required parameter 'zone'")
                        match command:
                            case "getStatus":
                                res = await avr.request(Zone.get_status(zone))

                            case "setPower":
                                power = kwargs["power"]
                                res = await avr.request(Zone.set_power(zone, power))
                                match power:
                                    case "on":
                                        self._state = media_player.States.ON
                                    case "standby":
                                        self._state = media_player.States.STANDBY
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setSleep":
                                sleep = int(kwargs["sleep"])
                                res = await avr.request(Zone.set_sleep(zone, sleep))
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setVolume":
                                volume_cmd = kwargs.get("volume")
                                if volume_cmd in ("up", "down"):
                                    step = float(self.device_config.volume_step)
                                    step = 1 if step < 1 else step * 2
                                    res = await avr.request(
                                        Zone.set_volume(zone, volume_cmd, int(step))
                                    )
                                else:
                                    volume = self._calculate_volume(kwargs)
                                    res = await avr.request(
                                        Zone.set_volume(zone, volume, 1)
                                    )
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._actual_volume = status.get("actual_volume", {})
                                self._volume_level = status.get("volume", 0)
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setMute":
                                mute = kwargs["mute"]
                                if mute == "toggle":
                                    current_status = await avr.request(
                                        Zone.get_status(zone)
                                    )
                                    current_status = await current_status.json()
                                    mute = not current_status["mute"]
                                res = await avr.request(Zone.set_mute(zone, mute))
                                self._muted = mute
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "controlCursor":
                                cursor = kwargs["cursor"]
                                res = await avr.request(
                                    Zone.control_cursor(zone, cursor)
                                )

                            case "controlMenu":
                                menu = kwargs["menu"]
                                res = await avr.request(Zone.control_menu(zone, menu))

                            case "setInput":
                                input_source = kwargs["input_source"].lower()
                                res = await avr.request(
                                    Zone.set_input(zone, input_source, mode=None)
                                )
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                source_text = status.get("input_text", input_source)
                                self._source = (
                                    source_text if source_text else input_source
                                )
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setSoundMode":
                                sound_mode = kwargs["sound_mode"].lower()
                                res = await avr.request(
                                    Zone.set_sound_program(zone, sound_mode)
                                )
                                self._sound_mode = sound_mode
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setDirect":
                                res = await avr.request(Zone.set_direct(zone, "True"))
                                self._sound_mode = "Direct"
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setPureDirect":
                                res = await avr.request(
                                    Zone.set_pure_direct(zone, "True")
                                )
                                self._sound_mode = "Pure Direct"
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setClearVoice":
                                res = await avr.request(
                                    Zone.set_clear_voice(zone, "True")
                                )
                                self._sound_mode = "Clear Voice"
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setSurroundAI":
                                enabled = kwargs["enabled"]
                                res = await avr.request(
                                    Zone.set_surround_ai(zone, enable=enabled)
                                )
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setSelect":
                                select_id = kwargs["select_id"]
                                option = kwargs["option"]
                                select_cfg = self.selects.get(select_id)
                                if select_cfg is None:
                                    raise ValueError(f"Unknown select: {select_id}")
                                if (
                                    select_cfg.options
                                    and option not in select_cfg.options
                                ):
                                    raise ValueError(
                                        f"Option '{option}' not valid for select '{select_id}'. "
                                        f"Valid options: {select_cfg.options}"
                                    )
                                # Dispatch to the appropriate pyamaha Zone method.
                                if not select_cfg.zone_command:
                                    raise ValueError(
                                        f"Select '{select_id}' has no zone_command configured"
                                    )
                                zone_method = getattr(
                                    Zone, select_cfg.zone_command, None
                                )
                                if zone_method is None:
                                    raise ValueError(
                                        f"pyamaha Zone has no method '{select_cfg.zone_command}'"
                                    )
                                res = await avr.request(zone_method(zone, option))
                                # Update the single source of truth (SensorConfig.value)
                                sensor_cfg = self.sensors.get(select_id)
                                if sensor_cfg:
                                    sensor_cfg.value = option
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                                self.push_update()

                            case "setScene":
                                scene = int(kwargs["scene"])
                                res = await avr.request(Zone.set_scene(zone, scene))

                    case "tuner":
                        zone = kwargs.get("zone", "main")
                        match command:
                            case "recallPreset":
                                band = kwargs.get("band")
                                num = kwargs.get("num")
                                if band is None or num is None:
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
                                    raise ValueError(
                                        "Missing required parameters 'band' and 'num'"
                                    )
                                res = await avr.request(
                                    NetUSB.recall_preset(zone=zone, num=int(num))
                                )

            return res

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOG.error(
                "[%s] Network error sending command %s: %s", self.log_id, command, err
            )
            raise
        except ValueError as err:
            _LOG.error(
                "[%s] Invalid parameter for command %s: %s", self.log_id, command, err
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

    # ── Volume helpers ────────────────────────────────────────────────────────

    def _calculate_volume(self, kwargs: dict[str, Any]) -> int:
        """Calculate absolute volume level from a percentage (0-100)."""
        volume_level = kwargs.get("volume_level", 0)
        volume = 0

        if volume_level is not None:
            try:
                percentage = int(volume_level)
                volume = int((percentage / 100.0) * self.max_volume)
                _LOG.debug(
                    "[%s] Converting volume_level %s%% to %s (max: %s)",
                    self.log_id,
                    percentage,
                    volume,
                    self.max_volume,
                )
            except (ValueError, TypeError):
                _LOG.warning(
                    "[%s] Invalid volume_level value: %s", self.log_id, volume_level
                )
                volume = 0

        return int(volume)

    # ── Sensor helpers ────────────────────────────────────────────────────────

    def _sensor_attributes(self, sensor_id: str) -> SensorAttributes:
        """Return SensorAttributes for the given sensor identifier."""
        sensor_config = self.sensors.get(sensor_id)
        if not sensor_config:
            return SensorAttributes()

        value = sensor_config.value
        sensor_state = (
            SensorStates.ON
            if self._state == media_player.States.ON
            else SensorStates.UNAVAILABLE
        )

        return SensorAttributes(
            STATE=sensor_state,
            VALUE=(
                value
                if self._state == media_player.States.ON and value is not None
                else sensor_config.default
            ),
            UNIT=sensor_config.unit,
        )

    def _update_sensors_from_status(self, status: dict[str, Any]) -> None:
        """Update sensor values from a Zone.get_status() response dict."""
        tone_control = status.get("tone_control", {})
        auro_3d = status.get("auro_3d", {})

        sensor_mappings = {
            "input": status.get("input"),
            "input_text": status.get("input_text"),
            "volume": status.get("volume"),
            "mute": status.get("mute"),
            "sound_program": status.get("sound_program"),
            "surr_decoder_type": status.get("surr_decoder_type"),
            "surround_ai": status.get("surround_ai"),
            "pure_direct": status.get("pure_direct"),
            "enhancer": status.get("enhancer"),
            "tone_control_mode": tone_control.get("mode"),
            "bass": tone_control.get("bass"),
            "treble": tone_control.get("treble"),
            "dialogue_level": status.get("dialogue_level"),
            "dialogue_lift": status.get("dialogue_lift"),
            "subwoofer_volume": status.get("subwoofer_volume"),
            "link_control": status.get("link_control"),
            "link_audio_delay": status.get("link_audio_delay"),
            "contents_display": status.get("contents_display"),
            "party_enable": status.get("party_enable"),
            "extra_bass": status.get("extra_bass"),
            "adaptive_drc": status.get("adaptive_drc"),
            "dts_dialogue_control": status.get("dts_dialogue_control"),
            "adaptive_dsp_level": status.get("adaptive_dsp_level"),
            "distribution_enable": status.get("distribution_enable"),
            "sleep": status.get("sleep"),
            "auro_3d_listening_mode": auro_3d.get("listening_mode"),
            "auro_matic_preset": auro_3d.get("auro_matic_preset"),
            "auro_matic_strength": auro_3d.get("auro_matic_strength"),
        }

        for sensor_id, value in sensor_mappings.items():
            sensor_cfg = self.sensors.get(sensor_id)
            if sensor_cfg and value is not None:
                sensor_cfg.value = value
