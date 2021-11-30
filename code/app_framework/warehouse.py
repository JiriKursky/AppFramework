# Obsolete
from typing import Any
from bootstart import boot_logger, boot_module
import hassapi as hass  # type:ignore
from helper_types import ListStr, RegisterType
from helper_tools import INDEX_KEY, STORED, MyHelp as h
import globals as g
from globals_def import eventsDef as e
from bootstart import ModuleClasses


class Warehouse(hass.Hass):
    end_trigger = e.BOOT_MODULE_DONE

    @boot_logger
    @boot_module
    def initialize(self):
        self._container: RegisterType = []

    def init(self):
        self.logger.debug("Init")

    def register_container(self, name: str, container: RegisterType = []):
        if not h.stored_exists(name, self._container):
            h.stored_push(name, self._container, container)

    def get_container(self, name) -> RegisterType:
        container = h.stored_get(name, self._container)
        if container is None:
            raise ValueError(f"Container {name}  not exists")
        return container

    def push(self, container_name: str, index_key: str, sentence: Any):
        container = self.get_container(container_name)

        h.stored_push(index_key, container, sentence)

    def get(self, container_name: str, index_key: str) -> Any:
        container = self.get_container(container_name)
        return h.stored_get(index_key, container)

    def remove(self, container_name: str, index_key: str) -> Any:
        container = self.get_container(container_name)
        return h.stored_remove(index_key, container)

    def replace(self, container_name: str, index_key: str, sentence: Any) -> Any:
        container = self.get_container(container_name)
        h.stored_replace(index_key, container, sentence)

    def clear_container(self, container_name: str, condition_to_delete):
        container = self.get_container(container_name)
        to_delete: list = []
        for p in container:
            if condition_to_delete(p[STORED]):
                to_delete.append(p[INDEX_KEY])
        for name in to_delete:
            h.stored_remove(name, container)
