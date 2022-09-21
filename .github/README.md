<h1><img src="../media/logo.png" align="right" width="100">TestMan</h1>

> A manager for automated testing by humans

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
name: Sending an email and checking that it was delivered

constants:
  UUID: uuid.uuid4

variables:
  TIMESTAMP: testman.util.utcnow

steps:
  - name: Sending an email
    perform: testman.testers.mail.send
    with:
      server: smtp.gmail.com:587
      username: $GMAIL_USERNAME
      password: $GMAIL_PASSWORD
      recipient: $GMAIL_USERNAME
      subject: A message from TestMan ($UUID)
      body: ~gmail_body.txt
  - name: Checking that the email has been delivered
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
    r = {}
    for k, v in dict(m.items()).items():
      r[k] = str(v)
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
{
  "Sending an email": {
    "start": "2022-09-21T07:07:44.982532",
    "end": "2022-09-21T07:07:46.204026",
    "output": null,
    "info": null,
    "status": "success",
    "skipped": false
  },
  "Checking that the email has been delivered": {
    "start": "2022-09-21T07:07:46.204132",
    "end": "2022-09-21T07:07:48.345193",
    "output": [
      {
        "Return-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (d54.access.telenet.be. [4.19.19.25])",
        "Message-ID": "<fd4dc.9827@mx.google.com>",
        "Date": "Sun, 18 Sep 2022 11:31:17 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan (1da6f05f-d819-44be-a07b-4d2cbe6acd04)",
        "Body": "Hello,\n\nThis is an automated message from TestMan.\nTime of sending: 2022-09-18T18:31:16.128970\n\nregards,\nTestMan"
      }
    ],
    "info": null,
    "status": "success",
    "skipped": false
  }
}
```

... and from the command line ...

```console
% python -m testman load examples/gmail.yaml execute results_as_json
% python -m testman load examples/gmail.yaml execute results_as_json
[2022-09-21 09:11:19 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-21 09:11:20 +0200] ✅ Sending an email
[2022-09-21 09:11:22 +0200] ✅ Checking that the email has been delivered
[2022-09-21 09:11:22 +0200] ◀ in /Users/xtof/Workspace/testman
{
  "Sending an email": {
    "start": "2022-09-21T07:07:44.982532",
    "end": "2022-09-21T07:07:46.204026",
    "output": null,
    "info": null,
    "status": "success",
    "skipped": false
  },
  "Checking that the email has been delivered": {
    "start": "2022-09-21T07:07:46.204132",
    "end": "2022-09-21T07:07:48.345193",
    "output": [
      {
        "Return-Path": "<someone@email.com>",
        "Received": "from ip6.arpa (d54.access.telenet.be. [4.19.19.25])",
        "Message-ID": "<fd4dc.9827@mx.google.com>",
        "Date": "Sun, 18 Sep 2022 11:31:17 -0700",
        "From": "someone@email.com",
        "To": "someone@email.com",
        "Subject": "A message from TestMan (1da6f05f-d819-44be-a07b-4d2cbe6acd04)",
        "Body": "Hello,\n\nThis is an automated message from TestMan.\nTime of sending: 2022-09-18T18:31:16.128970\n\nregards,\nTestMan"
      }
    ],
    "info": null,
    "status": "success",
    "skipped": false
  }
}
```

The examples folder contains another TestMan script, that uses some mocked up test functions to illustrate some of the possibilities:

```console
% python -m testman load examples/mock.yaml execute
[2022-09-21 09:11:55 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-21 09:11:55 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-21 09:11:55 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-21 09:11:55 +0200] 🚨 Test that a random value is bigger than 0.7 - 'result > 0.7' failed for result=0.16237524253063063
[2022-09-21 09:11:55 +0200] 🚨 Test that two keys of a random dict match criteria - 'result.result1 < 0.5' failed for result={'result1': 0.5824170196145589, 'result2': 0.6443538640468358, 'result3': 0.5201206405472322}
[2022-09-21 09:11:55 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-21 09:11:55 +0200] 🚨 Test that all of the dicts in a list have result1 < 0.5 - 'all item.result1 < 0.5 for item in result' failed for result=[{'result1': 0.5336479045489211, 'result2': 0.30981993872330327, 'result3': 0.27661254405288216}, {'result1': 0.23920511249278598, 'result2': 0.7080886447360248, 'result3': 0.1361173238448583}, {'result1': 0.719807760896399, 'result2': 0.21743598455790847, 'result3': 0.6627068916970688}]
[2022-09-21 09:11:55 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-21 09:11:55 +0200] ✅ Test that object properties and methods can be asserted
[2022-09-21 09:11:55 +0200] ◀ in /Users/xtof/Workspace/testman
```

And if you install Testman from PyPi, it will also install the `testman` command line script.

```console
% pip install testman
% testman version
0.0.3
% testman load ../testman/examples/mock.yaml execute
[2022-09-21 09:12:37 +0200] ▶ in /Users/xtof/Workspace/testman/examples
[2022-09-21 09:12:37 +0200] ✅ Test that an envrionment variable as argument is returned
[2022-09-21 09:12:37 +0200] 🚨 Test that an incorrect argument fails - 'result.hello == "world"' failed for result={'hello': 'WORLD'}
[2022-09-21 09:12:37 +0200] 🚨 Test that a random value is bigger than 0.7 - 'result > 0.7' failed for result=0.111074170853391
[2022-09-21 09:12:37 +0200] 🚨 Test that two keys of a random dict match criteria - 'result.result2 > 0.5 or result.result2 < 0.1' failed for result={'result1': 0.1970010221173848, 'result2': 0.20193458254324714, 'result3': 0.25430481982617814}
[2022-09-21 09:12:37 +0200] ✅ Test that any values in a random list is < 0.5
[2022-09-21 09:12:37 +0200] 🚨 Test that all of the dicts in a list have result1 < 0.5 - 'all item.result1 < 0.5 for item in result' failed for result=[{'result1': 0.36567629773296983, 'result2': 0.7890211368675198, 'result3': 0.28117765912895376}, {'result1': 0.6011158365310331, 'result2': 0.9422161128407222, 'result3': 0.9990457704008657}, {'result1': 0.1991118692356576, 'result2': 0.8839600916890447, 'result3': 0.7788144324166787}]
[2022-09-21 09:12:37 +0200] ✅ Test that values inside a nested dict can be asserted
[2022-09-21 09:12:37 +0200] ✅ Test that object properties and methods can be asserted
[2022-09-21 09:12:37 +0200] ◀ in /Users/xtof/Workspace/testman_test
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
... - name: say hello
...   perform: __main__.hello
...   with:
...     name: Christophe
...   assert: result == "hello Christophe"
... """)
>>> 
>>> mytest = Test.from_dict({"test" : "hello testman", "steps" : steps})
>>> mytest.execute()
>>> print(json.dumps(mytest.results, indent=2))
{
  "say hello": {
    "start": "2022-09-21T07:14:56.240191",
    "end": "2022-09-21T07:14:56.242444",
    "output": "hello Christophe",
    "info": null,
    "status": "success",
    "skipped": false
  }
}
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

## A Typical Workflow

I've designed TestMan with a specific workflow in mind: managing a set of tests that all take some time to complete and therefore need to be run multiple times, until all tests are done.

So a typical workflow would struturally look like:

1. load tests into a test suite
2. execute
3. execute
4. ...
5. until all tests in the suite have completed

In the mean time, the persisted test information can be used to visualize the status.

The following example, using the examples in the repository, illustrates this:

```console
% testman state mongodb://localhost:27017/testman/suites load ../testman/examples/mock.yaml load ../testman/examples/gmail.yaml

% testman state mongodb://localhost:27017/testman/suites suite summary        
mock:  {"unknown": 8, "success": 0, "ignored": 0, "pending": 0, "failed": 0, "summary": "8 in progress"}
gmail: {"unknown": 2, "success": 0, "ignored": 0, "pending": 0, "failed": 0, "summary": "2 in progress"}

% testman state mongodb://localhost:27017/testman/suites suite execute summary
mock:  {"unknown": 0, "success": 5, "ignored": 1, "pending": 2, "failed": 0, "summary": "2 in progress"}
gmail: {"unknown": 0, "success": 2, "ignored": 0, "pending": 0, "failed": 0, "summary": "all done"}
% testman state mongodb://localhost:27017/testman/suites suite execute summary
mock:  {"unknown": 0, "success": 5, "ignored": 1, "pending": 2, "failed": 0, "summary": "2 in progress"}
gmail: {"unknown": 0, "success": 2, "ignored": 0, "pending": 0, "failed": 0, "summary": "all done"}
% testman state mongodb://localhost:27017/testman/suites suite execute summary
mock:  {"unknown": 0, "success": 6, "ignored": 1, "pending": 1, "failed": 0, "summary": "1 in progress"}
gmail: {"unknown": 0, "success": 2, "ignored": 0, "pending": 0, "failed": 0, "summary": "all done"}
% testman state mongodb://localhost:27017/testman/suites suite execute summary
mock:  {"unknown": 0, "success": 6, "ignored": 1, "pending": 1, "failed": 0, "summary": "1 in progress"}
gmail: {"unknown": 0, "success": 2, "ignored": 0, "pending": 0, "failed": 0, "summary": "all done"}
% testman state mongodb://localhost:27017/testman/suites suite execute summary
mock:  {"unknown": 0, "success": 7, "ignored": 1, "pending": 0, "failed": 0, "summary": "all done"}
gmail: {"unknown": 0, "success": 2, "ignored": 0, "pending": 0, "failed": 0, "summary": "all done"}
```

After loading two tests into the MongoDB `suites` collection, the initial status shows that 8+2=10 steps in two tests (mock and gmail) need to performed.

After every execution, more steps have been performed succesfully or have been ignored, until alle steps have been completed as requested. 

The execution can be triggered from a function/cron job/... that is called every minute, or every hour, thus enabling long-during test suite executions.
