""" Trying to control flow  """
import asyncio
from apd_types import ApHass
from create_helpers import CreateHelpers
from entity_oper import EntityObject

import globals as g
from ws_comm import WsHA
from entity_register import EntityRegister
from app_system import AppSystem
from bootstart import boot_logger, boot_logger_off, boot_module


class Sanitarize(ApHass):
    @boot_logger_off
    @boot_module
    def initialize(self):
        self.debug("Initialize")

    def init(self, end_callback):
        """[summary]

        Args:
            end_callback (function): Will be called when all processes are done
        """
        self.info("Starting init")
        self.end_callback = end_callback  # for the boot system

        # Going throw all global definitions and adding them
        # result g.helper_register

        ########################################
        # reducing for only one entity for debug
        """
        new_register: RegisterType = []
        for p in g.helper_register:
            entity = p[INDEX_KEY]
            if entity == "input_text.mower_map":
                new_register.append(p)
        g.helper_register.clear()
        g.helper_register = new_register        
        self.logger.debug(g.helper_register)
        """
        ########################################
        self.debug(
            "Entity register execute and waiting for finishing with entity_register_done"
        )
        self.ws: WsHA = self.sync_get_app("ws_comm")
        self.appSystem: AppSystem = self.sync_get_app("app_system")  # type: ignore
        self.entityRegister: EntityRegister = self.sync_get_app("entity_register")  # type: ignore
        self.createHelpers: CreateHelpers = self.sync_get_app("create_helpers")  # type: ignore

        self._handler_loop = self.sync_create_task(self.main_loop())

    async def main_loop(self):
        self.info("Starting sanitarize")
        control_buffer = asyncio.Queue()
        tasks = {
            "appSystem": self.appSystem.execute(control_buffer),
            "entityRegister": self.entityRegister.execute(control_buffer),
            "createHelpers": self.createHelpers.execute(control_buffer),
            "addToAD": self._add_to_ad(control_buffer),
            "done": self._task_done(control_buffer),
        }
        # without creating helpers
        """
        tasks = {
            "appSystem": self.appSystem.execute(control_buffer),
            "entityRegister": self.entityRegister.execute(control_buffer),
            "done": self._task_done(control_buffer),
        }
        """

        for p in tasks.keys():
            await control_buffer.put(p)
        try:
            while True:
                process = await control_buffer.get()
                self.debug(f"Process: {process}")
                to_do = tasks.get(process)
                if to_do is None:
                    self.error("Wrong definition in tasks")
                    raise ValueError("Wrong definition in tasks")
                await to_do
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            raise ValueError("Fatal error in core")

    async def _task_done(self, control_buffer: asyncio.Queue):
        # info bootstart that it is done
        self._handler_loop.cancel()  # type: ignore
        self.end_callback(self)

    async def _add_to_ad(self, control_buffer: asyncio.Queue):
        self.info("Waiting for system")
        eo: EntityObject
        for eo in g.created_helpers_obj:
            if eo.cmd_finished:
                if not await self.entity_exists(eo.entity_id, replace=False):
                    await self.set_state(eo.entity_id, state=eo.initial)
        control_buffer.task_done()

    def _done(self, *kwargs):
        self.debug("Fired end created entity")
        self.end_callback()
