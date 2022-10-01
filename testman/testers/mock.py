import logging
logger = logging.getLogger(__name__)

import json
import random as rnd

def test(**kwargs):
  logger.debug(json.dumps(kwargs, default=str))
  if "fail" in kwargs:
    raise Exception(kwargs["fail"])
  return kwargs

def random():
  return rnd.random()

def random_dict():
  return {
    "result1" : random(),
    "result2" : random(),
    "result3" : random()
  }

def random_list():
  return [
    random(),
    random(),
    random()
  ]

def random_list_of_dict():
  return [
    random_dict(),
    random_dict(),
    random_dict()
  ]

def nested_dict():
  return {
    "result1" : 1,
    "subresults" : [
      {
        "subresult" : 1
      },
      {
        "subresult" : 2
      }
    ]
  }

class AClass():
  def __init__(self):
    self.a = 1
    self.b = 1
  def get_body(self):
    return "hello"

def an_object():
  return AClass()
