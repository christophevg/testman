from fire import Fire

from testman.cli import TestManCLI

def cli():
  try:
    Fire(TestManCLI, name="testman")
  except KeyboardInterrupt:
    pass

if __name__ == "__main__":
  cli()
