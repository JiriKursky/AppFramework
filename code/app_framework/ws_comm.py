# Revvised 02.10.2021 11:15
#
# WebSocket communication with HA
# https://developers.home-assistant.io/docs/api/websocket
#
# Dokumentace na
# https://websocket-client.readthedocs.io/en/latest/examples.html
#

from dataclasses import dataclass, field
from apd_types import ApHass


import json
import websocket  # type: ignore
from helper_tools import INDEX_KEY, MyHelp as h, STORED
from helper_types import (
    CallableType,
    DictType,
    IntType,
    StrType,
)
from typing import Union
from private import Private
from bootstart import boot_logger, boot_logger_off, boot_module
import asyncio


class ws_error:
    NOT_OPEN = "error not open"
    RECEIVE_EMPTY_RAW = "error empty received"
    NOT_JSON = "Not json answer"
    AUTH_REQUIRED = "Authorization asked"
    OPEN = "open_error"
    NOT_PREPARED = "NOT_PREPARED"


MAX_BATCH = 10


@dataclass
class Cmd:
    unique_id: StrType = None
    cmd_data: dict = field(default_factory=dict)
    callback: CallableType = None
    comment: StrType = None
    id: int = 0
    sent: bool = False
    received: bool = False
    success: bool = False
    raw: DictType = None
    error_code: str = ""
    result: list = field(default_factory=list)
    repeat: bool = True
    finished: bool = False
    error_code: str = ""
    _cmd_json: StrType = None

    @property
    def cmd_json(self) -> str:
        if self._cmd_json is None:
            self._cmd_json = json.dumps(self.cmd_data)
        return self._cmd_json

    @cmd_json.setter
    def cmd_json(self, value):
        self._cmd_json = value

    @property
    def display_data(self) -> dict:
        return dict(
            unique_id=self.unique_id,
            cmd_data=self.cmd_data,
            error_code=self.error_code,
            raw=self.raw,
            sent=self.sent,
            finished=self.finished,
        )

    def update_id(self, new_id: int):
        self.id = new_id
        self.sent = False
        self.cmd_data.update({"id": new_id})
        self.cmd_json = None
        self.received = False
        self.repeat = False
        self.error_code = ""
        self.finished = False
        self.result.clear()


CmdType = Union[None, Cmd]


