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

> TestMan uses `eval` to perform the tests **you** specify.  
> This means that it can run arbitrary code.  
> Don't just feed any TestMan script to it. 

## A Quick Example

Imagine you want to check that an email gets send and delivered succesfully.

The following TestMan script defines this test and can be written by a non-development-minded testing human:

```yaml
test: Sending an email and checking that it was delivered

steps:
  - step: Sending an email
    perform: mail.send
    with:
      server: smtp.gmail.com:587
      username: $GMAIL_USERNAME
      password: $GMAIL_PASSWORD
      recipient: $GMAIL_USERNAME
      subject: A message from TestMan
      body: >
        Hello,
      
        This is an automated message from TestMan.
      
        regards,
        TestMan
  - step: Checking that the email has been delivered
    perform: mail.pop
    with:
      server: pop.gmail.com
      username: $GMAIL_USERNAME
      password: $GMAIL_PASSWORD
    assert: any mail.Subject == "A message from TestMan" for mail in result
```

So this test consists of two `steps`:

Step 1: Sending an email
Step 2: Checking that the email has been delivered

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

> I stressed _would_, since these basic tester functions are part of TestMan's included set of testers ;-)

To excute this test TestMan offers both a Python and CLI way. Say that the TestMan script is saved as `examples/gmail.yaml` and we have a set two environment variables (GMAIL_USERNAME and GMAIL_PASSWORD), e.g. in a `.env` file, we now can execute the script from the Python REPL...

```pycon
>>> import yaml
>>> import json
>>> from dotenv import load_dotenv, find_dotenv
>>> load_dotenv(find_dotenv(usecwd=True))
True
>>> from testman import Test
>>> with open("examples/gmail.yaml") as fp:
...   script = yaml.safe_load(fp)
... 
>>> mytest = Test(script["test"], script["steps"])
>>> mytest.execute()
>>> print(json.dumps(mytest.results, indent=2))
[
  {
    "step": "Sending an email",
    "result": "success",
    "output": null
  },
  {
    "step": "Checking that the email has been delivered",
    "result": "success",
    "output": [
      {
        "Returna-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (c5.access.telenet.be. [85.14.89.21])        by smtp.gmail.com with ESMTPSA id kv13-20020a17090777.08.18.22        for <someone@email.com>        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);        Sat, 17 Sep 2022 08:18:22 -0700 (PDT)",
        "Message-ID": "<63222.170a0220.c50cb.ead4@mx.google.com>",
        "Date": "Sat, 17 Sep 2022 08:18:22 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan",
        "Body": "Hello,\nThis is an automated message from TestMan.\nregards, TestMan"
      }
    ]
  }
]

```

... and from the command line ...

```console
% python -m testman script examples/gmail.yaml execute results
[2022-09-17 17:23:25 +0200] ✅ Sending an email
[2022-09-17 17:23:27 +0200] ✅ Checking that the email has been delivered
[
  {
    "step": "Sending an email",
    "result": "success",
    "output": null
  },
  {
    "step": "Checking that the email has been delivered",
    "result": "success",
    "output": [
      {
        "Returna-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (c5.access.telenet.be. [85.14.89.21])        by smtp.gmail.com with ESMTPSA id kv13-20020a17090777.08.18.22        for <someone@email.com>        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);        Sat, 17 Sep 2022 08:18:22 -0700 (PDT)",
        "Message-ID": "<63222.170a0220.c50cb.ead4@mx.google.com>",
        "Date": "Sat, 17 Sep 2022 08:18:22 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan",
        "Body": "Hello,\nThis is an automated message from TestMan.\nregards, TestMan"
      }
    ]
  }
]

```

The examples folder contains another TestMan script, that uses some mocked up test functions to illustrate some of the possibilities:

```console
% python -m testman script examples/mock.yaml execute
[2022-09-17 17:24:04 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-17 17:24:04 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-17 17:24:04 +0200] 🚨 Test that a random value is bigger than 0.7 - 'result > 0.7' failed for result=0.2529799894294721
[2022-09-17 17:24:04 +0200] 🚨 Test that two keys of a random dict match criteria - 'result.result1 < 0.5' failed for result={'result1': 0.8126279122498545, 'result2': 0.2549604718248736, 'result3': 0.49840396114858765}
[2022-09-17 17:24:04 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-17 17:24:04 +0200] ✅ Test that all of the dicts in a list have result1 < 0.5
[2022-09-17 17:24:04 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-17 17:24:04 +0200] ✅ Test that object properties and methods can be asserted
```

And if you install Testman from PyPi, it will also install the `testman` command line script.

```console
% pip install testman
% testman version                                             
0.0.1
% testman script ../testman/examples/mock.yaml execute
[2022-09-17 17:55:42 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-17 17:55:42 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-17 17:55:42 +0200] ✅ Test that a random value is bigger than 0.7
[2022-09-17 17:55:42 +0200] ✅ Test that two keys of a random dict match criteria
[2022-09-17 17:55:42 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-17 17:55:42 +0200] 🚨 Test that all of the dicts in a list have result1 < 0.5 - 'all item.result1 < 0.5 for item in result' failed for result=[{'result1': 0.2990112005709744, 'result2': 0.5681822278622609, 'result3': 0.9809440441429035}, {'result1': 0.8029254861188387, 'result2': 0.5127534322747448, 'result3': 0.44403728680059495}, {'result1': 0.6927492142694232, 'result2': 0.9859886618355753, 'result3': 0.006196716166297134}]
[2022-09-17 17:55:42 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-17 17:55:42 +0200] ✅ Test that object properties and methods can be asserted

```

## Getting Started

To implement your own test functions, simply write a function and use its FQN as `perform` parameter:

```pycon
>>> import yaml
>>> import json
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
>>> mytest = Test("hello world test", steps)
>>> mytest.execute()
>>> print(json.dumps(mytest.results, indent=2))
[
  {
    "step": "say hello",
    "result": "success",
    "output": "hello Christophe"
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
