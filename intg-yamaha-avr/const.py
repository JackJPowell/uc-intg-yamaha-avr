"""Yamaha AVR integration constants."""

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum

from ucapi.media_player import States as MediaStates


@dataclass
class YamahaDevice:
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
    sound_modes: list[str] | None = None
    """List of sound modes for the device, if available."""


class SimpleCommands(str, Enum):
    """Additional simple commands of the Yamaha AVR not covered by media-player features."""

    SLEEP_OFF = "Sleep Off"
    SLEEP_30 = "Sleep 30"
    SLEEP_60 = "Sleep 60"
    SLEEP_90 = "Sleep 90"
    SLEEP_120 = "Sleep 120"
    HDMI_OUTPUT_1 = "HDMI Output 1"
    HDMI_OUTPUT_2 = "HDMI Output 2"
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


class IrCodes(StrEnum):
    """IR codes for the Yamaha AVR."""

    HOME = "7F016698"  # Stub code for Home button


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
