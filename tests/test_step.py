"""
  Step tests
"""

from testman import Step, Assertion

def test_basic_operation():
  def f():
    return True
  step = Step("name", f, asserts=[ Assertion("result == True")] )
  result = step.execute()
  assert result == True

def test_basic_failing_assertion():
  def f():
    return True
  step = Step("name", f, asserts=[ Assertion("result == False")] )
  success = True
  try:
    step.execute()
  except AssertionError:
    success = False
  if success:
    assert False, "should have raised an assertion error"

