""" Static functions for simplified coding """

from enum import Enum
from inspect import iscoroutine, iscoroutinefunction
from logging import raiseExceptions
import pytz  # type: ignore
import datetime
import time
import os
import uuid
from apd_types import APBasicApp
import globals as g
import yaml  # type: ignore
from pathlib import Path
from globals import ON, OFF
from functools import wraps
import asyncio
import globals as g

from helper_types import (
    BoolType,
    DateTime,
    DateTimeType,
    DictKeys,
    DictMixed,
    EntityName,
    EnumStrType,
    IntType,
    StateType,
    StrType,
    KwargParam,
    ListStr,
    RegisterType,
    StoredSentence,
)

from typing import (
    Any,
    List,
    Union,
)  # avoid recurse

INDEX_KEY = "index_key"
STORED = "_stored"


def sync_wrapper(coro):
    @wraps(coro)
    def inner_sync_wrapper(self, *args, **kwargs):
        iscoroutine = None
        try:
            # do this first to get the exception
            # otherwise the coro could be started and never awaited
            asyncio.get_event_loop()
            iscoroutine = True
        except RuntimeError:
            iscoroutine = False

        if iscoroutine is True:
            # don't use create_task. It's python3.7 only
            f = asyncio.ensure_future(coro(self, *args, **kwargs))
            self.AD.futures.add_future(self.name, f)
        else:
            f = run_coroutine_threadsafe(self, coro(self, *args, **kwargs))

        return f

    return inner_sync_wrapper


def run_coroutine_threadsafe(self, coro):
    result = None
    if self.AD.loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, self.AD.loop)
        try:
            result = future.result(self.AD.internal_function_timeout)
        except asyncio.TimeoutError:
            if hasattr(self, "logger"):
                self.logger.warning(
                    "Coroutine (%s) took too long (%s seconds), cancelling the task...",
                    coro,
                    self.AD.internal_function_timeout,
                )
            else:
                print(
                    "Coroutine ({}) took too long, cancelling the task...".format(coro)
                )
            future.cancel()
    else:
        self.logger.warning("LOOP NOT RUNNING. Returning NONE.")

    return result


