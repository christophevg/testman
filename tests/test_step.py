"""
  Step tests
"""

from testman import Step, Assertion

def test_basic_operation():
  def f():
    return True
  step = Step(name="name", func=f, asserts=[ Assertion("result == True")] )
  step.execute()
  assert step.last.output == True
  assert step.last.status == "success"

def test_basic_failing_assertion():
  def f():
    return True
  step = Step(name="name", func=f, asserts=[ Assertion("result == False")] )
  step.execute()
  assert step.last.status == "failed"
  assert step.last.info   == "'result == False' failed for result=True"
