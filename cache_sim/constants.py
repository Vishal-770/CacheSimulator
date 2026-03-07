from enum import Enum, auto

class WritePolicy(Enum):
    WRITE_THROUGH = auto()
    WRITE_BACK = auto()

class ReplacementAlgorithm(Enum):
    FIFO = auto()
    LRU = auto()
    LFU = auto()

class MissType(Enum):
    COMPULSORY = auto()
    CAPACITY = auto()
    CONFLICT = auto()