class StrOp:
    def __init__(self):
        pass

    @staticmethod
    def str_time_to_sec(s_time=str) -> int:
        if s_time == g.UNAVAILABLE:
            return 0
        try:
            date_time_obj = datetime.datetime.strptime(
                s_time, "%Y-%m-%dT%H:%M:%S.%f+00:00"
            )
        except:
            date_time_obj = None
        if not date_time_obj:
            try:
                date_time_obj = datetime.datetime.strptime(
                    s_time, "%Y-%m-%d %H:%M:%S.%f+00:00"
                )
            except:
                date_time_obj = None
        if not date_time_obj:
            try:
                date_time_obj = datetime.datetime.strptime(
                    s_time, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
            except:
                date_time_obj = None

        if not date_time_obj:
            return 0
        date_time_obj += datetime.timedelta(hours=1)
        sec = int(time.mktime(date_time_obj.timetuple()))
        return sec


class MyHelp(object):
    def __init__(self):
        pass

    @staticmethod
    def get_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def enum_to_str(source: dict) -> dict:
        retval: dict = {}
        for key, item in source.items():

            if isinstance(item, Enum):
                n_item = item.value
            else:
                n_item = item
            if isinstance(key, Enum):
                retval[key.value] = n_item
            else:
                retval[key] = n_item
        return retval

    @staticmethod
    def get_dict(source: DictMixed) -> dict:
        if isinstance(source, dict):
            return MyHelp.enum_to_str(source)
        elif isinstance(source, tuple):
            retval: dict = {source[0]: source[1]}
            return MyHelp.enum_to_str(retval)

    @staticmethod
    def get_str(value: EnumStrType) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value
        return str(value.value)

    @staticmethod
    def is_list(myvar) -> bool:
        return isinstance(myvar, list)

    @staticmethod
    def is_int(myvar) -> bool:
        return isinstance(myvar, int)

    @staticmethod
    def is_tuple(myvar) -> bool:
        return isinstance(myvar, tuple)

    @staticmethod
    def is_array(myvar):
        if myvar is None:
            return False
        return isinstance(myvar, list) or isinstance(myvar, tuple)

    @staticmethod
    def is_bool(myvar):
        return isinstance(myvar, bool)

    @staticmethod
    def is_dict(myvar):
        return isinstance(myvar, dict)

    @staticmethod
    def is_string(myvar) -> bool:
        return isinstance(myvar, str)

    @staticmethod
    def is_iterable(myvar: Any):
        return hasattr(myvar, "__iter__")

    @staticmethod
    def split_entity(entity_id: str):
        return entity_id.split(".")

    @staticmethod
    def entity_id(domain: str, name: str) -> str:
        return f"{domain}.{name}"

    @staticmethod
    def module_name(hass: object) -> str:
        return hass.__class__.__name__

    @staticmethod
    def stored_walk(callback: object, store_db, max_count: IntType = None) -> None:
        count = 0
        for p in store_db:
            count += 1
            key, sentence = MyHelp.decode_stored(p)
            callback(key, sentence)  # type: ignore
            if max_count is not None:
                if count >= max_count:
                    return

    @staticmethod
    async def async_stored_walk(
        callback: object, store_db, max_count: IntType = None
    ) -> None:
        count = 0
        for p in store_db:
            count += 1
            key, sentence = MyHelp.decode_stored(p)
            await callback(key, sentence)  # type: ignore
            if max_count is not None:
                if count >= max_count:
                    return

    @staticmethod
    def stored_exists(index_key: Union[str, int], store_db: RegisterType) -> bool:
        return MyHelp.stored_get(index_key, store_db) is not None

    @staticmethod
    def stored_push(
        index_key: Union[str, int], store_db: RegisterType, sentence: Any
    ) -> None:
        """Storing

        Args:
            index_key (str): Index key for to identify
            store_db (list): stored list
            sentence (dict|str|object): To be stored
        """
        if store_db is None:
            return

        to_store: dict = {INDEX_KEY: MyHelp.index_key_to_str(index_key)}
        if MyHelp.is_dict(sentence):
            to_store.update(sentence)
        else:
            to_store: dict = {
                INDEX_KEY: index_key,
                STORED: sentence,
            }
        store_db.append(to_store)

    @staticmethod
    def file_exists(filename: str) -> bool:
        """Checking if file exists

        Args:
            filename (str): including path

        Returns:
            bool: True if exists
        """

        my_file = Path(filename)
        return my_file.is_file()

    @staticmethod
    def decode_stored(sentence: StoredSentence) -> tuple:
        stored = MyHelp.par(sentence, STORED, None)
        if stored is None:
            attr = sentence.copy()
            index_key = MyHelp.par(attr, INDEX_KEY)
            MyHelp.remove_key(attr, INDEX_KEY)
            return (index_key, attr)
        else:
            return (MyHelp.par(sentence, INDEX_KEY), stored)

    @staticmethod
    def index_key_to_str(index_key: Union[str, int]) -> str:
        if MyHelp.is_string(index_key):
            return index_key  # type: ignore
        else:
            return str(index_key)

    @staticmethod
    def stored_item(index_key: Union[str, int], store_db: RegisterType) -> Any:
        if not MyHelp.is_iterable(store_db):
            return None
        s_index_key = MyHelp.index_key_to_str(index_key)
        stored = next(
            (item for item in store_db if item[INDEX_KEY] == s_index_key), None
        )
        return stored

    @staticmethod
    def stored_get(index_key: Union[str, int], store_db: RegisterType) -> Any:
        """Return from store_db sentence with

        Args:
            index_key (str): Index key for to identify
            store_db (dict): stored list

        Returns:
            dict|type|None: Stored sentence or directly stored type if was save without dict
        """
        if index_key is None:
            return None
        stored = MyHelp.stored_item(MyHelp.index_key_to_str(index_key), store_db)
        if stored is not None:
            if STORED in stored.keys():
                stored = stored[STORED]
        return stored

    @staticmethod
    def stored_get_stored(register: RegisterType) -> list:
        retval: list = []
        for p in register:
            _, sentence = MyHelp.decode_stored(p)
            retval.append(sentence)
        return retval

    @staticmethod
    def stored_remove(index_key: Union[str, int], store_db: RegisterType) -> Any:
        """Return from store_db sentence with

        Args:
            index_key (str): Index key for to identify
            store_db (dict): stored list

        Returns:
            dict|type|None: Stored sentence
        """
        if not MyHelp.is_iterable(store_db) or store_db is None:
            return
        s_index_key = MyHelp.index_key_to_str(index_key)
        stored = next(
            (item for item in store_db if item[INDEX_KEY] == s_index_key), None
        )
        if stored is not None:
            store_db.remove(stored)
        return stored

    @staticmethod
    def stored_replace(
        index_key: Union[str, int], store_db: RegisterType, sentence: Any
    ) -> None:
        reg = MyHelp.stored_get(index_key, store_db)
        if reg is not None:
            reg = MyHelp.stored_remove(index_key, store_db)
        MyHelp.stored_push(index_key, store_db, sentence)

    @staticmethod
    def in_array(to_search: str, arr: Union[list, DictKeys]) -> bool:
        if isinstance(arr, list):
            try:
                a = arr.index(to_search)
                return True
            except:
                return False
        elif isinstance(arr, dict):
            try:
                return MyHelp.in_array(to_search, list(arr.keys()))
            except:
                raise ValueError("Wrong argument in_array")

    @staticmethod
    def add_backslash(path: str) -> str:
        if path[-1] != "/":
            return path + "/"
        else:
            return path

    @staticmethod
    def apps_path() -> str:
        """Get path of apps
        before activation it is not possible to use self.app_dir

        Returns:
            StrType: path|None
        """

        to_find = "/apps/"
        file_path = os.path.realpath(__file__)
        index = file_path.index(to_find)
        if index > 0:
            path = file_path[0:index] + to_find
            return MyHelp.add_backslash(path)
        else:
            return ""

    @staticmethod
    def attr(attributes):
        return {key: None for key in attributes}

    @staticmethod
    def append_entity_register(entity_id: EntityName):
        if not MyHelp.in_array(entity_id, g.entity_register):
            g.entity_register.append(entity_id)

    @staticmethod
    def config_path() -> str:
        """Get path of apps

        Returns:
            StrType: path|None

        """
        to_find = "/"
        file_path = os.path.realpath(__file__)
        index = file_path.index(to_find, 1)
        if index > 0:
            path = file_path[0:index]
        else:
            path = ""
        return MyHelp.add_backslash(path)

    @staticmethod
    def www_path() -> str:
        path = MyHelp.config_path()
        return path + "www/"

    @staticmethod
    def create_dir(dir_name: str) -> str:
        if os.path.isdir(dir_name):
            return dir_name
        try:
            os.mkdir(dir_name)
        except:
            pass
        return dir_name

    @staticmethod
    def storage_path() -> str:
        config = MyHelp.config_path()
        path = MyHelp.create_dir(config + "data")
        return MyHelp.add_backslash(path)

    @staticmethod
    def get_first_key_in_dict(source: dict) -> StrType:
        key_list = source.keys()
        if len(key_list) == 0:
            return None
        key_iterator = iter(key_list)
        return next(key_iterator)

    @staticmethod
    def remove_key(
        param: Union[list, dict], key: Union[str, List[str]], default: Any = None
    ) -> Any:
        """Delete from dictionary or list with key

        Args:
            param (list|dict): source
            key (type): to be pop
        Returns:
            type: without key
        """
        retval_list: list = []
        retval = default
        if isinstance(key, list):
            for k in key:
                retval_list.append(MyHelp.remove_key(param, k))
            return retval_list
        if isinstance(param, list) and isinstance(key, str):
            if MyHelp.in_array(key, param):
                retval = key
                param.remove(key)
        elif isinstance(param, dict) and isinstance(key, str):
            if key in param.keys():
                retval = param.get(key, default)
                del param[key]
        return retval

    @staticmethod
    def get_yaml(filename: str) -> dict:
        """Returning yaml

        Args:
            filename (str): source

        Returns:
            dict|None: dictionary
        """
        try:
            with open(filename, "r") as stream:
                data_loaded = yaml.safe_load(stream)
                return data_loaded
        except FileNotFoundError as e:
            return {}

    @staticmethod
    def save_yaml(filename: str, data: dict, sort_keys: bool = False) -> BoolType:
        try:
            with open(filename, "w") as stream:
                yaml.dump(
                    data, stream, indent=4, sort_keys=sort_keys, allow_unicode=True
                )
            return True
        except:
            raise ValueError("Cannot write into %s", filename)
        return False

    @staticmethod
    def delete_file(filename: str):
        if os.path.exists(filename):
            os.remove(filename)

    @staticmethod
    def par(param: Any, k: Union[str, list], default=None) -> Any:
        """Returning value from param dictionary
        Args:
            param (dict): Source where will be searching
            k (str,list,tuple): searching
            default (type, optional): default vale. Defaults to None.

        Returns:
            type: value
        """
        if not param:
            return default
        if MyHelp.is_dict(param):
            if k in param.keys():
                return param[k]
            else:
                return default
        if MyHelp.is_array(k):
            ret_val = []
            for j in k:
                ret_val.append(MyHelp.par(param, j))  # type: ignore
            return ret_val
        if k in param:
            return param[k]
        else:
            return default

    @staticmethod
    def vrat_on_off(yes: bool) -> str:
        if yes:
            return ON
        return OFF

    @staticmethod
    def all_true(d: dict) -> bool:
        return next((item for item in d.values() if not item), True)

    @staticmethod
    def decode_args(args, params: tuple) -> list:
        retval: list = [None] * len(params)

        if not MyHelp.is_tuple(args):
            return retval
        if len(args) != 1:
            return retval

        retval.clear()
        oper = args[0]
        if MyHelp.is_dict(oper):
            for k in oper.values():
                retval.append(MyHelp.par(args[0], k, None))
        else:
            for k in params:
                retval.append(MyHelp.par(args[0], k, None))
        return retval

    @staticmethod
    def kwarg_split(
        kwargs: KwargParam,
        param: Union[str, ListStr],
        default: Any = None,
    ) -> Any:
        if MyHelp.is_list(param):
            ret_val: list = []
            for p in param:
                ret_val.append(MyHelp.kwarg_split(kwargs, p, default))
            return ret_val
        if len(kwargs) > 0:
            k = kwargs[1]
            return MyHelp.par(k, param, default)  # type:ignore
        else:
            return default

    @staticmethod
    def entity_from_event(kwargs) -> str:
        """Returning entity_id from calling event

        Args:
            kwargs (type): [description]

        Returns:
            str: event_id
        """
        return MyHelp.kwarg_split(kwargs, "entity_id")

    @staticmethod
    def yes(value: Any):
        """[summary]

        Args:
            value (type): to decode yes

        Returns:
            True if value is considered as "on"
        """
        return value == True or value == ON or value == g.PLAYING or value == g.HEAT

    @staticmethod
    def on_off(value: bool) -> str:
        """Converting bool to string ON,OFF

        Args:
            value (bool): [description]

        Returns:
            str: [description]
        """

        return ON if value else OFF

    @staticmethod
    def getting_on(old, new) -> bool:
        return (
            ((old == OFF) or (old == g.IDLE))
            and ((new == ON or new == g.PLAYING))
            or ((old == OFF) and (new == g.HEAT))
        )

    @staticmethod
    def getting_off(old, new) -> bool:
        return (old == ON or old == g.PLAYING) and (new == OFF or new == g.IDLE)

    @staticmethod
    def getting_off_on(old, new) -> bool:
        return MyHelp.getting_on(old, new) or MyHelp.getting_off(old, new)

    @staticmethod
    def update_strict(d: dict, to_update: dict) -> None:
        """Like dict.update but without adding new key
          args.update((k, to_parse[k]) for k in args.keys() & to_parse.keys())
        Args:
            d (dict): target
            to_update (dict): source
        """
        if not to_update:
            return
        d.update((k, v) for k, v in to_update.items() if k in d)

    @staticmethod
    def create_sub_dir(dir_name: str, base_file: str):
        file_path = MyHelp.add_backslash(os.path.dirname(base_file))
        file_path += dir_name
        MyHelp.create_dir(file_path)
        return file_path

    @staticmethod
    def get_apps_yaml_files(hass) -> list:
        retval: list = []
        path = MyHelp.add_backslash(hass.app_dir)
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".yaml"):
                    if root.find("docs") < 0:
                        if root[-1] == "/":
                            retval.append(root + f)
                        else:
                            retval.append(root + "/" + f)
        return retval

    @staticmethod
    def is_async(investigate) -> bool:
        return iscoroutine(investigate) or iscoroutinefunction(investigate)


