from abc import abstractmethod
from basic_app_sensors import AppApfSensors
from buffer_control import BufferInterface
from decorators import apf_logger, overrides
from devices_interface import (
    INTERFACE_TYPE,
    VALVE_OPERATION,
    VALVE_OPERATION_TYPE,
    DeviceRegister,
    VentilABC,
)
from helper_types import StrType
from task_register import TaskCoro, TaskLoop

LOOP_UPDATE = 30


class ValveClass(AppApfSensors, BufferInterface):
    def initialize(self):
        self.interface: INTERFACE_TYPE = INTERFACE_TYPE.UNKNOWN
        super().initialize()

    @apf_logger
    def init(self):
        self.debug("Valve Class")
        if self.interface == INTERFACE_TYPE.UNKNOWN:
            raise ValueError(
                "Not initialized self.interface! Must be before calling init."
            )

        self.register_task(
            TaskCoro(
                self,
                reg_name=VALVE_OPERATION.UPDATE_STATE_IMMEDIATELY,
                coro=self.update_state,
            )
        )

        self.register_task(
            TaskLoop(
                self,
                reg_name=VALVE_OPERATION.UPDATE_STATE,
                coro=self.update_state,
                loop_start_automaticaly=True,
                frequence=LOOP_UPDATE,
            )
        )

    @overrides(AppApfSensors)
    async def async_setup(self):
        await self.start_tasks_buffer()
        await self.put_in_queue(VALVE_OPERATION.UPDATE_STATE)
        await self.listen_event(
            self._event_set_operating_mode, VALVE_OPERATION.SET_OPERATING_MODE.value
        )

    async def update_state(self) -> bool:
        try:
            self.info("_ventily_update")
            register = DeviceRegister.get_interface_entities(self.interface)
            if len(register) == 0:
                self.warning("Nothing registered")
                return False
            self.debug(f"Valve update. Len register: {len(register)}")
            """
            _read_state: ListApiEntity = []            
            for ventil_def in register:
                if isinstance(ventil_def, HoneywellVentil):
                    self.debug(ventil_def)
                    await ventil_def.update_attributes()
                    suggest = ventil_def.suggest_operation()
                    if suggest in (VALVE_OPERATION.MAX, VALVE_OPERATION.MIN):
                        _read_state.append(ventil_def)
            if len(_read_state) > 0:
                await self.run_in_executor(self.read_state)
                for ventil_def in _read_state:
                    if isinstance(ventil_def, HoneywellVentil):
                        await ventil_def.nastav_dle_tlacitka()
            """
            for ventil_def in register:
                if isinstance(ventil_def, VentilABC):
                    self.debug(f"valve_update_state for: {ventil_def}")
                    await ventil_def.valve_update_state()

        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
        return True

    def _event_set_operating_mode(self, event, data, kwargs):
        device_id: StrType = data.get("device_id")
        valve_operation_value: StrType = data.get("operation")
        self.debug(
            f"Received event for: {device_id} operation: {valve_operation_value}"
        )
        if device_id is None or valve_operation_value is None:
            return
        else:
            if valve_operation_value == VALVE_OPERATION.MAX.value:
                self.set_operation_mode(device_id, VALVE_OPERATION.MAX)
            elif valve_operation_value == VALVE_OPERATION.MIN.value:
                self.set_operation_mode(device_id, VALVE_OPERATION.MIN)

    @abstractmethod
    def set_operation_mode(self, device_id: str, valve_operation: VALVE_OPERATION):
        ...
