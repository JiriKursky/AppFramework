# For listening event

# async def _event(self, event, data, kwargs):

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import hassapi as hass  # type:ignore
from typing import Any, Callable, Dict, List, Tuple, Union


from helper_types import (
    BoolType,
    CoroutineDefaultType,
    DictMixed,
    DictType,
    EntityName,
    EnumType,
    StateQuestionType,
    StrType,
    TupleType,
)


class HandlerCreateTask(ABC):
    @abstractmethod
    def cancel(self):
        ...


HandlerCreateTaskType = Union[HandlerCreateTask, None]


class FutureTask(ABC):
    @abstractmethod
    def cancel(self):
        ...


@dataclass
class EntityObjectABC(ABC):
    id: str = field(default="")


class SensorsABC(ABC):
    @abstractmethod
    async def binary_sensor(self, entity_id: str, default: BoolType = None) -> Any:
        ...

    @abstractmethod
    def register_sensor(self, sensor: Any):
        ...

    @abstractmethod
    async def temperature_sensor(self, entity_id: str) -> Any:
        ...

    def sync_temperature_sensor(self, entity_id: str) -> Any:
        return self.temperature_sensor(entity_id)

    @abstractmethod
    def time_sensor(self, entity_id: str) -> Any:
        ...

    def sync_time_sensor(self, entity_id: str) -> Any:
        return time_sensor(entity_id)  # type: ignore

    @abstractmethod
    def sync_update_timestamp(self, entity_id) -> bool:
        ...

    @abstractmethod
    async def update_timestamp(self, entity_id) -> bool:
        ...

    @abstractmethod
    async def state_sensor(self, entity_id: str, default: StrType = None) -> Any:
        ...

    @abstractmethod
    async def get_obj(self, entity_id: str) -> Any:
        ...


SensorsType = Union[SensorsABC, None]


class ApDefBase(ABC):
    args: dict = {}

    @abstractmethod
    def initialize(self):
        self.init_done: bool = False

    @abstractmethod
    def debug(self, msg):
        ...

    @abstractmethod
    async def turn_on(self, entity_id, **kwargs):
        ...

    @abstractmethod
    async def run_in_executor(self, func, *args, **kwargs):
        ...

    @abstractmethod
    def info(self, msg):
        ...

    @abstractmethod
    def warning(self, msg):
        ...

    @abstractmethod
    def error(self, msg):
        ...

    @abstractmethod
    async def get_app(self, name):
        ...

    async def async_get_app(self, name):
        app = await self.get_app(name)  # type: ignore
        assert app is not None, f"Not found get_app {name}"
        return app

    def sync_get_app(self, name) -> Any:
        app = self.get_app(name)
        assert app is not None, f"Not found get_app {name}"
        return app

    @abstractmethod
    async def listen_event(self, callback, event=None, **kwargs):
        # listening:
        # async def _event(self, event, data, kwargs):
        ...

    @abstractmethod
    async def run_in(self, callback, delay, **kwargs):
        ...

    @abstractmethod
    async def restart_app(self, app):
        ...

    @abstractmethod
    async def create_task(self, coro, callback=None, **kwargs) -> HandlerCreateTask:
        ...

    def sync_create_task(self, coro, callback=None, **kwargs) -> FutureTask:
        return self.create_task(coro, callback, **kwargs)  # type: ignore

    @abstractmethod
    async def fire_event(self, event, **kwargs):
        ...

    def sync_fire_event(self, event, **kwargs):
        self.fire_event(event, **kwargs)  # type: ignore

    @abstractmethod
    async def sleep(self, delay):
        ...

    @abstractmethod
    async def cancel_listen_state(self, handle):
        pass

    async def cancel_listen_event(self, handle):
        pass

    def sync_cancel_listen_event(self, handle):
        self.cancel_listen_event(handle)  # type:ignore

    @abstractmethod
    async def get_state(
        self, entity_id=None, attribute=None, default=None, copy=True, **kwargs
    ) -> Union[str, dict, None]:
        ...

    def sync_get_state(
        self, entity_id=None, attribute=None, default=None, copy=True, **kwargs
    ) -> Union[str, dict, int, None]:
        return self.get_state(  # type: ignore
            entity_id=entity_id, attribute=attribute, copy=copy, **kwargs
        )

    @abstractmethod
    async def turn_off(self, entity_id, **kwargs):
        ...

    def sync_turn_on(self, entity_id, **kwargs):
        self.turn_on(entity_id, **kwargs)  # type:ignore

    def sync_turn_off(self, entity_id, **kwargs):
        self.turn_off(entity_id, **kwargs)  # type: ignore

    def sync_run_in(self, callback, delay, **kwargs):
        self.run_in(callback, delay, **kwargs)  # type:ignore

    def sync_run_in_executor(self, func, *args, **kwargs):
        self.run_in_executor(func, *args, **kwargs)  # type: ignore

    @abstractmethod
    async def entity_exists(self, entity_id, **kwargs) -> bool:
        ...

    def sync_entity_exists(self, entity_id, **kwargs) -> bool:
        return self.entity_exists(entity_id, **kwargs)  # type: ignore

    def sync_listen_event(self, callback, event=None, **kwargs):
        self.listen_event(callback=callback, event=event, **kwargs)  # type:ignore

    @abstractmethod
    async def set_state(self, entity, **kwargs):
        ...

    def sync_set_state(self, entity, **kwargs):
        self.set_state(entity, **kwargs)  # type: ignore

    @abstractmethod
    async def listen_state(self, callback, entity=None, **kwargs):
        #  async def _listener(self, entity, attribute, old, new, kwargs):
        ...

    def sync_listen_state(self, callback, entity=None, **kwargs):
        self.listen_state(callback, entity, **kwargs)  # type:ignore

    @abstractmethod
    async def call_service(self, service, **kwargs):
        ...

    def sync_call_service(self, service, **kwargs):
        self.call_service(service, **kwargs)  # type: ignore