class DateTimeOp:
    @staticmethod
    def naive_timezone(date: DateTime) -> DateTime:
        timezone = pytz.timezone(g.time_zone)
        return date.astimezone(timezone)

    @staticmethod
    def get_iso_timestamp() -> str:
        return f"{datetime.datetime.utcnow().isoformat()}+00:00"

    @staticmethod
    def just_now() -> DateTime:
        today = datetime.datetime.now()
        after_timezone = DateTimeOp.naive_timezone(today)
        return after_timezone

    @staticmethod
    def just_now_sec() -> float:
        dnes = DateTimeOp.just_now()
        dnes_sec = time.mktime(dnes.timetuple())  # type: ignore
        return dnes_sec

    @staticmethod
    def in_interval(start_time=str, end_time=str, compare=str) -> bool:
        i_start_time = StrOp.str_time_to_sec(start_time)
        i_end_time = StrOp.str_time_to_sec(end_time)
        i_compare = StrOp.str_time_to_sec(compare)
        return i_end_time <= i_compare >= i_start_time

    @staticmethod
    def get_all_state(hass, entity_id):
        return hass.get_state(entity_id, attribute="all")

    @staticmethod
    def get_last_update(hass, entity_id):
        all_state = DateTimeOp.get_all_state(hass, entity_id)
        s_last_updated = all_state["last_updated"][
            :19
        ]  # 2019-08-05T19:22:40.626824+00:00
        lu = datetime.datetime.strptime(s_last_updated, "%Y-%m-%dT%H:%M:%S")
        return lu + datetime.timedelta(hours=2)

    @staticmethod
    def get_update_dif(hass, entity_id):
        last_updated = DateTimeOp.get_last_update(hass, entity_id)
        return DateTimeOp.just_now() - last_updated  # type: ignore

    @staticmethod
    def _uprav_cas(date_time_obj, letni_cas: bool):
        if letni_cas:
            date_time_obj += datetime.timedelta(hours=2)
        else:
            date_time_obj += datetime.timedelta(hours=1)
        return date_time_obj

    @staticmethod
    def get_last_changed(parent: APBasicApp, entity_id: str):
        """Get last changed from attribute

        Args:
            parent (object): [description]
            entity_id (str): [description]

        Returns:
            [type]: [description]
        """

        date_time_str: StateType = parent.sync_get_attr_state(entity_id, "last_changed")
        # 2019-11-22T12:36:12.340577+00:00
        assert date_time_str is not None, "Issue with get_last_chaned"

        date_time_obj = datetime.datetime.fromisoformat(str(date_time_str))
        return date_time_obj

    @staticmethod
    async def async_get_last_changed(parent: APBasicApp, entity_id: str):
        """Get last changed from attribute

        Args:
            parent (object): [description]
            entity_id (str): [description]

        Returns:
            [type]: [description]
        """

        date_time_str: StateType = await parent.get_attr_state(
            entity_id, "last_changed"
        )

        # 2019-11-22T12:36:12.340577+00:00
        if date_time_str is None:
            return None

        date_time_obj = datetime.datetime.fromisoformat(str(date_time_str))
        return date_time_obj

    @staticmethod
    def get_last_changed_sec(parent: APBasicApp, entity_id: str) -> float:
        """Getting seconds from 1900

        Args:
            parent (object): [description]
            entity_id (str): [description]

        Returns:
            float: [description]
        """
        last_changed = DateTimeOp.get_last_changed(parent, entity_id)
        last_changed = DateTimeOp.naive_timezone(last_changed)
        sec = time.mktime(last_changed.timetuple())
        return sec

    @staticmethod
    def sync_get_changed_diff_sec(parent: APBasicApp, entity_id: str) -> float:
        """Vraci rozdil v sekundach kdy byla zmena

        Args:
            entity_id (str): entita

        Returns:
            float: rozdil ve vterinach
        """

        ted = DateTimeOp.just_now_sec()
        last_updated = DateTimeOp.get_last_changed_sec(parent, entity_id)

        return ted - last_updated

    @staticmethod
    async def get_changed_diff_sec(parent: APBasicApp, entity_id: str) -> float:
        """Vraci rozdil v sekundach kdy byla zmena

        Args:
            entity_id (str): entita

        Returns:
            float: rozdil ve vterinach
        """

        ted = await parent.run_in_executor(DateTimeOp.just_now_sec)
        last_updated = await parent.run_in_executor(
            DateTimeOp.get_last_changed_sec, parent, entity_id
        )
        assert ted is not None and last_updated is not None, "Issue with getting time"
        return float(ted) - float(last_updated)

    @staticmethod
    def dif_time_sec(s_time: str) -> float:
        """Z načteného stavu přepočte k aktuálnímu datumu vteřiny

        Args:
            s_time (str): čas zapsaný jako string
            letni_cas (bool): ano, pokud je letni cas

        Returns:
            float: [description]
        """
        ted = DateTimeOp.just_now_sec()
        date_time_obj = datetime.datetime.strptime(s_time, "%Y-%m-%dT%H:%M:%S.%f+00:00")
        sec = time.mktime(date_time_obj.timetuple())
        return ted - sec

    @staticmethod
    def convert_timedelta(duration):
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return hours, minutes, seconds

    @staticmethod
    def convert_to_datetime(tm_hour, tm_min, tm_second):
        now = DateTimeOp.just_now()
        return now.replace(hour=tm_hour, minute=tm_min, second=tm_second)  # type: ignore

    @staticmethod
    def is_in_time_interval(
        start_hour, start_min, start_second, end_hour, end_min, end_second
    ):
        now = DateTimeOp.just_now()
        start_time = DateTimeOp.convert_to_datetime(start_hour, start_min, start_second)
        end_time = DateTimeOp.convert_to_datetime(end_hour, end_min, end_second)
        return (now >= start_time) and (now <= end_time)  # type: ignore

    @staticmethod
    def is_in_hour_interval(start_hour: int, end_hour: int) -> bool:
        """Pokud je v daném intervalu, vrací True

        Args:
            start_hour (int): zacatek
            end_hour (int): konec

        Returns:
            bool: True, je-li v intervalu
        """
        return DateTimeOp.is_in_time_interval(start_hour, 0, 0, end_hour, 0, 0)
