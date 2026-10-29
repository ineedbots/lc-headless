"""Scoped module replacements and an update clock for stdlib workflow tests."""

from test_dialogue_workflows import DialogueWorld


class PatchWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.patches = []

    def patch(self, module, name, value):
        self.patches.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def __exit__(self, *args):
        for module, name, value in reversed(self.patches):
            setattr(module, name, value)
        DialogueWorld.__exit__(self, *args)

    def tick(self):
        return self.now // 500
