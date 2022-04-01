from arclet.alconna import Alconna, Args, Option, Subcommand
from arclet.alconna.visitor import AlconnaNodeVisitor
from arclet.alconna.builtin.formatter import DefaultHelpTextFormatter


alc = Alconna("test_line", mainArgs="line:'...'")
print(alc.parse("test_line\nfoo\nbar\n"))
b = AlconnaNodeVisitor(
    Alconna(
        command="test",
        helpText="test_help",
        options=[
            Option("test", Args.foo[str], helpText="test_option"),
            Subcommand(
                "sub",
                options=[
                    Option("suboption", Args.foo[str], helpText="sub_option"),
                    Option("suboption2", Args.foo[str], helpText="sub_option2"),
                ]
            )
        ]
    )
)
print(b.formatNode(DefaultHelpTextFormatter(), b.require(["sub"])))
