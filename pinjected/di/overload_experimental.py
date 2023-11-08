"""
Here, we aim to implement a dependency injection feature for a dataclass, using
pyhton 3.11's dataclass_transform decorator.

The goal is to allow this kind of code:

@injected
class Data:
    dep1: X = iattr
    dep2: Y = iattr
    x: int = field(default=0)
    ...

@injected
def data_user(new_data: class[Data])->Data:
    data = new_data(x=10)
    data.dep1.do_something()
    data.dep2.do_something()
    ...

"""
from dataclasses import dataclass

from pinjected import injected


@dataclass
class Data:
    """
    docs for data
    """
    x: int = 0


class DataFactory:
    def __call__(self, x: int) -> Data:
        """
        This is a hello world example docstring
        :param x: tell me something special
        :return: Data
        """
        return Data(x)


# new_data:type[Data] = Data
@injected
def data_user(new_data: DataFactory,/,msg) -> Data:
    d = new_data(x=0)
    pass


class IDataUser:
    def __call__(self,msg:str):
        """
        This is a hello world example docstring
        :param msg:
        :return:
        """
        pass
