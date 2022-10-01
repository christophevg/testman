import os
import importlib
import re
import datetime

import yaml
import json

def get_function(func):
  mod_name, func_name = func.rsplit(".", 1)
  mod = importlib.import_module(mod_name)
  return getattr(mod, func_name)

def expand(value, vars=None):
  # dict?
  if isinstance(value, dict):
    return { k : expand(v, vars) for k, v in value.items() }

  # load from file (prefix ~)
  if value[0] == "~":
    with open(value[1:]) as fp:
      value = fp.read()

  # expand env vars
  if not vars: vars = {}
  r = re.compile(r"([$?])(\w+)\b")
  for _, var in r.findall(value):
    replacement = vars.get(var, os.environ.get(var))
    if replacement:
      if value == f"$var":
        value = replacement
      else:
        value = value.replace(f"${var}", str(replacement))
    else:
      raise ValueError(f"unknown variable '{var}'")

  # try it as a function
  try:
    value = get_function(value)()
    if value and not type(value) in [ int, float, bool, str, list, dict ]:
      value = str(value)
  except:
    pass

  return value

def utcnow():
  return datetime.datetime.utcnow().isoformat()

def prune(d):
  return { k:v for k,v in d.items() if v or v == False }

def load_ml(filename):
  _, ext = filename.rsplit(".", 1)
  loader = {
    "yaml" : yaml.safe_load,
    "yml"  : yaml.safe_load,
    "json" : json.load
  }[ext]
  with open(filename) as fp:
    return loader(fp)
