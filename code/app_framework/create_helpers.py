""" All entities parsed in AppSystem are here creating """
# Basef on g.helper_register - created in AppAsystem
# Creating registry g.entity_register
# creating entities registered in AppSystem - g.helper_register
#
import asyncio
from basic_app_sensors import HassBasicAppSensors


# import hassapi as hass  # type:ignore
from bootstart import boot_logger, boot_logger_off, boot_module
from entity_oper import CmdToDo, EntityObject, EntityOper, EntityOperType


from globals import HELPERS, OFF
import globals as g
from helper_tools import INDEX_KEY, MyHelp as h, STORED
from sensors import Sensors
import inspect

from sensor_entities import (
    BinarySensorObj,
    SensorObj,
    TimeSensorObj,
    StateSensorObj,
    NumberSensorObj,
    TemperatureSensorObj,
)

# Must be member of Basic app - in sensors registering it is used
class CreateHelpers(HassBasicAppSensors):
    @boot_module
    def initialize(self):
        super().initialize()
        self.info("EntityCreate initialize")

    @boot_logger_off
    def init(self):
        self.was_executed = False
        self.done_handle = None
        self.was_update = False
        entity_oper: EntityOperType = self.sync_get_app("entity_oper")
        assert entity_oper is not None
        self.entity_oper: EntityOper = entity_oper

    async def execute(self, buffer_control: asyncio.Queue) -> bool:
        self.info("Executing of creating")
        if self.was_executed:
            self.warning("Was executed")
            return True
        self.was_executed = True
        g.created_helpers_obj.clear()
        g.helper_register_obj.clear()
        ###
        # Loop
        await h.async_stored_walk(self._to_create_objects, g.helper_register)
        waiting: bool = len(g.created_helpers_obj) > 1
        eo: EntityObject
        self.info("Waiting to create!")
        while waiting:
            waiting = False
            for eo in g.created_helpers_obj:
                if eo.cmd is None:
                    raise ValueError(f"Found without cmd {eo.entity_id}")
                if not eo.cmd_finished:
                    waiting = True
                    self.debug(f"Wait for {eo.entity_id}")
                    await self.sleep(1)
                    break
        buffer_control.task_done()
        await self.run_in_executor(self._create_sensors)
        self.debug("Sensors updated")
        buffer_control.task_done()
        return True

    async def _to_create_objects(self, entity_id: str, sentence: dict):
        """Creating objects of all entities and register of sensor object

        Args:
            entity_id (str): [description]
            sentence (dict): [description]
        """
        # self.debug(f"Creating entity?: {entity_id} {self._to_create}")
        result = h.stored_get(entity_id, g.helper_register_obj)
        if result is not None:
            self.error(f"Duplicated {entity_id}")
            return

        new_one: bool = not h.in_array(entity_id, g.entity_register)
        cmd_to_do = CmdToDo.UPDATE
        if new_one:
            cmd_to_do = CmdToDo.CREATE

        initial = h.par(sentence, "initial", None)
        h.remove_key(sentence, "initial")
        eo: EntityObject = EntityObject(
            hass=self,
            name=entity_id,
            cmd_to_do=cmd_to_do,
            initial=initial,
            attributes=sentence,
        )
        try:
            if eo.domain in HELPERS:
                h.stored_replace(entity_id, g.helper_register_obj, eo)
                if new_one and eo.cmd_to_do == CmdToDo.CREATE:
                    g.created_helpers_obj.append(eo)
                    await self.entity_oper.register(eo)
                else:
                    # self.debug(f"reject: {entity_id}")
                    pass
            else:
                await self.run_in_executor(self.register_sensor, eo)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self.error(message)
            return None

    def _create_sensors(self):
        """Creating via calling sevice setter state"""
        self.debug("===== Sensors====")
        self.debug(g.sensor_register)
        sensor_obj: SensorObj
        for sensor in g.sensor_register:
            entity_id, sensor_obj = h.decode_stored(sensor)
            if not h.in_array(entity_id, g.entity_register):
                sensor_obj.sync_state = (
                    sensor_obj.initial
                )  # Be aware that there is calling service, it is here in state
                h.append_entity_register(entity_id)

    def register_sensor(self, eo: EntityObject):
        """Create entities in HA"""

        # self.debug(f"Registering sensor: {eo.entity_id} {eo.sensor_type}")
        # if eo.entity_id == "sensor.topeni_smycka":
        #    self.warning(
        #        f">>>>>>>>>>>>>>>>Registering sensor: {eo.entity_id} {eo.sensor_type}"
        #    )

        if eo.domain == "binary_sensor":
            self.sensors.register_sensor(
                BinarySensorObj(
                    self,
                    initial=OFF,
                    entity_id=eo.entity_id,
                    icon_off=eo.icon_off,
                    icon_on=eo.icon_on,
                    friendly_name=eo.friendly_name,
                    linked_entity=eo.linked_entity,
                    attributes=eo.attributes,
                )
            )
        elif eo.domain == "sensor":
            if eo.sensor_type == "number":
                self.sensors.register_sensor(
                    NumberSensorObj(
                        self,
                        eo.entity_id,
                        initial=eo.initial,
                        friendly_name=eo.friendly_name,
                        attributes=eo.attributes,
                    )
                )
            elif eo.sensor_type == "timestamp":
                self.sensors.register_sensor(
                    TimeSensorObj(
                        self,
                        eo.entity_id,
                        friendly_name=eo.friendly_name,
                        attributes=eo.attributes,
                    )
                )
            elif eo.sensor_type == "temperature":
                self.sensors.register_sensor(
                    TemperatureSensorObj(
                        self,
                        eo.entity_id,
                        initial=eo.initial,
                        friendly_name=eo.friendly_name,
                        attributes=eo.attributes,
                    )
                )
            else:
                self.sensors.register_sensor(
                    StateSensorObj(
                        self,
                        entity_id=eo.entity_id,
                        initial=eo.initial,
                        friendly_name=eo.friendly_name,
                        attributes=eo.attributes,
                    )
                )

    def divide_params(self, entity_id: str, to_parse: dict) -> dict:
        """Entity given in entity helper - parsed to create_entity in BasicApp*

        Args:
            entity_id (str): [description]
            to_parse (dict): [description]

        Returns:
            dict: [description]
        """
        ba = inspect.signature(self.create_entity).bind(entity_id)
        ba.apply_defaults()
        args = dict(ba.arguments)
        attributes: dict = {}
        attributes.update(
            pair for pair in to_parse.items() if not (pair[0] in args.keys())
        )
        to_parse.update(dict(attributes=attributes))
        h.update_strict(args, to_parse)
        return args

    """
    def delete_platform(self):
        filename = h.config_path() + ".storage/core.entity_registry"
        self.logger.debug(filename)
        registry = h.get_yaml(filename)
        if registry is None:
            return
        data = registry["data"]["entities"]
        for p in data:
            if p["platform"] == "indego_map":
                data.remove(p)
                self.logger.debug(p)
        self.logger.debug("konec")
    """
