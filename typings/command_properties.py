from typing import TypedDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Awaitable

if TYPE_CHECKING:
    from main import UpgradeMyWindowsBot


class CommandProperties(TypedDict):
    func: Callable[
        ["UpgradeMyWindowsBot", list[str]],
        Awaitable[None],
    ]
    super_chat_only: bool
    mods_only: bool
    owner_only: bool
