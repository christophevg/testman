import logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import os

LOG_LEVEL = os.environ.get("LOG_LEVEL") or "DEBUG"

logging.getLogger("urllib3").setLevel(logging.WARN)

FORMAT  = "[%(asctime)s] %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S %z"

logging.basicConfig(level=LOG_LEVEL, format=FORMAT, datefmt=DATEFMT)
formatter = logging.Formatter(FORMAT, DATEFMT)

import json
import yaml
from pymongo import MongoClient

from testman       import __version__, Suite, Test, Step, states
from testman.util  import prune, load_ml
from testman.state import State, YamlState, JsonState, MongoState

class TestManCLI():
  """
  A wrapper around testman.Test, intended to be used in combination with Fire.
  
  Typical usage:
      % testman load examples/mock.yaml execute status
  """
  def __init__(self):
    self.suites  = State()
    self._suite = "default"
  
  @property
  def version(self):
    """
    Return TestMan's version.
    """
    return __version__
  
  def state(self, uri):
    def create_mongo_state(connection_string):
      server, db_name, collection_name = connection_string.rsplit("/", 2)
      client = MongoClient(server)
      db = client[db_name]
      return MongoState(db[collection_name])

    moniker, connection_string = uri.split("://", 1)
    self.suites = {
      "yaml"   : YamlState,
      "json"   : JsonState,
      "mongodb": create_mongo_state
    }[moniker](connection_string)
    return self  
  
  def select(self, name):
    """
    Select the suite to work with.
    """
    self._suite = name
    return self

  @property
  def suite(self):
    """
    Return the currently selected suite, creating one if it doesn't exist yet.
    """
    try:
      return self.suites[self._suite]
    except KeyError:
      self.suites.add(Suite(self._suite))
    return self.suites[self._suite]
      
  def load(self, script):
    """
    Load a TestMan script/state encoded in JSON or YAML into the current suite.
    """
    logger.debug(f"loading test from '{script}'")
    
    self.suite.add(
      Test.from_dict(
        load_ml(script),
        work_dir=os.path.dirname(os.path.realpath(script))
      )
    )
    return self

  def list(self, what="suites"):
    """
    List known 'suites' or 'tests'.
    """
    return {
      "suites" : list(self.suites.keys()),
      "tests"  : [ test.uid for test in self.suite.tests ]
    }[what]

  def execute(self):
    """
    Execute the currently selected suite.
    """
    self.suite.execute()
    return self

  def drop(self, suite=None):
    """
    Drop/delete/remove a suite by name or 'all' for all suites.
    """
    if suite is None:
      self.suites.drop(self._suite)
    elif suite == "all":
      for suite in self.suites.keys():
        self.suites.drop(suite)
    else:
      self.suites.drop(suite)
    return self

  @property
  def summary(self):
    """
    Provide summaries for all suites.
    """
    return { suite.name : suite.summary for suite in self.suites.values() }

  @property
  def results(self):
    return self.suite.results

  @property
  def results_as_json(self):
    return json.dumps(self.results, indent=2)

  @property
  def results_as_yaml(self):
    return yaml.dump(self.results)

  @property
  def as_json(self):
    """
    Dump currently selected suite as json.
    """
    return json.dumps(self.suite.as_dict(), indent=2)

  @property
  def as_yaml(self):
    """
    Dump currently selected suite as yaml.
    """
    return yaml.dump(self.suite.as_dict(), indent=2)

  def __str__(self):
    return ""
