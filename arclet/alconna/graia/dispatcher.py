from typing import Literal, Dict, Callable, Optional, Coroutine, Union, AsyncIterator, TypedDict
import asyncio

from arclet.alconna import Alconna
from arclet.alconna.arpamar import Arpamar
from arclet.alconna.arpamar.duplication import AlconnaDuplication, generateDuplication
from arclet.alconna.arpamar.stub import ArgsStub, OptionStub, SubcommandStub
from arclet.alconna.proxy import AlconnaMessageProxy, AlconnaProperty
from arclet.alconna.manager import commandManager

from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await_safely
from graia.broadcast.entities.signatures import Force

from graia.ariadne import get_running
from graia.ariadne.app import Ariadne
from graia.ariadne.dispatcher import ContextDispatcher
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Quote
from graia.ariadne.util import resolve_dispatchers_mixin

from loguru import logger


class AriadneAMP(AlconnaMessageProxy):
    preTreatments: Dict[Alconna, Callable[
        [MessageChain, Arpamar, Optional[str], Optional[MessageEvent]],
        Coroutine[None, None, AlconnaProperty[MessageChain, MessageEvent]]
    ]]

    def addProxy(
            self,
            command: Union[str, Alconna],
            preTreatment: Optional[
                Callable[
                    [MessageChain, Arpamar, Optional[str], Optional[MessageEvent]],
                    Coroutine[None, None, AlconnaProperty[MessageChain, MessageEvent]]
                ]
            ] = None,
    ):
        if isinstance(command, str):
            command = commandManager.getCommand(command)  # type: ignore
            if not command:
                raise ValueError(f'Command {command} not found')
        self.pre_treatments.setdefault(command, preTreatment or self.defaultPreTreatment)  # type: ignore

    async def fetchMessage(self) -> AsyncIterator[MessageChain]:
        yield NotImplemented
        pass

    @staticmethod
    def laterCondition(result: AlconnaProperty[MessageChain, MessageEvent]) -> bool:
        return True


class AlconnaHelpDispatcher(BaseDispatcher):
    mixin = [ContextDispatcher]

    def __init__(self, alconna: "Alconna", helpString: str, source_event: MessageEvent):
        self.command = alconna
        self.helpString = helpString
        self.source_event = source_event

    async def catch(self, interface: "DispatcherInterface"):
        if interface.name == "helpString" and interface.annotation == str:
            return self.helpString
        if isinstance(interface.annotation, Alconna):
            return self.command
        if issubclass(interface.annotation, MessageEvent) or interface.annotation == MessageEvent:
            return self.source_event


class AlconnaHelpMessage(Dispatchable):
    """
    Alconna帮助信息发送事件
    如果触发的某个命令的帮助选项, 当AlconnaDisptcher的reply_help为False时, 会发送该事件
    """

    command: "Alconna"
    """命令"""

    helpString: str
    """帮助信息"""

    source_event: MessageEvent
    """来源事件"""


class _AlconnaLocalStorage(TypedDict):
    alconnaResult: AlconnaProperty[MessageChain, MessageEvent]


class AlconnaDispatcher(BaseDispatcher):
    proxy = AriadneAMP(loop=asyncio.new_event_loop())

    def __init__(
            self,
            *,
            alconna: "Alconna",
            HELP_FLAG: Literal["reply", "post", "stay"] = "stay",
            skipForUnmatch: bool = True,
            helpHandler: Optional[Callable[[str], MessageChain]] = None,
            allowQuote: bool = False
    ):
        """
        构造 Alconna调度器
        Args:
            alconna (Alconna): Alconna实例
            HELP_FLAG ("reply", "post", "stay"): 帮助信息发送方式
            skipForUnmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            allowQuote (bool): 是否允许引用回复消息触发对应的命令, 默认为 False
        """
        super().__init__()
        self.command = alconna
        self.helpFlag = HELP_FLAG
        self.skipForUnmatch = skipForUnmatch
        self.helpHandler = helpHandler or (lambda x: MessageChain.create(x))
        self.allowQuote = allowQuote

    async def beforeExecution(self, interface: DispatcherInterface):
        event: MessageEvent = interface.event
        app: Ariadne = get_running()

        async def replyHelpMessage(
                origin: MessageChain,
                result: Arpamar,
                helpText: Optional[str] = None,
                source: Optional[MessageEvent] = None,
        ) -> AlconnaProperty[MessageChain, MessageEvent]:
            source = source or event

            if result.matched is False and helpText:
                if self.helpFlag == "reply":
                    help_message: MessageChain = await run_always_await_safely(self.helpHandler, helpText)
                    if isinstance(source, GroupMessage):
                        await app.sendGroupMessage(source.sender.group, help_message)
                    else:
                        await app.sendMessage(source.sender, help_message)  # type: ignore
                    return AlconnaProperty(origin, result, None, source)
                if self.helpFlag == "post":
                    dispatchers = resolve_dispatchers_mixin(
                        [AlconnaHelpDispatcher(self.command, helpText, source), source.Dispatcher]
                    )
                    for listener in interface.broadcast.default_listener_generator(AlconnaHelpMessage):
                        await interface.broadcast.Executor(listener, dispatchers=dispatchers)
                    return AlconnaProperty(origin, result, None, source)
            return AlconnaProperty(origin, result, helpText, source)

        message: MessageChain = await interface.lookup_param("message", MessageChain, None)
        if not self.allowQuote and message.has(Quote):
            raise ExecutionStop
        self.proxy.addProxy(self.command, replyHelpMessage)
        try:
            await self.proxy.pushMessage(message, event, self.command)  # type: ignore
        except Exception as e:
            logger.warning(f"{self.command} error: {e}")
            raise ExecutionStop
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        local_storage['alconnaResult'] = await self.proxy.exportResults.get()

    async def catch(self, interface: DispatcherInterface):
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        res = local_storage['alconnaResult']
        if not res.result.matched and not res.helpText:
            if "-h" in str(res.origin):
                raise ExecutionStop
            if self.skipForUnmatch:
                raise ExecutionStop
        default_duplication = generateDuplication(self.command)
        default_duplication.setTarget(res.result)
        if interface.annotation == AlconnaDuplication:
            return default_duplication
        if issubclass(interface.annotation, AlconnaDuplication):
            return interface.annotation(self.command).setTarget(res.result)
        if issubclass(interface.annotation, AlconnaProperty):
            return res
        if interface.annotation == ArgsStub:
            arg = ArgsStub(self.command.args)
            arg.setResult(res.result.mainArgs)
            return arg
        if interface.annotation == OptionStub:
            return default_duplication.option(interface.name)
        if interface.annotation == SubcommandStub:
            return default_duplication.subcommand(interface.name)
        if interface.annotation == Arpamar:
            return res.result
        if interface.annotation == str and interface.name == "help_text":
            return res.helpText
        if issubclass(interface.annotation, Alconna):
            return self.command
        if interface.name in res.result.allMatchedArgs:
            if isinstance(res.result.allMatchedArgs[interface.name], interface.annotation):
                return res.result.allMatchedArgs[interface.name]
            return Force()
        if issubclass(interface.annotation, MessageEvent) or interface.annotation == MessageEvent:
            return Force(res.source)
