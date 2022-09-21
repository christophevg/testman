import logging
logger = logging.getLogger(__name__)

from collections import UserDict

import yaml
import json

from testman import Test, Suite

class State(UserDict):
  """
  Simple in-memory state without persistence. Behaves like a dict, with an 
  additional `add` method to add a Suite and to get a `status` of all suites.
  
  A State holds one or more Suites.
  Typical usages:
  
  >>> state = State()
  >>> suite1 = Suite("suite1")
  >>> state.add(suite1)
  >>> suite2 = Suite("suite2")
  >>> state.add(suite2)
  >>> state.keys()
  [
    "suite1",
    "suite2"
  ]
  >>> state.get("suite1").add(Test(...))
  >>> state.get("suite1").add(Test(...))
  >>> state.get("suite1").execute()
  >>> state.summary
  {
    "suite1" : {
      "unknown": 0,
      "success": 2,
      "ignored": 0,
      "failed" : 0,
      "pending": 0,
      "summary": "all done"
    },
    "suite2" : {
      "unknown": 0,
      "success": 0,
      "ignored": 0,
      "failed" : 0,
      "pending": 0,
      "summary": "all done"
    }
  }
  """
  
  @property
  def list(self):
    return list(self.keys())
  
  def add(self, suite):
    self[suite.name] = suite
    # TODO: look into more entry points to setup callback
    # - __setitem__
    # - update
    suite.on_change((lambda evt, ctx: self.persist(suite.name)))
    return self

  def drop(self, suite):
    del self[suite.name]
    self.persist()
    return self

  @property
  def summary(self):
    return { name : suite.status for name, suite in self.items() }

  def persist(self, suite):
    pass

class FileState(State):
  """
  Base class for file-based states.
  """
  def __init__(self, filename, loader=None, saver=None):
    super().__init__()
    self.filename = filename
    self._loader = loader
    self._saver  = saver
    self._load()

  def _load(self):
    logger.info("💾 loading")
    try:
      with open(self.filename) as fp:
        self.data = {}
        suites = self._loader(fp)
        if suites:
          for suite in suites:
            self.add(Suite.from_dict(suite))
    except FileNotFoundError:
      # no statefile yet
      pass

  def persist(self, suite):
    logger.info(f"💾 saving")
    with open(self.filename, "w") as fp:
      self._saver([ suite.as_dict() for suite in self.data.values() ], fp, indent=2)

class YamlState(FileState):
  def __init__(self, filename):
    super().__init__(filename, loader=yaml.safe_load, saver=yaml.dump)

class JsonState(FileState):
  def __init__(self, filename):
    super().__init__(filename, loader=json.load, saver=json.dump)

class MongoState(State):
  def __init__(self, collection):
    super().__init__()
    self.collection = collection
    self._load()

  def _load(self):
    for suite in self.collection.find({}):
      self.add(Suite.from_dict(suite))

  def persist(self, name):
    suite = self.data[name]
    self.collection.replace_one({ "name": name }, suite.as_dict(), True)

  @property
  def suites(self):
    return list(self.collection.distinct("suite"))

  def drop(self, suite):
    del self[suite]
    self.collection.delete_many({"name" : suite })
    return self
