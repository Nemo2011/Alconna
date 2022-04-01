<div align="center"> 

# Alconna?

</div>

![Alconna?](https://img.shields.io/badge/NeverGonna-GiveYouUp-2564c2.svg)
![latest release](https://img.shields.io/github/release/ArcletProject/Alconna)
[![Licence](https://img.shields.io/github/license/ArcletProject/Alconna)](https://github.com/ArcletProject/Alconna/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/arclet-alconna)](https://pypi.org/project/arclet-alconna)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/arclet-alconna)](https://www.python.org/)

> 经过一番大彻大悟，我发现python的代码规范实在是一言难尽, 于是我决定把Alconna代码全部修改一遍
> 
> 我抛弃了snakecase的命名规范，改用camelcase，并且把所有的变量都改为大写，这样就不会冲突了
> 
> 具体内容看这里: [链接](https://b23.tv/g49y0K)

`Alconna?` 隶属于`ArcletProject`， 是 `Cesloi-CommandAnalysis` 的高级版，
支持解析消息链或者其他原始消息数据

`Alconna?` 拥有复杂的解析功能与命令组件，但 一般情况下请当作~~奇妙~~简易的消息链解析器/命令解析器(雾)

## 安装

pip
```
pip install --upgrade arclet-alconna
```

## 文档

文档链接: [👉指路](https://y.music.163.com/m/song?app_version=8.1.70&id=5221167&userid=3269267634)

## 简单使用
```python
from arclet.alconna import Alconna, Option, Subcommand, Args

cmd = Alconna(
    "/pip",
    mainArgs=Args["using"],
    options=[
        Subcommand("install", [Option("-u| --upgrade")], Args.pak_name[str]),
        Option("list"),
    ]
)

result = cmd.parse("/pip using install cesloi --upgrade") # 该方法返回一个Arpamar类的实例
print(result.get('install'))  # 或者 result.install
```
其结果为
```
{'pak_name': 'cesloi', 'upgrade': Ellipsis}
```

## 讨论

QQ 交流群: [链接](https://jq.qq.com/?_wv=1027&k=PUPOnCSH)

## 性能参考
在 i5-10210U 处理器上, `Alconna` 的性能大约为 `31000~101000 msg/s`, 取决于 `Alconna` 的复杂程度