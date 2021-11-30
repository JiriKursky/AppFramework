from inspect import signature
from typing import Any, Union
from apd_types import ApDefBase, ApHass, BootStartBase, ChildObject
from globals import BOOT_CLASSES
from helper_tools import MyHelp as h
from asyncio import Queue

from helper_types import DictType, StrType
from globals import gv


class ModuleParams(object):
    def __init__(
        self, name: str, boot: bool, class_def: object = None, module: StrType = None
    ):
        self.boot = boot
        self.name: str = name
        self.module: StrType = module
        self.called_init: bool = False
        self.class_def: Any = class_def
        self.was_in_queue: bool = False

    @property
    def finished(self) -> bool:
        return self.called_init

    @finished.setter
    def finished(self, value):
        self.called_init = value

    @property
    def registered(self) -> bool:
        return self.class_def is not None

    @property
    def has_init(self) -> bool:
        if self.class_def is not None:
            return hasattr(self.class_def, "init")
        else:
            return False

    def register(self, parent: ApDefBase, module: str, class_def, boot: bool):
        self.name = h.module_name(parent)
        self.module = module
        self.boot = boot
        self.called_init = False
        self.class_def = class_def


ModuleParamsType = Union[None, ModuleParams]

# ModuleClasses have two type of queue
class ModuleClasses(ChildObject):
    def __post_init__(self):
        super().__post_init__()
        self.debug("Module classes")
        self._ba: BootStartBase
        self.modules: dict = {}
        self.boot_queue: Queue = Queue()
        self.apf_queue: Queue = Queue()
        for bt in BOOT_CLASSES:
            self.modules[bt] = ModuleParams(bt, True)

    @property
    async def all_boot_registered(self) -> bool:
        boot_modules: DictType = self.global_vars.get(gv.BOOT_MODULES)
        assert boot_modules is not None
        for k in self.modules.keys():
            if boot_modules.get(k) is None:
                self.info(f"Missing {k}")
                return False
        for k in self.modules.keys():
            module_param: ModuleParams = self.modules[k]
            class_def = await self._ba.async_get_app(boot_modules[k])  # type:ignore
            self.debug(f"Register: {k}, {class_def}")
            module_param.register(
                self._ba, module=boot_modules[k], class_def=class_def, boot=True
            )
        return True

    async def check_reload(self):
        self.debug("Reload?")
        if not self.global_boot_finished:
            return
        self.global_boot_finished = False
        modules = self.global_vars.get(gv.BOOT_MODULES, {})
        self.debug(">>>>>> Reloading <<<<<<<<")
        for module in modules:
            # ModuleClasses.check_list_queue.put(bt)  # sequence for running
            await self._ba.restart_app(module)
        self.debug(">>>>>> Done <<<<<<<<")

    def get_params(self, module_name) -> ModuleParamsType:
        return self.modules.get(module_name)

    def registered(self, module_name) -> bool:
        module_params: ModuleParamsType = self.get_params(module_name)
        if module_params is None:
            return False
        else:
            return module_params.registered

    @property
    def is_boot_prepared(self) -> bool:
        self.debug("Prepared?")
        for bt in BOOT_CLASSES:
            # ModuleClasses.check_list_queue.put(bt)  # sequence for running
            boot_module: ModuleParamsType = self.get_params(bt)
            if boot_module is None:
                raise ValueError("Wrong defined")
            elif not boot_module.registered:
                self.debug(f"Not prepared: {bt}")
                return False
        return True

    @property
    def global_boot_finished(self) -> bool:
        bf = self.global_vars.get(gv.BOOT_FINISHED)
        return bf is not None and bf

    @global_boot_finished.setter
    def global_boot_finished(self, yes: bool):
        self.global_vars.update({gv.BOOT_FINISHED: yes})

    @property
    def is_boot_finished(self) -> bool:
        self.debug("Boot finished?")
        for bt in BOOT_CLASSES:
            # ModuleClasses.check_list_queue.put(bt)  # sequence for running
            boot_module: ModuleParamsType = self.get_params(bt)
            if boot_module is None:
                raise ValueError("Wrong defined")
            elif not boot_module.finished:
                self.global_boot_finished = False
                return False
        self.global_boot_finished = True
        return True

    def put_boot_modules(self):
        for bt in BOOT_CLASSES:
            self.boot_queue.put_nowait(bt)

    async def put_apf_modules(self):
        """Putting apf module from self.hass.global_vars["apf_modules_init"][module_name]"""
        modules: DictType = self.global_vars.get(gv.APF_MODULES_INIT)
        if modules is None:
            self.info("APF modules missing")
            return
        else:
            apf_modules = modules.copy()
        for module_name, module in apf_modules.items():
            self.info(f"Module name: {module_name}")
            if module_name in BOOT_CLASSES:
                del self.global_vars[gv.APF_MODULES_INIT][module_name]
                continue
            module_params: ModuleParamsType = self.modules.get(module_name)
            if module_params is None:
                class_def = await self._ba.async_get_app(module)
                # self.debug(f"Defining module params {module_name} -> {class_def}")
                module_param: ModuleParams = ModuleParams(
                    name=module_name, boot=False, class_def=class_def, module=module
                )
                self.modules[module_name] = module_param
                self.debug(f">>>>> init and put {module_name}")
                module_param.was_in_queue = True
                del self.global_vars[gv.APF_MODULES_INIT][module_name]
                self.apf_queue.put_nowait(module_name)
            elif not module_params.finished:
                if module_params.class_def is None:
                    module_params.class_def = await self._ba.async_get_app(module)

                module_params.module = module
                if not module_params.was_in_queue:
                    self.debug(f">>>>> was not init {module_name}")
                    module_params.was_in_queue = True
                    del self.global_vars[gv.APF_MODULES_INIT][module_name]
                    self.apf_queue.put_nowait(module_name)

    async def run_init(self, module_name):
        self.debug(f"Run init module: {module_name}")
        self._ba.init_finished = module_name
        module_params: ModuleParamsType = self.get_params(module_name)
        if module_params is None:
            raise ValueError(f"Fatal {module_params}")
        if module_params.boot:
            if module_params.has_init:
                sig = signature(module_params.class_def.init)
                module_params.called_init = True

                # Checking if init has more than one param
                # This param must be end
                s_sig = str(sig)
                if len(s_sig) > 2:
                    self.debug("Has callback")
                    await self._ba.run_in_executor(
                        module_params.class_def.init, self._ba.init_done
                    )
                else:
                    self.debug(f"Run init module sync: {module_name}")
                    await self._ba.run_in_executor(module_params.class_def.init)
                    self.debug(f"Run init module done: {module_name}")
                    self._ba.init_finished = None
            else:
                raise ValueError(f"Fatal {module_params}")
        # APF module
        else:
            if module_params.class_def is None:
                self.debug("class_def None")
            else:
                self.debug(f"Calling async _init {module_params.class_def._init}")
                module_params.called_init = True
                await module_params.class_def._init()
                apf_modules_init_done = self.global_vars.get(gv.APF_INIT_DONE)
                if apf_modules_init_done is None:
                    apf_init_done: dict = {}
                    self.global_vars[gv.APF_INIT_DONE] = apf_init_done
                    apf_modules_init_done = self.global_vars.get(gv.APF_INIT_DONE)

                assert (
                    apf_modules_init_done is not None
                ), f"Missing done in {module_name}"
                if apf_modules_init_done.get(module_name) is None:
                    apf_modules_init_done.update({module_name: True})
                self._ba.init_finished = None

    def was_init(self, module_name) -> bool:
        module_params: ModuleParamsType = self.get_params(module_name)
        if module_params is None:
            return True
        elif module_params.has_init:
            return module_params.called_init
        else:
            raise ValueError(f"Missing init in {module_name}")

    def close_module(self, module_name):
        module_params: ModuleParamsType = self.get_params(module_name)
        if module_params is not None:
            module_params.finished = True
