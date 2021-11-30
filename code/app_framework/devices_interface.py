# Device interface used for controlling valves
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Union
from apd_types import ChildObjectBasicApp
from global_topeni import SWITCH_KOTEL, TOPENI_RUCNE
from helper_tools import MyHelp as h, DateTimeOp as dt
from helper_types import (
    AutoName,
    BoolType,
    DictMixed,
    DictType,
    EntityName,
    StrType,
)
from globals import ON, OFF


LIMIT_FOR_SWITCH_MODE = 3 * 60


class HEAT_PAR(AutoName):
    WINDOWS = auto()
    ON_GOOGLE = auto()
    OFF_GOOGLE = auto()
    VALVE_MAX = auto()
    BUTTON_CONTROL = auto()
    SENSOR_TEMPERATURE = auto()
    SENSOR_TEMPERATURE_EXT = auto()
    TARGET_TEMPERATURE = auto()
    TARGET_NIGHT_TEMPERATURE = auto()
    ENTITY_ID = auto()
    NIGHT_MODE = auto()
    IB_WINDOWS_OPENED = auto()
    USB_ENTITY_ID = auto()
    IB_CHARGING_ACTIVE = auto()
    FRIENDLY_NAME = auto()
    DEVICE_ERROR = auto()
    IB_CHARGING_DURING_NIGHT = auto()
    NAME_ID = auto()
    AT_EXCLUDE = auto()
    INTERFACE = auto()
    DEVICE_ID = auto()
    EXCLUDE_BOILER = auto()
    SENSOR_BATTERY = auto()
    SENSOR_STAT = auto()
    SCENE_MAX = auto()
    SCENE_MIN = auto()


class EVNT_DI(AutoName):
    VALVE_UPDATE_MAIN_LOOP = auto()


class INTERFACE_TYPE(AutoName):
    UNKNOWN = auto()
    FIBARO = auto()
    HONEYWELL = auto()


@dataclass
class ApiEntityABC(ABC):
    name_id: str = field(default="")
    device_id: str = field(default="")
    entity_id: EntityName = field(default="")
    state_changed: bool = field(default=False)
    interface: INTERFACE_TYPE = INTERFACE_TYPE.UNKNOWN
    dead: bool = field(default=False)
    parent: Any = None


ApiEntityABCType = Union[ApiEntityABC, None]
ListApiEntity = List[ApiEntityABC]


class DeviceRegister:
    entities_type: Dict[str, ListApiEntity] = {}
    entities: ListApiEntity = []

    @staticmethod
    def register(parent, entity: ApiEntityABC):
        # checking for duplicity
        check = DeviceRegister.get_entity(entity=entity)
        if check is not None:
            raise ValueError(f"Duplicity in register for:{entity}")
        entity.parent = parent
        DeviceRegister.entities.append(entity)
        if entity.interface == INTERFACE_TYPE.UNKNOWN:
            raise ValueError(
                f"Registering unknnown interface name_id: {entity.name_id}, entity_id: {entity.entity_id}"
            )
        device_type: str = str(entity.interface.value)

        # adding to current list
        get_list: ListApiEntity = DeviceRegister.entities_type.get(device_type, [])
        get_list.append(entity)
        DeviceRegister.entities_type[device_type] = get_list

    @staticmethod
    def get_interface_entities(interface_type: INTERFACE_TYPE) -> ListApiEntity:
        if interface_type == INTERFACE_TYPE.UNKNOWN:
            return []
        else:
            return DeviceRegister.entities_type.get(str(interface_type.value), [])

    @staticmethod
    def clear_state_change(inerface_type: INTERFACE_TYPE) -> None:
        for entity in DeviceRegister.get_interface_entities(inerface_type):
            entity.state_changed = False

    @staticmethod
    def get_entity(
        entity: ApiEntityABCType = None,
        name_id: StrType = None,
        entity_id: StrType = None,
        device_id: StrType = None,
        interface: INTERFACE_TYPE = INTERFACE_TYPE.UNKNOWN,
    ):
        def search(register: ListApiEntity, param: str, value: str) -> ApiEntityABCType:
            return next(
                (eo for eo in register if eo.__dict__.get(param, "") == value), None
            )

        if entity is not None:
            interface = entity.interface
            name_id = entity.name_id
            device_id = entity.device_id
            entity_id = entity.entity_id

        register = DeviceRegister.get_interface_entities(interface_type=interface)
        if len(register) == 0:
            return None

        if device_id is not None:
            return search(register, "device_id", device_id)
        elif entity_id is not None:
            return search(register, "entity_id", entity_id)
        elif name_id is not None:
            return search(register, "name_id", name_id)
        return None


