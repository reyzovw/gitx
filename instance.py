from commands.handler import CommandHandler
from core.repository import Repository
import sys

repository = Repository(".")
handler = CommandHandler(sys)

