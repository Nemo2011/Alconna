import re
from typing import Iterable, Union, Optional, List, Any, Dict, cast
import asyncio

from .analyser import Analyser
from ..component import Option, Subcommand
from ..exceptions import ParamsUnmatched, ArgumentMissing
from ..types import ArgPattern, AnyParam, AllParam, Empty, TypePattern
from ..base import Args, ArgAction


def loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


def analyseArgs(
        analyser: Analyser,
        optArgs: Args,
        sep: str,
        nargs: int,
        action: Optional[ArgAction] = None,
) -> Dict[str, Any]:
    """
    分析 Args 部分

    Args:
        analyser: 使用的分析器
        optArgs: 目标Args
        sep: 当前命令节点的分隔符
        nargs: Args参数个数
        action: 当前命令节点的ArgAction

    Returns:
        Dict: 解析结果
    """
    option_dict: Dict[str, Any] = {}
    for key, arg in optArgs.argument.items():
        value = arg['value']
        default = arg['default']
        kwonly = arg['kwonly']
        optional = arg['optional']
        may_arg, _str = analyser.getNextData(sep)
        if kwonly:
            _kwarg = re.findall(f'^{key}=(.*)$', may_arg)
            if not _kwarg:
                analyser.reduceData(may_arg)
                if analyser.isRaiseException:
                    raise ParamsUnmatched(f"{may_arg} missing its key. Do you forget to add '{key}='?")
                continue
            may_arg = _kwarg[0]
            if may_arg == '':
                may_arg, _str = analyser.getNextData(sep)
                if _str:
                    analyser.reduceData(may_arg)
                    if analyser.isRaiseException:
                        raise ParamsUnmatched(f"param type {may_arg.__class__} is incorrect")
                    continue
        if may_arg in analyser.paramIds:
            analyser.reduceData(may_arg)
            if default is None:
                if optional:
                    continue
                raise ArgumentMissing(f"param {key} is required")
            else:
                option_dict[key] = None if default is Empty else default
        elif value.__class__ in analyser.argHandlers:
            analyser.argHandlers[value.__class__](
                analyser, may_arg, key, value,
                default, nargs, sep, option_dict,
                optional
            )
        elif value.__class__ is TypePattern:
            arg_find = value.find(may_arg)
            if not arg_find:
                analyser.reduceData(may_arg)
                if default is None:
                    if optional:
                        continue
                    if may_arg:
                        raise ParamsUnmatched(f"param {may_arg} is incorrect")
                    else:
                        raise ArgumentMissing(f"param {key} is required")
                else:
                    arg_find = None if default is Empty else default
            option_dict[key] = arg_find
        elif value is AnyParam:
            if may_arg:
                option_dict[key] = may_arg
        elif value is AllParam:
            rest_data = analyser.recoverRawData()
            if not rest_data:
                rest_data = [may_arg]
            elif isinstance(rest_data[0], str):
                rest_data[0] = may_arg + sep + rest_data[0]
            else:
                rest_data.insert(0, may_arg)
            option_dict[key] = rest_data
            return option_dict
        else:
            if may_arg.__class__ is value:
                option_dict[key] = may_arg
            elif isinstance(value, type) and isinstance(may_arg, value):
                option_dict[key] = may_arg
            elif default is not None:
                option_dict[key] = None if default is Empty else default
                analyser.reduceData(may_arg)
            else:
                analyser.reduceData(may_arg)
                if optional:
                    continue
                if may_arg:
                    raise ParamsUnmatched(f"param type {may_arg.__class__} is incorrect")
                else:
                    raise ArgumentMissing(f"param {key} is required")
    if action:
        result_dict = option_dict.copy()
        kwargs = {}
        varargs = []
        if optArgs.varKeyword:
            kwargs = result_dict.pop(optArgs.varKeyword[0])
            if not isinstance(kwargs, dict):
                kwargs = {optArgs.varKeyword[0]: kwargs}
        if optArgs.varPositional:
            varargs = result_dict.pop(optArgs.varPositional[0])
            if not isinstance(varargs, Iterable):
                varargs = [varargs]
            elif not isinstance(varargs, list):
                varargs = list(varargs)
        if optArgs.varKeyword:
            addition_kwargs = analyser.alconna.localArgs.copy()
            addition_kwargs.update(kwargs)
        else:
            addition_kwargs = kwargs
            result_dict.update(analyser.alconna.localArgs)
        if action.awaitable:
            if loop().is_running():
                option_dict = cast(Dict, loop().create_task(
                    action.handleAsync(result_dict, varargs, addition_kwargs, analyser.isRaiseException)
                ))
            else:
                option_dict = loop().run_until_complete(
                    action.handleAsync(result_dict, varargs, addition_kwargs, analyser.isRaiseException)
                )
        else:
            option_dict = action.handle(result_dict, varargs, addition_kwargs, analyser.isRaiseException)
        if optArgs.varKeyword:
            option_dict.update({optArgs.varKeyword[0]: kwargs})
        if optArgs.varPositional:
            option_dict.update({optArgs.varPositional[0]: varargs})
    return option_dict


