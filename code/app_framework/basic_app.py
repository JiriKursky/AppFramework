""" Module extended BaseOp """
from apd_types import APBasicApp, ApHass, BufferInterfaceABC
from decorators import sync_wrapper
from helper_tools import DateTimeOp as dt, MyHelp as h

import datetime
import time
import globals as g
from globals import gv
from globals_def import eventsDef as e, constsDef as c


from globals import ON, OFF
from helper_types import (
    BlindLogger,
    BoolType,
    CallableType,
    DictMixed,
    DictType,
    EntityName,
    IntType,
    RegisterType,
    StateType,
)
from bootstart import apf_module
from typing import Any, NoReturn, Optional


class BasicApp(APBasicApp):
    def initialize(self):
        # Just ony type
        # use decorator
        self.logger: BlindLogger = BlindLogger()
        self.debug = self.logger.debug
        self.error = self.logger.error
        self.warning = self.logger.warning
        self.info = self.logger.info
        self.do_log = False

        module_name = h.module_name(self)
        config = self.get_plugin_config()  # type: ignore
        g.time_zone = h.par(config, "time_zone", "")
        if len(g.time_zone) > 0:
            time = format(
                dt.just_now().strftime("%Y-%m-%d %H:%M:%S")  # type:ignore
            )
            self.info(f"Ini {module_name} {time}")
        self._register_on_off: RegisterType = []
        self._log_button = ""
        self._fired_proc_buff = []
        self._fired_proc: dict = {}
        self._listen_state: list = []

        self._toggle_def = {}
        self._ovladac = {}
        self._async_run_update = False
        self._msg = ""
        self._events = {}
        self.def_sensors = {}
        self._do_init = True
        self.running = False

        self.fr = None
        self.init_done: bool = False
        module_name = h.module_name(self)
        apf_modules_init_done: DictType = self.global_vars.get(gv.APF_INIT_DONE)  # type: ignore
        if (
            apf_modules_init_done is not None
            and module_name in apf_modules_init_done.keys()
        ):
            self.sync_run_in(self._reload_init, 0.1)

    async def _reload_init(self, *kwargs):
        await self._init()

    async def _init(self):
        if hasattr(self, "running"):
            if self.running:
                return
        else:
            self.running = True
        self.running = True
        self._do_init = False
        self.debug(f"{self.__class__.__name__}")

        # self._log_button = f"input_boolean.log_{module_name}"
        # await self.create_entity(self._log_button)
        await self.run_in_executor(self.init)
        await self.async_setup()
        self.init_done = True

    async def now(self) -> int:
        ret: IntType = await self.run_in_executor(dt.just_now_sec)
        if ret is not None:
            return ret
        else:
            return 0

    def init(self):
        pass

    async def async_setup(self):
        pass

    def run_later(self, proc: object) -> None:
        """Calling proc after 5 seconds

        Args:
            proc (type): proc callback
        """
        self.sync_run_in(proc, 5)

    def _turn_log(self, yes):
        self.do_log = yes

    def google_say(self, msg, temporary=False):
        self._msg = msg
        self.sync_fire_event(e.API_GOOGLE, todo=msg, temporary=temporary)

        # self.run_in(self._say, 5)

    def _say(self, *kwargs):
        self.sync_call_service(
            "tts/google_translate_say",
            entity_id="media_player.family_room_speaker",
            message=self._msg,
        )

    async def entity_error(self, entity_id: str) -> bool:
        """Checking if entity exists and state is not unavailable fire event "ENTITY_ERROR"

        Args:
            entity_id (str): entity name

        Returns:
            bool: True if there is found error
        """
        not_exists = not self.entity_exists(entity_id)
        if not not_exists:
            not_exists = await self.get_state(entity_id) == g.UNAVAILABLE
        if not_exists:
            await self.fire_event(e.ENTITY_ERROR, entity_id=entity_id)
            self.error(f"Error entity: {entity_id}")
        return not_exists

    def sync_entity_error(self, entity_id: str) -> bool:
        """Checking if entity exists and state is not unavailable fire event "ENTITY_ERROR"

        Args:
            entity_id (str): entity name

        Returns:
            bool: True if there is found error
        """
        not_exists = not self.sync_entity_exists(entity_id)
        if not not_exists:
            not_exists = self.sync_get_state(entity_id) == g.UNAVAILABLE
        if not_exists:
            self.sync_fire_event(e.ENTITY_ERROR, entity_id=entity_id)
            self.error(f"Error entity: {entity_id}")
        return not_exists

    async def simple_loop(
        self, interval: int, start_asap: bool = True, callback=None
    ) -> None:
        """loop defined via takt
        There must be def loop(self,*kwargs) in module

        Args:
            interval (int): repeating in seconds, it is not exactly, how system is busy
            start_asap (bool, optional): asap start. Defaults to True.
        """

        self._loop_interval = interval
        if start_asap:
            await self.async_loop()
            await self.run_in_executor(self.loop)
        await self.create_task(self.def_loop())

    async def async_loop(self):
        pass

    def loop(self):
        pass

    async def def_loop(self) -> NoReturn:
        while True:
            await self.sleep(self._loop_interval)
            await self.async_loop()
            await self.run_in_executor(self.loop)

    @sync_wrapper
    async def toggle(self, entity_id: str) -> bool:
        """Providing toggle on entity_id

        Args:
            entity_id (str): entity_id name

        Returns:
            bool: False if there is entity_id error
        """

        if await self.entity_error(entity_id):
            self.debug("Entity error")
            return False

        if await self.is_entity_on(entity_id):
            self.logger.debug("Entity on")
            await self.turn_off(entity_id)
            return False
        else:
            self.debug("Entity off")
            await self.turn_on(entity_id)
            return True

    def sync_turn(self, entity_id: str, yes: Any) -> BoolType:
        """Turning entity_id

        Args:
            entity_id (str): entity name
            yes (type): can be True, 'on'

        Returns:
            bool: True if it is considered as 'on'
        """
        if self.sync_entity_error(entity_id):
            return None
        if h.yes(yes) and not self.sync_is_entity_on(entity_id):
            self.sync_turn_on(entity_id)
            return True
        elif not h.yes(yes) and not self.sync_is_entity_off(entity_id):
            self.sync_turn_off(entity_id)
        return False

    @sync_wrapper
    async def turn(self, entity_id: str, yes: Any) -> BoolType:
        """Turning entity_id

        Args:
            entity_id (str): entity name
            yes (type): can be True, 'on'

        Returns:
            bool: True if it is considered as 'on'
        """

        if await self.entity_error(entity_id):
            return None
        if h.yes(yes) and not await self.is_entity_on(entity_id):
            await self.turn_on(entity_id)
            return True
        elif not h.yes(yes) and not await self.is_entity_off(entity_id):
            await self.turn_off(entity_id)
        return False

    async def get_attr_state_float(self, entity_id: str, attr: str) -> float:
        """Converting attribute value to float

        Args:
            entity_id (str): entity name
            attr (str): attribute name

        Returns:
            float: value of attribute
        """
        retval: StateType = await self.get_attr_state(entity_id, attr)

        if retval is None:
            return 0
        elif isinstance(retval, str):
            if len(retval) == 0:
                self.warning(f"For entity {entity_id} is empty {attr}")
                return 0
            else:
                return float(retval)
        else:
            return 0

    def sync_get_attr_state_float(self, entity_id: str, attr: str) -> float:
        """Converting attribute value to float

        Args:
            entity_id (str): entity name
            attr (str): attribute name

        Returns:
            float: value of attribute
        """
        retVal: StateType = self.sync_get_attr_state(entity_id, attr)
        if retVal is not None:
            return float(retVal)
        else:
            return 0

    async def get_state_float(self, entity_id: str) -> float:
        """Converting state to float in case of error returning

        Args:
            entity_id (str): entity name

        Returns:
            float: state value
        """
        retval: float = 0
        value = await self.get_state(entity_id)
        if isinstance(value, str) and len(value) > 0:
            retval = float(value)
        else:
            retval = 0
        return retval

    def sync_get_state_float(self, entity_id: str) -> float:
        """Converting state to float in case of error returning

        Args:
            entity_id (str): entity name

        Returns:
            float: state value
        """
        retval: float = 0
        value = self.get_state(entity_id)
        if isinstance(value, str) and len(value) > 0:
            retval = float(value)
        else:
            retval = 0
        return retval

    async def get_state_bool(self, entity_id: str) -> bool:
        return h.yes(await self.get_state(entity_id))

    def sync_get_state_seconds(self, entity_id: str) -> int:
        """Using for input_number converting minutes to seconds

        Args:
            entity_id (str): entity name input_number

        Returns:
            int: value in seconds
        """
        return int(self.sync_get_state_float(entity_id) * 60)

    async def get_state_seconds(self, entity_id: str) -> int:
        """Using for input_number converting minutes to seconds

        Args:
            entity_id (str): entity name input_number

        Returns:
            int: value in seconds
        """
        return int(await self.get_state_float(entity_id) * 60)

    async def get_state_int(self, entity_id: str) -> int:
        """Converting state to integer in case of error returning 0

        Args:
            entity_id (str): entity name

        Returns:
            int: state value
        """
        return int(await self.get_state_float(entity_id))

    def sync_get_state_int(self, entity_id: str) -> int:
        """Converting state to integer in case of error returning 0

        Args:
            entity_id (str): entity name

        Returns:
            int: state value
        """
        return int(self.sync_get_state_float(entity_id))

    async def get_state_binary(self, entity_id: str) -> bool:
        """Using for binary sensor

        Args:
            entity_id (str): entity name binary_sensor.

        Returns:
            bool: return True if is entity on
        """
        state = await self.get_state(entity_id)
        return state == g.ON

    async def get_state_str(self, entity_id: str) -> str:
        return str(await self.get_state(entity_id))

    def sync_get_state_str(self, entity_id: str) -> str:
        s = self.get_state(entity_id)
        if s is not None:
            return str(s)
        else:
            return ""

    def dif_time_sec_mysql(self, s_time: str):
        ted = dt.just_now_sec()
        date_time_obj = datetime.datetime.strptime(s_time, "%Y-%m-%dT%H:%M:%S")
        sec = time.mktime(date_time_obj.timetuple())
        return ted - sec

    def set_datetime(self, entity_id, time):
        time_to_set = time.strftime("%Y-%m-%d %H:%M:%S")
        self.set_entity_state(entity_id, time_to_set)
        self.sync_call_service(
            "input_datetime/set_datetime", entity_id=entity_id, datetime=time_to_set
        )

    async def listen_toggle(self, callback: object, entity_id: str) -> None:
        """Listening to on/off

        Args:
            callback (object): callback
            entity_id (str): entity name
        """
        self._toggle_def[entity_id] = callback
        self.logger.debug(f"Switch {entity_id}")
        await self.listen_state(self._listen_toggle, entity_id, new=g.ON)

    async def _listen_toggle(self, entity, attribute, old, new, kwargs):
        switch = self._toggle_def[entity]
        self.logger.debug("Switch {}".format(switch))
        await self.toggle(switch)

    def force_update(self, entity_id):
        """Force update entity_id

        Args:
            entity_id ([type]): [description]
        """
        if self._async_run_update:
            self.logger.debug("Already in process")
            return
        self._async_run_update = True
        self.sync_call_service("homeassistant/update_entity", entity_id=entity_id)
        self._async_run_update = False

    def _catch_tlacitko_on(self, entity, attribute, old, new, kwargs):
        self.logger.debug(f"Chyceno {entity}, {old}, {new}")
        trigger = h.par(self._events[entity], c.trigger)
        if trigger:
            self.logger.debug(f"Fired {trigger}")
            params = h.par(self._events[entity], c.params)
            if params:
                self.sync_fire_event(trigger, **params)
            else:
                self.sync_fire_event(trigger)
            # proc = h.par(self._events[entity_id], c.procedure)
            # if proc:
            #    self.logger.debug(f"Bude volana: {proc}")
            #    self.run_in(proc, 1)

    def _get_proc(self, trigger):
        for e in self._events:
            if self._events[e][c.trigger] == trigger:
                return self._events[e][c.procedure]
        return None

    def _catch_event(self, *kwargs):
        self.logger.debug(f"Chyceno {kwargs[0]}")
        proc = self._get_proc(kwargs[0])
        if proc:
            self.logger.debug(f"Volana {proc}")
            self.sync_run_in(proc, 1)

    def button(
        self, callback: CallableType = None, entity_id: Optional[str] = None
    ) -> None:
        """Using for input_boolean like button Automatically set input_boolean to off
        After calling function is returning to state "off" Also firing event "BUTTON" with par entity
        Example:
            self.button(self.do_something, "input_boolean.like_button")
        """

        # Jen inicializace - prepne na off
        if entity_id is None or len(entity_id) == 0:
            raise ValueError("No entity!")
        self.sync_turn_off(entity_id)
        h.stored_replace(entity_id, g.register_button, callback)
        self.sync_listen_state(self._listener_button_on, entity_id, new=ON)

    async def async_button(
        self, callback: Any = None, entity_id: Optional[str] = None
    ) -> None:
        """Using for input_boolean like button Automatically set input_boolean to off
        After calling function is returning to state "off" Also firing event "BUTTON" with par entity
        Example:
            self.button(self.do_something, "input_boolean.like_button")
        """

        # Jen inicializace - prepne na off
        if entity_id is None or len(entity_id) == 0:
            raise ValueError("No entity!")
        await self.turn_off(entity_id)
        self.debug(type(callback))
        h.stored_replace(entity_id, g.register_button, callback)
        await self.listen_state(self._listener_button_on, entity_id, new=ON)

    async def _listener_button_on(self, entity, attribute, old, new, kwargs):
        self.debug(entity)
        proc = h.stored_get(entity, g.register_button)
        self.debug(type(proc))
        if proc is None:
            await self.fire_event(e.BUTTON, entity=entity)
            return
        is_async: bool = h.is_async(proc)
        if is_async:
            self.debug("Async call")
            await proc()
        else:
            self.debug("Sync call")
            await self.run_in_executor(proc)

    def ovladac_switch(self, input_boolean, switch):
        self._ovladac[input_boolean] = switch
        self.sync_listen_state(self._ovladac_switch, input_boolean)

    def _ovladac_switch(self, entity, attribute, old, new, kwargs):
        switch = self._ovladac[entity]
        self.sync_turn(switch, new)

    def get_counter(self, entity_id):
        try:
            retVal = self.get_state(entity_id)
        except:
            retVal = 0
        return retVal

    def counter_increment(self, entity_id):
        retVal = True
        try:
            self.sync_call_service("counter/increment", entity_id=entity_id)
        except:
            retVal = False
        return retVal

    def counter_reset(self, entity_id):
        retVal = True
        try:
            self.sync_call_service("counter/reset", entity_id=entity_id)
        except:
            retVal = False
        return retVal

    def set_input_select(self, entity_id, value):
        retVal = True
        try:
            self.sync_call_service(
                "input_select/select_option", entity_id=entity_id, option=value
            )
        except:
            retVal = False
        return retVal

    def set_input_number(self, entity_id: str, value: float):
        retVal = True
        try:
            self.sync_call_service(
                "input_number/set_value", entity_id=entity_id, value=float(value)
            )
        except:
            retVal = False
        return retVal

    def set_entity_state(
        self,
        entity_id: str,
        state: StateType,
        attributes: dict = {},
        save_attr: bool = True,
        forced_state: bool = True,
    ) -> None:
        """Setting entity_id state

        Args:
            entity_id (str): entity name
            state (type): can be even bool
            attributes (dict, optional): new attributes. Defaults to {}.
            save_attr (bool, optional): attributes will be left. Defaults to True.
            forced_state (bool, optional): if True will not check if entity_id exists. Defaults to True.
        """
        exists = self.entity_exists(entity_id)
        if not exists:
            exists = h.in_array(entity_id, g.entity_register)
        if not exists and not forced_state:
            return
        s_state: StateType = ""
        if h.is_string(state):
            s_state = state
        elif h.is_bool(state):
            if state:
                s_state = ON
            else:
                s_state = OFF
        else:
            s_state = str(state)
        # self.logger.debug(f"s_state: {s_state}")
        if save_attr and exists:
            attr: DictType = self.get_attributes(entity_id)  # type: ignore
            if attributes and attr:
                attr.update(attributes)
            if attr:
                attributes = attr
        if attributes:
            self.sync_set_state(entity_id, state=s_state, attributes=attributes)
        else:
            self.sync_set_state(entity_id, state=s_state)

    @sync_wrapper
    async def is_entity_on(self, entity_id: str) -> bool:
        """Safe returning if entity_id is in state 'on'

        Args:
            entity_id (str): entity name

        Returns:
            bool: if entity_id is not exists returning False
        """
        if await self.entity_exists(entity_id):
            state = await self.get_state(entity_id)
        else:
            return False
        return h.yes(state)

    def sync_is_entity_on(self, entity_id: str) -> bool:
        """Safe returning if entity_id is in state 'on'

        Args:
            entity_id (str): entity name

        Returns:
            bool: if entity_id is not exists returning False
        """
        if self.entity_exists(entity_id):
            state = self.get_state(entity_id)
        else:
            return False
        return h.yes(state)

    async def get_attr_state(self, entity_id: str, attr: str) -> str:
        """Returning attribute

        Args:
            entity_id (str): entity name
            attr (str): searching attribute

        Returns:
            atttribute, if not exists returns None
        """

        try:
            retval = await self.get_state(entity_id, attribute=attr)
            if isinstance(retval, int):
                return str(retval)
            elif not isinstance(retval, str):
                retval = ""
        except:
            self.warning(
                f"Error getting attribute entity: {entity_id} attribute {attr}"
            )
            retval = ""
        return retval

    def sync_get_attr_state(self, entity_id: str, attr: str) -> str:
        """Returning attribute

        Args:
            entity_id (str): entity name
            attr (str): searching attribute

        Returns:
            atttribute, if not exists returns None
        """
        retval: str = ""
        try:
            retval = str(self.sync_get_state(entity_id, attribute=attr))
            if retval is None:
                retval = ""
        except:
            retval = ""
        return retval

    async def get_all_state(self, entity_id: str) -> DictType:
        """Returning state including attributes

        Args:
            entity_id (str): entity name

        Returns:
            dict: all including state
        """

        try:
            return await self.get_state(entity_id, attribute="all")  # type: ignore
        except:
            return None

    def sync_get_all_state(self, entity_id: str) -> DictType:
        """Returning state including attributes

        Args:
            entity_id (str): entity name

        Returns:
            dict: all including state
        """

        try:
            return self.get_state(entity_id, attribute="all")  # type: ignore
        except:
            return None

    def sync_set_sensor_state(
        self, entity_id: EntityName, state: Any, attr: DictMixed = {}
    ):
        if not isinstance(entity_id, str) or len(entity_id) == 0:
            self.error(f"Error in calling sync_set_sensor_state: {entity_id}")
            return

        all_state = self.sync_get_all_state(entity_id)
        if all_state is None:
            return
        all_attr: dict = all_state.get("attributes", {})

        all_attr.update(h.get_dict(attr))
        self.sync_set_state(entity_id, state=state, attributes=all_attr)

    async def set_sensor_state(
        self, entity_id: EntityName, state: Any, attr: dict = {}
    ):
        all_state = await self.get_all_state(entity_id)
        if all_state is None:
            return
        all_attr: dict = all_state.get("attributes", {})

        all_attr.update(h.get_dict(attr))
        await self.set_state(entity_id, state=state, attributes=all_attr)

    @sync_wrapper
    async def get_attributes(self, entity_id: str) -> DictType:
        """Return attributes of entity

        Args:
            entity_id (str): entity name

        Returns:
            dict: attributes
        """
        all: DictType = await self.get_all_state(entity_id)
        if all is not None:
            return all.get("attributes")
        else:
            return None

    def create_entity(
        self,
        entity_id: str,
        initial: StateType = None,
        attributes: dict = {},
        friendly_name: str = "",
        icon_off: str = "",
        icon_on: str = "",
        linked_entity: str = "",
        linked_entity_copy_attributes: bool = False,
        sensor_type: str = "",
    ) -> object:
        """Create entities with modifying config of HA and sensors directly

        Args:
            entity_id (str): entity_name
            initial (type, optional): Defaults to None.
            attributes (dict, optional):  Defaults to {}.
            friendly_name (str, optional):  Defaults to "". Can be ommited
                if it s defined in attributes
            icon_off (str, optional): Defaults to "".
            icon_on (str, optional):  Defaults to "".
            linked_entity (str, optional):  Defaults to "".
            sensor_type (str, optional):  Defaults to "standard". sensor_type can be defined in attributes
                There are these possibilities:
                - standard
                - number
                - timestamp

        Returns:
            None.

        Examples:
            >>> create_entity("sensor.water", friendly_name="water sensor", icon_on="mdi:water", icon_off="mdi:water-off", linked_entity=switch.valve)

            if entity_id switch.valve is 'on' sensor will be automatically in state 'on' using icon_on
            This you can use in map etc.

        """
        if self.fr is None:
            if h.module_name(self) == "AppFramework":
                self.fr = self
            else:
                self.fr = self.sync_get_app("app_framework")
        return self.fr.create_entity(  # type: ignore
            entity_id=entity_id,
            initial=initial,
            attributes=attributes,
            friendly_name=friendly_name,
            icon_off=icon_off,
            icon_on=icon_on,
            linked_entity=linked_entity,
            sensor_type=sensor_type,
            linked_entity_copy_attributes=linked_entity_copy_attributes,
        )

    @sync_wrapper
    async def listen_on_off(self, callback: Any, entity_id: str) -> Any:
        """cathcing state on off and calling proc

        Args:
            callback (object): Volaná funkce
            entity_id (str): entita

        Returns:
            type: type: handler
        """
        h.stored_push(entity_id, self._register_on_off, callback)
        # self.debug(f">>>>>>>>>>>>> {entity_id} {h.is_async(callback)}")
        handler = await self.listen_state(self._async_fired_on_off, entity_id)
        return handler

    async def _async_fired_on_off(self, entity_id, attribute, old, new, kwargs):
        proc = h.stored_get(entity_id, self._register_on_off)
        if proc is None:
            self.error(f"System error of registration {entity_id}")
            return
        is_async: bool = h.is_async(proc)
        self.debug(f"Volano: {proc} async: {is_async}")
        if h.getting_on(old, new):
            if is_async:
                await proc(True)
            else:
                await self.run_in_executor(self._fired_on_off, proc, True)

        elif h.getting_off(old, new):
            if is_async:
                await proc(False)
            else:
                await self.run_in_executor(self._fired_on_off, proc, False)

    def _fired_on_off(self, proc, yes):
        proc(yes)

    @sync_wrapper
    async def listen_on(self, def_proc: Any, entity_id: str = None):
        """Reaguje na on volá proc

        Typical usage example:
            'prikazy = {
            lza.BOZENA_SEKAT: self._sekat,
            lza.BOZENA_DOMU: self._domu,
            lza.BOZENA_PAUZA: self._pauza,
            }'

            self.listen_on(prikazy)
            nebo
            self.listen_on(prikazy, 'enitiy_id')

        Args:
            def_proc (type): Volaná funkce nebo dict
            entity_id (str): entita

        Returns:
            type: handler

        """
        self.debug(f"Listen on {def_proc} {entity_id}")
        return await self.listen_state(def_proc, entity_id, new=ON)

    @sync_wrapper
    async def set_attributes(self, entity_id: str, attributes: dict) -> None:
        """Setting of new attributes, old attributes will not be touched

        Args:
            entity_id (str): entity name
            attributes (dict): attributes
        """
        state = await self.get_state(entity_id)
        await self.set_state(
            entity_id, state=state, attributes=attributes, replace=False
        )

    def update_entity(self, entity_id: str) -> None:
        """Calling service for update of entity_id

        :param entity_id: entity name
        :type entity_id: str
        """
        try:
            self.sync_call_service("homeassistant/update_entity", entity_id=entity_id)
        except:
            pass

    async def async_update_entity(self, entity_id: str) -> None:
        """Calling service for update of entity_id

        :param entity_id: entity name
        :type entity_id: str
        """
        try:
            await self.call_service("homeassistant/update_entity", entity_id=entity_id)
        except:
            pass


# This is for boot module with BasicApp
class HassBasicApp(ApHass, BasicApp):
    def initialize(self):
        BasicApp.initialize(self)


class AppApf(ApHass, BasicApp):
    @apf_module
    def initialize(self):
        BasicApp.initialize(self)
