"""Yamaha AVR integration constants."""

from enum import Enum, IntEnum, StrEnum
from ucapi.media_player import States as MediaStates


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
    SCENE_9 = "Scene 9"


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
