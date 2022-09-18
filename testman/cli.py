import logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import os

LOG_LEVEL = os.environ.get("LOG_LEVEL") or "INFO"

logging.getLogger("urllib3").setLevel(logging.WARN)

FORMAT  = "[%(asctime)s] %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S %z"

logging.basicConfig(level=LOG_LEVEL, format=FORMAT, datefmt=DATEFMT)
formatter = logging.Formatter(FORMAT, DATEFMT)

from testman       import __version__, Test, Step
from testman.util  import prune
from testman.store import MemoryStore, YamlStore, JsonStore, MongoStore

import json
import yaml

class TestManCLI():
  """
  A wrapper around testman.Test, intended to be used in combination with Fire.
  
  Typical usage:
      % testman script examples/mock.yaml execute results
  """
  def __init__(self):
    self.stored     = MemoryStore()
    self._selection = "all"
  
  def version(self):
    """
    Output TestMan's version.
    """
    print(__version__)
  
  def state(self, uri):
    moniker, connection_string = uri.split("://", 1)
    self.stored = {
      "yaml"   : YamlStore,
      "json"   : JsonStore,
      "mongodb": MongoStore
    }[moniker](connection_string)
    return self  
  
  def load(self, statefile):
    """
    Load a TestMan script/state encoded in JSON or YAML.
    """
    logger.debug(f"loading from '{statefile}'")
    
    self.stored.add(
      Test.from_dict(
        self._load(statefile),
        work_dir=os.path.dirname(os.path.realpath(statefile))
      )
    )
    return self

  def _load(self, filename):
    _, ext = filename.rsplit(".", 1)
    loader = {
      "yaml" : yaml.safe_load,
      "yml"  : yaml.safe_load,
      "json" : json.load
    }[ext]
    with open(filename) as fp:
      return loader(fp)

  def select(self, uids="all"):
    """
    Select one or more tests identified by a list of uids, or all for ... all.
    Default: all.
    """
    if uids == "all":
      self._selection = "all"
    elif isinstance(uids, tuple):
      self._selection = list(uids)
    elif not isinstance(uids, list):
      self._selection = [uids]
    return self

  @property
  def selection(self):
    if not self._selection or self._selection == "all":
      return self.list()
    return self._selection

  @property
  def tests(self):
    return [ self.stored[uid] for uid in self.selection ]

  @property
  def results(self):
    return [ [ prune(results) for results in test.results] for test in self.tests ]

  @property
  def results_as_json(self):
    return json.dumps(self.results, indent=2)

  @property
  def results_as_yaml(self):
    return yaml.dump(self.results)

  def list(self):
    """
    List all tests' uids.
    """
    return self.stored.keys()

  def execute(self):
    """
    Execute selected tests.
    """
    for uid in self.selection:
      # try:
        logger.info(f"⏳ running test '{uid}'")
        self.stored[uid].execute()
      # except AttributeError:
      #   logger.warn(f"🚨 unknown test '{uid}")
    return self

  def status(self):
    """
    Provide information about the status of the selected tests.
    Example output:
      {
        "mock":  {"done": 5, "pending": 2, "ignored": 1, "summary": "2 pending"}
        "gmail": {"done": 2, "pending": 0, "ignored": 0, "summary": "all done"}
      }
    """
    def summary(status):
      done    = status.count("done")
      pending = status.count("pending")
      ignored = status.count("ignored")
      return {
        "done"    : done,
        "pending" : pending,
        "ignored" : ignored,
        "summary" : f"{pending} pending" if pending else "all done"
      }
    return {
      uid : summary(self.stored[uid].status)
      for uid in self.selection 
    }

  def as_json(self):
    """
    Provide results.
    """
    print(json.dumps([ test.as_dict() for test in self.tests ], indent=2))
    return self

  def as_yaml(self):
    """
    Provide results.
    """
    print(yaml.dump([ test.as_dict() for test in self.tests ], indent=2))
    return self

  def __str__(self):
    return ""
