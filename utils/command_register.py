import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Awaitable

if TYPE_CHECKING:
    from main import UpgradeMyWindowsBot

COMMANDS: dict[
    str,
    Callable[
        ["UpgradeMyWindowsBot", list[str]],
        Awaitable[None],
    ],
] = {}


def command_register(name: str):
    def decorator(func):
        COMMANDS[name] = func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