class APBasicApp(ApDefBase):
    @abstractmethod
    async def now(self) -> int:
        ...

    @abstractmethod
    async def listen_on_off(self, callback: Any, entity_id: str) -> Any:
        ...

    @abstractmethod
    async def get_all_state(self, entity_id: str) -> DictType:
        ...

    @abstractmethod
    def sync_get_all_state(self, entity_id: str) -> DictType:
        ...

    def sync_fire_event(self, event, **kwargs):
        self.fire_event(event, **kwargs)  # type: ignore

    @abstractmethod
    async def toggle(self, entity_id: str) -> bool:
        ...

    @abstractmethod
    async def set_sensor_state(
        self, entity_id: EntityName, state: Any, attr: DictMixed = {}
    ):
        ...

    @abstractmethod
    def sync_set_sensor_state(
        self, entity_id: EntityName, state: Any, attr: DictMixed = {}
    ):
        ...

    @abstractmethod
    async def set_attributes(self, entity_id: str, attributes: dict) -> None:
        ...

    def sync_set_attributes(self, entity_id: str, attributes: dict) -> None:
        self.set_attributes(entity_id, attributes)  # type: ignore

    def sync_toggle(self, entity_id: str):
        self.toggle(entity_id)  # type: ignore

    @abstractmethod
    async def is_entity_on(self, entity_id: str) -> bool:
        ...

    @abstractmethod
    def sync_is_entity_on(self, entity_id: str) -> bool:
        ...

    async def is_entity_off(self, entity_id: str) -> bool:
        return not await self.is_entity_on(entity_id)

    def sync_is_entity_off(self, entity_id: str) -> bool:
        return not self.sync_is_entity_on(entity_id)

    @abstractmethod
    async def get_attr_state(self, entity_id: str, attr: str) -> str:
        ...

    def sync_get_attr_state(self, entity_id: str, attr: str) -> str:
        return self.get_attr_state(entity_id=entity_id, attr=attr)  # type:ignore

    @abstractmethod
    async def get_state_float(self, entity_id: str) -> float:
        ...

    @abstractmethod
    def sync_get_state_float(self, entity_id: str) -> float:
        ...

    @abstractmethod
    async def get_state_int(self, entity_id: str) -> int:
        ...

    @abstractmethod
    def sync_get_state_int(self, entity_id: str) -> int:
        ...

    @abstractmethod
    async def friendly_name(self, entity_id, **kwargs):
        ...

    def sync_friendly_name(self, entity_id, **kwargs):
        retval: Union[str, None] = self.friendly_name(entity_id, **kwargs)  # type: ignore
        return retval

    @abstractmethod
    async def turn(self, entity_id: str, yes: Any) -> BoolType:
        ...

    @abstractmethod
    def sync_turn(self, entity_id: str, yes: Any) -> BoolType:
        ...

    async def scene_turn_on(self, entity_id: str) -> None:
        await self.call_service("scene/turn_on", entity_id=entity_id)

    def sync_scene_turn_on(self, entity_id: str) -> None:
        self.sync_call_service("scene/turn_on", entity_id=entity_id)

    @abstractmethod
    async def get_attr_state_float(self, entity_id: str, attr: str) -> float:
        ...

    @abstractmethod
    def sync_get_attr_state_float(self, entity_id: str, attr: str) -> float:
        ...

    async def get_attr_state_int(self, entity_id: str, attr: str) -> int:
        return int(await self.get_attr_state_float(entity_id, attr))

    def sync_get_attr_state_int(self, entity_id: str, attr: str) -> int:
        return int(self.sync_get_attr_state_float(entity_id, attr))

    @abstractmethod
    async def split_entity(self, entity_id, **kwargs):
        ...

    async def cancel_timer(self, handle):
        ...

    def sync_cancel_timer(self, handle):
        self.cancel_timer(handle)  # type: ignore

    async def listen_on(self, def_proc: Any, entity_id: str = None):
        ...


