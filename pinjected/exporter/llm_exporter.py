import inspect
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pformat
from typing import Callable, Awaitable, List

import cytoolz

from pinjected import Design, Injected, injected, instances, providers, instance
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.expr_util import Expr, BiOp, Call, Attr, GetItem, Object, UnaryOp
from pinjected.di.injected import InjectedPure, InjectedFunction, PartialInjectedFunction, ZippedInjected, \
    MappedInjected, InjectedByName, FrameInfo, MZippedInjected, DictInjected
from pinjected.di.proxiable import DelegatedVar
from pinjected.exporter.optimize_import_stmts import fix_imports
from pinjected.helper_structure import IdeaRunConfiguration, MetaContext
from pinjected.module_inspector import ModuleVarSpec
from pinjected.module_var_path import ModuleVarPath


def add_async_to_function_source(function_source):
    # Get the source code of the function

    # Parse the function source code into an AST
    tree = ast.parse(function_source)

    # Find the function definition node
    function_def = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_def = node
            break

    if function_def:
        # Add the 'async' keyword to the function definition
        function_def.async_stmt = 1

        # Convert the modified AST back to source code
        modified_source = ast.unparse(tree)

        return modified_source
    else:
        return None


import ast


@dataclass
class Imports:
    imports: dict[str, str] = field(default_factory=dict)
    classes: dict[str, ast.ClassDef] = field(default_factory=dict)


@dataclass
class CodeBlock:
    target: str
    code: str
    # imports: dict[str, str] = field(default_factory=dict)
    imports: Imports = field(default_factory=Imports)

    def __post_init__(self):
        assert isinstance(self.imports, Imports), f"imports is not Imports:{self.imports},{type(self.imports)}"


