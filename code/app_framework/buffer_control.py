""" 
Main buffer for controlling queues
Each bufferControl has its own BufferInstance - this is core fo task registers

"""
from enum import Enum
from apd_types import (
    BufferInstanceABC,
    BufferInstanceType,
    BufferInterfaceABC,
    InstanceNameType,
    StateFunctionABC,
    TaskArgType,
    TaskBaseABC,
    TaskBaseList,
    TaskBaseType,
    TaskLoopABC,
    TaskParamABC,
    TaskParamType,
)
from basic_app import HassBasicApp


from bootstart import boot_logger, boot_logger_off, boot_module

from buffer_instance import BufferInstance
from decorators import sync_wrapper

from typing import Any, Union
from helper_tools import MyHelp as h

from task_register import (
    TaskParam,
)


from helper_types import StrType, TaskNameType

# Main control of buffer instances - creating buffer instances
class BufferControl(HassBasicApp):
    @boot_logger_off
    @boot_module
    def initialize(self):
        """boot_logger is also switching for buffer_instance"""
        self.debug("Initialize")
        self.instance: dict[str, BufferInstanceABC] = {}
        # Registered
        self.register: TaskBaseList = []

    def init(self):
        pass

    def create_new_instance(self, name: str) -> BufferInstanceABC:
        self.debug(f"Creating new buffer instance: {name}")
        self.instance[name] = BufferInstance(self, name)
        return self.instance[name]

    def get_instance(self, name: str) -> BufferInstanceType:
        return self.instance.get(name)


BufferControlType = Union[BufferControl, None]


