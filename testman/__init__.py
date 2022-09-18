__version__ = "0.0.2"

import logging
logger = logging.getLogger(__name__)

import os
import traceback
from dotmap import DotMap
import uuid

from testman.util import get_function, expand, prune, utcnow

class Test():
  
  """
  describes a test and allows executing it.
  
  A Test holds all information regarding a test and allows to execute it. It can
  be constructed from a dictionary and provides an `as_dict` function for
  marshalling, enabling round-tripping and state persistence, including
  execution results. This allows for repetitive executions with knowledge of 
  previous execution.
  
  >>> from testman import Test
  >>> import yaml
  >>> with open("examples/mock.yaml") as fp:
  ...   script = yaml.safe_load(fp)
  ... 
  >>> t1 = Test.from_dict(script)
  >>> d1 = t1.as_dict()
  >>> t2 = Test.from_dict(d1)
  >>> d2 = t2.as_dict()
  >>> d1 == d2
  True
  """
  def __init__(self, description, steps, uid=None,
                     variables=None, constants=None, work_dir=None, runs=None):
    self.uid         = uid if uuid else str(uuid.uuid4())
    self.description = description
    self._variables  = variables
    self.constants   = constants
    self.work_dir    = work_dir
    self.steps       = steps
    for step in steps: step.test = self # adopt tests (FIXME)
    self._runs       = runs if runs else []
    logger.debug(f"loaded '{self.description}' with {len(self.steps)} steps")

  @classmethod
  def from_dict(cls, d, work_dir=None):
    uid         = d.get("uid",      None)
    description = d.get("test",     None)
    work_dir    = d.get("work_dir", work_dir)
    variables   = d.get("variables", {})
    constants = {
      var : expand(value) for var, value in d.get("constants", {}).items()
    }
    steps = [
      Step.from_dict(s, idx) for idx, s in enumerate(d.get("steps", []))
    ]
    runs = [
      Run.from_dict(r) for r in d.get("runs", [])
    ]
    return Test(
      description, steps, uid=uid,
      variables=variables, constants=constants, work_dir=work_dir,
      runs=runs
    )

  def as_dict(self):
    return prune({
      "uid"      : self.uid,
      "test"     : self.description,
      "variables": self._variables,
      "constants": self.constants,
      "work_dir" : self.work_dir,
      "steps"    : [ step.as_dict() for step in self.steps ],
      "runs"     : [ run.as_dict()  for run in self._runs  ]
    })

  def execute(self):
    """
    Run the entire script.
    """
    with WorkIn(self.work_dir):
      with Run() as run:
        for step in self.steps:
          result = self.perform(step)
          run.add(result)
          if result["result"] == "failed" and not step.proceed:
            break
        self._runs.append(run)

  def perform(self, step):
    """
    Run a single step, provided as index or object.
    """
    if isinstance(step, int):
      step = self.steps[index]
    output  = None
    result  = "failed"
    info    = None
    skipped = False

    # skip previous success
    previous = step.result
    if not step.always and previous and previous["result"] == "success":
      logger.info(f"💤 skipping previously succesfull '{step.name}'")
      output = previous["output"]
      result = previous["result"]
      skipped = True
    # ignore this step if it failed previously (aka it will never succeed)
    elif previous and previous["result"] == "failed" and step.ignore:
      logger.info(f"💤 ignoring previously failed '{step.name}'")
      output = previous["output"]
      result = previous["result"]
      skipped = True      
    else:
      try:
        output = step.execute(self.vars)
        if output and not type(output) in [ int, float, bool, str, list, dict ]:
          output = repr(output)
        result = "success"
        logger.info(f"✅ {step.name}")
      except AssertionError as e:
        info = str(e)
        logger.info(f"🚨 {step.name} - {str(e)}")
      except Exception as e:
        info = traceback.format_exc()
        logger.info(f"🛑 {step.name}")
        logger.exception("unexpected exception...")

    return {
      "step"   : step.name,
      "output" : output,
      "result" : result,
      "info"   : info,
      "skipped": skipped
    }
  
  @property
  def vars(self):
    v = {}
    if self._variables:
      # expand when asked for...
      v.update({
        var : expand(value) for var, value in self._variables.items()
      })
    if self.constants:
      v.update(self.constants)
    return v
  
  @property
  def results(self):
    """
    Provide most recent results.
    """
    return self._runs[-1].results if self._runs else []
  
  @property
  def status(self):
    return [ step.status for step in self.steps ]
  
class Step():
  def __init__(self, index=None, name=None,    func=None,     args=None,
                     asserts=None, proceed=False, always=False, ignore=False):
    self.index   = index
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
    self.ignore  = ignore
    self.test    = None
  
  @property
  def status(self):
    if self.result:
      if self.result["result"] == "success":
        return "done"
      if self.result["result"] == "failed" and self.ignore:
        return "ignored"
    return "pending"

  @property
  def result(self):
    if self.index < len(self.test.results):
      return self.test.results[self.index]
    return None

  @classmethod
  def from_dict(cls, d, index, test=None):
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
      index, name, func, args, asserts,
      d.get("continue", None), d.get("always", None), d.get("ignore", None)
    )
  
  def as_dict(self):
    return prune({
      "step"     : self.name,
      "perform"  : f"{self.func.__module__}.{self.func.__name__}",
      "with"     : self.args,
      "assert"   : [ str(assertion) for assertion in self.asserts ],
      "continue" : self.proceed,
      "always"   : self.always,
      "ignore"   : self.ignore
    })
  
  def execute(self, vars=None):
    if not vars:
      vars = {}
    # substitute environment variables formatted as $name and files as @name
    args = { k : expand(v, vars) for k,v in self.args.items() }
    result = self.func(**args)
    for a in self.asserts:
      a(result, vars)
    return result

class Assertion():
  def __init__(self, spec):
    self._spec = spec
    self._test = spec
    cmd, args = spec.split(" ", 1)
    if cmd in [ "all", "any" ]:
      self._test = f"{cmd}( {args} )"
      
  def __str__(self):
    return self._spec
  
  def __call__(self, raw_result, vars):
    result = raw_result
    if isinstance(raw_result, dict):
      result = DotMap(raw_result)
    if isinstance(raw_result, list):
      result = [ DotMap(r) if isinstance(r, dict) else r for r in raw_result ]
    logger.debug(f"asserting '{result}' against '{self._test}'")
    assertion = expand(self._test, vars)
    assert eval(assertion), f"'{self._spec}' failed for result={raw_result}"

class Run():
  def __init__(self):
    self.start   = None
    self.end     = None
    self.results = []

  def add(self, result):
    self.results.append(result)

  def __enter__(self):
    self.start = utcnow()
    return self

  def __exit__(self, type, value, traceback):
    self.end = utcnow()

  @classmethod
  def from_dict(cls, d):
    run = Run()
    run.start   = d["start"]
    run.end     = d["end"]
    run.results = d["results"]
    return run

  def as_dict(self):
    return {
      "start"   : self.start,
      "end"     : self.end,
      "results" : self.results
    }

class WorkIn():
  def __init__(self, work_dir=None):
    self.work_dir = work_dir
    self.cwd      = None

  def __enter__(self):
    if self.work_dir:
      self.cwd = os.getcwd() 
      os.chdir(self.work_dir)
      logger.info(f"▶ in {self.work_dir}")
    return self

  def __exit__(self, type, value, traceback):
    if self.cwd:
      os.chdir(self.cwd)
      logger.info(f"◀ in {self.cwd}")
