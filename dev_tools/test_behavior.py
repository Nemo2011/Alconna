from arclet.alconna import Alconna, Args, Option
from arclet.alconna.arpamar import ArpamarBehavior, ArpamarBehaviorInterface
from arclet.alconna.builtin.actions import setDefault, exclusion, coolDown
import time


class Test(ArpamarBehavior):
    def operate(self, interface: "ArpamarBehaviorInterface"):
        print(interface.require("options.foo"))
        interface.changeConst("matched", False)


alc = Alconna(
    "command",
    options=[
        Option("foo"),
    ],
    mainArgs=Args["bar":int],
    behaviors=[setDefault(321, option="foo"), Test()],
)
print(alc.parse(["command", "123"]))

alc1 = Alconna(
    "test_exclusion",
    options=[
        Option("foo"),
        Option("bar"),
    ],
    behaviors=[exclusion(target_path="options.foo", other_path="options.bar")]
)
print(alc1.parse("test_exclusion\nfoo"))

alc2 = Alconna(
    "test_cool_down",
    mainArgs=Args["bar":int],
    behaviors=[coolDown(0.2)]
)
for i in range(4):
    time.sleep(0.1)
    print(alc2.parse("test_cool_down {}".format(i)))
