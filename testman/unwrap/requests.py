def json(response):
  return {
    "status_code" : response.status_code,
    "json"        : response.json()
  }