class WsHA(ApHass):
    @boot_module
    @boot_logger_off
    def initialize(self):
        pass

    def init(self, end_callback):
        self._cmd_register: dict = {}
        self.end_callback = end_callback
        self._finished = False
        self._ws = None
        self._used_id: int = 0
        self.connection_error: bool = False
        self.fatal_error: bool = False
        secrets = Private()
        self.at = secrets.get_secret("app_framework")
        if self.at is None:
            self.error("app_framework missing in secrects.yaml")
            self.fatal_error = True
            self._done()
            return
            # for debug purpose
        else:
            self.debug("Success secret")
        try:
            self._url = f"//{self.args['url_ha']}:{self.args['port']}"
        except:
            self.error("Bad parameters")
            self._done()
            return
        self._main_loop_handler = self.create_task(self.main_loop())

    @property
    def _generator_type_id(self) -> IntType:
        self._used_id += 1
        if self._used_id > MAX_BATCH:
            return None
        else:
            return self._used_id

    def _end_main_loop(self, *kwargs):
        try:
            if self._main_loop_handler is not None:
                self._main_loop_handler.cancel()  # type: ignore
        except:
            pass

    def terminate(self):
        self._done()

    def _done(self):
        self._end_main_loop()
        self.ws_close()

    async def main_loop(self):
        self._buffer = asyncio.Queue()
        success: bool = False

        # signal to bootstart - done
        self.end_callback(self)

        self.info("Loop!")
        cmd: CmdType
        while True:
            unique_id = await self._buffer.get()
            cmd = self._cmd_register.get(unique_id)

            if cmd is None:
                raise ValueError("Wrong cmd")
            else:
                self.debug(f"Sending {cmd.cmd_json}")
                success = await self._send_recieve_direct(cmd)
                self.debug(f"command received {cmd.raw}")
                cmd.finished = True
            h.remove_key(self._cmd_register, unique_id)

            self._buffer.task_done()
            """
            if not success:
                self._done()
            """

    async def _async_send(self, data):
        if self._ws is not None:
            self.debug(f"In executor: {data}")
            retval = await self.run_in_executor(self._ws.send, data)
            return retval
        return None

    async def _async_get_recv(self):
        if self._ws is not None:
            retval = await self.run_in_executor(self._ws.recv)
            return retval
        return None

    async def _get_recv(self, cmd: Cmd) -> None:
        if self._ws is None:
            self.debug("None")
            cmd.error_code = ws_error.NOT_OPEN
            return
        cmd.raw = await self._async_get_recv()
        self.debug(f"Raw:{cmd.raw}")
        if cmd.raw is None:
            cmd.error_code = ws_error.RECEIVE_EMPTY_RAW
            return
        cmd.received = True

        try:
            cmd.cmd_json = json.loads(cmd.raw)  # type: ignore
        except:
            cmd.error_code = ws_error.NOT_JSON
            return

        auth = cmd.cmd_json.get("type", "")
        if auth == "auth_required":
            cmd.error_code = ws_error.AUTH_REQUIRED
            return

        id: StrType = str(h.par(cmd.cmd_json, "id", None))
        if id is None:
            cmd.error_code = "return id None"
            return
        if int(id) != cmd.id:
            cmd.error_code = f"id returned {id}, should be: {cmd.id}"
            return
        cmd.result = cmd.cmd_json.get("result")
        if cmd.result is not None:
            cmd.success = cmd.cmd_json.get("success", False)

    @property
    def ws_url(self):
        if self._url is None:
            self.error("Fatal error")
            return None
        return "ws:" + self._url + "/api/websocket"

    @ws_url.setter
    def ws_url(self, value):
        self._url = value

    def ws_close(self):
        if hasattr(self, "_ws"):
            if self._ws is not None:
                self._ws.close()
        self._ws = None
        self._used_id = 0

    async def _check_connection(self) -> bool:
        self.debug("Checking connection inside")
        retval: bool = False
        if self.fatal_error:
            self.error("Fatal - token missing")
            return retval

        # if was connecion
        self.debug("Checking connection inside")
        if self._ws is not None:
            self.debug("Checking connection inside")
            if self._ws.connected:
                return True
            else:
                self.debug("Checking connection inside close")
                self.ws_close()
        self.debug("Checking connection inside continue")
        self.connection_error = False

        # part of opening connection
        self.debug(f"Checking connection inside here {self.ws_url}")
        try:
            self._ws = websocket.create_connection(self.ws_url)
        except TimeoutError:
            self._ws = None
            self.connection_error = True
            self.error("Timeout error connection")
            return False
        if self._ws is None:
            self.error("Nemam connection")
            return False
        self.debug(f"Asking for recv")
        recv = await self._async_get_recv()  # asking for authorization
        self.info(f"open received: {recv}")

        if recv is None:
            self.connection_error = True
            return False
        retval = json.loads(recv)
        auth = h.par(retval, "type", "")
        if auth != "auth_required":
            self.warning("Error in authentication")
            raise ValueError("Error in authentication")

        auth = {"type": "auth", "access_token": self.at}
        self.debug("Sending auth")
        await self._async_send(json.dumps(auth))
        recv = await self._async_get_recv()
        self.debug(f"Recieved{recv}")
        ret = None

        auth_result: str = ""
        if recv is not None:
            ret = json.loads(recv)
            auth_result = h.par(ret, "type", "")
        if ret is None or auth_result != "auth_ok":
            self._close_connection()
            self.warning("Error in authentication")
            raise ValueError("Error in authentication")
        else:
            retval = True
        return retval

    def register_cmd(self, cmd: Cmd):
        self.debug("Registering")
        self._cmd_register[cmd.unique_id] = cmd
        self._buffer.put_nowait(cmd.unique_id)
        return cmd

    async def async_register_cmd(self, cmd: Cmd):
        """Registering and executing command in ws

        Args:
            cmd (Cmd): [description]

        Returns:
            [type]: [description]
        """
        self._cmd_register[cmd.unique_id] = cmd
        await self._buffer.put(cmd.unique_id)
        return cmd

    async def delete_entity(self, entity_id: str):
        domain, name = h.split_entity(entity_id)
        cmd_data = dict(type=domain + "/delete")
        key = domain + "_id"
        cmd_data.update({key: name})
        cmd: Cmd = Cmd(h.get_id(), cmd_data=cmd_data)
        self.debug(f"Asking: {cmd_data}")
        await self.async_register_cmd(cmd)

    def get_entities(self, domain: str) -> Cmd:
        """Return list of entities

        Args:
            domain (str): [description]

        Returns:
            dict: [description]
        """

        to_send = dict(type=domain + "/list")
        cmd: Cmd = Cmd(h.get_id(), cmd_data=to_send)
        self.debug(f"Asking: {to_send}")
        self.register_cmd(cmd)
        return cmd

    async def prepare_for_send(self, cmd: Cmd) -> bool:
        # Checking - opening / close connection
        id: IntType = self._generator_type_id
        if id is None:
            self.ws_close()
        if self._ws is None:
            self.debug(f"Checking connection")
            retval = await self._check_connection()
            if retval:
                id = self._generator_type_id
                if id is None:
                    self.error("Fatal in generator")
                    return False
        if id is not None:
            cmd.update_id(id)
            return True
        else:
            return False

    async def _send_recieve_direct(self, cmd: Cmd) -> bool:
        """Called from MainLoop

        Args:
            cmd (Cmd): [description]

        Returns:
            Any: [description]
        """

        self.debug(f"Prepare {cmd.cmd_data}")

        # if return None - it means it is necessary close and re_open
        prepared: bool = await self.prepare_for_send(cmd)
        if not prepared:
            return False
        if self._ws is None:
            return False
        # self.debug(f"done {cmd}")
        # self.debug(f"done {cmd.cmd_json}")
        await self._async_send(cmd.cmd_json)

        # Marking that it was sent
        cmd.sent = True
        self.debug(f"Was sent {cmd.cmd_json}")

        await self._get_recv(cmd)
        if len(cmd.error_code) > 0:
            self.error(f"Mistake in communication {cmd.error_code}")
            return False
        return True