@dataclass
class PinjectedCodeExporter:
    src: Design
    a_llm: Callable[[str], Awaitable[str]]

    def __post_init__(self):
        digraph = self.src.to_vis_graph()
        self.mappings = {**digraph.explicit_mappings}

    async def to_source__instance(self, assign_target, tgt: InjectedPure) -> CodeBlock:
        # wait, tgt.value must be recoverable from the value. but it should always be.
        # let's get the relevant imports

        mod_name = tgt.__definition_module__
        from loguru import logger
        if mod_name == 'module.name':
            # the variable is defined at non-module script so let's read the file
            source = Path(tgt.__original_file__).read_text()
            imports = get_required_imports(source, module_name="__main__")
        else:
            module = sys.modules[mod_name]
            imports = get_required_imports(module)

        match tgt.value:
            case str():
                code = f'{assign_target} = """{tgt.value}"""'
            case int() | float():
                code = f'{assign_target} = {tgt.value}'
            case list() | dict():
                code = f'{assign_target} = {tgt.value}'
            case f if callable(f):
                src = inspect.getsource(tgt.value)
                logger.info(f"trying to en_source a callable:{src}")
                src = await self.extract_lambda(tgt.value)
                code = f'{assign_target} = {src}'
            case Path():
                code = f"{assign_target} = Path('{tgt.value}')"
            case None:
                code = f"{assign_target} = None"
            case _:
                raise ValueError(f"Unsupported type {tgt.value}")

        # assert isinstance(tgt.value, (str, int, float,list,dict,NoneType)), f"tgt.value must be a simple value, got {tgt.value}"

        return CodeBlock(
            target=assign_target,
            code=code,
            imports=imports
        )

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
        logger.info(f"prompt:\n{prompt}")
        return await self.a_llm(prompt)

    async def get_source_func(self, assign_target, f):
        from loguru import logger
        if f.__module__ == 'builtins':
            return f"{assign_target} = {f.__name__}"
        if hasattr(f, "__original_code__"):
            # logger.info(f"retrieving source from __original_code__")
            src = f.__original_code__
            # logger.debug(f"original source from __original_code__:\n{src}")
            modified = add_async_to_function_source(src)
            if modified is not None:
                src = modified
                # logger.debug(f"modified source from __original_code__:\n{src}")
        else:
            src = inspect.getsource(f)
        """
        @injected
        def g(f,/,x):
            return f(x=x,y=1)
        
        I need to remove @injected and positional only arguments. from this source, using AST.
        """
        # logger.info(f"getting source:{f.__name__}->\n{src}")
        try:
            if f.__name__.endswith('<lambda>'):
                src = await self.extract_lambda(f)
                src = src.replace("```python", "").replace('```', "").replace("\n", "")
                return f"{assign_target} = {src}\n"
            else:
                #logger.debug(f"parsing function:{assign_target},\n{src}")
                tree = ast.parse(src)
                #logger.debug(f"before un_pinjected->\n{src}")
                PinjectedCodeExporter.un_pinjected(assign_target, tree)
                unparsed = ast.unparse(tree)
                #logger.debug(f"un_pinjected->\n{unparsed}")
                return unparsed
            # return astor.to_source(tree)
        except Exception as e:
            logger.error(f"error in getting source for {f.__name__}:\n{e}")
            logger.error(f"source:\n{src}")
            raise e

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
                break

    @staticmethod
    def new_symbol():
        return str(uuid.uuid4())[:3]

    @staticmethod
    def tmp_symbol():
        return "tmp_" + PinjectedCodeExporter.new_symbol()

    def find_matching_mapping(self, data: Injected):
        from loguru import logger
        #logger.info(f"finding matching mapping for {data}")
        match data:
            case InjectedFunction(f, kwargs_mapping):
                for k, v in self.mappings.items():
                    match v:
                        case PartialInjectedFunction(InjectedFunction(_f)) if f == _f:
                            return k
        return None

    async def expr_to_source(self, assign_target: str, expr: Expr, visited) -> list[CodeBlock]:
        from loguru import logger

        predef_blocks = []

        async def to_src(e: Expr):
            nonlocal predef_blocks
            match e:
                case BiOp(sym, left, right):
                    return f"{await to_src(left)} {sym} {await to_src(right)}"
                case Call(f, args, kwargs):
                    args_str = ""
                    if args:
                        args_str = ','.join([await to_src(a) for a in args])
                    if args and kwargs:
                        args_str += ','
                    if kwargs:
                        args_str += ','.join([f'{k}={await to_src(v)}' for k, v in kwargs.items()])
                    return f"{await to_src(f)}({args_str})"
                case Attr(src, attr):
                    return f"{await to_src(src)}.{attr}"
                case GetItem(src, key):
                    return f"{await to_src(src)}[{await to_src(key)}]"
                case UnaryOp("await", tgt):
                    return f"(await {await to_src(tgt)})"
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
                            sym = self.tmp_symbol()
                        # here, we are seeing InjectedFunction
                        # We need to handle InjectedByName
                        # logger.info(f"creating new symbol:{sym}, for {data}")
                    # hmm, to_source returns code block.
                    if sym not in visited:
                        predef_blocks += await self.to_source(sym, data, visited)
                    return sym
                case Object(str() as literal):
                    return f'"{literal}"'
                case Object(float() | int() as num):
                    return str(num)
                case Object(Path() as p):
                    return f"Path('{p}')"
                case Object(unknown):
                    raise ValueError(f"Unsupported object:{unknown},{type(unknown)}")
                case _:
                    raise ValueError(f"Unsupported type {e}, {type(e)}")

        src = await to_src(expr)

        code = f"{assign_target} = {src}"

        #         if code.strip():
        #             prompt = f"""
        # Please simplify the following python script to remove tmp functions and variables, as much as possible.
        # The variables/functions to simplify have 'tmp' as their prefix.
        # The script's purpose is to calculate {assign_target}.
        # ```
        # {code}
        # ```
        # The answer should not contain any explanation or triple ticks.
        # Functions not in scope does not need to be defined.
        # Beware that {assign_target} name must be preserved.
        #     """
        #             logger.debug(f"prompt:\n{prompt}")
        #             simplified = await self.a_llm(prompt)
        #             simplified = simplified.replace("```python", "").replace('```', "")
        #             logger.debug(f"simplified:\n{simplified}")
        #             code = simplified

        return [
            *predef_blocks,
            CodeBlock(
                target=assign_target,
                code=code,
            )
        ]

    async def to_source(self, assign_target: str, src: Injected, visited: set = None) -> list[CodeBlock]:
        """
        TODOs:
        1. reduce blocks with tmp_ variables
        2. include class definitions -> 80%
        3. optimize imports -> 90%
        4. create main function with asyncio.run
        """
        if visited is None:
            visited = set()
        blocks = []
        if isinstance(src, str):
            src = Injected.by_name(src)
        src = Injected.ensure_injected(src)
        from loguru import logger
        # logger.info(f"visiting {assign_target}")
        for dep in src.complete_dependencies:
            if dep not in visited:
                if dep not in self.mappings:
                    logger.error(f"{dep} not in mappings! for {src}")
                visited |= {dep}
                if dep not in self.mappings:
                    logger.warning(f"mappings:{self.mappings}")
                    raise ValueError(f"{dep} not in mappings!")
                blks = await self.to_source(dep, self.mappings[dep], visited)
                for b in blks:
                    assert isinstance(b, CodeBlock), f"block is not CodeBlock:{b},{type(b)},src:{src}\n{pformat(blks)}"
                blocks += blks
                for b in blocks:
                    assert isinstance(b,
                                      CodeBlock), f"block is not CodeBlock:{b},{type(b)},src:{src}\n{pformat(blocks)}"

        # logger.info(f"getting source for {assign_target},type:{type(src)}")
        match src:
            case InjectedPure() as p:
                blocks += [await self.to_source__instance(assign_target, p)]
            case InjectedFunction(tgt_func, {'injected_kwargs': DictInjected(kwargs_mapping)}) as f if hasattr(f,
                                                                                                               '__is_partial__'):
                assign_blocks = await self.get_blocks_for_func_call(
                    assign_target,
                    f,
                    kwargs_mapping,
                    visited=visited,
                    call=False
                )
                blocks += assign_blocks
            case InjectedFunction(func_called, {'injected_kwargs': DictInjected(kwargs_mapping)}) as _if:
                # aha, we need to solve the keyword mappings and add it as code blocks
                # logger.warning(f"kwargs_mapping for injected_function:{kwargs_mapping}")
                assign_blocks = await self.get_blocks_for_func_call(
                    assign_target,
                    _if,
                    kwargs_mapping,
                    visited,
                    call=True
                )
                blocks += assign_blocks

            case InjectedFunction(tgt_func, {}) as _if:
                # when this is matching the caller is expecting a function call (for assignment)
                assign_blocks = await self.get_blocks_for_func_call(
                    assign_target,
                    _if,
                    kwargs_mapping=dict(),
                    visited=visited,
                    call=True
                )

                blocks += assign_blocks

            case PartialInjectedFunction(
                InjectedFunction(func, {'injected_kwargs': DictInjected(kwargs_mapping)}) as ifunc) as pif:
                assign_blocks = await self.get_blocks_for_func_call(
                    assign_target,
                    ifunc,
                    kwargs_mapping,
                    visited=visited,
                    call=False
                )
                blocks += assign_blocks

            case PartialInjectedFunction(InjectedFunction(func, kwargs_mapping) as ifunc) as pif:
                logger.warning(f"kwargs_mapping for partial_injected_function:{kwargs_mapping}")
                # ah,, in some cases the PartialInjectedFunction is manually created without Injected.partial

                assign_blocks = await self.get_blocks_for_func_call(
                    assign_target,
                    ifunc,
                    kwargs_mapping,
                    visited=visited,
                    call=True
                )
                blocks += assign_blocks

            case EvaledInjected(value, tree):
                from loguru import logger
                blocks += await self.expr_to_source(assign_target, tree, visited)
                for b in blocks:
                    assert isinstance(b,
                                      CodeBlock), f"block is not CodeBlock:{b},{type(b)},src:{src}\n{pformat(blocks)}"
            case ZippedInjected(a, b):
                left, right = self.tmp_symbol() + "left", self.tmp_symbol() + "right"
                left_block = await self.to_source(left, a, visited)
                right_block = await self.to_source(right, b, visited)
                assign_code = f"{assign_target} = ({left},{right})\n"
                blocks += [
                    *left_block,
                    *right_block,
                    CodeBlock(
                        target=assign_target,
                        code=assign_code,
                    )
                ]
            case MZippedInjected(srcs):
                symbols = []
                for src in srcs:
                    sym = self.tmp_symbol()
                    symbols.append(sym)
                    logger.info(f"resolving mzip item:{sym}, {src}")
                    _blks = await self.to_source(sym, src, visited)
                    logger.info(f"blocks:{pformat(_blks)}")
                    blocks += _blks

                assign_code = f"{assign_target} = ({','.join(symbols)})\n"
                blocks += [CodeBlock(
                    target=assign_target,
                    code=assign_code
                )]
                for b in blocks:
                    assert isinstance(b,
                                      CodeBlock), f"block is not CodeBlock:{b},{type(b)},src:{src}\n{pformat(blocks)}"
                logger.info(f"blocks:{pformat(blocks)}")
            case DictInjected(srcs):
                key_to_symbol = dict()
                for k, v in srcs.items():
                    sym = self.tmp_symbol()
                    key_to_symbol[k] = sym
                    _blks = await self.to_source(sym, v, visited)
                    blocks += _blks
                assign_code = assign_target + " = {\n" + ",\n".join(
                    [f'    "{k}":{v}' for k, v in key_to_symbol.items()]) + "\n}"
                blocks += [CodeBlock(
                    target=assign_target,
                    code=assign_code
                )]

            case MappedInjected(src, f) as mi:
                map_f = self.tmp_symbol()
                map_src = self.tmp_symbol()
                prep = await self.get_source_func(map_f, mi.original_mapper) + "\n"
                # prep += await self.to_source(map_src, src, visited) + "\n"
                last_code = f"{assign_target} = {map_f}({map_src})\n"
                module = inspect.getmodule(mi.original_mapper)
                imports = get_required_imports(module)
                blocks += [
                    CodeBlock(
                        target=map_f,
                        code=prep,
                        imports=imports
                    ),
                    *(await self.to_source(map_src, src, visited)),
                    CodeBlock(
                        target=assign_target,
                        code=last_code,
                    )
                ]
            case InjectedByName(name):
                blocks += await self.to_source(name, self.mappings[name], visited=visited)
                blocks.append(CodeBlock(
                    target=assign_target,
                    code=f"{assign_target} = {name}"
                ))

            case _:
                raise ValueError(f"Unsupported type {src}")
        for b in blocks:
            if '<lambda>' in b.code:
                logger.error(f"lambda found in code block:{b.code}")
            assert isinstance(b, CodeBlock), f"block is not CodeBlock:{b},{type(b)},src:{src}\n{pformat(blocks)}"
            assert '<lambda>' not in b.code, f"lambda found in code block:{b.code},blocks:\n{pformat(blocks)}"
        return blocks

    async def get_blocks_for_func_call(self, assign_target, f: InjectedFunction, kwargs_mapping, visited,
                                       call: bool):
        from loguru import logger
        key_to_symbol = dict()
        dep_blocks = []
        for key, bound in kwargs_mapping.items():
            if key not in visited:
                sym = self.tmp_symbol()
                key_to_symbol[key] = sym
                dep_blocks += await self.to_source(sym, bound, visited)
            else:
                pass
        org_func = f.original_function
        module = inspect.getmodule(org_func)
        # assert module is not None,f"module is None for {org_func},\n{inspect.getsource(org_func)}"
        if module is not None:
            imports = get_required_imports(module)
        else:
            imports = Imports()
        func_name = f"__{assign_target}"
        last_code = await self.get_source_func(func_name, f.target_function)
        # you need to actually call the func.
        pairs = [f"{k}={v}" for k, v in key_to_symbol.items()]
        if call:
            last_code += f"\n{assign_target} = {func_name}({','.join(pairs)})\n"
        else:
            last_code += f"\n{assign_target} = {func_name}"
        #logger.info(f"imports for {func_name}:{pformat(imports)}")
        assignment = CodeBlock(
            target=assign_target,
            code=last_code,
            imports=imports
        )
        return dep_blocks + [assignment]

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

    async def export(self, target, package_to_export: str):
        blocks: list[CodeBlock] = await self.to_source(target, self.mappings[target])
        imports = cytoolz.merge([b.imports.imports for b in blocks])
        classdefs = cytoolz.merge([b.imports.classes for b in blocks])
        classdefs = {k: v for k, v in classdefs.items() if imports[k].startswith(package_to_export)}
        # remove classdefs from imports
        from loguru import logger
        # logger.info(f"classdefs:{pformat(classdefs)}")
        imports = {k: v for k, v in imports.items() if k not in classdefs}

        tmp_code = "\n".join([b.code for b in blocks])

        used_names = extract_variable_names(tmp_code)
        # add classes used
        # logger.info(f"used_names:{used_names}")
        used_classdefs = {k: v for k, v in classdefs.items() if k in used_names}
        class_blocks = class_defs_to_blocks(used_classdefs)
        logger.info(f'class_blocks:\n{pformat(class_blocks)}')
        blocks += [
            CodeBlock(
                target="",
                code=f"return {blocks[-1].target}",
                imports=Imports()
            )
        ]

        block_asts = [ast.parse(b.code) for b in blocks]

        class_codes = "\n".join([b.code for b in class_blocks])

        code = wrap_in_async_main(block_asts)

        # recreate the code
        # code = "\n".join([b.code for b in blocks])

        import_lines = ""
        for name, full in imports.items():
            # logger.info(f"importing {name} from {full}")
            mod_paths = full.split('.')
            if len(mod_paths) <= 1:
                import_lines += f"import {name}\n"
            else:
                mod_name = ".".join(mod_paths[:-1])
                import_lines += f"from {mod_name} import {name}\n"

        src = import_lines + "\n" + class_codes + "\n" + code
        src = fix_imports(src)
        return src


