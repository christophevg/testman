import logging
logger = logging.getLogger(__name__)

import yaml
import json
from pymongo import MongoClient


from testman import Test

class Store():
  """
  Generic abstract base class for stores.
  """
  def __init__(self):
    self._tests = {}
    self._load()

  def add(self, test):
    self._tests[test.uid] = test
    self._persist(test.uid)
    return self

  def keys(self):
    return list(self._tests.keys())

  def __getitem__(self, uid):
    return self.get(uid)

  def get(self, uid):
    test = self._tests.get(uid)
    if test:
      test = TestWrapper(test, self)
    return test

  def _persist(self, uid):
    raise NotImplementedError

  def _load(self):
    raise NotImplementedError


class MemoryStore(Store):
  """
  Simple in-memory store without persistence.
  """
  def _persist(self, uid):
    pass

  def _load(self):
    pass


class FileStore(Store):
  """
  Base class for file-based stores.
  """
  def __init__(self, filename, loader, saver):
    self.filename = filename
    self._loader  = loader
    self._saver   = saver
    super().__init__()

  def _load(self):
    logger.info("💾 loading")
    try:
      with open(self.filename) as fp:
        self._tests = {}
        test_dicts = self._loader(fp)
        if test_dicts:
          for test_dict in test_dicts:
            test = Test.from_dict(test_dict)
            self._tests[test.uid] = test
    except FileNotFoundError:
      # no statefile yet
      pass

  def _persist(self, uid):
    logger.info(f"💾 saving {uid}")
    with open(self.filename, "w") as fp:
      self._saver([ test.as_dict() for test in self._tests.values() ], fp, indent=2)

class YamlStore(FileStore):
  def __init__(self, filename):
    super().__init__(filename, loader=yaml.safe_load, saver=yaml.dump)

class JsonStore(FileStore):
  def __init__(self, filename):
    super().__init__(filename, loader=json.load, saver=json.dump)

class MongoStore(Store):
  def __init__(self, connection_string):
    server, db_name, collection_name = connection_string.rsplit("/", 2)
    client = MongoClient(server)
    db = client[db_name]
    self.collection = db[collection_name]
    super().__init__()

  def _persist(self, uid):
    self.collection.replace_one({"_id": uid}, self._tests[uid].as_dict(), True)

  def _load(self):
    for test_dict in self.collection.find({}):
      test = Test.from_dict(test_dict)
      self._tests[test.uid] = test

class TestWrapper(object):
  """
  Wraps a Test. When executed, commits back the test state to the store. 
  """
  def __init__(self, test, store):
    self._test  = test
    self._store = store

  def execute(self):
    self._test.execute()
    self._store._persist(self._test.uid)

  def __getattr__(self, attr):
    if attr in self.__dict__:
      return getattr(self, attr)
    return getattr(self._test, attr)
