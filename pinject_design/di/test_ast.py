from pinject_design.di.ast import Object


def test_object():
    import pickle
    print(Object("hello world"))
    print(pickle.dumps(Object("fhm")))