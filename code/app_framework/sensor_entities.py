# from apps.app_framework.basic_app import BasicApp
from dataclasses import dataclass
from apd_types import APBasicApp

from decorators import sync_wrapper


from globals import ON, OFF
from helper_tools import DateTimeOp as dt, MyHelp as h
from helper_types import DictType, FloatType, StateType, StrType
from typing import Any, Union
import datetime
import asyncio

RT_STRING = "string"
RT_INTEGER = "integer"
RT_FLOAT = "float"


@dataclass
class SensorObj:
    _hass: APBasicApp = None  # type:ignore
    entity_id: StrType = None
    initial: StateType = None
    friendly_name: StrType = None
    attributes: DictType = None
    linked_entity: StrType = None
    _state_type: str = RT_STRING

    def __post_init__(self):
        assert self.entity_id is not None

        if self.attributes is not None:
            h.remove_key(self.attributes, "index_key")
            if (
                self.friendly_name is not None
                and self.attributes.get("friendly_name") is None
            ):
                if self.friendly_name is not None:
                    self.attributes.update({"friendly_name": self.friendly_name})
        if self.initial is not None:
            self._ini_state()

    @property
    def get_last_change(self):
        assert self.entity_id is not None
        return dt.sync_get_changed_diff_sec(self._hass, self.entity_id)

    @property
    async def async_get_last_change(self) -> float:
        assert self.entity_id is not None
        return await dt.get_changed_diff_sec(self._hass, self.entity_id)

    @property
    def entity_id_control(self):
        if self.linked_entity is not None:
            return self.linked_entity
        else:
            return self.entity_id

    def _ini_state(self):
        if self.linked_entity is not None:
            assert self._hass is not None
            self.initial = str(self._hass.sync_get_state(self.linked_entity))
            self._hass.sync_listen_state(self._listener, self.entity_id_control)
        self.sync_state = self.initial

    def _listener(self, entity, attribute, old, new, kwargs):
        if entity != self.entity_id_control or old == new:
            return
        if self.linked_entity:
            self.sync_state = new

    @property
    def sync_state(self) -> Any:
        return self._hass.sync_get_state(self.entity_id)

    @sync_state.setter
    def sync_state(self, state: Any):
        # self._hass.logger.error(f"State: {state}")
        self.set_entity_state(state)

    def set_entity_state(self, state: Any, attributes: DictType = None):
        if attributes is not None and self.attributes is not None:
            attributes.update(self.attributes)
        else:
            attributes = self.attributes
        self._hass.sync_call_service(
            "state/set",
            entity_id=self.entity_id,
            state=state,
            attributes=attributes,
            namespace="default",
        )

    async def async_set_entity_state(self, state: Any, attributes: DictType = None):
        if attributes is not None and self.attributes is not None:
            attributes.update(self.attributes)
        else:
            attributes = self.attributes
        assert self._hass is not None
        await self._hass.call_service(
            "state/set",
            entity_id=self.entity_id,
            state=state,
            attributes=attributes,
            namespace="default",
        )


@dataclass
class StateSensorObj(SensorObj):
    @property
    def get_float(self) -> float:
        assert self.entity_id is not None
        return self._hass.sync_get_state_float(self.entity_id)

    @property
    def get_int(self) -> float:
        assert self.entity_id is not None
        return self._hass.sync_get_state_int(self.entity_id)


StateSensorObjType = Union[StateSensorObj, None]


@dataclass
class BinarySensorObj(SensorObj):
    icon_on: StrType = None
    icon_off: StrType = None
    linked_entity_copy_attributes: bool = False

    async def async_set_entity_state(self, state: Any):
        if self.attributes is None:
            self.attributes = {}
        if self.icon_on is not None and self.icon_off is None:
            await self.async_set_entity_state(state)
            return
        if h.yes(state) and self.icon_on is not None:
            self.attributes.update({"icon": self.icon_on})

        elif not h.yes(state) and self.icon_off is not None:
            self.attributes.update({"icon": self.icon_off})
        if h.yes(state):
            state = ON
        else:
            state = OFF
        await super().async_set_entity_state(state)

    def set_entity_state(self, state: Any):
        """This is override and must be

        Args:
            state (Any): [description]
        """
        if self.attributes is None:
            self.attributes = {}
        if self.icon_on is not None and self.icon_off is None:
            super().set_entity_state(state)
            return
        if h.yes(state) and self.icon_on is not None:

            self.attributes.update({"icon": self.icon_on})
            super().set_entity_state(state)
            return

        elif not h.yes(state) and self.icon_off is not None:
            self.attributes.update({"icon": self.icon_off})
        if h.yes(state):
            state = ON
        else:
            state = OFF
        super().set_entity_state(state)

    @property
    def is_on(self):
        return self.state == ON

    @is_on.setter
    def is_on(self, value: str):
        self._hass.error("Here!")
        self.state = h.yes(value)


BinarySensorType = Union[BinarySensorObj, None]


@dataclass
class NumberSensorObj(SensorObj):
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        self.attributes.update({"device_class": "number"})
        super().__post_init__()


@dataclass
class TimeSensorObj(SensorObj):
    def __post_init__(self):
        assert self.entity_id is not None
        self.initial = self._hass.sync_get_attr_state(self.entity_id, "last_update")
        if self.initial is None:
            self.initial = str(dt.just_now())
        if self.attributes is None:
            self.attributes = {}
        self.attributes.update({"device_class": "timestamp"})
        super().__post_init__()

    def update_timestamp(self):
        """Provede update casoveho razitka sensoru"""
        state = dt.get_iso_timestamp()
        self.set_entity_state(state)


@dataclass
class TemperatureSensorObj(SensorObj):
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        self.attributes.update(
            {
                "device_class": "temperature",
                "unit_of_measurement": "°C",
            }
        )
        super().__post_init__()

    async def get_state(self) -> float:
        assert self.entity_id is not None
        retval: FloatType = await self._hass.get_state_float(self.entity_id)
        if retval is None:
            retval = 0
        return retval

    def sync_get_state(self) -> float:
        assert self.entity_id is not None
        retval: FloatType = self._hass.sync_get_state_float(self.entity_id)
        if retval is None:
            retval = 0
        return retval


TemperatureSensorObjType = Union[TemperatureSensorObj, None]
