__version__ = "0.0.2"

import logging
logger = logging.getLogger(__name__)

import os
import traceback
from dotmap import DotMap

from testman.util import get_function, expand

class Test():
  
  """
  describes a test and allows executing it.
  
  A Test holds all information regarding a test and allows to execute it.
  """
  def __init__(self, description, steps, vars=None, constants=None):
    self.description = description
    self.steps       = steps
    self._vars       = vars
    self.constants   = constants
    self._results    = []
    logger.debug(f"loaded '{self.description}' with {len(self.steps)} steps")

  @classmethod
  def from_dict(cls, d):
    vars = {
      var : expand(value) for var, value in d.get("variables", {}).items()
    }
    constants = {
      var : expand(value) for var, value in d.get("constants", {}).items()
    }
    steps  = [ Step.from_dict(s) for s in d.get("steps", []) ]
    return Test( d.get("test"), steps, vars, constants )

  def given(self, previous_results):
    """
    Consider previous results. This erases previously recorded results in this
    object.
    """
    self._results = [ previous_results ]

  def execute(self):
    """
    Execute the script.
    """
    results = []
    previous = self.results
    logger.debug(f"comparing to {len(previous)} previous results")
    for index, step in enumerate(self.steps):
      result = { "step" : step.name, "result" : "failed" }
      if not step.always and index < len(previous) and previous[index]["result"] == "success":
        logger.info(f"♻️ {step.name}")
        result = previous[index]
        result["skipped"] = True
      else:  
        try:
          result["output"] = step.execute(self.vars)
          result["result"] = "success"
          logger.info(f"✅ {step.name}")
        except AssertionError as e:
          result["info"] = str(e)
          logger.info(f"🚨 {step.name} - {str(e)}")
        except Exception as e:
          result["info"] = traceback.format_exc()
          logger.info(f"🛑 {step.name}")
          logger.exception()

      results.append(result)
      if result["result"] == "failed":
        if not step.proceed:
          break
    self._results.append(results)
  
  @property
  def vars(self):
    v = {}
    if self._vars:
      v.update(self._vars)
    if self.constants:
      v.update(self.constants)
    return v
  
  @property
  def results(self):
    """
    Provide most recent results.
    """
    return self._results[-1] if self._results else []
  
class Step():
  def __init__(self, name=None,    func=None,     args=None,
                     asserts=None, proceed=False, always=False):
    self.name    = name
    if not self.name:
      raise ValueError("a step needs a name")
    self.func    = func
    if not self.func:
      raise ValueError("a step needs a function")
    self.args    = args or {}
    self.asserts = asserts or []
    self.proceed = proceed
    self.always  = always
  
  @classmethod
  def from_dict(cls, d,):
    name = d["step"]
    func = d["perform"]
    # parse string into func
    if isinstance(func, str):
      try:
        func = get_function(func)
      except ModuleNotFoundError as e:
        raise ValueError(f"in step '{name}': unknown module for {func}") from e
      except AttributeError as e:
        raise ValueError(f"in step '{name}': unknown function {func}") from e
    args = d.get("with", {})
    # accept single string or list of strings
    asserts = d.get("assert", [])
    if not isinstance(asserts, list):
      asserts = [ asserts ]
    asserts = [ Assertion(a) for a in asserts ]

    return Step(
      name, func, args,
      asserts, d.get("continue", None), d.get("always", None)
    )
  
  def execute(self, vars=None):
    if not vars:
      vars = {}
    # substitute environment variables formatted as $name and files as @name
    args = { k : expand(v, vars) for k,v in self.args.items() }
    result = self.func(**args)
    for a in self.asserts:
      a(result)
    return result

class Assertion():
  def __init__(self, spec):
    self._spec = spec
    self._test = spec
    cmd, args = spec.split(" ", 1)
    if cmd in [ "all", "any" ]:
      self._test = f"{cmd}( {args} )"
  
  def __call__(self, raw_result):
    result = raw_result
    if isinstance(raw_result, dict):
      result = DotMap(raw_result)
    if isinstance(raw_result, list):
      result = [ DotMap(r) if isinstance(r, dict) else r for r in raw_result ]
    logger.debug(f"asserting '{result}' against '{self._test}'")
    assert eval(self._test), f"'{self._spec}' failed for result={raw_result}"
