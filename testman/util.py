import os
import importlib
import re
import datetime

def get_function(func):
  mod_name, func_name = func.rsplit(".", 1)
  mod = importlib.import_module(mod_name)
  return getattr(mod, func_name)

def expand(v, vars=None):
  if not vars:
    vars = {}
  # load from file
  if v[0] == "~":
    with open(v[1:]) as fp:
      v = fp.read()

  # expand env vars
  r = re.compile(r"([$?])(\w+)\b")
  for _, var in r.findall(v):
    value = vars.get(var, os.environ.get(var))
    if value:
      if v == f"$var":
        v = value
      else:
        v = v.replace(f"${var}", str(value))
    else:
      raise ValueError(f"unknown variable '{var}'")

  # try it as a function
  try:
    v = get_function(v)()
  except:
    pass

  return v

def utcnow():
  return datetime.datetime.utcnow().isoformat()
