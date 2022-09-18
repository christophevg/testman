from testman.util import expand

import os

def test_expand_basic_env_vars():
  os.environ["TV1"] = "tv1"
  os.environ["TV2"] = "tv2"
  os.environ["TV3"] = "tv3"
  
  assert expand("$TV1 and$TV2 and $TV3") == "tv1 andtv2 and tv3"
  assert expand("$TV1") == "tv1"

def test_expand_var_in_file(tmp_path):
  os.environ["BODY"] = "body"
  f = tmp_path / "content.txt"
  f.write_text("Testing...\n>> some $BODY <<\nDone...")
  assert expand(f"~{f.resolve()}") == "Testing...\n>> some body <<\nDone..."
