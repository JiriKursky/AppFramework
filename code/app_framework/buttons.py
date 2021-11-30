from dataclasses import dataclass
from apd_types import ApHass

from helper_tools import MyHelp as h
from globals import ON
from globals_def import eventsDef as e, constsDef as c
from typing import Any, Callable, Coroutine, Optional, Union
from helper_types import RegisterType, StrType

register_button: RegisterType = []


@dataclass
class BinaryButton:
    hass: ApHass
    callback: Any = None
    trigger: StrType = None
    entity_id: StrType = None

    def __post_init__(self):
        if self.trigger is not None:
            self.hass.sync_listen_event(self._catch_event, self.trigger)
        if self.callback is not None and self.entity_id is not None:
            self.hass.debug(f"{self.entity_id} {self.callback}")
            self.hass.listen_state(self._catch_event, self.entity_id, new=ON)  # type: ignore

    async def _catch_event(self, *kwargs):
        if h.is_async(self.callback) and callable(self.callback):
            await self.callback()
        elif callable(self.callback):
            await self.hass.run_in_executor(self.callback)
