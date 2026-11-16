"""Run a game or the menu: python -m core.games [menu|mazee_run|bmo_catch|angry_poppa]"""
import importlib
import json
import sys

from . import GAMES, common


def load(name):
    return importlib.import_module("core.games." + name).make()


def main(argv):
    name = argv[1] if len(argv) > 1 else "menu"
    if name == "menu":
        from . import launcher
        res = launcher.run_menu()
    elif name in GAMES:
        res = common.run(load(name))
    else:
        print("Unknown game: %s. Choices: menu, %s" % (name, ", ".join(GAMES)), file=sys.stderr)
        return 2
    print("RESULT " + json.dumps(res), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
