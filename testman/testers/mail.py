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
