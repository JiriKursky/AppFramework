# Used for creating helpers
from dataclasses import dataclass, field
from enum import auto
from typing import Union
from apd_types import ApDefBase, EntityObjectABC
from basic_app import HassBasicApp

from helper_types import (
    AutoName,
    DictListDef,
    DictType,
    StateType,
    StrType,
)
from helper_tools import MyHelp as h
from bootstart import boot_logger, boot_logger_off, boot_module
import asyncio
from globals import OFF
from ws_comm import WsHA, CmdType, Cmd


class CmdToDo(AutoName):
    UPDATE = auto()
    CREATE = auto()
    DELETE = auto()


ws_attributes: DictListDef = {
    "input_boolean": {"icon": None},
    "input_number": {
        "icon": None,
        "initial": 0,
        "min": 0,
        "max": 100,
        "step": 1,
        "mode": "box",
        "unit_of_measurement": None,
    },
}

ws_oper_def: DictListDef = {
    "input_boolean": {"type": "input_boolean/create", "name": "", "icon": None},
    "input_boolean_delete": {
        "type": "input_boolean/delete",
        "input_boolean_id": "",
    },
    "input_text": {
        "type": "input_text/create",
        "name": "",
        "icon": "",
        "initial": "",
        "min": 0,
        "max": 100,
        "pattern": "*",
        "mode": "text",
    },
    "input_number": dict(
        type="input_number/create", name="", min=0, max=100, mode="box"
    ),
    "add_item": {"type": "shopping_list/items/add", "name": ""},
    "update": {"type": "shopping_list/items/update", "item_id": ""},
    "clear": {"type": "shopping_list/items/clear"},
}

CmdToDoType = Union[CmdToDo, None]


@dataclass
class EntityObject(EntityObjectABC):
    hass: ApDefBase = None  # type: ignore
    id: str = field(default_factory=h.get_id)
    name: StrType = None
    domain: StrType = None
    initial: StateType = None
    attributes: DictType = None
    friendly_name: StrType = None
    confirmed: bool = False
    linked_entity: StrType = None
    icon_on: StrType = None
    icon_off: StrType = None
    cmd: CmdType = None
    cmd_to_do: CmdToDoType = None
    cmd_update_id: StrType = None
    cmd_update: CmdType = None
    data_restored: bool = False
    module_name: StrType = None
    confirmed: bool = False
    sensor_type: StrType = None
    entity_id: str = field(default="")

    def __post_init__(self):
        self.debug = self.hass.debug  # type: ignore

        self.module_name = h.module_name(self.hass)

        if self.domain is not None:
            assert self.name is not None
            self.entity_id = h.entity_id(self.domain, self.name)
        elif self.name is not None:
            self.entity_id = self.name
            self.domain, self.name = h.split_entity(self.name)

        if self.confirmed:
            return
        self._time = 0
        if self.attributes is None:
            self.attributes = {}

        if self.initial is None:
            if self.domain == "input_boolean":
                self.initial = OFF
            if self.domain == "input_number":
                self.initial = h.par(self.attributes, "min", 0)
        if self.initial is None:
            self.initial = ""
        self.state = self.initial

        if self.friendly_name is None:
            self.friendly_name = h.par(self.attributes, "friendly_name")

        if self.friendly_name is None:
            self.friendly_name = self.name

        if self.icon_on is None:
            self.icon_off = self.attributes.get("icon_on")

        if self.icon_off is None:
            self.icon_off = self.attributes.get("icon_off")

        self.sensor_type = h.remove_key(self.attributes, "sensor_type", "")
        h.remove_key(self.attributes, "icon_on")
        h.remove_key(self.attributes, "icon_off")

        assert self.domain is not None
        # ---- creating via ws

        params: dict = ws_oper_def.get(self.domain, {})
        if params is not None:
            self.params = params.copy()
            attr_mandatory = ws_attributes.get(self.domain)
            if attr_mandatory is not None:
                self.params.update(attr_mandatory)
                if len(self.attributes) > 0:
                    h.update_strict(self.params, self.attributes)
                    # delete all None
            self.params.update({"name": self.name})

            new_params: dict = {}
            for k in self.params.keys():
                if self.params[k] is not None:
                    new_params[k] = self.params[k]
            self.params = new_params

        if self.attributes is None:
            self.attributes = {}
        # Update attributes
        if self.friendly_name is not None and len(self.friendly_name) > 0:
            self.attributes.update({"friendly_name": self.friendly_name})

        if self.attributes is not None:
            self.attributes.update({"editable": True})
            for key in self.attributes:
                if self.attributes[key] is None:
                    h.remove_key(self.attributes, key)
            h.remove_key(self.attributes, "index_key")
        self.debug(f"{self.entity_id} prepared in objects {self.attributes}")

    @property
    def cmd_finished(self) -> bool:
        if self.cmd is not None and self.cmd_update is not None:
            return self.cmd.finished and self.cmd_update.finished
        if self.cmd is None:
            return False
        else:
            return self.cmd_finished

    def set_state(self, value):
        self.state = value
        self.hass.sync_call_service(
            f"{self.domain}/set_value", entity_id=self.entity_id, value=value
        )


