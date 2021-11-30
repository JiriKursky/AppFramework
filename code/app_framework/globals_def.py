""" For simple generating of events """

from collections import namedtuple
from enum import Enum, auto
from globals_def_custom import GlobalsDefCustom
from helper_tools import MyHelp as h
from helper_types import AutoName


class GlobalsDef(object):
    DEFINE: list = [
        "WS_COMMANDS_DONE",
        "ENTITY_ERROR",
        "TAKT",
        "DEF_LOOP",
        "ENTITIES_CREATED",
        "ENTITY_CREATED",
        "SYSTEM_READY",
        "BUTTON",
        "GLOBALS_ACTIVATED",
        "START_INIT",
        "REGISTER_INIT",
        "BOOT_MODULE_RELOADED",
        "BOOT_MODULE_DONE",
        "BOOT_MODULES_LOADED",
        "BOOT_MODULE_ADDED",
        "APF_MODULES_DONE",
    ]

    DEFINE_CONSTS: list = [
        "linked_control",
        "params",
        "procedure",
        "restart",
        "todo",
        "service_data",
        "notification_id",
        "interval",
        "trigger",
        "error",
        "timeout",
        "event",
        "timeout_event",
        "fire_event",
    ]


for d in GlobalsDefCustom.DEFINE:
    if not h.in_array(d, GlobalsDef.DEFINE):
        GlobalsDef.DEFINE.append(d)
for c in GlobalsDefCustom.DEFINE_CONSTS:
    if not h.in_array(c, GlobalsDef.DEFINE_CONSTS):
        GlobalsDef.DEFINE_CONSTS.append(c)


ConstsDef = namedtuple(
    "ConstsDef", GlobalsDef.DEFINE_CONSTS, defaults=GlobalsDef.DEFINE_CONSTS
)
EventsDef = namedtuple("EventsDef", GlobalsDef.DEFINE, defaults=GlobalsDef.DEFINE)

constsDef = ConstsDef()
eventsDef = EventsDef()


class GEVNT(AutoName):
    BUFFER_STARTED = auto()
    BUFFER_CLEARED = auto()
    BUFFER_INSTANCE_STATE_CHANGED = auto()
