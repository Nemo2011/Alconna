from typing import Union, Optional, Dict, Any
import traceback

from arclet.alconna.component import Option, Subcommand
from arclet.alconna.arpamar import Arpamar
from arclet.alconna.types import (
    MultiArg, ArgPattern, AntiArg, UnionArg, ObjectPattern, SequenceArg, MappingArg
)
from arclet.alconna.visitor import AlconnaNodeVisitor
from arclet.alconna.analysis.analyser import Analyser
from arclet.alconna.manager import commandManager
from arclet.alconna.analysis.arg_handlers import (
    multiArgHandler, commonArgHandler, antiArgHandler, unionArgHandler
)
from arclet.alconna.analysis.parts import analyseArgs, analyseOption, analyseSubcommand, analyseHeader
from arclet.alconna.exceptions import ParamsUnmatched, ArgumentMissing, NullTextMessage, UnexpectedElement
from arclet.alconna.util import split
from arclet.alconna.builtin.actions import helpSend

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
# from graia.amnesia.message import MessageChain
# from graia.amnesia.element import Text, Unknown


class GraiaCommandAnalyser(Analyser):
    """
    无序的分析器

    """

    filter_out = ["Source", "File", "Quote"]

    def addParam(self, opt: Union[Option, Subcommand]):
        if isinstance(opt, Subcommand):
            for sub_opts in opt.options:
                opt.subParams.setdefault(sub_opts.name, sub_opts)
        self.commandParams[opt.name] = opt

    def handleMessage(self, data: MessageChain) -> Optional[Arpamar]:
        """命令分析功能, 传入字符串或消息链, 应当在失败时返回fail的arpamar"""
        separate = self.separator
        i, __t, exc = 0, False, None
        raw_data: Dict[int, Any] = {}
        for unit in data:
            # using graia.amnesia.message and graia.amnesia.elements
            # if isinstance(unit, Text):
            #     res = split(unit.text.lstrip(' '), separate)
            #     if not res:
            #         continue
            #     raw_data[i] = res
            #     __t = True
            # elif isinstance(unit, Unknown):
            #     if self.is_raise_exception:
            #         exc = UnexpectedElement(f"{unit.type}({unit})")
            #     continue
            # elif unit.__class__.__name__ not in self.filter_out:
            #     raw_data[i] = unit
            if isinstance(unit, Plain):
                res = split(unit.text.lstrip(' '), separate)
                if not res:
                    continue
                raw_data[i] = res
                __t = True
            elif unit.type not in self.filter_out:
                raw_data[i] = unit
            else:
                if self.isRaiseException:
                    exc = UnexpectedElement(f"{unit.type}({unit})")
                continue
            i += 1

        if __t is False:
            if self.isRaiseException:
                raise NullTextMessage("传入了一个无法获取文本的消息链")
            return self.createArpamar(fail=True, exception=NullTextMessage("传入了一个无法获取文本的消息链"))
        if exc:
            if self.isRaiseException:
                raise exc
            return self.createArpamar(fail=True, exception=exc)
        self.raw_data = raw_data
        self.ndata = i

    def analyse(self, message: Union[MessageChain, None] = None) -> Arpamar:
        if commandManager.isDisable(self.alconna):
            return self.createArpamar(fail=True)
        if self.ndata == 0:
            if not message:
                raise ValueError('No data to analyse')
            if r := self.handleMessage(message):
                return r
        try:
            self.header = analyseHeader(self)
        except ParamsUnmatched as e:
            self.current_index = 0
            self.content_index = 0
            try:
                _, cmd, reserve = commandManager.findShortcut(
                    self.alconna, self.getNextData(self.alconna.separator, pop=False)[0]
                )
                if reserve:
                    data = self.recoverRawData()
                    data[0] = cmd
                    self.reset()
                    return self.analyse(data)  # type: ignore
                self.reset()
                return self.analyse(MessageChain.create(cmd))
            except ValueError:
                return self.createArpamar(fail=True, exception=e)

        for _ in self.partLength:
            _text, _str = self.getNextData(self.separator, pop=False)
            if not (_param := self.commandParams.get(_text, None) if _str else Ellipsis) and _text != "":
                for p in self.commandParams:
                    if _text.split(self.commandParams[p].separator)[0] in \
                            getattr(self.commandParams[p], 'aliases', [p]):
                        _param = self.commandParams[p]
                        break
            try:
                if not _param or _param is Ellipsis:
                    if not self.main_args:
                        self.main_args = analyseArgs(
                            self, self.selfArgs, self.separator, self.alconna.nargs, self.alconna.action
                        )
                elif isinstance(_param, Option):
                    if _param.name == "--help":
                        _record = self.currentIndex, self.contentIndex
                        _help_param = self.recoverRawData()
                        _help_param[0] = _help_param[0].replace("--help", "", 1).lstrip()
                        self.current_index, self.content_index = _record

                        def _get_help():
                            visitor = AlconnaNodeVisitor(self.alconna)
                            return visitor.formatNode(
                                self.alconna.formatter,
                                visitor.require(_help_param)
                            )

                        _param.action = helpSend(
                            self.alconna.name, _get_help
                        )
                        analyseOption(self, _param)
                        return self.createArpamar(fail=True)
                    opt_n, opt_v = analyseOption(self, _param)
                    if not self.options.get(opt_n, None):
                        self.options[opt_n] = opt_v
                    elif isinstance(self.options[opt_n], dict):
                        self.options[opt_n] = [self.options[opt_n], opt_v]
                    else:
                        self.options[opt_n].append(opt_v)

                elif isinstance(_param, Subcommand):
                    sub_n, sub_v = analyseSubcommand(self, _param)
                    self.subcommands[sub_n] = sub_v

            except (ParamsUnmatched, ArgumentMissing):
                if self.isRaiseException:
                    raise
                return self.createArpamar(fail=True)
            if self.currentIndex == self.ndata:
                break

        # 防止主参数的默认值被忽略
        if self.isMainArgsDefaultOnly and not self.main_args:
            self.main_args = analyseArgs(
                self, self.selfArgs,
                self.separator, self.alconna.nargs, self.alconna.action
            )

        if self.currentIndex == self.ndata and (not self.isNeedMainArgs or (self.isNeedMainArgs and self.main_args)):
            return self.createArpamar()

        data_len = self.getRestDataCount(self.separator)
        if data_len > 0:
            exc = ParamsUnmatched("Unmatched params: {}".format(self.getNextData(self.separator, pop=False)[0]))
        else:
            exc = ArgumentMissing("You need more data to analyse!")
        if self.isRaiseException:
            raise exc
        return self.createArpamar(fail=True, exception=exc)

    def createArpamar(self, exception: Optional[BaseException] = None, fail: bool = False):
        result = Arpamar()
        result.headMatched = self.headMatched
        if fail:
            tb = traceback.format_exc(limit=1)
            result.errorInfo = repr(exception) or repr(tb)
            result.errorData = self.recoverRawData()
            result.matched = False
        else:
            result.matched = True
            result.encapsulateResult(self.header, self.main_args, self.options, self.subcommands)
        self.reset()
        return result


GraiaCommandAnalyser.addArgHandler(MultiArg, multiArgHandler)
GraiaCommandAnalyser.addArgHandler(AntiArg, antiArgHandler)
GraiaCommandAnalyser.addArgHandler(UnionArg, unionArgHandler)
GraiaCommandAnalyser.addArgHandler(ArgPattern, commonArgHandler)
GraiaCommandAnalyser.addArgHandler(ObjectPattern, commonArgHandler)
GraiaCommandAnalyser.addArgHandler(SequenceArg, commonArgHandler)
GraiaCommandAnalyser.addArgHandler(MappingArg, commonArgHandler)
