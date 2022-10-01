"""
  Command tests

  Commands are string representations of functions and optional filters to apply
  on the result of the execution of the function.

  syntax: module.functionname | filter1 | filter2

  Filters can be
  - a key into a dict result                       : mod.get_a_dict | somekey
  - a method on an object result                   : mod.get_obj    | somemethod
  - a property on an object result                 : mod.get_obj    | prop
  - a function to call with the result as argument : mod.get_obj    | str

  Commands are used for the `perform` and when evaluating/exapnding values.
"""

from testman.util import parse_command, format_command, postprocess

# Parse

def test_parse_single_function_command():
  func, filters = parse_command("testman.util.utcnow")
  assert callable(func)
  assert len(filters) == 0

def test_parse_command_with_single_filter():
  func, filters = parse_command("testman.util.utcnow | isoformat")
  assert callable(func)
  assert len(filters) == 1
  assert filters[0] == "isoformat"

def test_parse_command_with_multiple_filter():
  func, filters = parse_command("testman.util.utcnow | isoformat | len")
  assert callable(func)
  assert len(filters) == 2
  assert filters[0] == "isoformat"
  assert filters[1] == "len"

# Format

def test_format_single_function_command():
  from testman.util import utcnow
  func = utcnow
  assert format_command(func) == "testman.util.utcnow"

def test_format_single_function_with_single_filter_command():
  from testman.util import utcnow
  func    = utcnow
  filters = ["isoformat"]
  assert format_command(func, filters ) == "testman.util.utcnow|isoformat"

# PostProcess

def test_processing_of_command_with_single_filter():
  func, filters = parse_command("testman.util.utcnow | isoformat")
  result = postprocess(func(), filters)
  assert isinstance(result, str)

def test_parse_command_with_multiple_filter():
  func, filters = parse_command("testman.util.utcnow | isoformat | len")
  result = postprocess(func(), filters)
  assert isinstance(result, int)