class APBAsicAppSensors(APBasicApp):
    @abstractmethod
    def activate_sensors(self) -> Any:
        """Activate (get_app) sensors module, can be used repeately

        Returns:
            Any: [description]
        """
        ...

    @property
    @abstractmethod
    def sensors(self) -> SensorsABC:
        ...

    @abstractmethod
    async def init_sensors(self):
        ...


@dataclass
class ChildObject:
    _ba: ApDefBase = None  # type: ignore
    module_name: str = field(default="")
    global_vars: dict = field(default_factory=dict)

    def __post_init__(self):
        try:
            self.global_vars = self._ba.global_vars  # type: ignore
        except:
            raise ValueError("Chyba")
        if self.module_name == "":
            self.module_name = self._ba.__class__.__name__

    def debug(self, msg):
        self._ba.debug(f"({self.module_name}) {msg}")

    def info(self, msg):
        self._ba.info(f"({self.module_name}) {msg}")

    def warning(self, msg):
        self._ba.warning(f"({self.module_name}) {msg}")

    def error(self, msg):
        self._ba.error(f"({self.module_name}) {msg}")

    async def create_task(self, coro, callback=None, **kwargs) -> HandlerCreateTask:
        return await self._ba.create_task(coro, callback, **kwargs)

    async def sleep(self, delay):
        await self._ba.sleep(delay)

    async def fire_event(self, event, **kwargs):
        await self._ba.fire_event(event, **kwargs)

    def sync_fire_event(self, event, **kwargs):
        self._ba.sync_fire_event(event, **kwargs)

    def sync_listen_event(self, callback, event=None, **kwargs):
        self._ba.sync_listen_event(callback=callback, event=event, **kwargs)

    def sync_listen_state(self, callback, entity=None, **kwargs):
        self._ba.sync_listen_state(callback, entity, **kwargs)

    def sync_run_in_executor(self, func, *args, **kwargs):
        self._ba.sync_run_in_executor(func, *args, **kwargs)


@dataclass
class ChildObjectBasicApp(ChildObject):
    _ba: APBAsicAppSensors = None  # type:ignore

    def sync_is_entity_on(self, entity_id: str) -> bool:
        return self._ba.sync_is_entity_on(entity_id=entity_id)

    async def is_entity_on(self, entity_id: str) -> bool:
        return await self._ba.is_entity_on(entity_id=entity_id)

    def sync_get_attr_state(self, entity_id: EntityName, attr: str) -> str:
        return self._ba.sync_get_attr_state(entity_id, attr)

    def sync_set_sensor_state(self, entity_id: EntityName, state: Any, attr: DictMixed):
        self._ba.sync_set_sensor_state(entity_id, state, attr)

    async def set_sensor_state(
        self, entity_id: EntityName, state: Any, attr: DictMixed
    ):
        await self._ba.set_sensor_state(entity_id, state, attr)


# Using for BootModule without BasicApp
class ApHass(hass.Hass, ApDefBase):
    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)


