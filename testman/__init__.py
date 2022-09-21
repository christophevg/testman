__version__ = "0.0.4"

import logging
logger = logging.getLogger(__name__)

import os
import traceback
from dotmap import DotMap
import uuid

from testman.util import get_function, expand, prune, utcnow

states = [ "unknown", "success", "ignored", "pending", "failed" ]
states_map = { state : index for index, state in enumerate(states) }
def reduce_states(l):
  state = 0
  for s in l:
    si = states_map[s]
    if si > state:
      state = si
  return states[state] 

class Suite():
  """
  is a collection of Tests, that can be managed as a whole.
  """
  def __init__(self, name, tests=None):
    self.name       = name
    self.tests      = [] if tests is None else tests
    self._on_change = []

  @classmethod
  def from_dict(cls, d):
    """
    Unmarshalls a dict to a suite.
    """
    return Suite(d["name"], [
      Test.from_dict(t) for t in d["tests"]
    ])

  def as_dict(self):
    """
    Marshalls the suite as a dict.
    """
    return {
      "name"   : self.name,
      "status" : self.status,
      "tests"  : [ t.as_dict() for t in self.tests ]
    }

  def __str__(self):
    return ""

  def on_change(self, callback):
    self._on_change.append(callback)
    return self

  def _notify(self, change, context):
    for callback in self._on_change:
      callback(change, context)

  def add(self, test):
    self.tests.append(test)
    self._notify("add", test)
    return self

  def execute(self):
    """
    Executes all tests.
    """
    for test in self.tests:
      test.execute()
    self._notify("execute", self)
    return self

  def reset(self):
    """
    Resets all test, removing all previous runs' information.
    """
    for test in self.tests:
      test.reset()
    self._notify("reset", self)
    return self

  @property
  def overview(self):
    """
    Provide a status overview of all tests.
    """
    return [ test.overview for test in self.tests ]

  @property
  def status(self):
    """
    Aggregate the status of the tests into one status for the suite.
    """
    return reduce_states([ reduce_states(test) for test in self.overview ])

  @property
  def results(self):
    return { test.uid : test.results for test in self.tests }

  @property
  def summary(self):
    """
    Provide information about the status of the selected tests.
    Example output:
      {
        "mock":  {"done": 5, "pending": 2, "ignored": 1, "summary": "2 pending"}
        "gmail": {"done": 2, "pending": 0, "ignored": 0, "summary": "all done"}
      }
    """
    def summary(status):
      s = { s : status.count(s) for s in states }
      in_progress = s["pending"] + s["unknown"]
      s["summary"] = f"{in_progress} in progress" if in_progress else "all done"
      return s
      
    return { test.uid : summary(test.overview) for test in self.tests }

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
                     variables=None, constants=None, work_dir=None):
    self.uid         = uid if uuid else str(uuid.uuid4())
    self.description = description
    self._variables  = variables
    self.constants   = constants
    self.work_dir    = work_dir
    self.steps       = steps
    for step in steps: step.test = self # adopt tests (FIXME)
    logger.debug(f"loaded '{self.description}' with {len(self.steps)} steps")

  @classmethod
  def from_dict(cls, d, work_dir=None):
    uid         = d.get("uid",      None)
    description = d.get("name",     None)
    work_dir    = d.get("work_dir", work_dir)
    variables   = d.get("variables", {})
    constants = {
      var : expand(value) for var, value in d.get("constants", {}).items()
    }
    steps = [
      Step.from_dict(s, idx) for idx, s in enumerate(d.get("steps", []))
    ]
    return Test(
      description, steps, uid=uid,
      variables=variables, constants=constants, work_dir=work_dir
    )

  def as_dict(self):
    return prune({
      "uid"      : self.uid,
      "name"     : self.description,
      "status"   : self.status,
      "variables": self._variables,
      "constants": self.constants,
      "work_dir" : self.work_dir,
      "steps"    : [ step.as_dict() for step in self.steps ]
    })

  def execute(self):
    """
    Run the entire script.
    """
    vars = self.vars
    with WorkIn(self.work_dir):
      for step in self.steps:
        step.execute(vars)
        if step.abort:
          break
  
  def reset(self):
    """
    Reset the test by removing al previous runs' information.
    """
    for step in self.steps:
      step.reset()
    return self
  
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
    return { step.name : step.result for step in self.steps }
  
  @property
  def overview(self):
    return [ step.status for step in self.steps ]

  @property
  def status(self):
    return reduce_states(self.overview)
  
