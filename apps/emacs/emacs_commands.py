from talon import Module, Context, actions, app, resource
from pathlib import Path
from typing import Optional, NamedTuple
from dataclasses import dataclass
import csv

mod = Module()
mod.list("emacs_command", desc="Emacs commands")

ctx = Context()
emacs_ctx = Context()
emacs_ctx.matches = r'''
app: Emacs
app: emacs
'''

class Command(NamedTuple):
    name: str
    keys: Optional[str] = None
    short: Optional[str] = None
    spoken: Optional[str] = None

@dataclass
class CommandInfo:
    by_name: dict                       # maps name to Commands.
    by_spoken: dict                     # maps spoken forms to Commands.
    def __init__(self):
        self.by_name = {}
        self.by_spoken = {}

emacs_commands = CommandInfo()

def load_csv():
    global emacs_commands
    filepath = Path(__file__).parents[0] / "emacs_commands.csv"
    with resource.open(filepath) as f:
        rows = list(csv.reader(f))
    # Check headers
    assert rows[0] == ["Command", " Key binding", " Short form", " Spoken form"]

    commands = []
    for row in rows[1:]:
        if 0 == len(row): continue
        if len(row) > 4:
            print(f'"{filepath}": More than four values in row: {row}. '
                  + ' Ignoring the extras')
        name, keys, short, spoken = \
            ([x.strip() or None for x in row] + [None, None, None])[:4]
        commands.append(Command(name=name, keys=keys, short=short, spoken=spoken))

    info = CommandInfo()
    info.by_name = {c.name: c for c in commands}

    # Generate spoken forms and apply overrides.
    try:
        command_list = actions.user.create_spoken_forms_from_list(
            [c.name for c in commands],
            generate_subsequences=False)
    except: pass
    else:
        for c in commands:
            if c.spoken:
                command_list[c.spoken] = c.name
        info.by_spoken = command_list

    global emacs_commands
    emacs_commands = info
    ctx.lists["self.emacs_command"] = info.by_spoken

# TODO: register on change to file!
app.register("ready", load_csv)

@mod.action_class
class Actions:
    def emacs_command(name: str):
        """
        Runs the emacs command `name`. Defaults to using M-x, but may use a
        key binding if known or rpc if available.
        """

@emacs_ctx.action_class('user')
class UserActions:
    def emacs_command(name):
        command = emacs_commands.by_name.get(name, Command(name))
        if command.keys is not None:
            actions.key(command.keys)
        else:
            actions.key("alt-x")
            actions.insert(command.short or command.name)
            actions.key("enter")
