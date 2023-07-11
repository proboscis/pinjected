from attrs import define,fields
from pinject_design import injected_function


@define
class A:
    x:int
    y:int

_A = injected_function(A)
#%%
