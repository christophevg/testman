__version__ = "0.0.1"

import logging
logger = logging.getLogger(__name__)

import os
import importlib
import traceback
from dotmap import DotMap

class Test():
  
  """
  describes a test and allows executing it.
  
  A Test holds all information regarding a test and allows to execute it.
  """
  def __init__(self, description, steps):
    self._description = description
    self._steps       = [ Step(step) for step in steps ]
    self._results     = []
    logger.debug(f"loaded '{self._description}' with {len(self._steps)} steps")

  def given(self, results):
    """
    Consider previous results. This erases previously recorded results in this
    object.
    """
    self._results = [ results ]
    return self

  def execute(self):
    """
    Execute the script.
    """
    results = []
    previous = self.results
    logger.debug(f"comparing to {len(previous)} previous results")
    for index, step in enumerate(self._steps):
      result = { "step" : step.name, "result" : "failed" }
      if not step.always and index < len(previous) and previous[index]["result"] == "success":
        logger.info(f"♻️ {step.name}")
        result = previous[index]
        result["skipped"] = True
      else:  
        try:
          result["output"] = step.execute()
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
  def results(self):
    """
    Provide most recent results.
    """
    return self._results[-1] if self._results else []
  

class Step():
  def __init__(self, spec):
    self.name  = spec.pop("step")
    mod_name, func_name = spec.pop("perform").rsplit(".", 1)
    try:
      mod                 = importlib.import_module(f"testman.testers.{mod_name}")
      self._fqn           = f"testman.testers.{mod_name}.{func_name}"
    except ModuleNotFoundError:
      try:
        mod                 = importlib.import_module(f"{mod_name}")
        self._fqn           = f"{mod_name}.{func_name}"      
      except ModuleNotFoundError:
        logger.error(f"could not find '{mod_name}.{func_name}")
        raise ValueError(f"could not find '{mod_name}.{func_name}")
    self._func          = getattr(mod, func_name)
    self._args          = {
      k : os.environ.get(v[1:]) if v[0] == "$" else v
      for k,v in spec.pop("with", {}).items()
    }
    assertions = spec.pop("assert", [])
    if not isinstance(assertions, list):
      assertions = [ assertions ]
    self._assertions    = [ Assertion(a) for a in assertions ]
    self.proceed        = spec.pop("continue", False)
    self.always         = spec.pop("always", False)
  
  def execute(self):
    result = self._func(**self._args)
    for a in self._assertions:
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
