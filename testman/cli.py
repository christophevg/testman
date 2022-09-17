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
    Load a TestMan script encoded in YAML.
    """
    logger.debug(f"loading script from '{script}'")
    with open(script) as fp:
      spec = yaml.safe_load(fp)
    self._test = Test.from_dict(spec)
    return self

  def given(self, results):
    """
    Consider previous results.
    """
    try:
      with open(results) as fp:
        previous = json.load(fp)
        self._test.given(previous)
    except:
      logger.warn("failed to load previous results")
    return self

  def execute(self):
    self._test.execute()
    return self

  def results(self):
    """
    Provide results.
    """
    print(json.dumps(self._test.results, indent=2, default=str))
    return self

  def __str__(self):
    return ""
