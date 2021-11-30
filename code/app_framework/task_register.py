from enum import Enum
from types import FunctionType, MethodType
from typing import Any, Tuple, Union
from apd_types import (
    BufferInstanceType,
    BufferInterfaceABC,
    ExecuteFunctionType,
    StateFunctionABCType,
    TaskBaseABC,
    TaskBtnABC,
    TaskCoroABC,
    TaskLoopABC,
    TaskParamABC,
)
from decorators import overrides


from globals import TASK_EVENT
from globals_def import GEVNT
from helper_types import (
    BoolType,
    CoroutinePointer,
    StateQuestionType,
)
from dataclasses import dataclass, field
from helper_types import (
    CallableType,
    EnumType,
    StrType,
    TupleType,
)
import uuid
from helper_tools import DateTimeOp as dt, MyHelp as h
from sensor_entities import BinarySensorType

RegNameType = Union[str, Enum, None]


@dataclass
class TaskBase(TaskBaseABC):
    parent: BufferInterfaceABC = field(default=None)  # type:ignore
    reg_name: RegNameType = None
    module_name: str = ""
    delay_minimum_in_queue: int = (
        0  # minimum delay before this task is running if it is in queue
    )
    _listen_state_handler: Any = None
    listen_to_state_event: bool = False  #  listening for GEVNT.BUFFER_INSTANCE_STATE_CHANGED - usually used in question function of state

    def __post_init__(self):
        if self.reg_name is None:
            self.name = str(uuid.uuid4())
        elif isinstance(self.reg_name, Enum):
            self.name = str(self.reg_name.value)
        else:
            self.name = self.reg_name

    def set_parent(self, parent: BufferInterfaceABC):
        self.parent = parent
        self.debug(f"Setting parent: {self.name} handler {self._listen_state_handler}")
        if self._listen_state_handler is None:
            self._listen_state_handler = self.parent.sync_listen_event(
                self._state_event, GEVNT.BUFFER_INSTANCE_STATE_CHANGED.value
            )
        if self.buffer_instance_name is None:
            assert self.parent is not None
            self.buffer_instance_name = self.parent.get_instance_name()

    async def _state_event(self, event, data, kwargs):
        """
        self.debug(
            f"Listenting state: event: {event} enabled: {self.listen_to_state_event} name: {self.name}"
        )
        """
        if self.listen_to_state_event:
            await self.state_changed()

    async def state_changed(self):
        pass

    @property
    def buffer_instance(self) -> BufferInstanceType:
        if self.parent is None:
            return None
        else:
            self._buffer_instance = self.parent.get_buffer_instance(
                self.buffer_instance_name
            )
            return self._buffer_instance

    def debug(self, msg):
        assert (
            self.parent is not None
        ), f"Cannot debug: self.parent is None task: {self.name}"
        self.parent.debug(f"({self.module_name}) {msg}")

    def info(self, msg):
        assert (
            self.parent is not None
        ), f"Cannot info: self.parent is None task: {self.name}"
        self.parent.info(f"({self.module_name}) {msg}")

    def warning(self, msg):
        assert (
            self.parent is not None
        ), f"Cannot warning: self.parent is None task: {self.name}"
        self.parent.warning(f"({self.module_name}) {msg}")

    def error(self, msg):
        if self.parent is not None:
            self.parent.error(f"({self.module_name}) {msg}")

    async def execute(self, **kwargs):
        self.error("Missing execute")
        pass

    def get_courotine(self, investigate: Any, param_call: Any) -> CoroutinePointer:
        if investigate is None:
            return None
        if isinstance(investigate, MethodType):
            if param_call is None:
                self.debug("Returning without param")
                return investigate()
            else:
                self.debug(f"Returning with param {param_call}")
                return investigate(param_call)
        else:
            return investigate

    async def call_fce(self, called: tuple):
        """Can call sync and async

        Args:
            called (tuple): [description]

        Raises:
            ValueError: [description]

        Returns:
            BoolType: [description]
        """
        try:
            assert self.parent is not None, "Parent is None"
            investigate, param_call = called
            if investigate is None:
                self.error("Asking to call None in call_fce")
                return
            self.debug(f"For investigate: {investigate}, {param_call}")
            if h.is_async(investigate):
                to_call: CoroutinePointer = self.get_courotine(
                    investigate=investigate, param_call=param_call
                )
                if to_call is None:
                    return None
                else:
                    await to_call
            else:
                if isinstance(investigate, FunctionType):
                    if param_call is None:
                        return investigate()
                    else:
                        return investigate(param_call)
                else:
                    if param_call is None:
                        return await self.parent.run_in_executor(investigate)
                    else:
                        return await self.parent.run_in_executor(
                            investigate, param_call
                        )
        except Exception as ex:
            template = (
                "An exception of type {0} occurred in task_register. Arguments:\n{1!r}"
            )
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")

    async def fire_event(
        self, event: Union[EnumType, str, int], name: StrType = None, arg: Any = None
    ):
        if event is None:
            return

        assert self.parent is not None, "parent is not defined use set_parent"
        if isinstance(event, str):
            s_event = event
        elif isinstance(event, int):
            s_event = str(int)
        else:
            s_event = event.value
        if name is None:
            name = self.name
        await self.parent.fire_event(s_event, task_param=arg)


