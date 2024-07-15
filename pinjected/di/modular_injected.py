from dataclasses import dataclass
from typing import List, Callable, Optional, Union

from pinjected import Injected
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.ast import Expr
from pinjected.di.injected import MappedInjected
from pinjected.di.proxiable import DelegatedVar, T
from pinjected.module_var_path import ModuleVarPath


@dataclass
class ModularInjected:
    """
    The purpose of this class is to accumulate modular injected,
    so that we can generate a source code from sources.
    """
    tgt: Injected
    imports: List[ModuleVarPath]
    ast: "an ast of an expression that returns Injected"

    def map(self, f: "ModularInjected"):
        """
        combine two ast to form new ast.
        what do I do?
        :param f:
        :return:
        """

        pass

def statements_to_expr(stmt:List["Stmt"]):
    """
    use __result__ as the final value

    :param stmt:
    :return:
    """
    pass


# so, let's start from implementing modular injected's contract
# let's then build a constructors which are easy to use
# then try to build a source code
#


def extract_modular_injected(target: ModuleVarPath) -> ModularInjected:
    """
    given modulepath of an InjectedFunction, get the file it is defined, and parse it to gather imports.
    :param target:
    :return:
    """
    pass


CustomConverter = Callable[[Injected], Optional[ModularInjected]]


def injected_to_modular_injected(src: Injected,
                                 custom_converter: CustomConverter = lambda x: None
                                 ) -> ModularInjected:
    res = custom_converter(src)
    if res is None:
        # TODO resolve
        pass
    return res


# TODO implement extraction of import dependencies
# -- 1. from inject_function annotated things
# -- 2. resolve cases...which utilizes map/zip
# we have so much variants of Injected.
# If we add __imports__ to Injected, every class gets affected.
# writing a parser for each Injected class is more robust.
# we can't reliably extract the functions used in map
# this means we can't really extract modules out o designs
# so, we have to use ModularInjected thing everywhere to form a new ModularInjected.
# also, a contract of ModularInjected is to have source for export.
def parse_evaled_injected(ei: EvaledInjected):
    def parse(i: Injected):
        match i:
            case MappedInjected(src, f):
                pass


def parse_injected(src: Union[Injected, DelegatedVar]) -> ModularInjected:
    # to parse, or not to parse, that is the question.
    match src:
        case DelegatedVar() as dv:
            return parse_injected(dv.eval())
        case EvaledInjected() as ei:
            expr: Expr = ei.ast

"""
a problem we have is, that
if a program imports other modules that lives in same package as the program,
we don't have a way to know that...?
we have to look for the variables imported, to get the ast of it.
"""