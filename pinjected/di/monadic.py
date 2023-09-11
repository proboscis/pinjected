from returns.result import safe


def getitem_opt(o, k):
    return safe(o.__getitem__)(k)
