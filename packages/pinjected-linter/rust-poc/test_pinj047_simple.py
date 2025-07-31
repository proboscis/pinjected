"""Simple test for PINJ047"""


class TooManyMutable:
    def __init__(self):
        self.mut_a = 0
        self.mut_b = 0

    def update(self):
        self.mut_a = 1
        self.mut_b = 2
        self.mut_c = 3  # This makes 3 mutable attributes, exceeds limit of 1


class OneMutable:
    def __init__(self):
        self.mut_count = 0

    def increment(self):
        self.mut_count += 1  # OK, only one mutable attribute
