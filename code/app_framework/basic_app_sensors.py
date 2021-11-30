from apd_types import APBAsicAppSensors, SensorsABC, SensorsType
from basic_app import AppApf, HassBasicApp
from bootstart import apf_module
from helper_tools import MyHelp as h


class BasicAppSensors(APBAsicAppSensors):
    def initialize(self):
        super().initialize()
        self._sensors: SensorsType = None

    def activate_sensors(self) -> SensorsABC:
        """Activate sensors module, can be used repeately

        Returns:
            SensorsABC: [description]
        """
        if self._sensors is None:
            self._sensors: SensorsType = self.sync_get_app("sensors")
            assert self._sensors is not None
        return self._sensors

    @property
    def sensors(self) -> SensorsABC:
        retval = self.activate_sensors()
        if h.is_async(retval):
            raise ValueError("Wrong using of Sensors. Activate in sync")
        return retval

    async def init_sensors(self):
        if self._sensors is None:
            self._sensors: SensorsType = await self.async_get_app("sensors")


class AppApfSensors(AppApf, BasicAppSensors):
    @apf_module
    def initialize(self):
        super().initialize()
        BasicAppSensors.initialize(self)
        self.activate_sensors()


class HassBasicAppSensors(HassBasicApp, BasicAppSensors):
    def initialize(self):
        super().initialize()
        BasicAppSensors.initialize(self)
        self.activate_sensors()
