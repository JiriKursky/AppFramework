from dataclasses import is_dataclass
from attr import dataclass
import hassapi as hass  # type:ignore
from functools import wraps
from helper_tools import MyHelp as h
import asyncio

debug_allowed = []  # name of modules where is debug allowed


def apf_logger(func):
    @wraps(func)
    def wrapper(hass: hass.Hass):
        try:
            log = hass.get_user_log("apf_logger")
        except:
            log = None
        if log is not None:
            module_name = h.module_name(hass)
            hass.logger = log
            hass.set_log_level("INFO")
            if h.in_array(module_name, debug_allowed):
                hass.set_log_level("DEBUG")
            hass.debug = hass.logger.debug
            hass.error = hass.logger.error
            hass.warning = hass.logger.warning
            hass.info = hass.logger.info
        return func(hass)

    return wrapper


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


def sync_wrapper(coro):
    @wraps(coro)
    def inner_sync_wrapper(self, *args, **kwargs):
        is_async = None
        try:
            # do this first to get the exception
            # otherwise the coro could be started and never awaited
            asyncio.get_event_loop()
            is_async = True
        except RuntimeError:
            is_async = False

        if is_async is True:
            # don't use create_task. It's python3.7 only
            f = asyncio.ensure_future(coro(self, *args, **kwargs))
            self.AD.futures.add_future(self.name, f)
        else:
            f = run_coroutine_threadsafe(self, coro(self, *args, **kwargs))

        return f

    return inner_sync_wrapper


def nested_dataclass(*args, **kwargs):  # noqa: D202
    """Wrap a nested dataclass object."""

    def wrapper(cls):
        cls = dataclass(cls, **kwargs)
        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            for name, value in kwargs.items():
                field_type = cls.__annotations__.get(name, None)
                if hasattr(field_type, "__args__"):
                    inner_type = field_type.__args__[0]
                    if is_dataclass(inner_type):
                        new_obj = [inner_type(**dict_) for dict_ in value]
                        kwargs[name] = new_obj
                else:
                    if is_dataclass(field_type) and isinstance(value, dict):
                        new_obj = field_type(**value)
                        kwargs[name] = new_obj

            original_init(self, *args, **kwargs)

        cls.__init__ = __init__
        return cls

    return wrapper(args[0]) if args else wrapper


def overrides(interface_class):
    def overrider(method):
        assert method.__name__ in dir(
            interface_class
        ), f"Wrong override {method.__name__}"
        return method

    return overrider
