from discord.ext import commands
from typing import TYPE_CHECKING
from utils.logger import get_logger

if TYPE_CHECKING:
    from main import UpgradeMyWindowsBot


class CogLogger(commands.Cog):
    def __init__(self, bot: "UpgradeMyWindowsBot"):
        self.bot = bot
        self.logger = get_logger(self.__class__.__name__)
