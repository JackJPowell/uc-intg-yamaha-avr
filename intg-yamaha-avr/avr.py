"""
This module implements the Yamaha AVR communication of the Remote Two integration driver.

"""

import asyncio
import logging
from asyncio import AbstractEventLoop
from typing import Any

import aiohttp
from const import YamahaConfig, SENSORS, SensorConfig
from pyamaha import AsyncDevice, System, Tuner, Zone, NetUSB
from ucapi import EntityTypes, media_player
from ucapi.sensor import States as SensorStates
from ucapi_framework import StatelessHTTPDevice, EntitySource, BaseIntegrationDriver
from ucapi_framework.helpers import MediaPlayerAttributes, SensorAttributes

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

        # Sensor storage
        self.sensors: dict[str, SensorConfig] = {s.identifier: s for s in SENSORS}

        # Initialize MediaPlayerAttributes dataclass
        self.attributes = MediaPlayerAttributes(
            STATE=media_player.States.UNKNOWN,
            SOURCE=None,
            SOURCE_LIST=self._source_list,
            MUTED=None,
            SOUND_MODE=None,
            SOUND_MODE_LIST=self._sound_mode_list,
            VOLUME=None,
        )

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
    def state(self) -> media_player.States:
        """Return the device state."""
        return (
            self.attributes.STATE
            if self.attributes.STATE
            else media_player.States.UNKNOWN
        )

    @property
    def source_list(self) -> list[str]:
        """Return a list of available input sources."""
        return sorted(self._source_list)

    @property
    def source(self) -> str:
        """Return the current input source."""
        return self.attributes.SOURCE if self.attributes.SOURCE else ""

    @property
    def zone(self) -> str:
        """Return the current zone."""
        return self._zone

    @property
    def muted(self) -> bool:
        """Return whether the device is muted."""
        return self.attributes.MUTED if self.attributes.MUTED is not None else False

    @property
    def sound_mode(self) -> str | None:
        """Return the current sound mode."""
        return self.attributes.SOUND_MODE if self.attributes.SOUND_MODE else ""

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
        """Return the current volume level (in dB for dB mode, or raw value for numeric mode)."""
        return self._actual_volume.get("value", 0.0)

    @property
    def volume_percent(self) -> int:
        """Return the current volume as a percentage (0-100) for the remote UI slider."""
        # Convert internal volume (0-161) to percentage (0-100)
        percentage = int((self._volume_level / self.max_volume) * 100)

        # Clamp to 0-100 range
        return max(0, min(100, percentage))

    def get_display_volume(self) -> int:
        """Return volume in the format specified by user's volume_mode config.

        - absolute: 0-98 scale (numeric mode)
        - relative: -79.5 to +10 scale (dB mode)
        """
        user_mode = self._device_config.volume_mode
        actual_mode = self._actual_volume.get("mode", "db")
        actual_value = self._actual_volume.get("value", 0.0)

        # If user wants absolute (0-98 scale)
        if user_mode == "absolute":
            if actual_mode == "numeric":
                # Already in numeric mode, return as-is
                return int(actual_value)
            else:
                # Convert from dB (-80.5 to +16.5) to numeric (0 to 97)
                # Formula: numeric = (dB + 80.5) / 97 * 97 = dB + 80.5
                return int(actual_value + 80.5)

        # If user wants relative (-79.5 to +10 dB scale)
        else:
            if actual_mode == "db":
                # Already in dB mode, return as-is
                return int(actual_value)
            else:
                # Convert from numeric (0 to 97) to dB (-80.5 to +16.5)
                # Formula: dB = numeric - 80.5
                return int(actual_value - 80.5)

    @property
    def volume_mode(self) -> str:
        """Return the volume mode (db or numeric)."""
        return self._actual_volume.get("mode", "db")

    @property
    def max_volume(self) -> int:
        """Return the maximum volume level, defaulting to 161 if not set."""
        return self._max_volume_level if self._max_volume_level > 0 else 161

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
            # Just verify we can reach the device - don't process the response
            await avr.request(Zone.get_status(self.zone))
            _LOG.debug("[%s] Device connection verified", self.log_id)

    async def connect(self) -> bool:
        """Establish connection to the AVR."""
        # Use the base class connect which calls verify_connection
        result = await super().connect()
        # After connection is verified, update attributes
        if result:
            await self._update_attributes()
        return result

    async def _update_attributes(self) -> None:
        _LOG.debug("[%s] Updating attributes", self.log_id)

        async with aiohttp.ClientSession() as session:
            try:
                avr = AsyncDevice(session, self.address)
                status = await avr.request(Zone.get_status(zone=self.zone))
                status = await status.json()

                # Update attributes from status
                power_str = status.get("power", "off").lower()
                if power_str == "on":
                    self.attributes.STATE = media_player.States.ON
                elif power_str == "standby":
                    self.attributes.STATE = media_player.States.STANDBY
                else:
                    self.attributes.STATE = media_player.States.OFF

                self.attributes.MUTED = status.get("mute", False)
                active_source_text = status.get("input_text", "")
                if not active_source_text:
                    active_source_text = status.get("input", "")
                self.attributes.SOURCE = (
                    active_source_text if active_source_text else ""
                )
                self.attributes.SOUND_MODE = status.get("sound_program", None)

                # Safely extract nested actual_volume data
                self._actual_volume = status.get("actual_volume", {})
                # Also store the internal volume value (0-161)
                self._volume_level = status.get("volume", 0)

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

        # Update remaining attributes
        self.attributes.SOURCE_LIST = self.source_list
        self.attributes.SOUND_MODE_LIST = self.sound_mode_list
        self.attributes.VOLUME = self.get_display_volume()

        # Update sensor values from status
        self._update_sensors_from_status(status)

        # Framework will call get_device_attributes() to retrieve updated attributes

    async def send_command(
        self, command: str, group: str, *args: Any, **kwargs: Any
    ) -> str:
        """Send a command to the AVR."""
        res: str = ""
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
                                res = await avr.request(System.set_hdmi_out_1("True"))
                            case "setHdmiOut2":
                                res = await avr.request(System.set_hdmi_out_2("True"))
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
                                        self.attributes.STATE = media_player.States.ON
                                    case "standby":
                                        self.attributes.STATE = (
                                            media_player.States.STANDBY
                                        )

                                # Update sensors after power change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setSleep":
                                sleep = int(kwargs["sleep"])  # 0,30,60,90,120
                                res = await avr.request(Zone.set_sleep(zone, sleep))

                                # Update sensors after sleep change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setVolume":
                                volume_cmd = kwargs.get("volume")

                                # Handle up/down commands directly
                                if volume_cmd in ("up", "down"):
                                    step = float(self.device_config.volume_step)
                                    if step < 1:
                                        step = 1
                                    else:
                                        step = step * 2
                                    res = await avr.request(
                                        Zone.set_volume(zone, volume_cmd, int(step))
                                    )
                                else:
                                    # Calculate volume from percentage
                                    volume = self._calculate_volume(kwargs)
                                    res = await avr.request(
                                        Zone.set_volume(zone, volume, 1)
                                    )

                                await asyncio.sleep(0.1)
                                res = await avr.request(Zone.get_status(self.zone))
                                status = await res.json()

                                # Extract actual_volume data and internal volume
                                self._actual_volume = status.get("actual_volume", {})
                                self._volume_level = status.get("volume", 0)
                                self.attributes.VOLUME = self.get_display_volume()

                                # Update sensors
                                self._update_sensors_from_status(status)
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
                                self.attributes.MUTED = mute

                                # Update sensors after mute change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
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

                                await asyncio.sleep(0.1)
                                res = await avr.request(Zone.get_status(self.zone))
                                status = await res.json()

                                source_text = status.get("input_text", input_source)
                                if not source_text:
                                    source_text = input_source
                                self.attributes.SOURCE = source_text

                                # Update sensors
                                self._update_sensors_from_status(status)
                            case "setSoundMode":
                                sound_mode = kwargs["sound_mode"]
                                sound_mode = sound_mode.lower()
                                res = await avr.request(
                                    Zone.set_sound_program(zone, sound_mode)
                                )
                                self.attributes.SOUND_MODE = sound_mode

                                # Update sensors after sound mode change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setDirect":
                                res = await avr.request(Zone.set_direct(zone, "True"))
                                self.attributes.SOUND_MODE = "Direct"

                                # Update sensors after direct mode change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setPureDirect":
                                res = await avr.request(
                                    Zone.set_pure_direct(zone, "True")
                                )
                                self.attributes.SOUND_MODE = "Pure Direct"

                                # Update sensors after pure direct mode change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setClearVoice":
                                res = await avr.request(
                                    Zone.set_clear_voice(zone, "True")
                                )
                                self.attributes.SOUND_MODE = "Clear Voice"

                                # Update sensors after clear voice mode change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
                            case "setSurroundAI":
                                enabled = kwargs["enabled"]  # True, False
                                res = await avr.request(
                                    Zone.set_surround_ai(zone, enable=enabled)
                                )

                                # Update sensors after surround AI change
                                await asyncio.sleep(0.1)
                                status_res = await avr.request(
                                    Zone.get_status(self.zone)
                                )
                                status = await status_res.json()
                                self._update_sensors_from_status(status)
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

    def _calculate_volume(self, kwargs: dict[str, Any]) -> int:
        """Calculate volume command and step based on user input.

        Args:
            kwargs: Command arguments which may contain:
                - volume_level: integer percentage (0-100) to convert to integer
                percentage of max_volume

        Returns:
            tuple: (volume_command, step) where volume_command is 'up', 'down', or integer
        """
        volume_level = kwargs.get("volume_level", 0)  # integer 0-100

        # If volume_level is provided (0-100), convert to integer percentage of max_volume
        if volume_level is not None:
            try:
                percentage = int(volume_level)
                # Convert percentage (0-100) to integer volume (0-max_volume)
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
                    "[%s] Invalid volume_level value: %s",
                    self.log_id,
                    volume_level,
                )
                volume = 0

        return int(volume)

    def _sensor_attributes(self, sensor_id: str) -> SensorAttributes:
        """Return sensor attributes for the given sensor identifier.

        Args:
            sensor_id: Sensor identifier (e.g., 'sound_program', 'surround_ai')

        Returns:
            SensorAttributes dataclass with STATE, VALUE, and optionally UNIT
        """
        sensor_config = self.sensors.get(sensor_id)
        if not sensor_config:
            return SensorAttributes()

        # Get value directly from sensor config
        value = sensor_config.value

        # Determine sensor state based on AVR power state
        sensor_state = SensorStates.UNAVAILABLE
        if self.state == media_player.States.ON:
            sensor_state = SensorStates.ON
        elif self.state in (media_player.States.STANDBY, media_player.States.OFF):
            sensor_state = SensorStates.UNAVAILABLE

        # Return value if AVR is ON, otherwise use default
        return SensorAttributes(
            STATE=sensor_state,
            VALUE=value
            if self.state == media_player.States.ON and value is not None
            else sensor_config.default,
            UNIT=sensor_config.unit,
        )

    def _update_sensors_from_status(self, status: dict[str, Any]) -> None:
        """Update sensor values from status response.

        Args:
            status: Status dictionary from Zone.get_status()
        """
        # Extract nested structures
        tone_control = status.get("tone_control", {})
        auro_3d = status.get("auro_3d", {})

        # Update sensor values from status
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

        # Track which sensors have changed values
        changed_sensors = set()

        for sensor_id, value in sensor_mappings.items():
            sensor = self.sensors.get(sensor_id)
            if sensor and value is not None:
                # Only mark as changed if value is different
                if sensor.value != value:
                    sensor.value = value
                    changed_sensors.add(sensor_id)

        # Always trigger sensor entity state refresh (even when AVR is off)
        if self.driver and changed_sensors:
            # Get all sensor entities from the driver
            sensor_entities = self.driver.filter_entities_by_type(
                EntityTypes.SENSOR, EntitySource.CONFIGURED
            )

            # Only refresh sensors that have changed
            for entity in sensor_entities:
                # Entity ID format: sensor.{device_id}.{sensor_id}
                for sensor_key in changed_sensors:
                    if entity.id.endswith(f".{sensor_key}"):
                        entity.refresh_state()  # ty:ignore[unresolved-attribute]
                        break

    def get_device_attributes(
        self, entity_id: str
    ) -> MediaPlayerAttributes | SensorAttributes:
        """
        Return device attributes for the given entity.

        Called by framework when refreshing entity state to retrieve current attributes.
        For sensor entities, extracts the sensor identifier from entity_id and returns sensor attributes.

        :param entity_id: Entity identifier (format: sensor.{device_id}.{sensor_id} for sensors)
        :return: MediaPlayerAttributes for media player, SensorAttributes for sensors
        """
        # Check if this is a sensor entity by looking for the pattern
        if "sensor." in entity_id:
            # Extract sensor identifier from entity_id using split
            # Format: sensor.{device_id}.{sensor_id}
            parts = entity_id.split(".", 2)
            if len(parts) >= 3:
                sensor_id = parts[2]
                return self._sensor_attributes(sensor_id)

        # Default to media player attributes
        return self.attributes
