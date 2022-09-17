import yaml
import json
from testman import Test

def hello(name):
  return f"hello {name}"

steps = yaml.safe_load("""
- step: say hello
  perform: __main__.hello
  with:
    name: Christophe
  assert: result == "hello Christophe"
""")

mytest = Test("hello world test", steps)
mytest.execute()
print(json.dumps(mytest.results, indent=2))