def analyseOption(
        analyser: Analyser,
        param: Option,
) -> List[Any]:
    """
    分析 Option 部分

    Args:
        analyser: 使用的分析器
        param: 目标Option
    """

    name, _ = analyser.getNextData(param.separator)
    if name not in param.aliases:  # 先匹配选项名称
        raise ParamsUnmatched(f"{name} dose not matched with {param.name}")
    name = param.name.lstrip("-")
    if param.nargs == 0:
        if param.action:
            if param.action.awaitable:
                if loop().is_running():
                    r = loop().create_task(
                        param.action.handleAsync(
                            {}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException
                        )
                    )
                else:
                    r = loop().run_until_complete(
                        param.action.handleAsync(
                            {}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException
                        )
                    )
            else:
                r = param.action.handle({}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException)
            return [name, r]
        return [name, Ellipsis]
    return [name, analyseArgs(analyser, param.args, param.separator, param.nargs, param.action)]


def analyseSubcommand(
        analyser: Analyser,
        param: Subcommand
) -> List[Union[str, Any]]:
    """
    分析 Subcommand 部分

    Args:
        analyser: 使用的分析器
        param: 目标Subcommand
    """
    name, _ = analyser.getNextData(param.separator)
    if param.name != name:
        raise ParamsUnmatched(f"{name} dose not matched with {param.name}")
    name = name.lstrip("-")
    if param.subPartLength.stop == 0:
        if param.action:
            if param.action.awaitable:
                if loop().is_running():
                    r = loop().create_task(
                        param.action.handleAsync(
                            {}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException
                        )
                    )
                else:
                    r = loop().run_until_complete(
                        param.action.handleAsync(
                            {}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException
                        )
                    )
            else:
                r = param.action.handle({}, [], analyser.alconna.localArgs.copy(), analyser.isRaiseException)
            return [name, r]
        return [name, Ellipsis]

    subcommand = {}
    args = None
    need_args = True if param.nargs > 0 else False
    for _ in param.subPartLength:
        text, _str = analyser.getNextData(param.separator, pop=False)
        sub_param = param.subParams.get(text, None) if _str else Ellipsis
        if not sub_param and text != "":
            for sp in param.subParams:
                if text.split(param.subParams[sp].separator)[0] in param.subParams[sp].aliases:
                    _param = param.subParams[sp]
                    break
        if isinstance(sub_param, Option):
            opt_n, opt_v = analyseOption(analyser, sub_param)
            if not subcommand.get(opt_n):
                subcommand[opt_n] = opt_v
            elif isinstance(subcommand[opt_n], dict):
                subcommand[opt_n] = [subcommand[opt_n], opt_v]
            else:
                subcommand[opt_n].append(opt_v)
        elif not args and (args := analyseArgs(analyser, param.args, param.separator, param.nargs, param.action)):
            subcommand.update(args)
    if need_args and not args:
        raise ArgumentMissing(f"\"{name}\" subcommand missed its args")
    return [name, subcommand]


def analyseHeader(
        analyser: Analyser,
) -> Union[str, bool, None]:
    """
    分析命令头部

    Args:
        analyser: 使用的分析器
    Returns:
        head_match: 当命令头内写有正则表达式并且匹配成功的话, 返回匹配结果
    """
    command = analyser.commandHeader
    separator = analyser.separator
    head_text, _str = analyser.getNextData(separator)
    if isinstance(command, ArgPattern):
        if _str and (_head_find := command.find(head_text)):
            analyser.headMatched = True
            return _head_find if _head_find != head_text else True
    else:
        may_command, _m_str = analyser.getNextData(separator)
        if _m_str:
            if isinstance(command, List) and not _str:
                for _command in command:
                    if (_head_find := _command[1].find(may_command)) and head_text == _command[0]:
                        analyser.headMatched = True
                        return _head_find if _head_find != may_command else True
            elif isinstance(command[0], list) and not _str:
                if (_head_find := command[1].find(may_command)) and head_text in command[0]:  # type: ignore
                    analyser.headMatched = True
                    return _head_find if _head_find != may_command else True
            elif _str:
                if (_command_find := command[1].find(may_command)) and (  # type: ignore
                    _head_find := command[0][1].find(head_text)
                    ):  
                        analyser.headMatched = True
                        return _command_find if _command_find != may_command else True
            else:
                if (_command_find := command[1].find(may_command)) and head_text in command[0][0]:  # type: ignore
                    analyser.headMatched = True
                    return _command_find if _command_find != may_command else True

    if not analyser.headMatched:
        raise ParamsUnmatched(f"{head_text} dose not matched")
