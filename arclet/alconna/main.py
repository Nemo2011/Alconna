"""Alconna 主体"""
from typing import Dict, List, Optional, Union, Type, Callable, Any, Tuple, TypeVar, overload
from .analysis.analyser import Analyser
from .analysis import compile
from .base import CommandNode, Args, ArgAction
from .component import Option, Subcommand
from .arpamar import Arpamar, ArpamarBehavior
from .arpamar.duplication import AlconnaDuplication
from .types import DataCollection, DataUnit
from .manager import commandManager
from .visitor import AlconnaNodeVisitor, AbstractHelpTextFormatter
from .builtin.formatter import DefaultHelpTextFormatter
from .builtin.analyser import DisorderCommandAnalyser

T_Duplication = TypeVar('T_Duplication', bound=AlconnaDuplication)


class Alconna(CommandNode):
    """
    亚尔康娜 (Alconna), Cesloi 的妹妹

    用于更加精确的命令解析，支持 String 与 MessageChain

    Examples:

    >>> from arclet.alconna import Alconna
    >>> alc = Alconna(
    ...     headers=["h1", "h2"],
    ...     command="name",
    ...     options=[
    ...         Option("opt", Args["opt_arg":"opt_arg"]),
    ...         Subcommand(
    ...             "sub_name",
    ...             Option("sub_opt", Args["sub_arg":"sub_arg"]),
    ...             args=Args["sub_main_args":"sub_main_args"]
    ...         )
    ...     ],
    ...     mainArgs=Args["main_args":"main_args"],
    ...  )
    >>> alc.parse("name opt opt_arg")


    其中
        - name: 命令名称
        - sub_name: 子命令名称
        - sub_opt: 子命令选项名称
        - sub_arg: 子命令选项参数
        - sub_main_args: 子命令主参数
        - opt: 命令选项名称
        - opt_arg: 命令选项参数
        - main_args: 命令主参数
    """

    headers: Union[List[Union[str, DataUnit]], List[Tuple[DataUnit, str]]]  # type: ignore
    command: str
    options: List[Union[Option, Subcommand]]
    analyserType: Type[Analyser]
    customTypes: Dict[str, Type] = {}
    namespace: str
    __clsName__: str = "Alconna"
    localArgs: dict = {}
    formatter: AbstractHelpTextFormatter
    defaultAnalyser: Type[Analyser] = DisorderCommandAnalyser  # type: ignore

    def __init__(
            self,
            command: Optional[str] = None,
            mainArgs: Union[Args, str, None] = None,
            headers: Optional[Union[List[Union[str, DataUnit]], List[Tuple[DataUnit, str]]]] = None,
            options: Optional[List[Union[Option, Subcommand]]] = None,
            isRaiseException: bool = False,
            action: Optional[Union[ArgAction, Callable]] = None,
            namespace: Optional[str] = None,
            separator: str = " ",
            helpText: Optional[str] = None,
            analyser_type: Optional[Type[Analyser]] = None,
            behaviors: Optional[List[ArpamarBehavior]] = None,
            formatter: Optional[AbstractHelpTextFormatter] = None,
    ):
        """
        以标准形式构造 Alconna

        Args:
            headers: 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 command 至少有一个填写
            command: 命令名称，你的命令的名字，与 headers 至少有一个填写
            options: 命令选项，你的命令可选择的所有 option ，包括子命令与单独的选项
            mainArgs: 主参数，填入后当且仅当命令中含有该参数时才会成功解析
            isRaiseException: 当解析失败时是否抛出异常，默认为 False
            action: 命令解析后针对主参数的回调函数
            namespace: 命令命名空间，默认为 'Alconna'
            separator: 命令参数分隔符，默认为空格
            helpText: 帮助文档，默认为 'Unknown Information'
            analyser_type: 命令解析器类型，默认为 DisorderCommandAnalyser
        """
        # headers与command二者必须有其一
        if all((not headers, not command)):
            command = "Alconna"
        self.headers = headers or [""]
        self.command = command or ""
        self.options = options or []
        super().__init__(
            f"ALCONNA::{command or self.headers[0]}",
            mainArgs,
            action,
            separator,
            helpText or "Unknown Information"
        )
        self.isRaiseException = isRaiseException
        self.namespace = namespace or self.__clsName__
        self.options.append(Option("--help", alias=["-h"], helpText="显示帮助信息"))
        self.analyserType = analyser_type or self.defaultAnalyser
        commandManager.register(self)
        self.__class__.__clsName__ = "Alconna"
        self.behaviors = behaviors
        self.formatter = formatter or DefaultHelpTextFormatter()  # type: ignore

    def __class_getitem__(cls, item):
        if isinstance(item, str):
            cls.__clsName__ = item
        return cls

    def resetNamespace(self, namespace: str):
        """重新设置命名空间"""
        commandManager.delete(self)
        self.namespace = namespace
        commandManager.register(self)
        return self

    def resetBehaviors(self, behaviors: List[ArpamarBehavior]):
        self.behaviors = behaviors
        return self

    def getHelp(self) -> str:
        """返回 help 文档"""
        return AlconnaNodeVisitor(self).formatNode(self.formatter)

    @classmethod
    def setCustomTypes(cls, **types: Type):
        """设置自定义类型"""
        cls.customTypes = types

    def shortcut(self, shortKey: str, command: str, reserveArgs: bool = False):
        """添加快捷键"""
        commandManager.addShortcut(self, shortKey, command, reserveArgs)

    def __repr__(self):
        return (
            f"<ALC.{self.namespace}::{self.command or self.headers[0]} "
            f"with {len(self.options)} options; args={self.args}>"
        )

    def option(
            self,
            name: str,
            sep: str = " ",
            args: Optional[Args] = None,
            helpText: Optional[str] = None,
    ):
        """链式注册一个 Option"""
        commandManager.delete(self)
        opt = Option(name, args, separator=sep, helpText=helpText)
        self.options.append(opt)
        commandManager.register(self)
        return self

    def setAction(self, action: Union[Callable, str, ArgAction], customTypes: Optional[Dict[str, Type]] = None):
        """设置针对main_args的action"""
        if isinstance(action, str):
            ns = {}
            exec(action, getattr(self, "custom_types", customTypes), ns)
            action = ns.popitem()[1]
        self.__checkAction__(action)
        return self

    @overload
    def parse(
            self,
            message: Union[str, DataCollection],
            duplication: Type[T_Duplication],
            static: bool = True,

    ) -> T_Duplication:
        ...

    @overload
    def parse(
            self,
            message: Union[str, DataCollection],
            static: bool = True
    ) -> Arpamar:
        ...

    def parse(
            self,
            message: Union[str, DataCollection],
            duplication: Optional[Type[T_Duplication]] = None,
            static: bool = True,
    ):
        """命令分析功能, 传入字符串或消息链, 返回一个特定的数据集合类"""
        if static:
            analyser = commandManager.require(self)
        else:
            analyser = compile(self)
        result = analyser.handleMessage(message)
        if duplication:
            arp = (result or analyser.analyse()).update(self.behaviors)
            dup = duplication(self).setTarget(arp)
            return dup
        return (result or analyser.analyse()).update(self.behaviors)

    def toDict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "headers": self.headers,
            "command": self.command,
            "options": [opt.toDict() for opt in self.options if opt.name != "--help"],
            "main_args": self.args.toDict(),
            "is_raise_exception": self.isRaiseException,
            "separator": self.separator,
            "namespace": self.namespace,
            "help_text": self.helpText,
        }

    def __truediv__(self, other):
        self.resetNamespace(other)
        return self

    def __rtruediv__(self, other):
        self.resetNamespace(other)
        return self

    def __rmatmul__(self, other):
        self.resetNamespace(other)
        return self

    def __matmul__(self, other):
        self.resetNamespace(other)
        return self

    def __radd__(self, other):
        if isinstance(other, Option):
            commandManager.delete(self)
            self.options.append(other)
            commandManager.register(self)
        return self

    def __add__(self, other):
        return self.__radd__(other)

    def __getstate__(self):
        return self.toDict()

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Alconna":
        """从字典中恢复一个 Alconna 对象"""
        headers = data["headers"]
        command = data["command"]
        options = []
        for o in data["options"]:
            if o['type'] == 'Option':
                options.append(Option.fromDict(o))
            elif o['type'] == 'Subcommand':
                options.append(Subcommand.fromDict(o))
        main_args = Args.fromDict(data["main_args"])
        is_raise_exception = data["is_raise_exception"]
        namespace = data["namespace"]
        return cls(
            command=command, options=options, mainArgs=main_args, headers=headers,
            isRaiseException=is_raise_exception, namespace=namespace,
            separator=data["separator"], helpText=data["help_text"],
        )

    def __setstate__(self, state):
        options = []
        for o in state["options"]:
            if o['type'] == 'Option':
                options.append(Option.fromDict(o))
            elif o['type'] == 'Subcommand':
                options.append(Subcommand.fromDict(o))
        self.__init__(
            headers=state["headers"], command=state["command"], options=options,
            mainArgs=Args.fromDict(state["main_args"]), isRaiseException=state["is_raise_exception"],
            namespace=state["namespace"], separator=state["separator"], helpText=state["help_text"],
        )
