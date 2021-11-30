""" Controlling via boot_store - there is loading all boot modules that should be controlled"""
"""
except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")
        
"""

from apd_types import BootStartBase, FutureTask
import hassapi as hass  # type:ignore
from functools import wraps
import decorators as d

from module_register import ModuleClasses
from helper_tools import MyHelp as h
from helper_types import QueueType
from asyncio import Queue

from globals import gv
import globals as g


# Do not put in decorators - it is regarding bootstart only
def boot_module(func):
    """Adding to boot_store for controlling, necessary to do that in initialize

    Args:
        func ([type]): [description]

    Returns:
        [type]: [description]
    """

    @wraps(func)
    def wrapper(hass: hass.Hass):
        # Signal that module was loaded by system
        module_name = h.module_name(hass)
        boot_modules = hass.global_vars.get(gv.BOOT_MODULES)
        if boot_modules is None:
            boot_modules: dict = {}
            hass.global_vars[gv.BOOT_MODULES] = boot_modules

        if boot_modules.get(module_name) is None:
            boot_modules.update({module_name: hass.args["module"]})
        return func(hass)

    return wrapper


def initialized(func):
    """Adding to boot_store for controlling, necessary to do that in initialize

    Args:
        func ([type]): [description]

    Returns:
        [type]: [description]
    """


def apf_module(func):
    @wraps(func)
    def wrapper(hass: hass.Hass):
        module_name = h.module_name(hass)

        apf_modules = hass.global_vars.get("apf_modules")
        if apf_modules is None:
            apf_modules: dict = {}
            hass.global_vars["apf_modules"] = apf_modules
        if apf_modules.get(module_name) is None:
            apf_modules.update({module_name: hass.args["module"]})

        apf_modules_init = hass.global_vars.get(gv.APF_MODULES_INIT)
        if apf_modules_init is None:
            apf_modules_init: dict = {}
            hass.global_vars[gv.APF_MODULES_INIT] = apf_modules_init

        if apf_modules_init.get(module_name) is None:
            apf_modules_init.update({module_name: hass.args["module"]})

        return func(hass)

    return wrapper


def boot_logger(func):
    @wraps(func)
    def wrapper(hass: hass.Hass):
        try:
            log = hass.get_user_log("apf_logger")
        except:
            log = None
        if log is not None:
            hass.logger = log
            hass.set_log_level("INFO")
            hass.set_log_level("DEBUG")
            hass.debug = hass.logger.debug
            hass.error = hass.logger.error
            hass.info = hass.logger.info
            hass.warning = hass.logger.warning
        return func(hass)

    return wrapper


def boot_logger_off(func):
    @wraps(func)
    def wrapper(hass: hass.Hass):
        try:
            log = hass.get_user_log("apf_logger")
        except:
            log = None
        if log is not None:
            hass.logger = log
            hass.set_log_level("INFO")
            hass.debug = hass.logger.debug
            hass.error = hass.logger.error
            hass.info = hass.logger.info
            hass.warning = hass.logger.warning
        return func(hass)

    return wrapper


class BootStart(BootStartBase):
    @boot_logger
    def initialize(self):
        super().initialize()
        self.info("Initialize")
        self.boot_queue: QueueType = None
        self.apf_queue = None
        # in case of debug to allow only some classes
        self.apf_allowed = h.par(self.args, "apf_allowed", [])
        # self.warning(self.apf_allowed)
        d.debug_allowed = h.par(self.args, "debug_allowed", [])

        self._handler_end = None
        self._finished = False
        config = self.get_plugin_config()
        g.time_zone = h.par(config, "time_zone", "")
        self._main_loop_running = False
        self.go_init = True
        self._task_future: FutureTask = self.sync_create_task(self._main_loop())

    async def clear(self):
        self.debug("Clear!")
        while True:
            if self.boot_queue is not None:
                try:
                    self.boot_queue.get_nowait()
                except:
                    return
                self.boot_queue.task_done()

    # ################################################################################
    # Maiun loop
    # - waiting till all defined boot_modules are done, only then can go to apf modules
    # - waiting to all apf modules
    ##############################################################################
    async def _main_loop(self):

        self._boot_sequence_finished = False
        self.warning("Start main loop")
        self.module_classes: ModuleClasses = ModuleClasses(self, "module_classes")
        self.warning("Module classes ok")
        await self.module_classes.check_reload()
        self._main_loop_running = True
        self.debug("-Start main loop")
        while self._main_loop_running:
            self.debug("Waiting")
            if await self.module_classes.all_boot_registered:
                break
            await self.sleep(5)
        self.module_classes.put_boot_modules()

        self.debug("Registered")
        while self._main_loop_running:
            if self.module_classes.is_boot_finished:
                break
            self.debug(f"Waiting for get")
            module_name = await self.module_classes.boot_queue.get()
            self.debug(f"Boot module_name: {module_name}, starting")

            await self.run_init_boot_module(module_name)

        # Boot modules done, calling APF
        self._boot_sequence_finished = True

        self.debug("APF ini")
        try:
            while self._main_loop_running:
                await self.module_classes.put_apf_modules()
                module_name = await self.module_classes.apf_queue.get()
                self.debug(f"APF module_name: {module_name}, running init")

                # Checking if it is allowed
                can_be_called = False
                if len(self.apf_allowed) == 0:
                    can_be_called = True
                elif h.in_array(module_name, self.apf_allowed):
                    can_be_called = True
                if can_be_called:
                    await self.run_init_apf_module(module_name)
                else:
                    self.debug(f"Not allowed>>>: {module_name}")
                    self.module_classes.close_module(module_name)
                    self.module_classes.apf_queue.task_done()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")

    async def run_init_apf_module(self, module_name):
        try:
            await self.module_classes.run_init(module_name)
        except Exception as ex:
            self.error(f"Could not ini: {module_name}")
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
        self.module_classes.apf_queue.task_done()

    async def run_init_boot_module(self, module_name):
        try:
            await self.module_classes.run_init(module_name)
        except Exception as ex:
            self.error(f"Could not ini: {module_name}")
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")
        await self.wait_for_finished_boot()

    async def wait_for_finished_boot(self):
        while self.init_finished is not None:
            self.debug(f"Waiting for finishing: {self.init_finished}")
            await self.sleep(1)
        self.module_classes.boot_queue.task_done()

    def init_done(self, source: hass.Hass):
        """Called from child (boot, apf) module"""
        finished = h.module_name(source)
        if self.init_finished is None:
            self.error("Already finished")
            return
        if self.init_finished != finished:
            self.error(f"Waiting for {self.init_finished}  and finished: {finished}")
        self.init_finished = None

    def terminate(self):
        self.debug("Terminate")
        self._task_future.cancel()  # type:ignore
        self._main_loop_running = False
