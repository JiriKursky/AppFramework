###########################################
# From Honeywell:
# The limit is 400 hits per hour I believe and that depends on the number of zones you have.
# It is suggested to set the system to perform changes no often than 15 minutes in between.
###########################################
LIMIT_PER_HOUR = 300

from dataclasses import dataclass, field
import datetime
import time
from typing import List, Union
from apd_types import APBAsicAppSensors
from devices_interface import (
    HEAT_PAR,
    INTERFACE_TYPE,
    VALVE_OPERATION,
    ApiEntityABC,
    DeviceRegister,
    VentilABC,
)
from evohome_comm.controlsystem import ControlSystem
from evohome_comm.zone import Zone

from global_honeywell import (
    HONEYWELL_COMM_INSTANCE,
    SENSOR_HONEY_INFO,
    SENSOR_REQ,
    TEMP_OPERATION_MAX,
    TEMP_OPERATION_MIN,
    HoneywellTaskName,
)
from basic_app_sensors import AppApfSensors
from buffer_control import BufferInterface
from decorators import apf_logger, overrides
from helper_tools import DateTimeOp as dt
from evohome_comm import EvohomeClient


from helper_types import DateTime, IntType, StrType
from private import Private
from task_register import TaskCoro
from topeni_helpers import TopeniHelpers
from valve_interface import ValveClass


@dataclass
class Temperature:
    thermostat: str = field(default="")
    id: str = field(default="")
    name: str = field(default="")
    temp: float = field(default=0)
    setpoint: float = field(default=0)


TemperatureType = Union[Temperature, None]

ZoneType = Union[Zone, None]


@dataclass
class HoneywellVentil(VentilABC):
    zone_id: str = field(default="")
    temp: float = field(default=0)
    zone_def: ZoneType = None
    sent_post: VALVE_OPERATION = VALVE_OPERATION.NO_CHANGE

    def __post_init__(self):
        super().__post_init__()
        self.sent_post = VALVE_OPERATION.UNKNOWN
        params = TopeniHelpers.get_params(self.device_id, HEAT_PAR.DEVICE_ID)
        if isinstance(params, dict):
            self.params = params
        else:
            self.error(f"Wrong definition params for {self.device_id}")
        self.buffer_instance_name = HONEYWELL_COMM_INSTANCE
        self.entity_id = self.name_id.replace(" ", "_")
        self.module_name = "Honeywell Ventil"
        VentilABC.init(self)

    async def async_setup(self):
        self.debug("async_setup")
        await self.update_attributes()

    async def update_attributes(self) -> None:
        await self.update_operating_mode(self.setpoint)
        await super().update_attributes()
        asked: str = "-"
        if self.sent_post == VALVE_OPERATION.MAX:
            asked = "max"
        elif self.sent_post == VALVE_OPERATION.MAX:
            asked = "min"

        await self.update_sensor_stat({"asked": asked})

    def get_operating_mode(self, oper_mode: Union[int, float]) -> VALVE_OPERATION:
        if isinstance(oper_mode, float):
            oper_mode = int(oper_mode)
        """Translating

        Args:
            oper_mode (int): [description]

        Returns:
            VALVE_OPERATION: [description]
        """
        if oper_mode < TEMP_OPERATION_MIN + 5:
            return VALVE_OPERATION.MIN
        elif oper_mode > TEMP_OPERATION_MAX - 5:
            return VALVE_OPERATION.MAX
        else:
            return VALVE_OPERATION.UNKNOWN

    async def get_battery_status(self) -> int:
        sensor_battery = self.get_param_entity(HEAT_PAR.SENSOR_BATTERY)
        await self._ba.set_state(sensor_battery, state=0)
        return 0

    @classmethod
    def set_values(cls, parent: APBAsicAppSensors, temperature: Temperature):
        return cls(
            _ba=parent,
            params={
                HEAT_PAR.NAME_ID: temperature.name,
                HEAT_PAR.INTERFACE: INTERFACE_TYPE.HONEYWELL,
            },
            name_id=temperature.name,
            zone_id=temperature.id,
            device_id=temperature.id,
            temp=temperature.temp,
            setpoint=temperature.setpoint,
            interface=INTERFACE_TYPE.HONEYWELL,
            asking_attempt=0,
        )

    def __repr__(self):
        rep: str = f"(HW) {self.name_id} - temp: {self.temp}, setpoint: {self.setpoint}, interface: {self.interface}"
        rep += f"  operating_mode: {self.operating_mode} buffer instance {self.buffer_instance_name}"
        return rep


