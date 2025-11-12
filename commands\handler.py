from commands.base import *
from commands.rest import *

class CommandHandler:
    def __init__(self, sys):
        self.__commands = {
            "init": init,
            "clone": clone,
            "add": add,
            "commit": commit,
            "branch": branch,
            "remote": remote,
            "push": push,
            "auth": auth
        }
        self.__sys = sys

    def __execute(self, prompt: str):
        if prompt not in self.__commands:
            return
        return self.__commands[prompt](self.__sys)

    def execute(self, command: str, **kwargs):
        if command not in self.__commands.keys():
            print(f"Command '{command}' not found")
            return
        from instance import repository
        return self.__commands[command](repository, kwargs)