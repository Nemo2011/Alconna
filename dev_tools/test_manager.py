from dev_tools.test_alconna_1 import *
from dev_tools.test_alconna_2 import *

print("\n\n## ------------- Test Manager -------------## \n\n")
print(commandManager.getAllCommandHelp(max_length=6, page=3, pages="[%d/%d]"))
print("\n")
print(commandManager.broadcast("cmd.北京天气"))
print(commandManager.require("/pip"))
print(commandManager.getCommandHelp("/pip"))