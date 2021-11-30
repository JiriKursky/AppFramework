from asyncio.queues import Queue
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, NoReturn, Union
from apd_types import (
    BufferInstanceABC,
    StateFunctionABC,
    TaskBaseABC,
    TaskBaseList,
    TaskCoroABC,
    TaskLoopABC,
    TaskParamType,
)
from globals_def import GEVNT
from helper_tools import MyHelp as h

from globals import BUFFER_EVENT, OFF, ON, TASK_EVENT
from helper_types import EnumType
from task_register import TaskBtn, TaskParam


# It is parent of BufferControl
# This class is not parent of BufferInterface
# boot_logger is also switching for buffer_instance - go there for debugging
@dataclass
class BufferInstance(BufferInstanceABC):
    _asking_tasks: bool = field(default=False)
    _state: int = field(default=0)
    _queue: List[str] = field(default_factory=list)
    #
    curent_task_param: TaskParamType = None
    state_command: EnumType = None  # What will be called during exception

    # Task with button
    # if button is activate and there is definition of exception
    # BtnTask will be assigned to this variable
    # when expectation is fulfiled it will be None

    _exception_loop_handler: Any = None
    _to_check: str = field(default=OFF)

    async def start(
        self,
        state_function: StateFunctionABC,
        state_command: Enum,
    ):
        if self._asking_tasks:
            self.warning(f"Already asked asks {self.module_name}")
            return
        self.debug(f"Go start with state function {state_function}")
        if state_function is not None:
            self.state_command = state_command
            tasks: TaskBaseList = self.get_registered_tasks()
            for task in tasks:
                if isinstance(task, TaskCoroABC):
                    self.debug(f"Assigning state function to {task.name}")
                    task.set_state_function(state_function)
        await self.start_tasks()

    async def start_tasks(self):
        self.debug(f"start tasks with control task")
        if self._asking_tasks or self.main_loop_started:
            self.warning(f"Already asked asks {self.module_name}")
            return

        self._command_buffer: Queue = Queue()
        self.debug("Create task")
        self.task_main_loop = await self.create_task(self.main_loop())
        # await self._ba.create_task(self.watchdog())
        self.debug(f" Create task for expection: {self.state_command is not None}")
        if self.state_command is not None and self._exception_loop_handler is None:
            self._exception_loop_handler = await self.create_task(self.exception_loop())
        index: int = 0
        self.debug("Waiting for buffer start")
        while not self.main_loop_started and index < 20:
            await self.sleep(1)
            index += 1
        self._asking_tasks = True

    async def join(self):
        await self._command_buffer.join()

    async def clear_queue(self):
        self.debug("Clearing queue!")
        self.expection_task = None
        await self.fire_event(GEVNT.BUFFER_CLEARED.value)
        while True:
            try:
                self._command_buffer.get_nowait()
                self._command_buffer.task_done()
            except:
                pass
            try:
                self.waiting.clear()
                self._queue.clear()
                self.debug("Clear done")
                if self.task_main_loop is not None:
                    self.task_main_loop.cancel()
            except:
                pass
            self.task_main_loop = await self.create_task(self.main_loop())
            return

    async def _main_process(self) -> TaskParamType:
        retval: TaskParamType = None
        try:
            self.debug(f"Main process {self.module_name} - waiting")
            self.curent_task_param = await self._command_buffer.get()
            if self.curent_task_param is None:
                self.error("Fatal error getting task")
                self._command_buffer.task_done()
                return None
            self.debug("_main_process")
            assert isinstance(
                self.curent_task_param, TaskParam
            ), "Instance in main buffer is not TaskParam"

            self.debug(f"Received: {self.curent_task_param.name} {self.module_name}")

            await self.curent_task_param.execute()
            assert (
                self.curent_task_param.task is not None
            ), "self.curent_task_param.task is None in _main_process"
            self.debug(
                f"Is auto_done: {self.curent_task_param.task.auto_done} for: {self.curent_task_param.name}"
            )
            if self.curent_task_param.task.auto_done:
                retval = await self.execution_finished()
            else:
                retval = self.curent_task_param
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")
        self.debug("_main process finished")
        return retval

    async def execution_finished(self) -> TaskParamType:
        self.debug(f"Execution finished")
        self.debug(f"Was waiting: {self.waiting}")

        assert self.curent_task_param is not None, "Wrong definition current task"
        self.debug(f"Current task param name: {self.curent_task_param.name}")

        # safety removing
        h.remove_key(self.waiting, self.curent_task_param.name)
        h.remove_key(self._queue, self.curent_task_param.name)

        self.debug(f"Is waiting: {self.waiting} task done, trying to done")
        try:
            self._command_buffer.task_done()
            self.debug(f"Done with size: {self._command_buffer.qsize()}")
        except:
            pass

        return self.curent_task_param

    @property
    def expection_task_active(self) -> bool:
        return self.expection_task is None

    @expection_task_active.setter
    def expection_task_active(self, value):
        self.expection_task = value

    async def exception_loop(self) -> NoReturn:
        # in exceptance is waiting for state_command
        self.debug("Exception loop in buffer started")
        while True:
            if self.expection_task is None:
                # self.debug("Exception loop is not active")
                await self.sleep(5)
                continue

            # waiting for the task
            self.debug(f">>>>>>>>Waiting in buffer exception {self.waiting}")
            await self.fire_event(BUFFER_EVENT.WAITING_ON.value)

            # Waiting for expected state
            try:
                await self._main_process()

                self.debug(f"After main_process to check: '{self._to_check}''")
                self.debug(f"Expection task name: {self.expection_task.name}")

                if self._to_check == ON and self.expection_task.expected_on is not None:
                    self.debug(f"For on: {self.expection_task.expected_on}")
                    if await self.expection_task.call_fce(
                        self.expection_task.expected_on
                    ):
                        self.debug("have what expected")
                        self.expection_task = None
                        await self.fire_event(BUFFER_EVENT.WAITING_OFF.value)
                elif self.expection_task.expected_off is not None:
                    self.debug(f"For off: {self.expection_task.expected_off}")
                    if await self.expection_task.call_fce(
                        self.expection_task.expected_off
                    ):
                        await self.fire_event(BUFFER_EVENT.WAITING_OFF.value)
                        self.debug("have what expected")
                        self.expection_task = None
                else:
                    self.error("self._expection_task is None!")
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                self.error(message)
                raise ValueError("Fatal error in core")

            if self.expection_task is not None:
                self.warning("Exception is active waiting 10 seconds for state command")
                await self.sleep(10)
                await self.put_in_queue(self.state_command)

    async def main_loop(self):
        """Checking and providing future tasks based on queue"""

        if self.main_loop_started:
            return
        self.main_loop_started = True
        self.info(f"Main loop in buffer started instance: {self.module_name}")

        await self.fire_event(
            TASK_EVENT.BUFFER_STARTED.value, instance=self.module_name
        )

        while True:
            if self.expection_task:
                self.debug("Exception is active ")
                await self.sleep(5)
                continue
            self.debug(f"Waiting in buffer main_loop {self.waiting}")

            if len(self.waiting) == 0:
                await self.fire_event(BUFFER_EVENT.WAITING_OFF.value)
            # Main process
            task_param = await self._main_process()

            self.debug(f"After main process: {task_param}")
            if task_param is None:
                self.warning("Task param is None")
                continue
            if not isinstance(task_param.task, TaskBtn):
                continue
            if task_param.task.input_boolean is None:
                self.debug("Has not input_boolean")
                continue
            self.debug("Condition on exception")
            try:
                if (
                    task_param.task.expected_is_on is not None
                    or task_param.task.expected_is_off is not None
                ):
                    self._to_check = str(
                        await (self._ba.get_state(task_param.task.input_boolean))
                    )
                    self.expection_task_active = task_param.task
                    await self.put_in_queue(self.state_command)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                self.error(message)
                raise ValueError("Fatal error in core")

    async def put_in_queue(self, task: Union[TaskParam, EnumType]):
        if not self.main_loop_started:
            self.debug(
                f"Buffer instance was not started name: {self.module_name} {self.main_loop_started}"
            )
            await self.start_tasks()
        if isinstance(task, TaskParam):
            task_param = task
        else:
            assert task is not None, "Task can not be None for putting in queue"
            task_obj: Union[TaskBaseABC, None] = None
            for task_obj in self.register():
                assert task_obj is not None, "None in register"
                if (
                    task_obj.buffer_instance_name == self.module_name
                    and task_obj.name == task.value
                ):
                    break
            assert task_obj is not None, f"Not registered: {task.value}"
            task_param = TaskParam(task=task_obj, name=task_obj.name)

        if task_param.name in self.waiting.keys():
            self.debug(f"{task_param.name} is waiting")
            return False

        task_param.in_buffer = await self._ba.now()
        self.waiting[task_param.name] = task_param

        self._queue.append(task_param.name)
        assert self._command_buffer is not None, "Not initialized _buffer_command"
        await self._command_buffer.put(task_param)
        self.debug(
            f"Task in queue: {task_param.name} param: {task_param.arg} {task_param.task}"
        )

    def get_registered_tasks(self) -> TaskBaseList:
        retval: TaskBaseList = []
        task_obj: TaskBaseABC
        for task_obj in self.register():
            if task_obj.buffer_instance_name == self.module_name:
                retval.append(task_obj)
        return retval

    async def _control_loops(self, stop: bool):
        self.info(f"Control loops, stop: {stop}")
        tasks: TaskBaseList = self.get_registered_tasks()
        for task_obj in tasks:
            self.info(f"Registered: {task_obj.name} {isinstance(task_obj,TaskLoopABC)}")
            if isinstance(task_obj, TaskLoopABC):
                self.info(f"Loop for {task_obj.name} stop: {stop}")
                await task_obj.loop_run(not stop)
