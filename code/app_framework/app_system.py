# Going throw global_modules and adding entities in g.helper_register
# Part of Sanitarize
# version: 1.2
import asyncio
from typing import Union
from apd_types import ApHass


import globals as g
import yaml
import os
import re
import ntpath
from helper_tools import MyHelp as h
from bootstart import boot_logger, boot_logger_off, boot_module

GLOBAL_LIST: Union[list, None] = None

# Tags in global files
START_TAG = "@auto_create"
END_TAG = "@end"


class AppSystem(ApHass):
    """Control of creating user defined entities
    Reading all globals and searching @auto_create and @end
    fire e.ENTITIES_CREATED to allow listening - entities defined

    Args:
        BasicApp (object): root class
    """

    @boot_logger_off
    @boot_module
    def initialize(self):
        # There is defined call of entities_defined
        self.handler_event_done = None

        # Listening to event when entity_id is created
        # sending entity_id

    # Divne
    def init(self):
        self.debug("Init AppSystem")

    def _store_entity_add(self, entity_id, attr):
        """By app_system to store founds
        Args:
            entity_id ([type]): [description]
            attr ([type]): [description]
        """
        # self.logger.debug(entity_id)
        stored_entity_id = h.stored_get(entity_id, g.helper_register)
        if stored_entity_id is None:
            h.stored_push(entity_id, g.helper_register, attr)
        else:
            self.error(f"Duplicated: {entity_id}")

    def _parse(self, filename: str, pattern_def: tuple):
        lines: list = []

        # Reading file
        with open(filename) as f:
            lines = f.readlines()
        start_block = False
        d_after_at = "#\s*(.*)"  # type: ignore

        for line in lines:
            if start_block:
                if END_TAG in line:
                    start_block = False
            if start_block:
                for pattern in pattern_def:
                    found = re.search(pattern, line)
                    if found:
                        entity_id = found.group(0)[1:-1]
                        attr = {}
                        found = re.search(d_after_at, line)
                        if found:
                            after_at = found.group(0)[1:].strip()
                            try:
                                attr = eval(after_at)
                            except Exception as error:
                                self.debug(f"Error: {entity_id} {error.args}")
                                continue
                        else:
                            attr = {}
                        self._store_entity_add(entity_id, attr)
            if not start_block:
                start_block = START_TAG in line

    def _parse_file(self, file_path: str, name: str, patterns):
        if GLOBAL_LIST is not None and len(GLOBAL_LIST) > 0:
            if not name in GLOBAL_LIST:
                self.debug(f"{name} will not be added - GLOBAL_LIST defined")
                return
        filename = file_path + "/" + name + ".py"

        if os.path.exists(filename):
            try:
                self._parse(filename, patterns)
            except:
                self.error(f"Fatal error in {filename}")
        else:
            self.error(f"Error in f - not found: {filename}")

    async def execute(self, buffer_com: asyncio.Queue) -> None:
        """Read from *.yaml all global modules defined in *.yaml block global_modules for parsing. Files can be in GLOBAL_LIST"""
        self.debug("Starting execute")
        g.helper_register.clear()
        types = (
            "input_boolean",
            "input_number",
            "input_text",
            "sensor",
            "binary_sensor",
        )
        patterns: list = []
        for t in types:
            patterns.append('"' + t + '.(.+?)"')

        yaml_files = h.get_apps_yaml_files(self)

        for yaml_filename in yaml_files:
            self.debug(yaml_filename)
            data_loaded: dict = {}
            try:
                with open(yaml_filename, "r") as stream:
                    data_loaded = yaml.safe_load(stream)
                if not data_loaded:
                    self.error("Fatal error in reading apps.yaml")
                    return
            except:
                self.error(f"Fatal error in parsing: {yaml_filename}")
            glob = h.par(data_loaded, "global_modules")
            if glob is None:
                continue

            file_path = ntpath.dirname(os.path.realpath(yaml_filename))

            if h.is_string(glob):
                self._parse_file(file_path, glob, patterns)
                continue
            # Main creating
            for f in glob:
                self._parse_file(file_path, f, patterns)
        buffer_com.task_done()
