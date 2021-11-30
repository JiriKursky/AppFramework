""" App for creating user-defined directly from global modules using AppFramework """
# version: 1.2

from apd_types import SensorsABC
from basic_app import HassBasicApp
from decorators import sync_wrapper
from globals_def import eventsDef as e
from globals import ON, OFF
import globals as g
from helper_tools import MyHelp as h, DateTimeOp as dt
from globals_def import eventsDef as e  # type: ignore
from helper_types import BoolType, StateType, StrType
from sensor_entities import (
    NumberSensorObj,
    SensorObj,
    StateSensorObj,
    TemperatureSensorObj,
    BinarySensorObj,
)
from bootstart import boot_logger, boot_logger_off, boot_module

from sensor_entities import TimeSensorObj
from typing import Any, Union


SensorType = Union[
    SensorObj, TimeSensorObj, NumberSensorObj, TemperatureSensorObj, BinarySensorObj
]

SensorNoneType = Union[SensorType, None]


class Sensors(HassBasicApp, SensorsABC):
    @boot_module
    def initialize(self):
        super().initialize()
        self._tmp_sensor = []

    @boot_logger_off
    def init(self):
        g.sensor_register.clear()

    def _set_attr_from_linked(self, sensor: SensorObj):
        if sensor.linked_entity is not None and len(sensor.linked_entity) > 0:
            state = self.sync_get_state(sensor.linked_entity, attribute="all")
            if not isinstance(state, dict):
                return
            attr = state.get("attributes")
            if isinstance(attr, dict):
                h.remove_key(attr, "friendly_name")

            self.sync_set_state(
                sensor.entity_id, state=h.par(state, "state", OFF), attributes=attr
            )

    async def _get_sensor_type(self, entity_id) -> tuple:
        state = await self.get_state(entity_id, attribute="all")
        if not isinstance(state, dict):
            return ("state", "")
        attributes = state.get("attributes")
        if attributes is None:
            return ("state", attributes)

        device_class = attributes.get("device_class")
        device_class = device_class if device_class is not None else "state"
        return (device_class, attributes)

    @sync_wrapper
    async def get_obj(self, entity_id: str) -> Any:
        sensor_obj = h.stored_get(entity_id, g.sensor_register)
        if sensor_obj is not None:
            return sensor_obj
        if await self.entity_exists(entity_id):
            domain, _ = h.split_entity(entity_id)
            attributes: dict = {}
            if domain == "sensor":
                sensor_type, attributes = await self._get_sensor_type(entity_id)
                if sensor_type == "state":
                    sensor_obj = StateSensorObj(self, entity_id, attributes=attributes)
                elif sensor_type == "temperature":
                    sensor_obj = TemperatureSensorObj(
                        self, entity_id, attributes=attributes
                    )
                elif sensor_type == "timestamp":
                    sensor_obj = TimeSensorObj(self, entity_id, attributes=attributes)
            elif domain == "binary_sensor":
                sensor_obj = BinarySensorObj(self, entity_id, attributes=attributes)
        if sensor_obj is not None:
            h.stored_push(entity_id, g.sensor_register, sensor_obj)
        return sensor_obj

    @sync_wrapper
    async def binary_sensor(
        self, entity_id: str, default: BoolType = None
    ) -> BinarySensorObj:
        sensor: BinarySensorObj = await self.get_obj(entity_id)
        if sensor is None:
            raise ValueError(f"Sensor {entity_id} is not defined")
        return sensor

    @sync_wrapper
    async def number_sensor(self, entity_id: str, default: int = 0) -> NumberSensorObj:
        sensor: NumberSensorObj = await self.get_obj(entity_id)
        if sensor is None:
            raise ValueError(f"Sensor {entity_id} is not defined")

        sensor.sync_state = default
        return sensor

    @sync_wrapper
    async def state_sensor(
        self, entity_id: str, default: StrType = None
    ) -> StateSensorObj:
        sensor: StateSensorObj = await self.get_obj(entity_id)
        if sensor is None:
            raise ValueError(f"Sensor {entity_id} is not defined")

        await sensor.async_set_entity_state(default)
        return sensor

    @sync_wrapper
    async def time_sensor(self, entity_id: str) -> TimeSensorObj:
        sensor: TimeSensorObj = await self.get_obj(entity_id)
        self.info(sensor)
        if sensor is None:
            raise ValueError(f"Sensor {entity_id} is not defined")
        return sensor

    @sync_wrapper
    async def temperature_sensor(self, entity_id: str) -> TemperatureSensorObj:
        sensor: TemperatureSensorObj = await self.get_obj(entity_id)
        if sensor is None:
            raise ValueError(f"Sensor {entity_id} is not defined")
        return sensor

    def register_sensor(self, sensor: SensorType):
        """
        if sensor.linked_entity is not None and len(sensor.linked_entity) > 0:
            self.debug(f"Registering: {sensor}")
            sensor.state = self.get_state(sensor.linked_entity)

            # self._set_attr_from_linked(sensor)

            sensor.friendly_name = h.par(sensor.attributes, "friendly_name")
            if not sensor.friendly_name:
                _, sensor.friendly_name = self.split_entity(sensor.entity_id)
        sensor.attributes.update({"friendly_name": sensor.friendly_name})
        """

        if sensor.entity_id is not None:
            if h.stored_exists(sensor.entity_id, g.sensor_register):
                self.error(f"Entity {sensor.entity_id} already registered")
            else:
                h.stored_push(sensor.entity_id, g.sensor_register, sensor)

    def sync_update_timestamp(self, entity_id) -> bool:
        self.info(f"Sync update timestamp {entity_id}")
        sensor: TimeSensorObj = self.get_obj(entity_id)  # type:ignore
        if sensor is None:
            self.error(f"Not found: {entity_id}")
            return False
        sensor.update_timestamp()
        return True

    async def update_timestamp(self, entity_id) -> bool:
        self.info(f"Sync update timestamp {entity_id}")
        sensor: TimeSensorObj = await self.get_obj(entity_id)
        if sensor is None:
            self.error(f"Not found: {entity_id}")
            return False
        state = dt.get_iso_timestamp()
        await sensor.async_set_entity_state(state)
        return True
