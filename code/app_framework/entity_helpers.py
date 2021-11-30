# Helping for getting current
from dataclasses import dataclass, field
from typing import NoReturn
from apd_types import ChildObjectBasicApp, HandlerCreateTaskType
from helper_types import FloatType


CURRENT_LOOP = 2


@dataclass
class WatchCurrent(ChildObjectBasicApp):
    entity_current: str = ""
    auto_start: bool = True
    _current: FloatType = field(default=None)
    _current_watch: HandlerCreateTaskType = field(default=None)

    async def __aenter__(self):
        if self.auto_start:
            await self.run(True)

    @property
    def current(self) -> float:
        if self._current is None:
            return 0
        return self._current

    def _watch_cancel(self):
        if self._current_watch is not None:
            self._current_watch.cancel()
            self._current_watch = None
        self._current = None

    def terminate(self):
        self._watch_cancel()

    async def run(self, yes: bool):
        if yes:
            if self._current_watch is None:
                self._current = None
                self._current_watch = await self.create_task(self._loop())
                while self._current is None:
                    await self.sleep(1)
        else:
            self._watch_cancel()

    async def _loop(self) -> NoReturn:
        while True:
            self._current = await self._ba.get_state_float(self.entity_current)
            self.debug(f"Current: {self._current}")
            await self.sleep(CURRENT_LOOP)
