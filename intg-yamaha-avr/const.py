"""Yamaha AVR integration constants."""

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import Final

from ucapi.media_player import States as MediaStates


@dataclass
class YamahaConfig:
    """Yamaha device configuration."""

    identifier: str
    """Unique identifier of the device. (MAC Address)"""
    name: str
    """Friendly name of the device."""
    address: str
    """IP Address of device"""
    input_list: list[str] | None = None
    """List of inputs for the device, if available."""
    volume_step: str = "1"
    """Volume step for the device, default is 1. Can be set to '0.5' or '2'."""
    volume_mode: str = "relative"
    """Volume mode for the device, either 'relative' or 'absolute'. Default is 'relative'."""
    sound_modes: list[str] | None = None
    """List of sound modes for the device, if available."""


@dataclass
class SensorConfig:
    """Configuration for a sensor entity."""

    identifier: str
    """Unique identifier for the sensor (e.g., 'sound_program')."""
    name: str
    """Human-readable name for the sensor."""
    unit: str | None = None
    """Unit of measurement (optional)."""
    default: str | int | float = ""
    """Default value when sensor is unavailable."""
    value: str | int | float | bool | None = None
    """Current runtime value of the sensor."""


class SimpleCommands(str, Enum):
    """Additional simple commands of the Yamaha AVR not covered by media-player features."""

    SLEEP_OFF = "Sleep Off"
    SLEEP_30 = "Sleep 30"
    SLEEP_60 = "Sleep 60"
    SLEEP_90 = "Sleep 90"
    SLEEP_120 = "Sleep 120"
    HDMI_OUTPUT_1_ON = "HDMI Output 1 On"
    HDMI_OUTPUT_1_OFF = "HDMI Output 1 Off"
    HDMI_OUTPUT_2_ON = "HDMI Output 2 On"
    HDMI_OUTPUT_2_OFF = "HDMI Output 2 Off"
    SOUND_MODE_DIRECT = "Sound Mode Direct"
    SOUND_MODE_PURE = "Sound Mode Pure Direct"
    SOUND_MODE_CLEAR_VOICE = "Clear Voice"
    NUMBER_ENTER = "Number Enter"
    RETURN = "Return"
    OPTIONS = "Options"
    SURROUND_AI_ON = "Surround AI On"
    SURROUND_AI_OFF = "Surround AI Off"
    SCENE_1 = "Scene 1"
    SCENE_2 = "Scene 2"
    SCENE_3 = "Scene 3"
    SCENE_4 = "Scene 4"
    SCENE_5 = "Scene 5"
    SCENE_6 = "Scene 6"
    SCENE_7 = "Scene 7"
    SCENE_8 = "Scene 8"
    FM_1 = "FM 1"
    FM_2 = "FM 2"
    FM_3 = "FM 3"
    FM_4 = "FM 4"
    FM_5 = "FM 5"
    FM_6 = "FM 6"
    FM_7 = "FM 7"
    FM_8 = "FM 8"
    FM_9 = "FM 9"
    FM_10 = "FM 10"
    DAB_1 = "DAB 1"
    DAB_2 = "DAB 2"
    DAB_3 = "DAB 3"
    DAB_4 = "DAB 4"
    DAB_5 = "DAB 5"
    DAB_6 = "DAB 6"
    DAB_7 = "DAB 7"
    DAB_8 = "DAB 8"
    DAB_9 = "DAB 9"
    DAB_10 = "DAB 10"
    TUNER_NEXT = "Tuner Next Preset"
    TUNER_PREV = "Tuner Previous Preset"
    NETUSB_1 = "Net/USB 1"
    NETUSB_2 = "Net/USB 2"
    NETUSB_3 = "Net/USB 3"
    NETUSB_4 = "Net/USB 4"
    NETUSB_5 = "Net/USB 5"
    NETUSB_6 = "Net/USB 6"
    NETUSB_7 = "Net/USB 7"
    NETUSB_8 = "Net/USB 8"
    NETUSB_9 = "Net/USB 9"
    NETUSB_10 = "Net/USB 10"


class IrCodes(StrEnum):
    """IR codes for the Yamaha AVR."""

    HOME = "7F016698"  # Stub code for Home button


# Sensor configurations
SENSORS: Final[tuple[SensorConfig, ...]] = (
    SensorConfig(identifier="input", name="Input"),
    SensorConfig(identifier="input_text", name="Input Text"),
    SensorConfig(identifier="volume", name="Volume"),
    SensorConfig(identifier="mute", name="Mute"),
    SensorConfig(identifier="sound_program", name="Sound Program"),
    SensorConfig(identifier="surr_decoder_type", name="Surround Decoder Type"),
    SensorConfig(identifier="surround_ai", name="Surround AI"),
    SensorConfig(identifier="pure_direct", name="Pure Direct"),
    SensorConfig(identifier="enhancer", name="Enhancer"),
    SensorConfig(identifier="tone_control_mode", name="Tone Control Mode"),
    SensorConfig(identifier="bass", name="Bass", unit="dB"),
    SensorConfig(identifier="treble", name="Treble", unit="dB"),
    SensorConfig(identifier="dialogue_level", name="Dialogue Level"),
    SensorConfig(identifier="dialogue_lift", name="Dialogue Lift"),
    SensorConfig(identifier="subwoofer_volume", name="Subwoofer Volume", unit="dB"),
    SensorConfig(identifier="link_control", name="Link Control"),
    SensorConfig(identifier="link_audio_delay", name="Link Audio Delay"),
    SensorConfig(identifier="contents_display", name="Contents Display"),
    SensorConfig(identifier="party_enable", name="Party Mode"),
    SensorConfig(identifier="extra_bass", name="Extra Bass"),
    SensorConfig(identifier="adaptive_drc", name="Adaptive DRC"),
    SensorConfig(identifier="dts_dialogue_control", name="DTS Dialogue Control"),
    SensorConfig(identifier="adaptive_dsp_level", name="Adaptive DSP Level"),
    SensorConfig(identifier="distribution_enable", name="Distribution Enable"),
    SensorConfig(identifier="sleep", name="Sleep Timer", unit="min"),
    SensorConfig(identifier="auro_3d_listening_mode", name="Auro-3D Listening Mode"),
    SensorConfig(identifier="auro_matic_preset", name="Auro-Matic Preset"),
    SensorConfig(identifier="auro_matic_strength", name="Auro-Matic Strength"),
)


class States(IntEnum):
    """State of a connected Yamaha AVR."""

    UNKNOWN = 0
    UNAVAILABLE = 1
    OFF = 2
    ON = 3
    STANDBY = 4


YAMAHA_STATE_MAPPING = {
    States.OFF: MediaStates.OFF,
    States.ON: MediaStates.ON,
    States.STANDBY: MediaStates.STANDBY,
    States.UNAVAILABLE: MediaStates.UNAVAILABLE,
    States.UNKNOWN: MediaStates.UNKNOWN,
}
