from pinjected.di.expr_util import Object


def test_object():
    import pickle
    print(Object("hello world"))
    print(pickle.dumps(Object("fhm")))