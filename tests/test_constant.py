from testman import Constant

def test_constant_value():
  c = Constant("testman.util.utcnow | isoformat")
  v = c.value
  assert c.value == v

def test_reset_constant():
  c = Constant("testman.util.utcnow | isoformat")
  v = c.value
  assert c.value == v
  c.reset()
  assert c.value != v

def test_as_dict():
  c = Constant("testman.util.utcnow | isoformat | len")
  assert c.as_dict() == {
    "expression" : "testman.util.utcnow | isoformat | len",
    "value"      : 26
  }

def test_from_dict():
  c = Constant.from_dict({
    "expression" : "testman.util.utcnow | isoformat | len",
    "value"      : 26
  })
  assert c.value == 26