ApiEntityABCType = Union[ApiEntityABC, None]


class STAT_ATTR(AutoName):
    battery_level = auto()
    valve_max = auto()
    temperature = auto()
    friendly_name = auto()
    is_max = auto()
    active = auto()
    windows_open = auto()
    windows_open_delay = auto()
    is_chilly = auto()
    target_temp = auto()
    setpoint = auto()
    dead = auto()
    device_id = auto()
    name_id = auto()
    last_operation_change = auto()
    last_target_reached = auto()


class VALVE_OPERATION(AutoName):
    MAX = auto()
    MIN = auto()
    UNKNOWN = auto()
    STATE_CHANGED = auto()
    SET_OPERATING_MODE = auto()
    UPDATE_STATE_IMMEDIATELY = auto()
    UPDATE_STATE = auto()
    NO_CHANGE = auto()
    NASTAV_DLE_TLACITKA = auto()


VALVE_OPERATION_TYPE = Union[VALVE_OPERATION, None]
VentilParamType = Union[str, list, None]


@dataclass
class VentilABC(ChildObjectBasicApp, ApiEntityABC):
    # operation_mode_convert: OperationModeConvertABC
    value: str = field(default="")
    friendly_name: str = field(default="")
    params: dict = field(default_factory=dict)
    state_changed: bool = field(default=False)
    _operating_mode: VALVE_OPERATION = VALVE_OPERATION.UNKNOWN
    _value: int = field(default=-1)
    battery_status: int = field(default=0)
    update_timestamp: str = field(default="")
    buffer_instance_name: str = field(default="")
    has_ha_control: bool = field(default=False)
    kotel_bezi: bool = field(default=False)
    heating_manually: bool = field(default=False)
    baterie_min: int = field(default=0)
    baterie_max: int = field(default=0)
    aktivni: bool = field(default=False)
    okno_otevrene_delay: bool = field(default=False)
    okno_otevrene: bool = field(default=False)
    control_entity: str = field(default="")
    temperature: float = field(default=0)
    setpoint: float = field(default=0)
    target_temperature: float = field(default=0)
    sensor_temperature: EntityName = field(default="")
    sensor_temperature_ext: bool = field(default=False)
    is_chilly: bool = field(default=False)
    stat_id: EntityName = field(default="")
    asking_attempt: int = field(default=0)
    last_changed_operation_state: float = field(default=0)
    target_reached: float = field(default=0)
    boiler_excluded: bool = field(default=False)

    def init(self):
        # ChildObjectBasicApp(_ba=self._ba, module_name="Ventil")
        self.debug(f"Init {self.module_name} {self._ba}")

        self.interface = self.params.get(HEAT_PAR.INTERFACE, INTERFACE_TYPE.FIBARO)
        self.debug(f"Valve type: {self.interface}")
        self.stat_id = self.params.get(HEAT_PAR.SENSOR_STAT, "")

        if len(self.name_id) == 0:
            self.name_id = self.params.get(HEAT_PAR.NAME_ID, "")
        if len(self.device_id) == 0:
            self.device_id = self.params.get(HEAT_PAR.DEVICE_ID, "")
        assert (
            len(self.name_id) > 0 or len(self.device_id) > 0
        ), "HEAT_PAR.NAME_ID or HEAT_PAR.DEVICE_ID is mandatory field (global_topeni), __post_init__"
        self.entity_id = self.params.get(HEAT_PAR.ENTITY_ID, "")
        self.has_ha_control = self.params.get(HEAT_PAR.BUTTON_CONTROL, False)

        if len(self.entity_id) == 0:
            self.warning(f"HEAT_PAR.ENTITY_ID is missing (not mandatory)")

        self._ba.activate_sensors()
        assert self._ba is not None, f"Missing parent_ba for: {self}"

        # This line ensure of regulary updat

        self.debug(f"Entity name: {self.entity_id} {self.params}")

        self.control_entity = self.params.get(HEAT_PAR.BUTTON_CONTROL, "")

        if self.has_ha_control:
            self._ba.sync_listen_state(self.button_changed, self.control_entity)
        sensor_temperature: VentilParamType = self.get_param_entity(
            HEAT_PAR.SENSOR_TEMPERATURE
        )
        if isinstance(sensor_temperature, str):
            self.sensor_temperature = sensor_temperature
        else:
            self.error(f"Wrong definition temperature for: {self.name_id}")

        s = self.get_param_entity(HEAT_PAR.FRIENDLY_NAME)
        if isinstance(s, str) and len(s) == 0:
            s = self.get_param_entity(HEAT_PAR.NAME_ID)
        if isinstance(s, str):
            self.sync_update_sensor_stat((STAT_ATTR.friendly_name, s))
        self.sync_update_sensor_stat((STAT_ATTR.is_max, OFF))
        ext = self.get_param_entity(HEAT_PAR.SENSOR_TEMPERATURE_EXT)
        if isinstance(ext, bool):
            self.sensor_temperature_ext = ext
        else:
            self.sensor_temperature_ext = False

    async def update_sensor_stat(self, attr: DictMixed):
        await self.set_sensor_state(self.stat_id, "info", attr)

    def sync_update_sensor_stat(self, attr: DictMixed):
        self.sync_set_sensor_state(self.stat_id, "info", attr)

    async def get_okno_otevrene(self) -> bool:
        # Otevreno - senzor znamena on
        entity_id = self.get_param_entity(HEAT_PAR.WINDOWS)
        if entity_id is None:
            return False
        if h.is_iterable(entity_id):
            for e in entity_id:  # type: ignore
                if await self.is_entity_on(e):
                    return True
            return False
        else:
            if h.is_string(entity_id):
                return await self.is_entity_on(entity_id)  # type: ignore
            else:
                return False

    async def get_okno_otevrene_delay(self) -> bool:
        # Otevreno - senzor znamena on
        entity_id = self.get_param_entity(HEAT_PAR.WINDOWS)
        if entity_id is None:
            return False
        if h.is_iterable(entity_id):
            for e in entity_id:  # type: ignore
                if (
                    await self.is_entity_on(e)
                    and await dt.get_changed_diff_sec(self._ba, e) > 2 * 60
                ):
                    return True
            return False
        else:
            if h.is_string(entity_id):
                return await self.is_entity_on(entity_id)  # type: ignore
            else:
                return False

    @property
    def _valve_max(self) -> bool:
        entity_id = self.get_param_entity(HEAT_PAR.VALVE_MAX)
        return (
            self.sync_is_entity_on(entity_id) if isinstance(entity_id, str) else False
        )

    def _sync_set_valve_max_stat(self):
        value: bool = self.operating_mode == VALVE_OPERATION.MAX
        entity_id = self.get_param_entity(HEAT_PAR.VALVE_MAX)
        if isinstance(entity_id, str):
            self._ba.sync_turn(entity_id, value)
            self.debug(f"(DI) Max for: {entity_id} {value} {h.on_off(value)}")
            self.sync_update_sensor_stat((STAT_ATTR.is_max, h.on_off(value)))

    async def _set_valve_max(self):
        value: bool = self.operating_mode == VALVE_OPERATION.MAX
        entity_id = self.get_param_entity(HEAT_PAR.VALVE_MAX)
        if isinstance(entity_id, str):
            self._ba.sync_turn(entity_id, value)
            self.debug(f"(DI) Max for: {entity_id} {value} {h.on_off(value)}")
            await self.update_sensor_stat((STAT_ATTR.is_max, h.on_off(value)))

    async def button_changed(self, entity, attribute, old, new, kwargs):
        self.info("Button changed")
        if h.getting_off_on(old, new):
            self.aktivni = h.yes(new)  # to speed up
            await self.put_in_queue(VALVE_OPERATION.UPDATE_STATE_IMMEDIATELY)
            """
            await self.fire_event(
                EVNT_DI.VALVE_UPDATE_MAIN_LOOP.value, instance=self.buffer_instance_name
            )
            """

    async def get_aktivni(self) -> bool:
        retval: bool = False
        if self.has_ha_control:
            retval = await self.is_entity_on(self.control_entity)
        return retval

    @property
    def zavrena_okna(self) -> bool:
        return not self.okno_otevrene_delay

    async def get_target_temperature(self) -> float:
        sensor = self.params.get(HEAT_PAR.TARGET_TEMPERATURE)
        if sensor is None:
            self.debug(f"Has no target_temperature {self.params}")
            return 0.0
        retval = await self._ba.get_state_float(sensor)
        self.debug(f"Target {self.entity_id} {sensor} {retval}")
        return retval

    @property
    def operating_mode(self) -> VALVE_OPERATION:
        return self._operating_mode

    def sync_update_operating_mode(self, value: Union[int, float]):
        oper_mode: int = 0
        if isinstance(value, str) or isinstance(value, float):
            oper_mode = int(value)
        elif isinstance(value, int):
            oper_mode = value
        if oper_mode != self._value:
            self._value = oper_mode
            self._operating_mode = self.get_operating_mode(oper_mode)
            self.state_changed = True
        self._sync_set_valve_max_stat()

    async def update_operating_mode(self, value: Union[int, float]):
        oper_mode: int = 0
        if isinstance(value, str) or isinstance(value, float):
            oper_mode = int(value)
        elif isinstance(value, int):
            oper_mode = value
        if oper_mode != self._value:
            self._value = oper_mode
            self._operating_mode = self.get_operating_mode(oper_mode)
            self.state_changed = True
        await self._set_valve_max()

    @abstractmethod
    def get_operating_mode(self, oper_mode: Union[int, float]) -> VALVE_OPERATION:
        ...

    @abstractmethod
    async def async_setup(self):
        ...

    def get_param_entity(self, param) -> VentilParamType:
        return self.params.get(param)

    async def update_attributes(self) -> None:
        self.temperature = await self._ba.get_state_int(self.sensor_temperature)
        self.battery_status = await self.get_battery_status()
        self.target_temperature = await self.get_target_temperature()
        self.kotel_bezi = await self.is_entity_on(SWITCH_KOTEL)
        self.aktivni = await self.get_aktivni()
        self.okno_otevrene_delay = await self.get_okno_otevrene_delay()
        self.okno_otevrene = await self.get_okno_otevrene()
        self.is_chilly: bool = (
            self.temperature < self.target_temperature and self.temperature > 0
        )
        """
        if (
            is_chilly != self.is_chilly
            and abs(self.target_temperature - self.temperature) > 1
            and not is_chilly
        ):
            self.is_chilly = is_chilly

        await self._ba.turn(
            self.params[HEAT_PAR.IB_WINDOWS_OPENED], self.okno_otevrene_delay
        )
        """

        self.heating_manually = await self.is_entity_on(TOPENI_RUCNE)

        def get_minutes(seconds):
            return int(seconds / 60)

        attr: dict = {
            STAT_ATTR.battery_level: self.battery_status,
            STAT_ATTR.temperature: self.temperature,
            STAT_ATTR.battery_level: self.battery_status,
            STAT_ATTR.temperature: self.temperature,
            STAT_ATTR.active: h.on_off(self.aktivni),
            STAT_ATTR.windows_open: h.on_off(self.okno_otevrene),
            STAT_ATTR.windows_open_delay: h.on_off(self.okno_otevrene_delay),
            STAT_ATTR.is_chilly: h.vrat_on_off(self.is_chilly),
            STAT_ATTR.is_max: ON if self.operating_mode == VALVE_OPERATION.MAX else OFF,
            STAT_ATTR.target_temp: self.target_temperature,
            STAT_ATTR.dead: h.vrat_on_off(self.dead),
            STAT_ATTR.setpoint: self.setpoint,
            STAT_ATTR.device_id: self.device_id,
            STAT_ATTR.name_id: self.name_id,
            STAT_ATTR.last_operation_change: get_minutes(self.get_last_oper_change()),
            STAT_ATTR.last_target_reached: get_minutes(self.get_last_target_reached()),
        }

        await self.update_sensor_stat(attr)

    @property
    def let_boiler_on(self) -> bool:
        exclude = self.get_param_entity(HEAT_PAR.EXCLUDE_BOILER)
        retval: BoolType = None
        self.debug(f"Exclude boiler: {exclude} v {self}")
        if isinstance(exclude, bool):
            if exclude:
                retval = False

        if retval is None:
            retval = False
            if self.aktivni and self.zavrena_okna:
                retval = self.is_chilly
        self.debug(f"Boiler on: {retval} for: {self}")

        return retval

    @abstractmethod
    async def get_battery_status(self) -> int:
        ...

    async def valve_update_state(self) -> None:
        # Nema vubec tlacitko na ovladani nebo se ovlada rucne
        self.info(f"(DI) valve_update_state for {self}")
        self.debug(self.dead)

        await self.update_attributes()
        operation = await self.suggest_operation()
        self.debug(
            f"Checking setting {self.name_id} current:{self.operating_mode} suggested: {operation}"
        )
        if operation != self.operating_mode:
            self.debug(f"Calling operation mode for: {self.device_id}")
            await self.fire_event(
                VALVE_OPERATION.SET_OPERATING_MODE.value,
                device_id=self.device_id,
                operation=operation.value,
            )
            """
            nefunguje!
            await self._ba.run_in_executor(
                self.parent.set_operation_mode, self.device_id, operation
            )
            """
        else:
            self.debug("Nothing to do")

    async def kontrola(self):
        pass

    def get_last_oper_change(self):
        """Return time in seconds from last changing of operation mode

        Returns:
            [type]: [description]
        """
        dif = dt.just_now_sec() - self.last_changed_operation_state
        self.debug(f"------------------------dif: {self.name_id} {dif}")
        return dif

    def get_last_target_reached(self):
        """Return time in seconds from last changing of operation mode

        Returns:
            [type]: [description]
        """
        dif = dt.just_now_sec() - self.target_reached
        self.debug(f"Target reached: {self.name_id} {dif}")
        return dif

    async def suggest_operation(self) -> VALVE_OPERATION:
        suggest: VALVE_OPERATION = VALVE_OPERATION.NO_CHANGE
        if self.heating_manually:
            suggest = VALVE_OPERATION.MAX if self.aktivni else VALVE_OPERATION.MIN
        elif self.has_ha_control:
            await self.update_operating_mode(self.setpoint)

            suggest = (
                VALVE_OPERATION.MAX
                if self.is_chilly and self.aktivni and self.zavrena_okna
                else VALVE_OPERATION.MIN
            )
        suggest = (
            VALVE_OPERATION.NO_CHANGE if self.operating_mode == suggest else suggest
        )

        if not suggest in (VALVE_OPERATION.MAX, VALVE_OPERATION.MIN):
            return suggest

        if suggest == VALVE_OPERATION.MIN and not self.is_chilly:
            self.target_reached = dt.just_now_sec()

        if (
            suggest == VALVE_OPERATION.MAX
            and self.get_last_target_reached() < 60 * 60
            and abs(self.temperature - self.target_temperature) < 2
        ):
            return VALVE_OPERATION.NO_CHANGE
        if self.get_last_oper_change() < LIMIT_FOR_SWITCH_MODE:
            return VALVE_OPERATION.NO_CHANGE
        return suggest

    async def put_in_queue(self, task_arg: Enum, arg: DictType = None):
        self.debug(f"Putting in queue: {task_arg} arg: {arg}")
        await self._ba.put_in_queue(  # type: ignore
            task_arg,
            arg,
            instance_name=self.buffer_instance_name,
        )

    async def put_in_queue_value(
        self, task_arg: Enum, value: Enum, device_id: StrType = None
    ):
        if device_id is None:
            device_id = self.device_id
        self.debug(
            f"Putting in queue value, device_id: {device_id} buffer_instance: {self.buffer_instance_name}, value: {value}"
        )
        await self.put_in_queue(task_arg, arg=dict(device_id=device_id, value=value))

    async def set_param_state(self, param, value):
        entity_id: VentilParamType = self.get_param_entity(param)
        if isinstance(entity_id, str):
            if await self._ba.entity_exists(entity_id):
                await self._ba.turn(entity_id, value)

    async def get_param_state(self, param) -> bool:
        entity_id: VentilParamType = self.get_param_entity(param)

        if isinstance(entity_id, str):
            return await self.is_entity_on(entity_id)
        else:
            return False


class VentilEntity(VentilABC, ApiEntityABC):
    ...


VentilEntityList = List[VentilEntity]
VentilEntityListType = Union[VentilEntityList, None]
VentilEntityType = Union[VentilEntity, None]


class VentilRegister(DeviceRegister):
    @staticmethod
    def get_interface_entities(interface_type: INTERFACE_TYPE):
        retval = DeviceRegister.get_interface_entities(interface_type)
        return retval


class ValveRegister(DeviceRegister):
    @staticmethod
    def entities() -> VentilEntityList:

        retval = [
            entity
            for entity in DeviceRegister.entities
            if isinstance(entity, VentilABC)
        ]
        return retval  # type:ignore


VentilABCType = Union[VentilABC, None]