# Interface for adding in AppApf
# For adding in App as hepler class - will connect together
# registering classes etc
# Has its own BufferControl via get_app
# BufferInterface is not BufferInstance it is extending APF module
class BufferInterface(BufferInterfaceABC):

    BufferInterfaceVersion: str = "1.0 "

    def init(self, instance_name: InstanceNameType = None):
        """Must be called in the beginning

        Args:
            instance_name (InstanceNameType, optional): [description]. Defaults to None.
        """
        self.debug(f"Buffer instance init: {instance_name}")
        buffer_control: BufferControlType = self.sync_get_app("buffer_control")
        assert (
            buffer_control is not None
        ), "Buffer control is None, usually mistake in buffer_control module"
        self.buffer_control: BufferControl = buffer_control
        self._default_instance_name: StrType = None
        if instance_name is not None:
            self._default_instance_name = self.get_instance_name(instance_name)
        self.was_init: bool = True

    def get_registered_tasks(self, instance_name: InstanceNameType) -> TaskBaseList:
        """Return registered TaskBase according instance

        Args:
            instance_name (InstanceNameType): [description]

        Returns:
            TaskBaseList: [description]
        """
        s_instance_name: str = self.get_instance_name(instance_name)
        retval: TaskBaseList = []
        for task_obj in self.buffer_control.register:
            if task_obj.buffer_instance_name == s_instance_name:
                retval.append(task_obj)
        return retval

    def get_buffer_instance(self, instance_name: InstanceNameType = None):
        s_instance_name = self.get_instance_name(instance_name)
        return self.buffer_control.get_instance(s_instance_name)

    def define_buffer_instance(
        self, instance_name: InstanceNameType
    ) -> BufferInstanceABC:
        self.debug(f"Defining buffer instance with name: {instance_name}")
        s_instance_name = self.get_instance_name(instance_name)
        assert (
            s_instance_name is not None
        ), "Bad definition of buffer instance, missing name"
        buffer_instance: BufferInstanceType = self.buffer_control.get_instance(
            s_instance_name
        )

        if buffer_instance is None:
            self.debug("Define buffer")
            assert self.buffer_control is not None, "Buffer control is none"
            self.debug(f"Create new instance: buffer_instance {buffer_instance}")

            buffer_instance = self.buffer_control.create_new_instance(s_instance_name)
        assert (
            buffer_instance is not None
        ), f"Buffer instance is None, trying to define: {s_instance_name}"
        return buffer_instance

    def get_instance_name(self, instance_name: InstanceNameType) -> str:
        """Instance name can be several types.

        Args:
            instance_name (InstanceNameType): [description]

        Returns:
            str: instance name as str
        """
        s_instance_name: StrType = None
        if instance_name is None:
            if self._default_instance_name is None:
                s_instance_name = h.module_name(self)
            else:
                s_instance_name = self._default_instance_name
        elif isinstance(instance_name, TaskBaseABC):
            s_instance_name = instance_name.buffer_instance_name
            if s_instance_name is None:
                s_instance_name = h.module_name(self)
        elif isinstance(instance_name, Enum):
            s_instance_name = instance_name.value
        elif isinstance(instance_name, str):
            s_instance_name = instance_name
        assert s_instance_name is not None, "Not possible to get instance name"
        return s_instance_name

    def register_task(
        self, task_obj: TaskBaseABC, instance_name: InstanceNameType = None
    ):
        """Registering task. If instance is missing it is using default_instance_name defining in init

        Args:
            task_obj (TaskBase): [description]
            instance_name (InstanceNameType, optional): [description]. Defaults to None.
        """
        assert len(task_obj.name) > 0, "Fatal error in registering task. Name not found"
        self.debug(f"Registering task: {task_obj.name}")

        s_instance_name: str = self.get_instance_name(instance_name)
        self.debug(
            f"s instance name: {s_instance_name} task obj instance name (normally None) {task_obj.buffer_instance_name}"
        )
        if instance_name is None:
            if task_obj.buffer_instance_name is None:
                task_obj.buffer_instance_name = s_instance_name
            else:
                s_instance_name = task_obj.buffer_instance_name
        self.debug(f"Checking buffer {task_obj.buffer_instance_name}")
        # buffer_instance: BufferInstance = self.define_buffer_instance(s_instance_name)
        self.debug(
            f"To append: {task_obj.name} into instance: {task_obj.buffer_instance_name}"
        )

        self.debug(f"Setting parent for: {task_obj.name}")

        task_obj.set_parent(self)
        self.buffer_control.register.append(task_obj)

    def _get_task_name(self, name: TaskNameType) -> str:
        if isinstance(name, Enum):
            return name.value
        else:
            return name

    def _get_task(
        self, name: TaskNameType, instance_name: InstanceNameType = None
    ) -> TaskBaseType:
        s_name: str = self._get_task_name(name)
        task_obj_list: TaskBaseList = self.get_registered_tasks(instance_name)

        # Very important it is searching throw name
        retval: TaskBaseType = next(
            (task_obj for task_obj in task_obj_list if task_obj.name == s_name),
            None,
        )
        self.debug(f"Found task: {retval}")
        return retval

    def _get_task_base(
        self, task_arg: TaskArgType, instance_name: InstanceNameType = None
    ) -> TaskBaseType:
        if isinstance(task_arg, Enum):
            self.debug(f"get_task: {task_arg} from instance: {instance_name}")
            return self._get_task(task_arg, instance_name=instance_name)
        elif isinstance(task_arg, TaskBaseABC):
            return task_arg

    async def put_in_queue(
        self,
        task_arg: TaskArgType,
        arg: Any = None,
        instance_name: InstanceNameType = None,
    ):
        self.debug(f"Put in queue {task_arg} arg: {arg}")
        s_instance_name: str = self.get_instance_name(instance_name)

        self.debug(f"Found {task_arg} in instance: {s_instance_name}")

        task_param: TaskParamType = None
        task_obj: TaskBaseType = None
        if isinstance(task_arg, TaskParamABC):
            self.debug("It is instance of TaskParam")
            task_param = task_arg
        else:
            self.debug(f"The first get task: {task_arg} in instance: {s_instance_name}")
            task_obj = self._get_task_base(task_arg, s_instance_name)
            if task_obj is None:
                self.warning(
                    f"None during get task: {task_arg} in instance {s_instance_name}"
                )
                self.warning(f"{task_arg} is not found. Will be not putting in queue")
                return
            else:
                # Defining task param what is BufferControl working with
                task_param = TaskParam(task=task_obj, arg=arg, name=task_obj.name)

        if task_param is None or task_obj is None:
            self.error("Wrong definition in putting queue")
            return
        if task_obj.buffer_instance_name is None and s_instance_name is not None:
            task_obj.buffer_instance_name = s_instance_name
        self.debug(f"Task obj instance name: {task_obj.buffer_instance_name}")
        assert task_obj.buffer_instance_name is not None

        buffer_instance: BufferInstanceType = self.get_buffer_instance(task_obj)
        if buffer_instance is None:
            buffer_instance = self.define_buffer_instance(task_obj)
        assert (
            buffer_instance is not None
        ), f"Buffer instance is None in getting: {task_obj}"
        self.debug(
            f"Putting in queue {task_param.name}, buffer_instance: {buffer_instance.module_name}, waiting: {buffer_instance.waiting}"
        )
        await buffer_instance.put_in_queue(task=task_param)

    async def task_loop_run(
        self,
        task_arg: TaskArgType,
        instance_name: InstanceNameType = None,
        yes: bool = True,
    ):
        task_loop: TaskBaseType = self._get_task_base(
            task_arg=task_arg, instance_name=instance_name
        )
        if task_loop is None:
            self.error(f"task_loop: {task_arg} not found")
            return
        if isinstance(task_loop, TaskLoopABC):
            await task_loop.loop_run(yes)
        else:
            self.error(f"Task: {task_loop.name} is not TaskLoop")

    async def task_done(
        self, task_base: TaskArgType, instance_name: InstanceNameType = None
    ):
        self.debug("Task done method")
        task_base_obj: TaskBaseType = self._get_task_base(task_base, instance_name)
        if task_base_obj is not None:
            instance_name = task_base_obj.buffer_instance_name
        buffer_instance: BufferInstanceType = self.get_buffer_instance(instance_name)

        assert buffer_instance is not None, "Buffer instance is None in task_done"
        assert task_base_obj is not None, "task_base_obj is None in task_done"
        self.debug(
            f"Task: {task_base_obj.name} done with auto_done: {task_base_obj.auto_done}"
        )
        await buffer_instance.execution_finished()

    async def start_tasks_buffer(self, buffer_instance: StrType = None):
        self.debug("Start tasks")
        if not hasattr(self, "was_init") or not self.was_init:
            self.error("Missing init!")
            raise ValueError("Missing init")
        self.debug("start_tasks_buffer")
        assert self.buffer_control is not None
        instance: BufferInstanceType = self.get_buffer_instance(buffer_instance)
        if instance is None:
            instance = self.define_buffer_instance(buffer_instance)
        if instance is None:
            self.error("Missing instance definition")
            raise ValueError("Missing instance definition")
        else:
            self.debug("Starting tasks buffer")
            await instance.start_tasks()

    async def start_instance(
        self,
        state_function: StateFunctionABC,
        state_command: Enum,
        buffer_instance: StrType = None,
    ):
        """[summary]

        Args:
            state_function (StateFunction): Define function for getting state
            state_command (Enum): Which task will checking state
            buffer_instance (StrType, optional): [description]. Defaults to None.
        """
        self.debug("Start instance")
        assert self.buffer_control is not None, "Buffer control is none"
        if buffer_instance is None:
            buffer_instance = self._default_instance_name

        instance_name = self.get_instance_name(buffer_instance)
        assert instance_name is not None, "Wrong definition of instance name"

        instance: BufferInstanceType = self.get_buffer_instance(instance_name)
        if instance is None:
            instance = self.define_buffer_instance(instance_name)
        assert instance is not None, "Not possible to define instance"

        self.debug(f"instance start {instance}")
        await instance.start(
            state_function=state_function,
            state_command=state_command,
        )
        self.info(f"---- instance started with state_command: {state_command}")