HoneywellVentilType = Union[HoneywellVentil, None]
HoneyWellVentilList = List[HoneywellVentil]
TemperatureList = List[Temperature]
EvohomeClientType = Union[EvohomeClient, None]

LOOP_UPDATE = 60


class HoneywellComm(ValveClass):
    def initialize(self):
        super().initialize()
        self.interface: INTERFACE_TYPE = INTERFACE_TYPE.HONEYWELL

    @apf_logger
    def init(self):
        self.debug("Honeywell start")
        self.sync_publish_info("Starting init")
        self.time_counter: list[DateTime] = []
        self.counter_start_number: int = 0
        secrets: Private = Private()
        username: StrType = secrets.get_secret("honeywell_username")
        password: StrType = secrets.get_secret("honeywell_password")
        self.fatal_error: bool = False
        if username is None or password is None:
            self.error(
                "Missing credentials in secret file. honeywell_username='xxx', honeywell_password='xxx'"
            )
            self.fatal_error = True
            return

        self.client: EvohomeClient = EvohomeClient(username=username, password=password)
        BufferInterface.init(self, HONEYWELL_COMM_INSTANCE)
        self.initialize_amount: int = 0

        super().init()

        self.register_task(
            TaskCoro(
                self,
                reg_name=HoneywellTaskName.AUTHORIZE,
                coro=self._authorize,
            )
        )
        self.register_task(
            TaskCoro(
                self,
                reg_name=HoneywellTaskName.INITIALIZE,
                coro=self._initialize,
            )
        )

        self.ventily_count: int = len(
            TopeniHelpers.get_ventils_params_interface(
                interface=INTERFACE_TYPE.HONEYWELL
            )
        )
        self.last_temperatures: TemperatureList = []
        self.sync_publish_info("Init done")

    def sync_publish_info(self, msg):
        self.sync_set_state(SENSOR_HONEY_INFO, state=msg)

    async def publish_info(self, msg):
        await self.set_state(SENSOR_HONEY_INFO, state=msg)

    def terminate(self):
        self.sync_publish_info("Terminated")
        self.debug("should logout")

    @overrides(AppApfSensors)
    async def async_setup(self):
        await super().async_setup()
        # await self.start_tasks_buffer()
        await self.put_in_queue(HoneywellTaskName.AUTHORIZE)
        await self.put_in_queue(VALVE_OPERATION.UPDATE_STATE)

    def set_sensor_temperature(self, ventil: HoneywellVentil, temperature: Temperature):
        ventil.temp = temperature.temp
        if not ventil.sensor_temperature_ext:
            self.debug(
                f"Setting temperature to {ventil.sensor_temperature} {ventil.temp}"
            )
            self.sync_set_sensor_state(ventil.sensor_temperature, ventil.temp)

    def read_state(self):
        self.info("Honeywell is asking for state")
        for temperature in self.temperatures:  # Honeywell cloud
            ventil = DeviceRegister.get_entity(
                device_id=temperature.id, interface=INTERFACE_TYPE.HONEYWELL
            )
            if ventil is None:
                self.warning(f"Not found temp {temperature.id}")
                continue
            if isinstance(ventil, HoneywellVentil):
                self.debug(f"Collected data : {temperature}")
                self.set_sensor_temperature(ventil, temperature)
                ventil.setpoint = temperature.setpoint
                if ventil.sent_post == VALVE_OPERATION.UNKNOWN:
                    ventil.sync_update_operating_mode(temperature.setpoint)
                else:
                    new_operating_mode = ventil.get_operating_mode(
                        int(temperature.setpoint)
                    )
                    if new_operating_mode == ventil.sent_post:
                        self.debug(
                            f"I have what asked for changing for valve: {ventil.name_id}"
                        )
                        ventil.last_changed_operation_state = dt.just_now_sec()
                        ventil.asking_attempt = 0
                        ventil.sent_post = VALVE_OPERATION.UNKNOWN
                        ventil.sync_update_operating_mode(temperature.setpoint)
                    else:
                        self.warning(
                            f"Asked for ({ventil.asking_attempt}): {ventil.name_id} sent: {ventil.sent_post} received: {new_operating_mode}, nothing happened"
                        )
                        ventil.asking_attempt += 1
                        if ventil.asking_attempt > 5:
                            self.warning(">>>>> Fixing ask <<<")
                            self.fix_operation_mode(ventil)

                        if ventil.asking_attempt > 10:
                            ventil.sent_post = VALVE_OPERATION.UNKNOWN
                            ventil.last_changed_operation_state = dt.just_now_sec()
                            ventil.asking_attempt = 0
                            ventil._sync_set_valve_max_stat()

                self.info(ventil)
            else:
                self.error(f"Unknown instance: {type(ventil)} {ventil}")

    def _update_req_sensor(self) -> bool:
        self.time_counter.append(dt.just_now())
        count = len(self.time_counter) + self.counter_start_number
        self.sync_set_state(SENSOR_REQ, state=count)
        #
        return True

    @property
    def honeywell_register(self):
        return DeviceRegister.get_interface_entities(INTERFACE_TYPE.HONEYWELL)

    @property
    def temperatures(self) -> TemperatureList:
        if not self.client_ok():
            self.error("Client is not defined")
            self.sync_publish_info("Problems with client")
            return []
        try:
            self.last_temperatures = [
                Temperature(**a) for a in self.client.temperatures()
            ]
            if not self._update_req_sensor():
                self.error("Overflow request for Honeywell API")
                return self.last_temperatures

            attr: dict = {}
            for temp in self.last_temperatures:
                attr.update({temp.id: temp.name})
                self.debug(temp)
            self.sync_set_sensor_state(SENSOR_HONEY_INFO, "Everything ok", attr)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Error honeywell")
        return self.last_temperatures

    def get_zone_def(self, ventil: HoneywellVentil) -> ZoneType:
        if ventil.zone_def is not None:
            return ventil.zone_def
        if self.client is None:
            return None
        control_system: Union[
            ControlSystem, None
        ] = self.client._get_single_heating_system()
        if control_system is None:
            return None
        ventil.zone_def = control_system.zones_by_id.get(ventil.device_id)
        return ventil.zone_def

    def get_temperature(self, valve_operation: VALVE_OPERATION) -> IntType:
        if valve_operation == VALVE_OPERATION.MAX:
            return TEMP_OPERATION_MAX
        elif valve_operation == VALVE_OPERATION.MIN:
            return TEMP_OPERATION_MIN
        return None

    def set_operation_mode(self, device_id: str, valve_operation: VALVE_OPERATION):
        self.debug(
            f"Setting operation mode for {device_id} valve operation: {valve_operation}"
        )
        ventil = DeviceRegister.get_entity(
            device_id=device_id, interface=INTERFACE_TYPE.HONEYWELL
        )
        if not isinstance(ventil, HoneywellVentil):
            self.debug(f"This is not belong to Honeywell")
            return

        zone_def: ZoneType = self.get_zone_def(ventil)
        if zone_def is None:
            return
        self.info(
            f"Checking operation mode device_id :{device_id} valve operation: {valve_operation}"
        )

        try:
            if isinstance(ventil, HoneywellVentil):
                if ventil.sent_post != VALVE_OPERATION.UNKNOWN:
                    self.debug(f"Waiting for changing {ventil.name_id}")
                    return
                temperature: IntType = None
                if valve_operation != ventil.operating_mode:
                    temperature = self.get_temperature(valve_operation)

                    self.info(
                        f"Setting {valve_operation} with temperature  {temperature} for device_id: {ventil.name_id}"
                    )
                    if temperature is not None:
                        zone_def.set_temperature(temperature)
                        ventil.sent_post = valve_operation

            else:
                self.error(f"Not found temp {device_id}")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Error honeywell")

    def fix_operation_mode(self, ventil: HoneywellVentil):
        self.debug(">>>>>>>>>>>>>> fix <<<<<<<<<<<<<<")
        zone_def: ZoneType = self.get_zone_def(ventil)
        until = dt.just_now() + datetime.timedelta(hours=2)
        if zone_def is None:
            return
        data = {
            "SetpointMode": "TemporaryOverride",
            "TimeUntil": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.debug(data)
        zone_def.set_temperature(20, until)
        self.debug("sleeping 20 secs")
        time.sleep(20)
        teplota: IntType = self.get_temperature(ventil.sent_post)
        if teplota is not None:
            self.debug("Setting temperature")
            zone_def.set_temperature(teplota)

    async def _authorize(self):
        if self.fatal_error:
            return
        self.info("Authorize")
        await self.publish_info("Authorization process")
        if self.client_ok():
            self.debug("client is ok")
            await self.publish_info("Authorization ok. Waiting for initialize...")
            return

        if self.ventily_count == 0:
            self.debug("Nothing registered for Honeywell")
            return

        try:
            if self.client.account_info is None:
                self.debug("Client login")
                await self.run_in_executor(self.client.login)
            self.debug(f"Account info: {self.client.account_info}")
            await self.run_in_executor(self.client.installation)
            if self.client_ok():
                self.info("Authorized initialize honeywell valves")
                self.initialize_amount = 0
                await self.run_in_executor(self.client.set_status_custom)
                await self.publish_info("Authorization ok.")
                await self.put_in_queue(HoneywellTaskName.INITIALIZE)
            else:
                self.initialize_amount += 1
                if self.initialize_amount > 3:
                    await self.sleep(5 * 60)
                if self.initialize_amount > 10:
                    self.fatal_error = True
                    await self.publish_info("Authorization fatal error")
                    return
                await self.publish_info("Authorization not success, will try later")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            self.error(f"Nepodarilo se autorizace account: {self.client.account_info}")

    def _initialize(self):
        """During initialize - registering

        Raises:
            ValueError: [description]
        """
        if self.fatal_error:
            return
        honeywell_info: list = []
        # first defining of honeywell valves
        self.debug("initialize")
        self.sync_publish_info("Initialization")
        try:
            for temperature in self.temperatures:
                self.warning(temperature)
                params = TopeniHelpers.get_params(temperature.id, HEAT_PAR.DEVICE_ID)
                if isinstance(params, dict):
                    # Here is direct
                    honey_ventil = HoneywellVentil.set_values(
                        parent=self, temperature=temperature
                    )
                    self.debug("* Appending ventil" * 50)
                    self.debug(honey_ventil)
                    self.set_sensor_temperature(honey_ventil, temperature)
                    honeywell_info.append(honey_ventil)

            if len(honeywell_info) == 0:
                self.initialize_amount += 1
                if self.initialize_amount > 10:
                    self.error("It is not possible to initialize")
                    self.sync_publish_info("Fatal error during initialize")
                    self.fatal_error = True
                    return
                self.sync_publish_info("Initialization with error, will try later")
                return

            self.initialize_amount = 0
            # in global_topeni missing Honeywell
            everything_ok: bool = True
            for ventil_def in honeywell_info:
                if isinstance(ventil_def, ApiEntityABC):
                    params = TopeniHelpers.get_params(
                        ventil_def.device_id, HEAT_PAR.DEVICE_ID
                    )
                    if params is None:
                        self.warning(
                            f"No ID for {ventil_def.name_id} {ventil_def.device_id}"
                        )
                        continue
                    else:
                        self.debug(f"Ventil params: {params}")

                    if isinstance(ventil_def, VentilABC):
                        self.debug(f"HoneyVentil ventil: {ventil_def}")
                        try:
                            DeviceRegister.register(self, ventil_def)
                        except:
                            everything_ok = False
                            self.error(f"Not possible to register {ventil_def}")
                            self.sync_publish_info(
                                f"Problems with {ventil_def}. Stopped"
                            )
                            return
            if everything_ok:
                self.sync_put_in_queue(
                    VALVE_OPERATION.UPDATE_STATE_IMMEDIATELY,
                    instance_name=HONEYWELL_COMM_INSTANCE,
                )
            else:
                self.error("Something went wrong")
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in module")

    async def update_state(self):
        if self.ventily_count == 0:
            self.debug("No definition")
            await self.publish_info("No definition of valves")
            return
        if self.client_ok():
            register = DeviceRegister.get_interface_entities(INTERFACE_TYPE.HONEYWELL)
            self.debug(f"Registered: {len(register)}, defined: {self.ventily_count}")
            if len(register) < self.ventily_count:
                self.debug("Wrong number asking for state")
                self.initialize_amount += 1
                if self.initialize_amount > 2:
                    await self.sleep(3)
                if self.initialize_amount > 10:
                    self.error("Something wrong in defined and registered entities")
                    self.fatal_error = True
                    return
                await self.put_in_queue(HoneywellTaskName.INITIALIZE)
            else:
                ### Core ####
                self.debug("Everything ok")
                self.initialize_amount = 0
                await self.publish_info("Everything ok")
                await self.run_in_executor(self.read_state)
                await super().update_state()
        else:
            self.debug("Client is not ok")
            await self.put_in_queue(HoneywellTaskName.AUTHORIZE)

    def client_ok(self) -> bool:
        if self.fatal_error:
            return False
        if isinstance(self.client, EvohomeClient):
            if self.client.locations is None or self.client.account_info is None:
                return False
            else:
                return len(self.client.locations) > 0
        else:
            return False
