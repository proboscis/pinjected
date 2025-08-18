from returns.result import safe


def getitem_opt(o, k):
    if o is None or not hasattr(o, "__getitem__"):
        from returns.result import Failure

        return Failure(
            AttributeError(
                f"'{type(o).__name__}' object has no attribute '__getitem__'"
            )
        )
    return safe(o.__getitem__)(k)
