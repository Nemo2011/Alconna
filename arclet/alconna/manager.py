"""Alconna 负责记录命令的部分"""

import re
from typing import TYPE_CHECKING, Dict, Optional, Union, List, Tuple
from .exceptions import DuplicateCommand, ExceedMaxCount
from .analysis import compile as compile_analysis
from .util import Singleton
from .types import DataCollection

if TYPE_CHECKING:
    from .main import Alconna
    from .analysis.analyser import Analyser


class CommandManager(metaclass=Singleton):
    """
    命令管理器
    """
    sign: str = "ALCONNA::"
    defaultNamespace: str = "Alconna"
    __shortcuts: Dict[str, Tuple[str, str, bool]] = {}
    __commands: Dict[str, Dict[str, "Analyser"]]
    __abandons: List["Alconna"]
    currentCount: int
    maxCount: int = 100

    def __init__(self):

        self.__commands = {}
        self.__abandons = []
        self.currentCount = 0

    def __del__(self):  # td: save to file
        self.__commands = {}
        self.__abandons = []

    @property
    def getAllNamespace(self):
        return list(self.__commands.keys())

    def _commandPart(self, command: str) -> Tuple[str, str]:
        """获取命令的组成部分"""
        command_parts = command.split(".")
        if len(command_parts) != 2:
            command_parts.insert(0, self.defaultNamespace)
        return command_parts[0], command_parts[1]

    def register(self, command: "Alconna") -> None:
        """注册命令"""
        if self.currentCount >= self.maxCount:
            raise ExceedMaxCount
        if command.namespace not in self.__commands:
            self.__commands[command.namespace] = {}
        cid = command.name.replace(self.sign, "")
        if cid not in self.__commands[command.namespace]:
            self.__commands[command.namespace][cid] = compile_analysis(command)
            self.currentCount += 1
        else:
            raise DuplicateCommand("命令已存在")

    def require(self, command: Union["Alconna", str]) -> "Analyser":
        """获取解析器"""
        if isinstance(command, str):
            namespace, name = self._commandPart(command)
            try:
                ana = self.__commands[namespace][name]
            except KeyError:
                raise ValueError("命令不存在")
            return ana
        else:
            cid = command.name.replace(self.sign, "")
            namespace = command.namespace
            return self.__commands[namespace][cid]

    def delete(self, command: Union["Alconna", str]) -> None:
        """删除命令"""
        if isinstance(command, str):
            namespace, name = self._commandPart(command)
            try:
                del self.__commands[namespace][name]
            finally:
                if self.__commands[namespace] == {}:
                    del self.__commands[namespace]
                return None
        cid = command.name.replace(self.sign, "")
        namespace = command.namespace
        try:
            del self.__commands[namespace][cid]
        finally:
            if self.__commands[namespace] == {}:
                del self.__commands[namespace]
            return None

    def isDisable(self, command: "Alconna") -> bool:
        """判断命令是否被禁用"""
        if command in self.__abandons:
            return True
        return False

    def setEnable(self, command: Union["Alconna", str]) -> None:
        """启用命令"""
        if isinstance(command, str):
            namespace, name = self._commandPart(command)
            for alc in self.__abandons:
                if alc.namespace == namespace and alc.name.replace(self.sign, "") == name:
                    self.__abandons.remove(alc)
            return
        self.__abandons.remove(command)

    def addShortcut(self, target: Union["Alconna", str], shortcut: str, command: str, reserve: bool = False) -> None:
        """添加快捷命令"""
        if isinstance(target, str):
            namespace, name = self._commandPart(target)
            try:
                target = self.__commands[namespace][name].alconna
            except KeyError:
                raise ValueError("命令不存在")
        if shortcut in self.__shortcuts:
            raise DuplicateCommand("快捷命令已存在")
        self.__shortcuts[shortcut] = (target.namespace + "." + target.name.replace(self.sign, ""), command, reserve)

    def findShortcut(self, target: Union["Alconna", str], shortcut: str):
        """查找快捷命令"""
        if shortcut not in self.__shortcuts:
            raise ValueError("快捷命令不存在")
        info, command, reserve = self.__shortcuts[shortcut]
        if isinstance(target, str):
            namespace, name = self._commandPart(target)
            if info != (namespace + "." + name):
                raise ValueError("目标命令错误")
            try:
                target = self.__commands[namespace][name].alconna
            except KeyError:
                raise ValueError("目标命令不存在")
            else:
                return target, command, reserve
        if info != (target.namespace + "." + target.name.replace(self.sign, "")):
            raise ValueError("目标命令错误")
        return target, command, reserve

    def setDisable(self, command: Union["Alconna", str]) -> None:
        """禁用命令"""
        if isinstance(command, str):
            namespace, name = self._commandPart(command)
            try:
                self.__abandons.append(self.__commands[namespace][name].alconna)
            finally:
                return None
        self.__abandons.append(command)

    def getCommand(self, command: str) -> Union["Alconna", None]:
        """获取命令"""
        command_parts = self._commandPart(command)
        if command_parts[0] not in self.__commands:
            return None
        if command_parts[1] not in self.__commands[command_parts[0]]:
            return None
        return self.__commands[command_parts[0]][command_parts[1]].alconna

    def getCommands(self, namespace: Optional[str] = None) -> List["Alconna"]:
        """获取命令列表"""
        if namespace is None:
            return [alc.alconna for alc in self.__commands[self.defaultNamespace].values()]
        if namespace not in self.__commands:
            return []
        return [alc.alconna for alc in self.__commands[namespace].values()]

    def broadcast(self, command: Union[str, DataCollection], namespace: Optional[str] = None):
        """广播命令"""
        command = str(command)
        may_command_head = command.split(" ")[0]
        if namespace is None:
            for n in self.__commands:
                if self.__commands[n].get(may_command_head):
                    return self.__commands[n][may_command_head].analyse(command)
                for k in self.__commands[n]:
                    if re.match("^" + k + ".*" + "$", command):
                        return self.__commands[n][k].analyse(command)
        else:
            commands = self.__commands[namespace]
            if commands.get(may_command_head):
                return self.__commands[namespace][may_command_head].analyse(command)
            for k in self.__commands[namespace]:
                if re.match("^" + k + ".*" + "$", command):
                    return self.__commands[namespace][k].analyse(command)

    def getAllCommandHelp(
            self,
            namespace: Optional[str] = None,
            header: Optional[str] = None,
            pages: Optional[str] = None,
            footer: Optional[str] = None,
            max_length: int = -1,
            page: int = 1,
    ) -> str:
        header = header or "# 当前可用的命令有:"
        pages = pages or "第 %d/%d 页"
        if pages.count("%d") != 2:
            raise ValueError("页码格式错误")
        footer = footer or "# 输入'命令名 --help' 查看特定命令的语法"
        command_string = ""
        cmds = self.__commands[namespace or self.defaultNamespace]
        if max_length < 1:
            for name, cmd in cmds.items():
                command_string += "\n - " + name + " : " + cmd.alconna.helpText
        else:
            max_page = len(cmds) // max_length + 1
            if page < 1 or page > max_page:
                page = 1
            header += "\t" + pages % (page, max_page)
            for name in list(cmds.keys())[(page - 1) * max_length: page * max_length]:
                alc = cmds[name].alconna
                command_string += "\n - " + (
                    (
                        "[" + "|".join([f"{h}" for h in alc.headers]) + "]"
                        if len(alc.headers) > 1 else f"{alc.headers[0]}"
                    ) if alc.headers != [''] else ""
                ) + alc.command + " : " + alc.helpText
        return f"{header}{command_string}\n{footer}"

    def getCommandHelp(self, command: str) -> Optional[str]:
        """获取单个命令的帮助"""
        command_parts = self._commandPart(command)
        cmd = self.getCommand(f"{command_parts[0]}.{command_parts[1]}")
        if cmd:
            return cmd.getHelp()


commandManager = CommandManager()
