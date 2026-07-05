from enum import Enum

class ContextBand(Enum):
    SHORT = 4096
    MEDIUM = 32768
    LONG = 131072
    EXTREME = 262144

BAND_MAP = {
    "short": ContextBand.SHORT,
    "medium": ContextBand.MEDIUM,
    "long": ContextBand.LONG,
    "extreme": ContextBand.EXTREME
}
