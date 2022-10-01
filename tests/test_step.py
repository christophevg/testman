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

def test_serialization_of_object_result():
  import uuid
  step = Step(name="name", func=uuid.uuid4)
  step.execute()
  assert isinstance(step.last.raw, str)
  assert len(step.as_dict()["runs"][0]["output"]) == 36