def wrap_in_async_main(nodes):
    # Create the 'async main' function
    async_main_func = ast.AsyncFunctionDef(
        name='main',
        args=ast.arguments(
            args=[],
            vararg=None,
            posonlyargs=[], kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
        ),
        body=nodes,
        decorator_list=[],
        returns=None,
        lineno=0,
    )

    # Convert the 'async main' function to a string
    func_string = ast.unparse(async_main_func)

    # Add the '__main__' section using a string
    main_string = f"""
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
"""

    # Combine the function string and the main string
    final_string = func_string + main_string

    return final_string


import ast


def extract_variable_names(code):
    tree = ast.parse(code)
    variable_names = []

    def visit_node(node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    variable_names.append(target.id)
        elif isinstance(node, ast.FunctionDef):
            variable_names.append(node.name)
            for arg in node.args.args:
                variable_names.append(arg.arg)
        elif isinstance(node, ast.ClassDef):
            variable_names.append(node.name)
        elif isinstance(node, ast.Name):
            variable_names.append(node.id)

    for node in ast.walk(tree):
        visit_node(node)

    return list(set(variable_names))


def class_defs_to_blocks(class_defs: dict[str, ast.ClassDef]):
    blocks = []
    for name, class_def in class_defs.items():
        blocks.append(CodeBlock(
            target=name,
            code=ast.unparse(class_def),
            imports=Imports()
        ))
    return blocks


@injected
async def _export_injected(logger, a_llm, /, tgt: str):
    tgt = ModuleVarPath(tgt)
    from loguru import logger
    mc: MetaContext = await MetaContext.a_gather_from_path(tgt.module_file_path)
    logger.debug(f"loaded meta context for {tgt.module_file_path}")
    logger.debug(f"using meta context:{mc}")
    fd = await mc.a_final_design
    logger.debug(f"meta context final design:{pformat(fd.bindings)}")
    # hmm, the design must contain the tgt.var_name, so we add it here
    fd += providers(**{tgt.var_name: tgt.load()})
    exporter = PinjectedCodeExporter(fd, a_llm)
    src = await exporter.export(tgt.var_name, tgt.module_name.split('.')[0])
    logger.info(f"script:\n{src}")
    original_path = Path(tgt.module_file_path)
    dst = original_path.parent / (original_path.stem + f"__{tgt.var_name}.py")
    dst.write_text(src)


export_injected: Injected = _export_injected(injected("export_target"))

"""
Current limitations:
- code that works like a meta programming is not supported
  - async_cached
    - 
- classes are not copied
"""


@injected
def add_export_config(
        interpreter_path,
        default_working_dir,
        /,
        tgt: ModuleVarSpec,
) -> List[IdeaRunConfiguration]:
    """
    options to pass secret variables:
    1. set it here as a --ray-job-kwargs
    2. use env var
    3. upload ~/.pinjected.py <- most flexible, but need a source .pinject.py file

    """
    import pinjected

    conf = IdeaRunConfiguration(
        name=f"Export script",
        script_path=str(pinjected.__file__).replace("__init__.py", "__main__.py"),
        interpreter_path=interpreter_path,
        arguments=[
            "run",
            "pinjected.exporter.llm_exporter.export_injected",
            f"--export-target={tgt.var_path}"
        ],
        working_dir=default_working_dir.value_or("."),
    )

    return [conf]


test_export_injected: Injected = _export_injected("pinjected.exporter.llm_exporter.export_injected")

test_pure = Injected.pure(instance)


@instance
def test_injected_pure_imports(logger):
    def_frame: FrameInfo = test_pure.__definition_frame__
    frm = def_frame.original_frame
    mod_name = frm.f_globals['__name__']
    module = sys.modules[mod_name]
    return get_required_imports(module)


#
# def get_required_imports(module_or_source):
#     if isinstance(module_or_source, str):
#         source = module_or_source
#     else:
#         source = inspect.getsource(module_or_source)
#     tree = ast.parse(source)
#     imports = {}
#
#     for node in ast.walk(tree):
#         if isinstance(node, ast.Import):
#             for alias in node.names:
#                 var_name = alias.asname if alias.asname else alias.name
#                 imports[var_name] = alias.name
#         elif isinstance(node, ast.ImportFrom):
#             for alias in node.names:
#                 var_name = alias.asname if alias.asname else alias.name
#                 imports[var_name] = f"{node.module}.{alias.name}"
#
#     return imports


def get_required_imports(module_or_source, module_name=None) -> Imports:
    if isinstance(module_or_source, str):
        source = module_or_source
        if module_name is None:
            module_name = "."
    else:
        if module_or_source.__name__ == 'builtins':
            return Imports()
        source = ast.unparse(ast.parse(ast.unparse(ast.parse(inspect.getsource(module_or_source)))))
        module_name = module_or_source.__name__

    tree = ast.parse(source)
    module_info = {}
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                var_name = alias.asname if alias.asname else alias.name
                module_info[var_name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                var_name = alias.asname if alias.asname else alias.name
                module_info[var_name] = f"{node.module}.{alias.name}"
                try:
                    module = __import__(module_name, fromlist=[var_name])
                    maybe_class = getattr(module, var_name)
                    if inspect.isclass(maybe_class):
                        src = inspect.getsource(maybe_class)
                        classes[var_name] = ast.parse(src)
                except (ImportError, AttributeError, OSError, TypeError):
                    continue
        elif isinstance(node, ast.ClassDef):
            classes[node.name] = node
            module_info[node.name] = f"{module_name}.{node.name}"
        elif isinstance(node, ast.FunctionDef):
            module_info[node.name] = f"{module_name}.{node.name}"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_info[target.id] = f"{module_name}.{target.id}"

    return Imports(
        imports=module_info,
        classes=classes
    )


default_design = instances(
) + providers(
    a_llm=injected('a_llm__gpt4_turbo')
)

__meta_design__ = instances(
    default_design_paths=["pinjected.exporter.llm_exporter.default_design"],
    overrides=instances(

    ),
) + providers(
    # custom_idea_config_creator=add_export_config,
)
