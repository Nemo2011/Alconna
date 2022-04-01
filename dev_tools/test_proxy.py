from arclet.alconna import AlconnaString
from arclet.alconna.proxy import AlconnaMessageProxy


def test(something):
    print(something)
    print(something.origin)
    print(something.result)
    print(something.helpText)


class Test(AlconnaMessageProxy):

    async def fetchMessage(self):
        yield "test --foo"
        yield "test --help foo"
        yield "test --help foo"


alc = AlconnaString("test  #测试命令", "--foo #测试选项")
proxy = Test()

proxy.addProxy("test")


async def main():
    await proxy.run()
    res = await proxy.export("test")
    test(res)

proxy.loop.run_until_complete(main())