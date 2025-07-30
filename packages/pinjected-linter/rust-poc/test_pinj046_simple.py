"""Simple test for PINJ046"""


class BadClass:
    def __init__(self):
        self.value = 0

    def update(self):
        self.value = 1  # Should trigger PINJ046


class GoodClass:
    def __init__(self):
        self.mut_value = 0

    def update(self):
        self.mut_value = 1  # OK
