""" Definuje takt tzn. veskery _loop je volan odsud 
definice se vola pres e.DEF_LOOP
"""

from typing import NoReturn
from apd_types import ApHass
from entity_oper import EntityObject
from helper_tools import MyHelp as h
from globals import ON, OFF
from globals_def import eventsDef as e, constsDef as c
from bootstart import boot_logger_off, boot_module, boot_logger, ModuleClasses
import globals as g

ENTITY_VALUES = "EntityValues"


class LastMile(ApHass):
    @boot_module
    @boot_logger_off
    def initialize(self):
        # If you do not want define "input_boolean.log_takt"
        # You can use this one
        # self.do_log = True

        self._stored_filename = h.storage_path() + "appf.yaml"
        self.takt_defs: dict = {}
        self.debug("Starting initializing takt")
        # Listening for definition of loop
        self.sync_listen_event(self._takt_op, e.DEF_LOOP)
        self.sync_listen_state(self._listen_state)
        # Pouze pocatecni start
        self._log_counter = 5
        self._takt_handler = None

    def init(self, callback):
        self.callback = callback
        self.restore_data()
        entity_object: EntityObject
        self.debug("Restoring")
        for entity_object in h.stored_get_stored(g.helper_register_obj):
            self.debug(entity_object.entity_id)
            if not self.entity_exists(entity_object.entity_id):
                self.debug(f"Not exists: {entity_object.entity_id}")
            elif not entity_object.data_restored:
                entity_object.set_state(entity_object.initial)
        self.sync_create_task(self._main_loop_takt())

    async def _main_loop_takt(self):
        """Vlastni loop"""
        self.info("Takt starting")
        self.callback(self)
        takt_def: TaktDef
        while True:
            self._log_counter -= 1
            if self._log_counter <= 0:
                self._log_counter = 5
            await self.fire_event(e.TAKT)
            for k in self.takt_defs.keys():
                takt_def = self.takt_defs[k]
                if takt_def.beat:
                    await self.fire_event(takt_def.trigger, value=takt_def.get_value)
            await self.sleep(1)

    def _takt_op(self, *kwargs):
        """Definuje taktování
        *kwargs
            - trigger - co bude voláno
            - interval - v sekundách
            - to_do - může být stop
        """

        trigger, interval, to_do = h.kwarg_split(
            kwargs, [c.trigger, c.interval, c.todo]
        )

        if interval:
            self.takt_defs[trigger] = TaktDef(trigger, interval)
        if to_do:
            if to_do == "stop":
                takt_def = self.takt_defs[trigger]
                takt_def.stop = True

    def _listen_state(self, entity, attribute, old, new, kwargs):
        """Listener for storing values

        Args:
            entity ([type]): [description]
            attribute ([type]): [description]
            old ([type]): [description]
            new ([type]): [description]
            kwargs ([type]): [description]
        """
        if old == new:
            return

        entity_object: EntityObject = h.stored_get(entity, g.helper_register_obj)
        self.debug(f"Entity: {entity} entity_object: {entity_object}")
        if entity_object is None:
            return
        # This entities has own stored
        if (
            entity_object.domain in ("sensor", "binary_sensor", "input_boolean")
            or entity_object.state == new
        ):
            return
        self.debug(f"Zapis: {entity}")
        stored_values: dict = h.get_yaml(self._stored_filename)
        if not ENTITY_VALUES in stored_values.keys():
            stored_values[ENTITY_VALUES] = []
        entities_list = stored_values[ENTITY_VALUES]
        found = False
        for ent_dict in entities_list:
            key_list = ent_dict.keys()
            key_iterator = iter(key_list)
            key = next(key_iterator)
            if key == entity:
                found = True
                ent_dict.update({entity: new})
                break
        if not found:
            stored_values[ENTITY_VALUES].append({entity: new})
        entity_object.state = new
        self.debug(stored_values)
        h.save_yaml(self._stored_filename, stored_values, sort_keys=True)

    def restore_data(self):
        try:  # The reason is Tuyaha
            stored_values: dict = h.get_yaml(self._stored_filename)
        except:
            raise ValueError("Fatal error in declaration of stored filename")

        # stored
        if ENTITY_VALUES in stored_values.keys():
            self.debug(stored_values)
            records = stored_values[ENTITY_VALUES]

            entity_object: EntityObject
            for record in records:
                entity_id = h.get_first_key_in_dict(record)
                if entity_id is None:
                    continue

                entity_object = h.stored_get(entity_id, g.helper_register_obj)

                if entity_object is None:
                    continue
                value = record[entity_id]
                self.debug(f"record: {record}: entity_id: {entity_id} value: {value}")
                entity_object.set_state(value)
                entity_object.data_restored = True
                h.stored_replace(entity_id, g.helper_register_obj, entity_object)


class TaktDef(object):
    def __init__(self, trigger, interval):
        # Event waht will be fired
        self.trigger = trigger
        self.interval = interval
        self.counter = 0
        self.value = interval
        self.repeat = True
        self.stop = False

    @property
    def beat(self):
        if self.stop:
            return False
        ret_val = False
        self.is_beat()

        self.counter += 1
        if self.counter >= self.interval:
            self.counter = 0
            ret_val = True
        self.value -= 1
        return ret_val

    @property
    def get_value(self):
        return self.value

    def is_beat(self):
        pass
