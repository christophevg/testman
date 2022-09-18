__version__ = "0.0.2"

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
    self.description = description
    self.steps       = steps
    self._results    = []
    logger.debug(f"loaded '{self.description}' with {len(self.steps)} steps")

  @classmethod
  def from_dict(cls, d):
    return Test(d.get("test"), [Step.from_dict(s) for s in d.get("steps", [])])

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
  def from_dict(cls, d):
    name = d["step"]
    func = d["perform"]
    # parse string into func
    if isinstance(func, str):
      mod_name, func_name = func.rsplit(".", 1)
      try:
        mod  = importlib.import_module(f"{mod_name}")
        func = getattr(mod, func_name)
      except ModuleNotFoundError as e:
        raise ValueError(f"in step '{name}': unknown module {mod_name}") from e
      except AttributeError as e:
        raise ValueError(f"in step '{name}': unknown function {func_name}") from e
    # substitute environment variables formatted as $name and files as @name
    def expand(v):
      if v[0] == "~":
        with open(v[1:]) as fp:
          v = fp.read()
      elif v[0] == "$":
        try:
          v = os.environ[v[1:]]
        except KeyError as e:
          raise ValueError(f"in step '{name}': unknown variable '{v}'") from e
      return v
    args = { k : expand(v) for k,v in d.get("with", {}).items() }
    # accept single string or list of strings
    asserts = d.get("assert", [])
    if not isinstance(asserts, list):
      asserts = [ asserts ]
    asserts = [ Assertion(a) for a in asserts ]

    return Step(
      name, func, args,
      asserts, d.get("continue", None), d.get("always", None)
    )
  
  def execute(self):
    result = self.func(**self.args)
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
