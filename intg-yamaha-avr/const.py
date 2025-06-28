"""Yamaha AVR integration constants."""

from enum import Enum, IntEnum
from ucapi.media_player import States as MediaStates


class SimpleCommands(str, Enum):
    """Additional simple commands of the Yamaha AVR not covered by media-player features."""

    EXIT = "Exit"
    SLEEP = "Sleep"
    HDMI_1 = "HDMI 1"
    HDMI_2 = "HDMI 2"
    HDMI_3 = "HDMI 3"
    HDMI_4 = "HDMI 4"
    HDMI_OUTPUT_1 = "HDMI Output 1"
    HDMI_OUTPUT_2 = "HDMI Output 2"
    SOUND_MODE_DIRECT = "Sound Mode Direct"
    SOUND_MODE_PURE = "Sound Mode Pure Direct"
    SOUND_MODE_CLEAR_VOICE = "Clear Voice"


class States(IntEnum):
    """State of a connected Yamaha AVR."""

    UNKNOWN = 0
    UNAVAILABLE = 1
    OFF = 2
    ON = 3


YAMAHA_STATE_MAPPING = {
    States.OFF: MediaStates.OFF,
    States.ON: MediaStates.ON,
    States.UNAVAILABLE: MediaStates.UNAVAILABLE,
    States.UNKNOWN: MediaStates.UNKNOWN,
}
