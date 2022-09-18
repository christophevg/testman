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
    self.tests    = MemoryStore()
    self._selection = "all"
  
  def version(self):
    """
    Output TestMan's version.
    """
    print(__version__)
  
  def state(self, uri):
    moniker, connection_string = uri.split("://", 1)
    self.tests = {
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
    
    self.tests.add(
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
  def _selected_tests(self):
    return [ self.tests[uid].as_dict() for uid in self.selection ]

  def list(self):
    """
    List all tests' uids.
    """
    return self.tests.keys()

  def execute(self):
    """
    Execute selected tests.
    """

    for uid in self.selection:
      # try:
        logger.info(f"⏳ running test '{uid}'")
        self.tests[uid].execute()
      # except AttributeError:
      #   logger.warn(f"🚨 unknown test '{uid}")
    return self

  def as_json(self):
    """
    Provide results.
    """
    print(json.dumps(self._selected_tests, indent=2))
    return self

  def as_yaml(self):
    """
    Provide results.
    """
    print(yaml.dump(self._selected_tests, indent=2))
    return self

  def __str__(self):
    return ""
