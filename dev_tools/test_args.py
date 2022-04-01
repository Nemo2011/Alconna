import time
from typing import Union

from arclet.alconna import Args, AnyFloat
from arclet.alconna.analysis import analyseArgs

print("\nArgs KVWord construct:")
arg = Args(pak=str, upgrade=bool).default(upgrade=True)
print("arg:", arg)
print(analyseArgs(arg, "arclet-alconna True"))

print("\nArgs Magic construct:")
arg1 = Args["round":AnyFloat, "test":bool:True]["aaa":str] << Args["perm":str:...] + ["month", int]
arg1["foo"] = ["bar", ...]
arg11 = Args.baz[int]
print("arg1:", arg1)
print("arg11:", arg11)

print("\nArgs Feature: Default value")
arg2 = Args["foo":int, "de":bool:True]
print("arg2:", arg2)
print(analyseArgs(arg2, "123 False"))
print(analyseArgs(arg2, "123"))

print("\nArgs Feature: Choice")
arg3 = Args["choice":("a", "b", "c")]
print("arg3:", arg3)
print(analyseArgs(arg3, "a"))  # OK
time.sleep(0.1)
print(analyseArgs(arg3, "d"))  # error

print("\nArgs Feature: Multi")
arg4 = Args["*multi":str]
print("arg4:", arg4)
print(analyseArgs(arg4, "a b c d"))
arg44 = Args["**kwargs":str]
print("arg44:", arg44)
print(analyseArgs(arg44, "a=b c=d"))

print("\nArgs Feature: Anti")
arg5 = Args["!anti":r"(.+?)/(.+?)\.py"]
print("arg5:", arg5)
print(analyseArgs(arg5, "a/b.mp3"))  # OK
time.sleep(0.1)
print(analyseArgs(arg5, "a/b.py"))  # error

print("\nArgs Feature: Union")
arg6 = Args["bar":Union[float, int]]
print("arg6:", arg6)
print(analyseArgs(arg6, "1.2"))  # OK
time.sleep(0.1)
print(analyseArgs(arg6, "1"))  # OK

print("\nArgs Feature: Force")
arg7 = Args["#bar":bool]
print("arg7:", arg7)
print(analyseArgs(arg7, "True"))  # error

print("\nArgs Feature: Optional")
arg8 = Args["?bar":int]
print("arg8:", arg8)
print(analyseArgs(arg8, "abc"))  # OK

print("\nArgs Feature: KWord")
arg9 = Args["@bar":int]
print("arg9:", arg9)
print(analyseArgs(arg9, "bar=123"))  # OK
print(analyseArgs(arg9, "123"))  # error
