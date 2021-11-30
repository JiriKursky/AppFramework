from enum import auto
from typing import Dict

from attr import dataclass

from devices_interface import VALVE_OPERATION
from helper_types import AutoName


# @auto_create
SENSOR_REQ = (
    "sensor.honeywell_req"  # {"friendly_name": "Request","sensor_type": "number"}
)

SENSOR_HONEY_INFO = "sensor.honeywell_info"  # {"friendly_name": "Info Honeywell com"}
# @end

TEMP_OPERATION_MAX = 35
TEMP_OPERATION_MIN = 5


class HoneywellTaskName(AutoName):
    AUTHORIZE = auto()
    INITIALIZE = auto()


def convert_operating_mode_int(operation: VALVE_OPERATION) -> int:
    if operation == VALVE_OPERATION.MAX:
        return TEMP_OPERATION_MAX
    else:
        return TEMP_OPERATION_MIN


def convert_operating_mode(value: int) -> VALVE_OPERATION:
    if value == TEMP_OPERATION_MIN:
        return VALVE_OPERATION.MIN
    if value == TEMP_OPERATION_MAX:
        return VALVE_OPERATION.MAX
    return VALVE_OPERATION.UNKNOWN


HONEYWELL_COMM_INSTANCE = "HoneywellComm"
