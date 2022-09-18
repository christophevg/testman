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

from testman import __version__, Test, Step

import json
import yaml

class TestManCLI():
  """
  A wrapper around testman.Test, intended to be used in combination with Fire.
  
  Typical usage:
      % testman script examples/mock.yaml execute results
  """
  def __init__(self):
    self._test = None
  
  def version(self):
    """
    Output TestMan's version.
    """
    print(__version__)
  
  def script(self, script):
    """
    Load a TestMan script encoded in JSON or YAML.
    """
    logger.debug(f"loading script from '{script}'")

    _, ext = script.rsplit(".", 1)
    loader = {
      "yaml" : yaml.safe_load,
      "yml"  : yaml.safe_load,
      "json" : json.load
    }[ext]
    with open(script) as fp:
      spec = loader(fp)

    wd = os.path.dirname(os.path.realpath(script))
    self._test = Test.from_dict(spec, work_dir=wd)
    
    return self

  def given(self, results):
    """
    Consider previous results.
    """
    try:
      with open(results) as fp:
        previous = json.load(fp)
        if "constants" in previous:
          self._test.constants = previous["constants"]
        if "results" in previous:
          self._test.given(previous["results"])
    except Exception as e:
      logger.warn(f"failed to load previous results: {str(e)}")
    return self

  def execute(self):
    self._test.execute()
    return self

  def as_json(self):
    """
    Provide results.
    """
    print(json.dumps(self._test.as_dict(), indent=2))
    return self

  def as_yaml(self):
    """
    Provide results.
    """
    print(yaml.dump(self._test.as_dict(), indent=2))
    return self

  def __str__(self):
    return ""
