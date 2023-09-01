from expression import Nothing
from returns import maybe as raybe
from returns.maybe import Some, Maybe


def patch_maybe():
    def maybe__or__(self, other):
        match self:
            case Some(x):
                return self
            case raybe.Nothing:
                return other

    def maybe_filter(self: Maybe, flag_to_keep):
        match self.map(flag_to_keep):
            case Some(True):
                return self
            case _:
                return Nothing

    Maybe.__or__ = maybe__or__
    Maybe.filter = maybe_filter