EntityObjectType = Union[EntityObject, None]


class EntityOper(HassBasicApp):
    @boot_logger
    @boot_module
    def initialize(self):
        self.debug("EntityOper initialize")
        self.entities_register: dict = {}

    def init(self, end_callback):
        self.ws: WsHA = self.sync_get_app("ws_comm")
        self.end_callback = end_callback
        self._entity_buffer: dict = {}
        self._main_loop_handler = self.sync_create_task(self.main_loop())

    async def _put_in_queue(self, eo):
        if self._entity_queue is not None:
            self._entity_buffer[eo.id] = eo
            await self._entity_queue.put(eo.id)

    async def main_loop(self):
        self.info("Main loop started")
        self._entity_queue: asyncio.Queue = asyncio.Queue()
        self.end_callback(self)
        while True:
            self.debug("Waiting......")
            id = await self._entity_queue.get()
            self.debug(f"Id: {id}")
            eo: EntityObjectType = self._entity_buffer.get(id)
            if eo is None:
                self.error("Unknown id")
                raise ValueError("Unknown id")
            if eo.cmd is None:
                self.error("Missing cmd defintion")
                raise ValueError("Missing cmd defintion")
            self.debug(f"Registering and executing cmd: {eo.cmd.cmd_data}")
            await self.ws.async_register_cmd(eo.cmd)
            if eo.cmd_update is not None:
                while not eo.cmd.finished:
                    await self.sleep(0.1)
                self.debug(f"Registering update: {eo.cmd_update.cmd_data}")
                await self.ws.async_register_cmd(eo.cmd_update)

    def _get_cmd_update(self, entity_object: EntityObject) -> Cmd:
        t_str = f"{entity_object.domain}/update"
        id_name = f"{entity_object.domain}_id"
        _, id_name_var = h.split_entity(entity_object.entity_id)

        cmd_data: dict = {
            "type": t_str,
            id_name: id_name_var,
            "name": entity_object.friendly_name,
        }
        icon = None
        if entity_object.attributes is not None:
            icon = entity_object.attributes.get("icon")
        if icon is not None:
            cmd_data.update({"icon": icon})
        self.debug(cmd_data)
        cmd = Cmd(
            unique_id=entity_object.id,
            cmd_data={
                "type": t_str,
                id_name: id_name_var,
                "name": entity_object.friendly_name,
            },
        )
        return cmd

    def _get_cmd_create(self, entity_object: EntityObject) -> CmdType:
        if entity_object.domain in ws_oper_def.keys():
            assert entity_object.domain is not None
            if entity_object.attributes is None:
                entity_object.attributes = {}
            cmd_data = ws_oper_def[entity_object.domain].copy()
            h.update_strict(cmd_data, entity_object.attributes)
            cmd_data.update({"name": entity_object.name})
            to_delete: list = []
            for k, val in cmd_data.items():
                if val is None:
                    to_delete.append(k)
            for d in to_delete:
                h.remove_key(cmd_data, d)

            return Cmd(unique_id=entity_object.id, cmd_data=cmd_data)
        else:
            self.error("Not in keys!")
            return None

    async def register(self, entity_object: EntityObject):
        self.debug(f"Registering {entity_object}")
        if entity_object.cmd_to_do == CmdToDo.UPDATE:
            self.debug("Update")
            entity_object.cmd = self._get_cmd_update(entity_object)
        elif entity_object.cmd_to_do == CmdToDo.CREATE:

            entity_object.cmd = self._get_cmd_create(entity_object)
            entity_object.cmd_update = self._get_cmd_update(entity_object)

        self.debug("Putting in queue")
        await self._put_in_queue(entity_object)


EntityOperType = Union[EntityOper, None]