InstanceNameType = Union[str, TaskBase, Enum, None]


@dataclass
class TaskCoro(TaskBase, TaskCoroABC):
    on_start: CallableType = None
    on_end: CallableType = None
    timeout: int = 15  # Timeout for executing
    time_overflow: bool = False
    _coro_must_be_async: bool = False
    state_is_on: StateQuestionType = None
    state_is_off: StateQuestionType = None
    state_on: TupleType = field(default=None)
    state_off: TupleType = field(default=None)

    _timestamp_start: float = field(default=0)
    _timestamp_end: float = field(default=0)

    def __post_init__(self):
        super().__post_init__()
        self.set_state_function()

    def _assign_question(self, source):
        if source is not None:
            return self._question(source)
        else:
            return None

    def set_state_function(self, state_function: StateFunctionABCType = None):
        self.state_function = state_function
        if self.state_function is None:
            return
        self.state_on = self._assign_question(self.state_is_on)
        self.state_off = self._assign_question(self.state_is_off)

    def _question(self, question: StateQuestionType) -> TupleType:
        if self.state_function is not None:
            return (self.state_function.is_state, question)
        else:
            return None

    async def do_call(self, aw=None, param_call=None):
        self.time_overflow = False
        if aw is None:
            aw = self.coro
            param_call = self.arg
        await self.call_fce((aw, param_call))

    async def task_finished(self):
        """Called when execution is done and checking call_back"""
        if self.on_end is not None and not self.time_overflow:
            if h.is_async(self.on_end):
                if self.arg is not None:
                    await self.on_end(self.arg)
                else:
                    await self.on_end()
            else:
                if self.arg is not None:
                    await self.parent.run_in_executor(self.on_end, self.arg)
                else:
                    await self.parent.run_in_executor(self.on_end)
        self.finished = True
        await self.reset_task_timestamp_end()
        self.running = False
        await self.fire_event(TASK_EVENT.TASK_FINISHED, name=self.name)

    async def reset_task_timestamp_end(self):
        """Reseting time of loop"""
        if hasattr(self, "_timestamp_end"):
            self._timestamp_end = await self.parent.now()

    async def do_execute(self, exe: tuple, **kwargs):
        """Separated for overwriting

        Args:
            exe (tuple): [description]
        """
        self.debug("do_execute in TaskCoro")
        await self.call_fce(exe)

    async def execute(self, **kwargs):
        self.debug("Base task register")
        arg = kwargs.get("arg")
        if self.delay_minimum_in_queue > 0:
            # How to long delay before start
            # useful for asking api server
            await self.parent.sleep(self.delay_minimum_in_queue)
        self.debug(f"To call: coro {self.coro} with arg: {arg}")
        try:
            if arg is None:
                arg = self.arg

            assert self.parent is not None
            self.running = True
            time = await self.parent.now()
            if time is not None:
                self._timestamp_start = float(time)
            if self.on_start is not None and callable(self.on_start):
                self.debug("On start")
                await self.parent.run_in_executor(self.on_start)
            self.debug(f"Execute coro: {self.coro} with arg: {arg}")
            await self.do_execute((self.coro, arg), **kwargs)
            await self.task_finished()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)

    async def put_in_queue(self, arg: Any):
        """Be careful this is override - sending param

        Args:
            arg ([type]): [description]
        """
        await self.parent.put_in_queue(self, arg=arg)

    async def clear_queue(self):
        await self.parent.clear_queue()


TaskCoroType = Union[TaskCoro, None]


