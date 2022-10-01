import yaml
import json
from testman import Test, Step

def hello(name):
  return f"hello {name}"

steps = yaml.safe_load("""
- name: say hello
  perform: __main__.hello
  with:
    name: Christophe
  assert: result == "hello Christophe"
""")

mytest = Test("hello world test", [ Step.from_dict(step) for step in steps ])
mytest.execute()
print(json.dumps(mytest.results, indent=2))
