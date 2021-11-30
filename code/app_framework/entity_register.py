""" Creating list of registers """
# Revised 27.8.2021 11:15
# Creating registry g.entity_register
# creating entities registered in AppSystem - g.helper_register
#
import asyncio
from apd_types import ApHass
from bootstart import boot_logger_off, boot_module, boot_logger
import globals as g
from ws_comm import WsHA, Cmd
from helper_tools import MyHelp as h


class EntityRegister(ApHass):
    @boot_module
    @boot_logger
    def initialize(self):
        self.debug("Initialize")
        self.ws: WsHA = self.sync_get_app("ws_comm")

    def init(self):
        self.info("Init")

    async def execute(self, buffer_control: asyncio.Queue):
        # notify that not created
        self._helpers_domain: dict = {}  # created?
        domain_name: str = ""
        for domain_name in g.HELPERS:
            self._helpers_domain.update({domain_name: False})

        self.debug("Updating entity_register - calling list and update")
        g.entity_register.clear()
        # callback in this is calling during flush
        cmd: Cmd
        for domain in g.HELPERS:
            cmd = self.ws.get_entities(domain)
            while not cmd.finished:
                self.info("Waiting")
                await self.sleep(0.1)
            for p in cmd.result:
                id = p.get("id")
                if id is not None:
                    entity_id = domain + "." + id
                    h.append_entity_register(entity_id)
        buffer_control.task_done()
