import ast
import inspect
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Awaitable

import astor

from pinjected import Design, Injected
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.ast import Expr, BiOp, Call, Attr, GetItem, Object
from pinjected.di.injected import InjectedPure, InjectedFunction, PartialInjectedFunction, ZippedInjected, \
    MappedInjected, InjectedByName
from pinjected.di.proxiable import DelegatedVar


@dataclass
class PinjectedCodeExporter:
    src: Design
    a_llm: Callable[[str], Awaitable[str]]

    def __post_init__(self):
        digraph = self.src.to_vis_graph()
        self.mappings = {**digraph.explicit_mappings}

    @staticmethod
    async def to_source__instance(assign_target, tgt: InjectedPure):
        # wait, tgt.value must be recoverable from the value. but it should always be.
        return f"{assign_target} = {tgt.value}"

    async def extract_lambda(self, f):
        from loguru import logger
        logger.info(f"extracting lambda from {f.__name__}")
        src = inspect.getsource(f)
        prompt = f"""
    Please extract the lambda expression in question from function:{f.__name__} below.
    ```
    {src}
    ```
    The answer must be a valid python expression without comments, in the form of 
    lambda ...: ...
    """
        return await self.a_llm(prompt)

    async def get_source_func(self, assign_target, f):
        from loguru import logger
        if hasattr(f, "__original_code__"):
            # logger.info(f"retrieving source from __original_code__")
            src = f.__original_code__
        else:
            src = inspect.getsource(f)
        """
        @injected
        def g(f,/,x):
            return f(x=x,y=1)
        
        I need to remove @injected and positional only arguments. from this source, using AST.
        """
        # logger.info(f"getting source:{f.__name__}->\n{src}")
        if f.__name__.endswith('<lambda>'):
            src = await self.extract_lambda(f)
            return f"{assign_target} = {src}\n"
        else:
            tree = ast.parse(src)
            PinjectedCodeExporter.un_pinjected(assign_target, tree)
            unparsed = ast.unparse(tree)
            logger.debug(f"un_pinjected->\n{unparsed}")
            return unparsed
            # return astor.to_source(tree)

    # Function to remove the @injected decorator and positional-only argument marker
    @staticmethod
    def un_pinjected(assignment, tree):
        deletion_targets = {"injected", "instance"}
        for node in ast.walk(tree):
            # Check if the node is a function definition
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Remove @injected decorator if present
                is_instance = bool([decorator for decorator in node.decorator_list if
                                    hasattr(decorator, 'id') and decorator.id == 'instance'])
                node.decorator_list = [decorator for decorator in node.decorator_list if
                                       not (hasattr(decorator, 'id') and decorator.id in deletion_targets)]
                node.name = assignment

                # Check for positional only arguments (Python 3.8+)
                if node.args.posonlyargs:
                    # Remove the positional-only argument marker
                    node.args.posonlyargs = []

                if is_instance:
                    # Remove all args if it's @instance
                    node.args.args = []

    @staticmethod
    def new_symbol():
        return str(uuid.uuid4())[:3]

    @staticmethod
    def tmp_symbol():
        return "tmp_" + PinjectedCodeExporter.new_symbol()

    def find_matching_mapping(self, data: Injected):
        from loguru import logger
        logger.info(f"finding matching mapping for {data}")
        match data:
            case InjectedFunction(f, kwargs_mapping):
                for k, v in self.mappings.items():
                    match v:
                        case PartialInjectedFunction(InjectedFunction(_f)) if f == _f:
                            return k
        return None

    async def expr_to_source(self, assign_target: str, expr: Expr, visited):
        from loguru import logger
        predef_buffer = ""

        async def to_src(e: Expr):
            nonlocal predef_buffer
            match e:
                case BiOp(sym, left, right):
                    return f"{await to_src(left)} {sym} {await to_src(right)}"
                case Call(f, args, kwargs):
                    args_str = ""
                    if args:
                        args_str = ','.join([await to_src(a) for a in args])
                    if kwargs:
                        args_str += ',' + ','.join([f'{k}={await to_src(v)}' for k, v in kwargs.items()])
                    return f"{await to_src(f)}({args_str})"
                case Attr(src, attr):
                    return f"{await to_src(src)}.{attr}"
                case GetItem(src, key):
                    return f"{await to_src(src)}[{await to_src(key)}]"
                case Object(InjectedByName(name)):
                    return name
                case Object(Injected() | DelegatedVar() as data):
                    # we don't know if the data is from design or not, so the full function is constructed.
                    # we need to look at a table...
                    vid_to_key = {id(v): k for k, v in self.mappings.items()}
                    sym = self.find_matching_mapping(data)
                    if sym is None:
                        if id(data) in vid_to_key:
                            sym = vid_to_key[id(data)]
                            logger.info(f"using symbol:{sym}")
                        else:
                            sym = "tmp__" + self.new_symbol()
                        # here, we are seeing InjectedFunction
                        # We need to handle InjectedByName
                        logger.info(f"creating new symbol:{sym}, for {data}")
                    if sym not in visited:
                        predef_buffer += f"{await self.to_source(sym, data, visited)}\n"
                    return sym
                case Object(str() as literal):
                    return f'"{literal}"'
                case Object(float() | int() as num):
                    return str(num)
                case Object(Path() as p):
                    return f"Path({p})"
                case Object(unknown):
                    raise ValueError(f"Unsupported object:{unknown},{type(unknown)}")
                case _:
                    raise ValueError(f"Unsupported type {e}, {type(e)}")

        src = await to_src(expr)
        code = f"{predef_buffer}\n{assign_target} = {src}"
        if predef_buffer.strip():
            prompt = f"""
Please simplify the following python script to remove tmp functions and variables, as much as possible.
The variables/functions to simplify have 'tmp' as their prefix.
The script's purpose is to calculate {assign_target}.
```
{code}
```
The answer should not contain any explanation or triple ticks.
Functions not in scope does not need to be defined.
Beware that {assign_target} name must be preserved.
    """
            logger.debug(f"prompt:\n{prompt}")
            simplified = await self.a_llm(prompt)
            simplified = simplified.replace('```', "")
            logger.debug(f"simplified:\n{simplified}")
            return simplified
        return code

    async def to_source(self, assign_target: str, src: Injected, visited: set = None):
        if visited is None:
            visited = set()
        code = ""
        if isinstance(src, str):
            src = Injected.by_name(src)
        src = Injected.ensure_injected(src)
        from loguru import logger
        logger.info(f"visiting {assign_target}")
        for dep in src.complete_dependencies:
            if dep not in visited:
                if dep not in self.mappings:
                    logger.error(f"{dep} not in mappings! for {src}")
                visited |= {dep}
                code += await self.to_source(dep, self.mappings[dep], visited)

        match src:
            case InjectedPure() as p:
                last_code = await self.to_source__instance(assign_target, p)
            case InjectedFunction(tgt_func, _km) as f:
                last_code = await self.get_source_func(assign_target, tgt_func)
            case PartialInjectedFunction(InjectedFunction(func)) as pif:
                last_code = await self.get_source_func(assign_target, func)
            case EvaledInjected(value, tree):
                from loguru import logger
                logger.info(tree)
                logger.info(value)
                last_code = await self.expr_to_source(assign_target, tree, visited)
            case ZippedInjected(a, b):
                left, right = self.tmp_symbol() + "left", self.tmp_symbol() + "right"
                prep = (await self.to_source(left, a, visited)
                        + "\n"
                        + await self.to_source(right, b, visited)
                        + "\n")
                last_code = prep + "\n" + f"{assign_target} = ({left},{right})\n"
            case MappedInjected(src, f):
                map_f = self.tmp_symbol()
                map_src = self.tmp_symbol()
                prep = await self.get_source_func(map_f, f) + "\n"
                prep += await self.to_source(map_src, src, visited) + "\n"
                last_code = prep + f"{assign_target} = {map_f}({map_src})\n"
            case InjectedByName(name):
                last_code = await self.to_source(name, self.mappings[name], visited=visited)
            case _:
                raise ValueError(f"Unsupported type {src}")
        code += last_code + "\n"
        return code

    async def simplify_code(self, target_name, code):
        prompt = f"""
    Please convert the following python into simplified python script?
    This script is for calculating result variable "{target_name}".
    ```
    {code}
    ```
    Simplification should involve removing placeholder function into an expression.
    The answer should keep properly named variables and functions.
    Variable assignments for tmp variables should be simplified as much as possible.
    If tmp variables cannot be simplified, it should be renamed to proper variable names.
    """
        return await self.a_llm(prompt)

    async def export(self, target):
        return await self.to_source(target, self.mappings[target])
