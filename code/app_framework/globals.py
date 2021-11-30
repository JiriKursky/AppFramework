from dataclasses import replace
from typing import Any, Union
from helper_types import RegisterType, AutoName
from enum import auto

ON = "on"
OFF = "off"
ANO = "Ano"
NE = "Ne"
IDLE = "idle"
PLAYING = "playing"

UNAVAILABLE = "unavailable"
HEAT = "heat"
HOME = "home"
NOT_HOME = "not_home"

HELPERS = ("input_boolean", "input_number", "input_text")

DAEMON_TERMINATE = "DAEMON_TERMINATE"

# Sequence how will be loaded boot modules


module_register: RegisterType = []  # known modules - object of AppBasic
entity_register: list = [str]  # all entities registered in hass, simple list
helper_register: RegisterType = []  # entities defined in app_system
helper_register_obj: list = (
    []
)  # entities defined in app_system converted in entity_create
register_button: RegisterType = []
sensor_register: RegisterType = []
created_helpers_obj: list = []  # list of created helpers via ws EntityObjects
time_zone: str = ""  # storing time zone

BOOT_CLASSES: tuple = (
    "WsHA",
    "Sensors",
    "AppSystem",
    "EntityRegister",
    "EntityOper",
    "CreateHelpers",
    "Sanitarize",
    "LastMile",
    "BufferControl",
)


class gv:
    APF_MODULES_INIT = "apf_modules_init"
    BOOT_MODULES = "boot_modules"  # simple boot module name list
    BOOT_FINISHED = "boot_finished"
    APF_INIT_DONE = "apf_init_done"


class TASK_EVENT(AutoName):
    EXECUTE_TASK = auto()
    IGNORE_STATE = auto()
    TASK_FINISHED = auto()
    BUFFER_STARTED = auto()


class BUFFER_EVENT(AutoName):
    WAITING_ON = auto()
    WAITING_OFF = auto()
