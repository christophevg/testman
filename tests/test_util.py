from testman.util import expand

import os

def test_expand_basic_env_vars():
  os.environ["TV1"] = "tv1"
  os.environ["TV2"] = "tv2"
  os.environ["TV3"] = "tv3"
  
  assert expand("{TV1} and{TV2} and {TV3}") == "tv1 andtv2 and tv3"
  assert expand("{TV1}") == "tv1"
  assert expand("TV1")   == "tv1"

def test_expand_var_in_file(tmp_path):
  f = tmp_path / "content.txt"
  f.write_text("Testing...\n>> some {BODY} <<\nDone...")
  assert expand(f"~{f.resolve()}", {"BODY" : "body"}) == \
        "Testing...\n>> some body <<\nDone..."

def test_expand_dict():
  value = {
    "hello" : "test-{WORLD}"
  }
  assert expand(value, { "WORLD" : "world" }) == { "hello" : "test-world" }

def test_expand_nested_dicts():
  value = {
    "hello" : "test-{WORLD}",
    "world" : {
      "nested" : "also-test-{WORLD}"
    }
  }
  assert expand(value, { "WORLD" : "world" }) == \
         { "hello" : "test-world", "world" : { "nested" : "also-test-world" } }

def test_expand_list():
  value = [ "hello" , "test-{WORLD}" ]
  assert expand(value, { "WORLD" : "world" }) == [ "hello", "test-world" ]

def test_expand_nested_lists():
  value = [ "hello" , "test-{WORLD}", [ "nested", "also-test-{WORLD}" ] ]
  assert expand(value, { "WORLD" : "world" }) == \
         [ "hello" , "test-world", [ "nested", "also-test-world" ] ]

def test_expand_mixed_nested_data_structures():
  value = {
    "lists" : [ "hello" , "test-{WORLD}", [ "nested", "also-test-{WORLD}" ] ],
    "dicts" : {
      "nested" : "also-test-{WORLD}"
    }
  }
  assert expand(value, { "WORLD" : "world" }) == \
   {
     "lists" : [ "hello" , "test-world", [ "nested", "also-test-world" ]],
     "dicts" : {
       "nested" : "also-test-world"
     }
   }

def test_expand_expanded_function():
  value = "uuid.{FUNC}"
  assert len(str(expand(value, { "FUNC" : "uuid4" }))) == 36

def test_expand_dict_access():
  value = "{DICT['hello']}"
  assert expand(value, {"DICT" : { "hello" : "world" } }) == "world"
  value = "DICT['hello']"
  assert expand(value, {"DICT" : { "hello" : "world" } }) == "world"
  value = "DICT.hello"
  assert expand(value, {"DICT" : { "hello" : "world" } }) == "world"