@dataclass
class TaskBinarySensor(TaskCoro):
    binary_sensor: BinarySensorType = None
    entity_id: str = ""
    state_on: ExecuteFunctionType = None

    def __post_init__(self):
        super().__post_init__()
        self.module_name = self.entity_id

    @overrides(TaskCoro)
    def set_parent(self, parent):
        super().set_parent(parent)
        self.listen_to_state_event = True

    async def state_changed(self):
        """Based on fire event"""
        if self.binary_sensor is None:
            self.binary_sensor = await self.parent.sensors.binary_sensor(
                self.entity_id, False
            )
        assert self.binary_sensor is not None
        if self.state_on is not None:
            self.debug(f"Calling state_on: {self.state_on}")
            if await self.call_fce(self.state_on):
                await self.binary_sensor.async_set_entity_state(True)
            else:
                await self.binary_sensor.async_set_entity_state(False)


@dataclass
class TaskLoop(TaskCoro, TaskLoopABC):
    _handler: Any = field(default=None)
    loop_enabled: bool = True
    loop_testing_function: Any = None
    frequence: float = 0
    loop_start_automaticaly: bool = True
    _main_loop_started: bool = False
    _loop_run: bool = field(default=True)

    async def loop_run(self, yes: bool):
        """If loop should run or not

        Args:
            yes (bool): [description]
        """
        if yes:
            await self.reset_task_timestamp_end()
        self._loop_run = yes
        self.info(f"loop_run: {self.name} {self._loop_run}")

    @overrides(TaskCoro)
    def set_parent(self, parent):
        super().set_parent(parent)

        if self.buffer_instance is not None and self.buffer_instance.main_loop_started:
            self.start_loop()
        else:
            self.listen_handler = self.parent.listen_event(
                self._start_loop, GEVNT.BUFFER_STARTED.value
            )

    def start_loop(self):
        if self._main_loop_started:
            self.debug(f"Main loop already started {self.buffer_instance_name}")
            return
        self.debug(f"Starting loop {self.name}")
        self._handler = self.parent.create_task(self._main_loop())

    def _start_loop(self, event, data, kwargs):
        if self.buffer_instance_name == data.get("instance", ""):
            if self.listen_handler is not None:
                self.parent.sync_cancel_listen_event(self.listen_handler)
            self.start_loop()

    async def execute(self, **kwargs):
        await super().execute()
        self.loop_enabled = True

    async def exec_time_overflow(self):
        self.debug("Exec time overflow")
        self.loop_enabled = False
        await self.execute()
        self.loop_enabled = True

    async def _main_loop(self):
        """loop for overflow of time"""
        if self._main_loop_started:
            return
        self._main_loop_started = True
        self.info(f"In main_loop with frequence: {self.frequence}")
        if self.frequence == 0:
            self.warning(f"{self.name} has frequence 0")
        while True:
            if self._loop_run:
                if self.frequence > 0:
                    go_loop = await self._go_loop()
                    # self.debug(f"calling go_loop {go_loop}")
                    if go_loop is not None and go_loop:
                        time_overflow = await self._check_time_overflow()
                        # self.debug(f"Time overflow: {time_overflow}")
                        if time_overflow:
                            await self.exec_time_overflow()
            await self.parent.sleep(1)

    async def _go_loop(self) -> BoolType:
        if not self.loop_enabled or self.loop_testing_function is None:
            return True
        return await self.call_fce(self.loop_testing_function)

    async def ultimate_end(self) -> float:
        retval: float = 0
        if self._timestamp_end == 0:
            self.warning("Zero")
            return retval
        ted = await self.parent.now()
        retval = ted - self._timestamp_end
        return retval

    async def task_finished(self):
        await super().task_finished()
        self.loop_enabled = True

    async def _check_time_overflow(self) -> bool:
        retval: bool = False
        if not self.loop_enabled:
            # self.debug("Loop is disabled for checking time")
            return False
        if self._timestamp_end == 0:
            self.debug("Time stamp is 0")
            return True
        ultimate_end: float = await self.ultimate_end()
        # self.debug(f"{ultimate_end} {self.frequence}")
        if ultimate_end > self.frequence:
            retval = True
        return retval


