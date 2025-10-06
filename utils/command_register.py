import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Awaitable
from typings.command_properties import CommandProperties

if TYPE_CHECKING:
    from main import UpgradeMyWindowsBot

COMMANDS: dict[
    str,
    CommandProperties,
] = {}


def command_register(
    name: str,
    super_chat_only: bool = False,
    mods_only: bool = False,
    owner_only: bool = False,
):
    def decorator(func):
        COMMANDS[name] = {
            "func": func,
            "super_chat_only": super_chat_only,
            "mods_only": mods_only,
            "owner_only": owner_only,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