@dataclass
class TaskBaseABC(ABC):
    name: str = field(default="")
    buffer_instance_name: StrType = None
    auto_done: bool = (
        True  # if is False it is necessary to call await self.task_done(task_name:enum)
    )

    @abstractmethod
    async def call_fce(self, called: tuple) -> Any:
        ...

    @abstractmethod
    async def execute(self, **kwargs):
        ...

    @abstractmethod
    def set_parent(self, parent):
        ...

    def __repr__(self) -> str:
        return f"TaskBase name: {self.name} instance: {self.buffer_instance_name}"


TaskBaseType = Union[TaskBaseABC, None]


StateFunctionArg = Union[CoroutineDefaultType, Callable, StateQuestionType]
ExecuteFunction = Tuple[StateFunctionArg, ...]
ExecuteFunctionType = Union[ExecuteFunction, None]


class StateFunctionABC(ChildObject):
    @abstractmethod
    def is_state(self, question: StateQuestionType) -> bool:
        ...


StateFunctionABCType = Union[StateFunctionABC, None]


@dataclass
class TaskCoroABC(TaskBaseABC):
    coro: Any = None
    arg: Any = None
    state_function: StateFunctionABCType = None

    @abstractmethod
    def set_state_function(self, state_function: StateFunctionABCType = None):
        ...


@dataclass
class TaskBtnABC(TaskCoroABC):
    expected_is_on: StateQuestionType = None
    expected_is_off: StateQuestionType = None
    expected_on: TupleType = field(default=None)
    expected_off: TupleType = field(default=None)


TaskBtnABCType = Union[TaskBtnABC, None]


@dataclass
class TaskLoopABC(TaskCoroABC):
    @abstractmethod
    async def loop_run(self, yes: bool):
        ...


@dataclass
class TaskParamABC(ABC):
    name: str = ""  # the same as task name
    in_buffer: int = 0
    task: TaskBaseABC = None  # type:ignore
    in_buffer: int = field(default=0)  # timestamp
    finished: bool = field(default=True)


TaskParamType = Union[TaskParamABC, None]
TaskArgType = Union[Enum, TaskBaseABC]

ApDefBaseType = Union[ApDefBase, None]


TaskBaseList = List[TaskBaseABC]


@dataclass
class BufferInstanceABC(ChildObjectBasicApp):
    main_loop_started: bool = field(default=False)
    expection_task: TaskBtnABCType = None
    waiting: Dict[str, TaskParamABC] = field(default_factory=dict)

    def register(self) -> TaskBaseList:
        return self._ba.register  # type:ignore

    @abstractmethod
    async def execution_finished(self) -> Any:
        ...

    @abstractmethod
    async def start(self, state_function: Any, state_command: Enum):
        ...

    @abstractmethod
    async def put_in_queue(self, task: Union[TaskParamABC, EnumType]):
        ...

    @abstractmethod
    async def async_setup(self):
        ...

    @abstractmethod
    async def start_tasks(self):
        ...

    @abstractmethod
    async def clear_queue(self):
        ...


BufferInstanceType = Union[BufferInstanceABC, None]
InstanceNameType = Union[str, TaskBaseABC, Enum, None]  # to_do


class BufferABC(ABC):
    control_task: Any = None
    started: bool = False

    @abstractmethod
    def init(self, instance_name: Any = None):
        ...

    @abstractmethod
    async def start_instance(self, state_function: Any, state_command: Enum):
        ...

    @abstractmethod
    async def put_in_queue(
        self,
        task: Any,
        arg: Any = None,
        instance_name: InstanceNameType = None,
    ):
        ...

    async def clear_queue(self):
        pass

    def sync_put_in_queue(
        self,
        task: Any,
        arg: Any = None,
        instance_name: InstanceNameType = None,
    ):
        self.put_in_queue(task, arg, instance_name)  # type: ignore

    @abstractmethod
    def get_buffer_instance(self, instance_name: Any = None):
        ...

    @abstractmethod
    def get_instance_name(self, instance_name: Any = None) -> str:
        ...


class BufferInterfaceABC(APBAsicAppSensors, BufferABC):
    @abstractmethod
    def init(self, instance_name: InstanceNameType = None):
        ...


BufferInterfaceABCType = Union[BufferABC, None]


class BootStartBase(ApHass):
    def initialize(self):
        self.init_finished: StrType = None
