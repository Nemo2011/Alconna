"""杂物堆"""
import contextlib
import inspect
from functools import lru_cache
from collections import OrderedDict
from typing import TypeVar, Optional, Any, Iterator, Hashable, Tuple, Union, Mapping

R = TypeVar('R')


@lru_cache(4096)
def is_async(o: Any):
    return inspect.iscoroutinefunction(o) or inspect.isawaitable(o)


class Singleton(type):
    """单例模式"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def remove(mcs, cls):
        mcs._instances.pop(cls, None)


@lru_cache(4096)
def split_once(text: str, separates: Union[str, Tuple[str, ...]], crlf: bool = True):
    """单次分隔字符串"""
    out_text = ""
    quotation = ""
    separates = tuple(separates)
    for index, char in enumerate(text):
        if char in {"'", '"'}:  # 遇到引号括起来的部分跳过分隔
            if not quotation:
                quotation = char
                if index and text[index - 1] == "\\":
                    out_text += char
            elif char == quotation:
                quotation = ""
                if index and text[index - 1] == "\\":
                    out_text += char
        if (char in separates and not quotation) or (crlf and char in {"\n", "\r"}):
            break
        out_text += char
    return out_text, text[len(out_text) + 1:]


@lru_cache(4096)
def split(text: str, separates: Optional[Tuple[str, ...]] = None, crlf: bool = True):
    """尊重引号与转义的字符串切分

    Args:
        text (str): 要切割的字符串
        separates (Set(str)): 切割符. 默认为 " ".
        crlf (bool): 是否去除 \n 与 \r，默认为 True

    Returns:
        List[str]: 切割后的字符串, 可能含有空格
    """
    separates = separates or (" ",)
    result = ""
    quotation = ""
    for index, char in enumerate(text):
        if char in {"'", '"'}:
            if not quotation:
                quotation = char
                if index and text[index - 1] == "\\":
                    result += char
            elif char == quotation:
                quotation = ""
                if index and text[index - 1] == "\\":
                    result += char
        elif (not quotation and char in separates) or (crlf and char in {"\n", "\r"}):
            if result and result[-1] != "\0":
                result += "\0"
        elif char != "\\":
            result += char
    return result.split('\0') if result else []


def levenshtein_norm(source: str, target: str) -> float:
    """编辑距离算法, 计算源字符串与目标字符串的相似度, 取值范围[0, 1], 值越大越相似"""
    l_s, l_t = len(source), len(target)
    s_range, t_range = range(l_s + 1), range(l_t + 1)
    matrix = [[(i if j == 0 else j) for j in t_range] for i in s_range]

    for i in s_range[1:]:
        for j in t_range[1:]:
            sub_distance = matrix[i - 1][j - 1] + (0 if source[i - 1] == target[j - 1] else 1)
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, sub_distance)

    return 1 - float(matrix[l_s][l_t]) / max(l_s, l_t)


_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")
_T = TypeVar("_T")


class LruCache(Mapping[_K, _V]):
    max_size: int
    cache: OrderedDict

    __slots__ = ("max_size", "cache", "__size")

    def __init__(self, max_size: int = -1) -> None:
        self.max_size = max_size
        self.cache = OrderedDict()
        self.__size = 0

    def get(self, key: _K, default: Optional[_T] = None) -> Union[_V, _T]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return default

    def __getitem__(self, item):
        if res := self.get(item):
            return res
        raise ValueError

    def set(self, key: _K, value: Any) -> None:
        if key in self.cache:
            return
        self.cache[key] = value
        self.__size += 1
        if 0 < self.max_size < self.__size:
            _k = self.cache.popitem(last=False)[0]
            self.__size -= 1

    def delete(self, key: _K) -> None:
        self.cache.pop(key)

    def size(self) -> int:
        return self.__size

    def has(self, key: _K) -> bool:
        return key in self.cache

    def clear(self) -> None:
        self.cache.clear()

    def __len__(self) -> int:
        return len(self.cache)

    def __contains__(self, key: _K) -> bool:
        return key in self.cache

    def __iter__(self) -> Iterator[_K]:
        return iter(self.cache)

    def __repr__(self) -> str:
        return repr(self.cache)

    @property
    def recent(self) -> Optional[_V]:
        with contextlib.suppress(KeyError):
            return self.cache[list(self.cache.keys())[-1]]
        return None

    def keys(self):
        return self.cache.keys()

    def values(self):
        return self.cache.values()

    def items(self, size: int = -1) -> Iterator[Tuple[_K, _V]]:
        if size > 0:
            with contextlib.suppress(IndexError):
                return iter(list(self.cache.items())[:-size-1:-1])
        return iter(self.cache.items())
