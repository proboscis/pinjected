from attrs import define,fields
from pinjected import injected_function


@define
class A:
    x:int
    y:int

_A = injected_function(A)
#%%
