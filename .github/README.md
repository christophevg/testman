# TestMan

> A manager for testing at a human level

[![Latest Version on PyPI](https://img.shields.io/pypi/v/testman.svg)](https://pypi.python.org/pypi/testman/)
[![Supported Implementations](https://img.shields.io/pypi/pyversions/testman.svg)](https://pypi.python.org/pypi/testman/)
[![Build Status](https://secure.travis-ci.org/christophevg/testman.svg?branch=master)](http://travis-ci.org/christophevg/testman)
[![Documentation Status](https://readthedocs.org/projects/testman/badge/?version=latest)](https://testman.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/christophevg/testman/badge.svg?branch=master)](https://coveralls.io/github/christophevg/testman?branch=master)
[![Built with PyPi Template](https://img.shields.io/badge/PyPi_Template-v0.2.0-blue.svg)](https://github.com/christophevg/pypi-template)

## Rationale

Although automated testing inherently requires code, and Python has a very readable syntax, it is still not the best abstraction layer for "humans" who focus on testing and not on code.

Still testers still want to describe tests in a way that they can easily be automated - if possible without having to rely on developers to (en)code them. 

TestMan tries to offer a simple framework that brings together both worlds, by offering a simple test definition interface combined with a simple way for developers to provide additional, reusable testing functions.

## A Word of Caution

> TestMan uses `eval` to perform the tests and assertions **you** specify.  
> This means that it can run arbitrary code.  
> Don't just feed any TestMan script to it. 

## A Quick Example

Imagine you want to check that an email gets send and delivered succesfully.

The following TestMan script defines this test and can be written by a non-development-minded testing human:

```yaml
uid: gmail
test: Sending an email and checking that it was delivered

constants:
  UUID: uuid.uuid4

variables:
  TIMESTAMP: testman.util.utcnow

steps:
  - step: Sending an email
    perform: testman.testers.mail.send
    with:
      server: smtp.gmail.com:587
      username: $GMAIL_USERNAME
      password: $GMAIL_PASSWORD
      recipient: $GMAIL_USERNAME
      subject: A message from TestMan ($UUID)
      body: ~gmail_body.txt
  - step: Checking that the email has been delivered
    perform: testman.testers.mail.pop
    with:
      server: pop.gmail.com
      username: $GMAIL_USERNAME
      password: $GMAIL_PASSWORD
    assert: any mail.Subject == "A message from TestMan ($UUID)" for mail in result
```

So this test consists of two `steps`:

Step 1: Sending an email (with a unique marker)
Step 2: Checking that the email has been delivered (checking the marker)

For each step, an action to `perform` is executed optionally `with` arguments. Finally, one or more `assertions` can be expressed to validate the method's result.

A developer _would_ only have to provide a module consisting of the following two functions, one for sending and one for fetching mail:

```python
import smtplib
import poplib
import email
import email.policy

def send(server=None, username=None, password=None, recipient=None, subject=None, body=None):
  msg = "\r\n".join([
    f"From: {recipient}",
    f"To: {recipient}",
    f"Subject: {subject}",
    "",
    body
  ])
  server = smtplib.SMTP(server)
  server.ehlo()
  server.starttls()
  server.login(username, password)
  server.sendmail(username, [recipient], msg)
  server.close()

def pop(server=None, username=None, password=None):
  conn = poplib.POP3_SSL(server)
  conn.user(username)
  conn.pass_(password)
  messages = [ conn.retr(i) for i in range(1, len(conn.list()[1]) + 1) ]
  conn.quit()
  result = []
  for msg in messages:
    m = email.message_from_bytes(b"\n".join(msg[1]), policy=email.policy.default)
    r = dict(m.items())
    r["Body"] = m.get_content()
    result.append(r)
  return result
```

Notice that these functions merely implement the execution of the test action. The assertions are handled by TestMan. This way it is simple to extend TestMan with custom methods to gather information and have TestMan perform assertions over it.

> I stressed _would_, since these basic tester functions are part of TestMan's included set of testers - which was also visible from the `performed` function name ;-)

To execute this test TestMan offers both a Python and CLI way. Say that the TestMan script is saved as `examples/gmail.yaml` and we have a set two environment variables (GMAIL_USERNAME and GMAIL_PASSWORD), e.g. in a `.env` file, we now can execute the script from the Python REPL...

```pycon
>>> import yaml, json
>>> from dotenv import load_dotenv, find_dotenv
>>> load_dotenv(find_dotenv(usecwd=True))
True
>>> from testman import Test
>>> with open("examples/gmail.yaml") as fp:
...   script = yaml.safe_load(fp)
... 
>>> mytest = Test.from_dict(script, work_dir="examples/")
>>> mytest.execute()
>>> print(json.dumps(mytest.results, indent=2))
[
  {
    "step": "Sending an email",
    "output": null,
    "result": "success",
    "info": null,
    "skipped": false
  },
  {
    "step": "Checking that the email has been delivered",
    "output": [
      {
        "Return-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (d54c2bdfb.access.telenet.be. [84.194.189.251])",
        "Message-ID": "<fd4dc.9827@mx.google.com>",
        "Date": "Sun, 18 Sep 2022 11:31:17 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan (1da6f05f-d819-44be-a07b-4d2cbe6acd04)",
        "Body": "Hello,\n\nThis is an automated message from TestMan.\nTime of sending: 2022-09-18T18:31:16.128970\n\nregards,\nTestMan"
      }
    ],
    "result": "success",
    "info": null,
    "skipped": false
  }
]
```

... and from the command line ...

```console
% python -m testman load examples/gmail.yaml execute results_as_json
[2022-09-18 20:32:04 +0200] ⏳ running test 'gmail'
[2022-09-18 20:32:04 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-18 20:32:06 +0200] ✅ Sending an email
[2022-09-18 20:32:08 +0200] ✅ Checking that the email has been delivered
[2022-09-18 20:32:08 +0200] ◀ in /Users/xtof/Workspace/testman
[
  {
    "step": "Sending an email",
    "output": null,
    "result": "success",
    "info": null,
    "skipped": false
  },
  {
    "step": "Checking that the email has been delivered",
    "output": [
      {
        "Return-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (d54c2bdfb.access.telenet.be. [84.194.189.251])",
        "Message-ID": "<fd4dc.9827@mx.google.com>",
        "Date": "Sun, 18 Sep 2022 11:31:17 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan (1da6f05f-d819-44be-a07b-4d2cbe6acd04)",
        "Body": "Hello,\n\nThis is an automated message from TestMan.\nTime of sending: 2022-09-18T18:31:16.128970\n\nregards,\nTestMan"
      }
    ],
    "result": "success",
    "info": null,
    "skipped": false
  }
]
```

The examples folder contains another TestMan script, that uses some mocked up test functions to illustrate some of the possibilities:

```console
% python -m testman load examples/mock.yaml execute
[2022-09-18 20:35:09 +0200] ⏳ running test 'mock'
[2022-09-18 20:35:09 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-18 20:35:09 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-18 20:35:09 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-18 20:35:09 +0200] ✅ Test that a random value is bigger than 0.7
[2022-09-18 20:35:09 +0200] 🚨 Test that two keys of a random dict match criteria - 'result.result2 > 0.5 or result.result2 < 0.1' failed for result={'result1': 0.02073252292540928, 'result2': 0.22656189460680887, 'result3': 0.46902653623128454}
[2022-09-18 20:35:09 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-18 20:35:09 +0200] ✅ Test that all of the dicts in a list have result1 < 0.5
[2022-09-18 20:35:09 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-18 20:35:09 +0200] ✅ Test that object properties and methods can be asserted
[2022-09-18 20:35:09 +0200] ◀ in /Users/xtof/Workspace/testman
```

And if you install Testman from PyPi, it will also install the `testman` command line script.

```console
% pip install testman
% testman version
0.0.2
% testman load ../testman/examples/mock.yaml execute
[2022-09-18 20:36:21 +0200] ⏳ running test 'mock'
[2022-09-18 20:36:21 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-18 20:36:21 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-18 20:36:21 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-18 20:36:21 +0200] 🚨 Test that a random value is bigger than 0.7 - 'result > 0.7' failed for result=0.4020109040150247
[2022-09-18 20:36:21 +0200] ✅ Test that two keys of a random dict match criteria
[2022-09-18 20:36:21 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-18 20:36:21 +0200] 🚨 Test that all of the dicts in a list have result1 < 0.5 - 'all item.result1 < 0.5 for item in result' failed for result=[{'result1': 0.24236524998489084, 'result2': 0.8798206841418267, 'result3': 0.2151746637364007}, {'result1': 0.6300145921822637, 'result2': 0.3710688620345316, 'result3': 0.8003818254117001}, {'result1': 0.524604320014001, 'result2': 0.28222806362024966, 'result3': 0.3942522752529033}]
[2022-09-18 20:36:21 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-18 20:36:21 +0200] ✅ Test that object properties and methods can be asserted
[2022-09-18 20:36:21 +0200] ◀ in /Users/xtof/Workspace/testman_test
```

## Getting Started

To implement your own test functions, simply write a function and use its FQN as `perform` parameter:

```pycon
>>> import yaml, json
>>> from testman import Test
>>> 
>>> def hello(name):
...   return f"hello {name}"
... 
>>> steps = yaml.safe_load("""
... - step: say hello
...   perform: __main__.hello
...   with:
...     name: Christophe
...   assert: result == "hello Christophe"
... """)
>>> 
>>> mytest = Test.from_dict({"test" : "hello testman", "steps" : steps})
>>> mytest.execute()
>>> print(json.dumps(mytest.results, indent=2))
[
  {
    "step": "say hello",
    "output": "hello Christophe",
    "result": "success",
    "info": null,
    "skipped": false
  }
]
```

## The TestMan Steps DSL

TestMan uses a nested dictionary structure as its domain specific language to encode the steps to take during the test. I personally prefer to write them in `yaml`, yet this is purely optional and a personal choice. As loong as you pass a dictionary to TestMan, it will happily process it.

The dictionary looks like this:

```
steps = [
  {
    "step" : "a description of the step used to refer to it",
    "perform" : "the fully qualified name of a function, or a short hand into the TestMan Standard Testers",
    "with" : {
      "key" : "value pairs of arguments passed to the function as named arguments",
    },
    "assert" : "optionally, a single string or list of strings to be evaluated to assert the result (see below for the full description of the assertion DSL)",
    "continue" : "yes, optionally, allows to indicate that in case of an assertion failure, the steps should be continued, whereas the default is to stop processing the steps on first failure",
    "always": "yes, optionally, allows to ensure that a step is always performed, even if it previously was successful, whereas the default is to not perform a step if it previously was successful"
  }
]
``` 