class Step():
  def __init__(self, index=None, name=None,    func=None,     args=None,
                     asserts=None,
                     proceed=False, always=False, ignore=False, noretry=False,
                     runs=None):
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
    self.noretry = noretry
    self.test    = None
    self.runs    = runs or []
  
  @classmethod
  def from_dict(cls, d, index, test=None):
    name = d["name"]
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
    # runs 1 or more
    runs = d.get("runs", [])
    if not isinstance(runs, list):
      runs = [ runs ]
    runs    = [ Run.from_dict(run) for run in runs]

    return Step(
      index, name, func, args, asserts,
      d.get("continue", None), d.get("always", None), d.get("ignore", None),
      d.get("noretry", None),
      runs
    )
  
  def as_dict(self):
    return prune({
      "name"     : self.name,
      "status"   : self.status,
      "perform"  : f"{self.func.__module__}.{self.func.__name__}",
      "with"     : self.args,
      "assert"   : [ str(assertion) for assertion in self.asserts ],
      "continue" : self.proceed,
      "always"   : self.always,
      "ignore"   : self.ignore,
      "noretry"  : self.ignore,
      "runs"     : [ run.as_dict() for run in self.runs ]      
    })
  
  def reset(self):
    self.runs = []
    return self
  
  @property
  def status(self):
    """
    A step can have several states:
    - unknown: no execution information is known
    - success: the last execution was successful
    - ignored: the last execution failed, but this could be ignored
    - failed : the last execution failed, and no retrying is allowed
    - pending: the last execution failed, the test will be retried
    """
    if self.last:
      if self.last.status == "success":
        return "success"
      if self.last.status == "failed" and self.ignore:
        return "ignored"
      if self.last.status == "failed" and self.noretry:
        return "failed"
      if self.last.status == "failed":
        return "pending"
    return "unknown"

  @property
  def result(self):
    if self.runs:
      return self.runs[-1].as_dict()
    return None
  
  @property
  def last(self):
    if self.runs:
      return self.runs[-1]
    return None

  @property
  def abort(self):
    if self.runs:
      return self.last.status == "failed" and not self.proceed
    return False

  def execute(self, vars):
    with Run() as run:
      # if previous run as successful, skip
      if self.last and self.last.status == "success" and not self.always:
        logger.info(f"💤 skipping previously succesfull '{self.name}'")
        run.status = self.last.status
        run.skipped = True
      # if previous run failed, but we ignore it because it will always fail
      elif self.last and self.last.status == "failed" and self.ignore:
        logger.info(f"💤 ignoring previously failed '{self.name}'")
        run.status = self.last.status
        run.skipped = True
      else:
        # actually execute it
        try:
          args = { k : expand(v, vars) for k,v in self.args.items() }
          run.output = self.func(**args)
          for a in self.asserts:
            a(run.raw, vars)
          run.status = "success"
          logger.info(f"✅ {self.name}")
        except AssertionError as e:
          run.info = str(e)
          run.status = "failed"
          logger.info(f"🚨 {self.name} - {str(e)}")
        except Exception as e:
          run.info = traceback.format_exc()
          run.status = "failed"
          logger.info(f"🛑 {self.name}")
          logger.exception("unexpected exception...")

      self.runs.append(run)

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
    self.raw     = None
    self._output = None
    self.info    = None
    self.status  = "unknown"
    self.skipped = False

  @property
  def output(self):
    return self._output

  @output.setter
  def output(self, output):
    self.raw = output
    if output and not type(output) in [ int, float, bool, str, list, dict ]:
        output = repr(output)
    self._output = output

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
    run.output  = d.get("output")
    run.info    = d.get("info")
    run.status  = d["status"]
    run.skipped = d.get("skipped")
    return run

  def as_dict(self):
    return {
      "start"   : self.start,
      "end"     : self.end,
      "output"  : self.output,
      "info"    : self.info,
      "status"  : self.status,
      "skipped" : self.skipped,
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