@dataclass
class TaskBtn(TaskCoro, TaskBtnABC):
    expected_is_on: StateQuestionType = None
    expected_is_off: StateQuestionType = None
    expected_on: TupleType = field(default=None)
    expected_off: TupleType = field(default=None)

    input_boolean: Union[str, Tuple[str, ...]] = ""

    cmd_on_not_allowed: TupleType = field(default=None)
    cmd_on_not_allowed_def: TupleType = field(default=None)

    cmd_off_not_allowed: TupleType = field(default=None)
    cmd_off_not_allowed_def: TupleType = field(default=None)

    # Calling on what should be done
    execute_on_on: ExecuteFunctionType = None
    execute_on_not_allowed: TupleType = None
    execute_on_off: ExecuteFunctionType = None
    execute_off_not_allowed: TupleType = None

    listen_event: bool = False  # event of state
    timeout_to_change_state: float = 0  # not used now
    testing_function: Any = None
    _state_ignore: bool = field(
        default=False
    )  # will ignore button on/off - no execution
    _timestamp_last_change: float = field(default=0)
    _timestamp_of_expecting: int = field(default=0)
    _btn_state_handler: Any = None

    def __post_init__(self):
        super().__post_init__()
        self.module_name = self.name
        self.set_state_function()

    def set_state_function(self, state_function: StateFunctionABCType = None):
        super().set_state_function(state_function)
        self.cmd_on_not_allowed_def = self._assign_question(self.cmd_on_not_allowed)
        self.cmd_on_not_allowed_def = self._assign_question(self.cmd_off_not_allowed)
        self.expected_on = self._assign_question(self.expected_is_on)
        self.expected_off = self._assign_question(self.expected_is_off)

    def set_parent(self, parent):
        super().set_parent(parent)

        if isinstance(self.input_boolean, Tuple):
            for p in self.input_boolean:
                self.parent.sync_listen_state(self._state, p)
        else:
            self.parent.sync_listen_state(
                self._state, self.input_boolean
            )  # calling for btn push
        if self.execute_on_on is None and self.execute_on_off is None:
            self.execute_on_on = self.coro
            self.parent.sync_turn_off(self.input_boolean)
        if self.state_is_on is not None and self.state_is_off is not None:
            self.listen_to_state_event = True

        # initialization
        self._time_stamp_last_change = dt.just_now_sec()
        self.listen_to_state_event = (
            self.state_is_on is not None or self.state_is_off is not None
        )

    @overrides(TaskCoro)
    async def state_changed(self):
        """Listening for change of state depends on fire

        Args:
            event ([type]): [description]
            data ([type]): [description]
        """

        self.debug(f"State changed instance name: {self.name}")
        self.debug(f"on state on do: {self.state_is_on}")
        self.debug(f"on state off do: {self.state_is_off}")
        assert (
            self.buffer_instance is not None
        ), f"Buffer instance is None in {self.module_name}"
        try:
            if self.buffer_instance.expection_task is None:
                if self.state_on is not None:

                    # without efect of execution
                    await self.turn(await self.call_fce(self.state_on))

                elif self.state_off is not None:
                    if await self.call_fce(self.state_off):
                        # without efect of execution
                        await self.turn(False)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")

    async def _state(self, entity, attribute, old, new, kwargs):
        self.debug(f"{entity} ignore: {self._state_ignore} ignore {new}")
        if self._state_ignore:
            self._state_ignore = False
            return

        # Main execution
        if h.getting_on(old, new):
            if self.execute_on_on is not None:
                if self.execute_on_not_allowed is None or await self.call_fce(
                    self.execute_on_not_allowed
                ):
                    await self.parent.put_in_queue(self)

    async def turn(self, on: BoolType):
        """
        if self.timeout_to_change_state > 0:
            now = await self.parent.run_in_executor(dt.just_now_sec)
            if now - self._time_stamp_last_change < self.timeout_to_change_state:
                return
        """
        if on is None:
            on = False
        if self.input_boolean is None or not isinstance(self.input_boolean, str):
            return
        self._state_ignore = True
        if await self.parent.is_entity_on(self.input_boolean) and not on:
            await self.parent.turn_off(self.input_boolean)
        elif await self.parent.is_entity_off(self.input_boolean) and on:
            await self.parent.turn_on(self.input_boolean)
        self._time_stamp_last_change = await self.parent.now()
        self._state_ignore = False


@dataclass
class TaskParam(TaskParamABC):
    """TaskParam is using for execution in BufferInstance. It has more attributes for executing of Task

    Args:
        TaskParamABC ([type]): [description]
    """

    arg: Any = None  # usualy dict for sending arguments in execute, if is missing - execute will be called without arg

    async def execute(self):
        if self.task is not None:
            await self.task.execute(arg=self.arg)
