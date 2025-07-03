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


class IrCodes(StrEnum):
    """IR codes for the Yamaha AVR."""

    CURSOR_DOWN = "5EA139C6"
    CURSOR_LEFT = "5EA1F906"
    CURSOR_RIGHT = "5EA17986"
    CURSOR_UP = "5EA1B946"
    CURSOR_ENTER = "5EA17B84"
    BACK = "5EA155AA"
    DIGIT_0 = "FE805AA5"
    DIGIT_1 = "FE808A75"
    DIGIT_2 = "FE804AB5"
    DIGIT_3 = "FE80CA35"
    DIGIT_4 = "FE802AD5"
    DIGIT_5 = "FE80AA55"
    DIGIT_6 = "FE806A95"
    DIGIT_7 = "FE80EA15"
    DIGIT_8 = "FE801AE5"
    DIGIT_9 = "FE809A65"
    INFO = "5EA1E41A"
    SETTINGS = "5EA1D628"
    MENU = "5EA1D628"
    HOME = "5EA155AA"

    NUMBER_ENTER = "FE803AC5"


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
