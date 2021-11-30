from abc import ABC, abstractmethod
from asyncio.futures import Future
from asyncio import Queue
from dataclasses import replace
import dataclasses
from datetime import datetime
from enum import Enum


from typing import (
    Any,
    Coroutine,
    Dict,
    Final,
    List,
    Tuple,
    Union,
    TypeVar,
    Callable,
)


class BlindLogger:
    def info(self, msg: Any, *args, **kwargs):
        pass

    def log(self, msg: Any, *args, **kwargs):
        pass

    def error(self, msg: Any, *args, **kwargs):
        pass

    def debug(self, msg: Any, *args, **kwargs):
        pass

    def warning(self, msg: Any, *args, **kwargs):
        pass


FutureType = Union[Future, None]
StrType = Union[None, str]
FloatType = Union[None, float]
DictType = Union[None, dict]
IntType = Union[None, int]
EntityObjectType = Union[None, object]
DateTime = datetime
DateTimeType = Union[None, datetime]
StoredSentence = dict
CALLABLE_T = TypeVar("CALLABLE_T", bound=Callable)
TupleType = Union[None, tuple]
BoolType = Union[bool, None]
StoredItem = Dict[str, Any]
RegisterType = Union[List[StoredItem], list]
ListStr = Union[tuple, List[str]]
KwargParam = Any
ParamType = Union[list, dict]
CoordinatesType = Union[dict, None]
EntityListType = List[str]
ConstStrType = Final[str]
ConstBoolType = Final[bool]
ConstIntType = Final[int]
ConstFloatType = Final[float]
EntityNameConst = ConstStrType
EntityName = str
EntityNameType = Union[EntityName, None]
ListType = Union[list, None]
StateType = Union[None, str, int, float]
CallableType = Union[Callable, None]
EnumType = Union[Enum, None]
ObjectType = Union[object, None]
CoroutinePointer = Union[Coroutine, None]
StateQuestionType = Union[Enum, Tuple[Enum, ...], None]
EnumStrType = Union[Enum, str, None]
QueueType = Union[Queue, None]
CoroutineDefaultType = Union[Any, Any, None]
DictKeys = Dict[str, Any]
InstanceNameType = Union[Enum, str, None]
TaskNameType = Union[Enum, str]
DictList = Dict[str, dict]
DictListDef = Final[DictList]
DictMixed = Union[dict, tuple]


class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):  # type:ignore
        return name


def update_from_dict(zdroj: dict, cil: Any):
    for key, value in zdroj.items():
        if hasattr(cil, key):
            setattr(cil, key, value)
    return cil


def update_dataclass(zdroj: Any, cil: Any):
    for key, value in dataclasses.asdict(zdroj).items():
        setattr(cil, key, value)
    return cil


def _generate_update(field: Any, new: dict, new_class: Any):
    """Update a field to the new value, or instantiated the class and return the updated or new.

    Args:
        field (None|State Class): current value of the to be updated field.
        new (dict): new values coming back from the api.
        new_class (State Class): Class to instantiate the value with if necessary.

    Returns:
        (new_class): new value of the type that was passed as the new_class.

    """

    if field:
        retval = None
        try:
            retval = replace(field, **new)
        except:
            pass
        return retval
    return new_class(**new)


def generate_update(field: Any, new: dict, new_class: Any) -> Any:
    """Update a field to the new value, or instantiated the class and return the updated or new.

    Args:
        field (None|State Class): current value of the to be updated field.
        new (dict): new values coming back from the api.
        new_class (State Class): Class to instantiate the value with if necessary.

    Returns:
        (new_class): new value of the type that was passed as the new_class.

    """

    if dataclasses.is_dataclass(field):
        return replace(field, **new)
    return new_class(**new)
