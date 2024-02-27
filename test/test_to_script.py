import ast
import asyncio
import base64
import inspect
import io
import re
import uuid

import astor
from openai import AsyncOpenAI, RateLimitError

from pinjected import instances, providers, injected, Design, Injected, instance
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.ast import Expr, BiOp, Call, Attr, GetItem, Object
from pinjected.di.injected import InjectedPure, PartialInjectedFunction, InjectedFunction, MappedInjected, \
    ZippedInjected
from pinjected.run_helpers.run_injected import load_user_default_design
from pinjected.visualize_di import DIGraph


def to_content(img: "Image"):
    from loguru import logger
    # convert Image into jpeg bytes
    jpg_bytes = io.BytesIO()
    img.convert('RGB').save(jpg_bytes, format='jpeg', quality=95)
    b64_image = base64.b64encode(jpg_bytes.getvalue()).decode('utf-8')
    mb_of_b64 = len(b64_image) / 1024 / 1024
    logger.info(f"image size: {mb_of_b64:.2f} MB in base64.")
    return {
        "type": 'image_url',
        "image_url": f"data:image/jpeg;base64,{b64_image}"
    }


@injected
async def a_repeat_for_rate_limit(task):
    from loguru import logger
    while True:
        try:
            return await task()
        except RateLimitError as e:
            logger.error(f"rate limit error: {e}")
            pat = "Please retry after (\d+) seconds."
            match = re.search(pat, e.message)
            if match:
                seconds = int(match.group(1))
                logger.info(f"sleeping for {seconds} seconds")
                await asyncio.sleep(seconds)
            else:
                logger.warning(f"failed to parse rate limit error message: {e.message}")
                await asyncio.sleep(10)


@injected
async def a_llm__openai(
        async_openai_client: AsyncOpenAI,
        a_repeat_for_rate_limit,
        /,
        text: str,
        images: list["Image"],
        model_name
) -> str:
    assert isinstance(async_openai_client, AsyncOpenAI)

    for img in images:
        assert isinstance(img, "Image"), f"image is not Image, but {type(img)}"

    async def task():
        chat_completion = await async_openai_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": 'text',
                            "text": text
                        },
                        *[to_content(img) for img in images]
                    ]
                }
            ],
            # model="gpt-4-vision-preview",
            model=model_name,
            max_tokens=2048
        )
        return chat_completion

    chat_completion = await a_repeat_for_rate_limit(task)
    res = chat_completion.choices[0].message.content
    assert isinstance(res, str)
    return res


@instance
def async_openai_client(openai_api_key) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=openai_api_key,
    )


# @instance
# def openai_api_key() -> str:
#     import os
#     if (api_key := os.environ.get('OPENAI_API_KEY', None)) is None:
#         api_key = Path(os.path.expanduser("~/.openai_api_key.txt")).read_text().strip()
#     return api_key
@injected
async def a_llm__gpt35(a_llm__openai, /, text):
    return await a_llm__openai(text=text, images=[], model_name="gpt-3.5-turbo")


@injected
async def a_llm__gpt4_turbo(a_llm__openai, /, text):
    return await a_llm__openai(text=text, images=[], model_name="gpt-4-turbo-preview")


llm_design = instances() + load_user_default_design()
a_llm = llm_design.provide(a_llm__gpt4_turbo)
# %%

asyncio.run(a_llm("hello"))


# %%


@injected
def f(x, /, y):
    return x + y


@injected
def g(f, /, x):
    return f(x=x, y=1)


@instance
def CONST(g, x):
    return g(x)


@instance
def alpha(CONST):
    return CONST + 1


test_target = f(g(CONST + alpha))

d: Design = instances(
    x=0
) + providers(
    f=f,
    v=CONST,
    target=test_target
)
dig: DIGraph = d.to_vis_graph()
dig.parse_injected(g)
"""
so, in order to form a script from digraph,
I need to:
1. make each injected as an expression.

The result should look like:
Instances:
x = 0
y = 1
Providers:
def provider_func(x,y):
    ... local variable declarations ...
    ....
z = provider_func(x,y)
ASTs:
def lambda_0(x,y):
    __res__ = ... constructed ast ...
    return __res__
z = lambda_0(x,y)

Yeah, let's do it.
"""

mappings: dict[str, Injected] = {**dig.implicit_mappings, **dig.explicit_mappings}
mappings


async def to_source__instance(assign_target, tgt: InjectedPure):
    # wait, tgt.value must be recoverable from the value. but it should always be.
    return f"{assign_target} = {tgt.value}"


async def extract_lambda(f):
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
    return await a_llm(prompt)


async def get_source_func(assign_target, f):
    if hasattr(f, "__original_code__"):
        from loguru import logger
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
        src = await extract_lambda(f)
        return f"{assign_target} = {src}\n"
    else:
        tree = ast.parse(src).body[0]
        modify_function(assign_target, tree)
        return astor.to_source(tree)


# Function to remove the @injected decorator and positional-only argument marker
def modify_function(assignment, tree):
    deletion_targets = {"injected", "instance"}
    for node in ast.walk(tree):
        # Check if the node is a function definition
        if isinstance(node, ast.FunctionDef):
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


def new_symbol():
    return str(uuid.uuid4())[:3]


def find_matching_mapping(data: Injected):
    from loguru import logger
    logger.info(f"finding matching mapping for {data}")
    match data:
        case InjectedFunction(f, kwargs_mapping):
            for k, v in mappings.items():
                match v:
                    case PartialInjectedFunction(InjectedFunction(_f)) if f == _f:
                        return k
    return None


async def expr_to_source(assign_target: str, expr: Expr, visited):
    from loguru import logger
    predef_buffer = ""

    async def to_src(e: Expr):
        nonlocal predef_buffer
        logger.info(f"<- {e}")
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
            case Object(data):
                # we don't know if the data is from design or not, so the full function is constructed.
                # we need to look at a table...
                vid_to_key = {id(v): k for k, v in mappings.items()}
                logger.debug(f"data->{data}")
                logger.debug(f"vid_to_key->{mappings}")
                sym = find_matching_mapping(data)
                if sym is None:
                    if id(data) in vid_to_key:
                        sym = vid_to_key[id(data)]
                        logger.info(f"using symbol:{sym}")
                    else:
                        sym = "tmp__" + new_symbol()
                    # here, we are seeing InjectedFunction
                    logger.info(f"creating new symbol:{sym}, for {data}")
                if sym not in visited:
                    predef_buffer += f"{await to_source(sym, data, visited)}\n"
                return sym
            case _:
                raise ValueError(f"Unsupported type {e}")

    src = await to_src(expr)
    code = f"{predef_buffer}\n{assign_target} = {src}"
    if predef_buffer.strip():
        prompt = f"""
Please simplify the following python script to remove tmp functions and variables, as much has possible.
The variables/functions to simplify have 'tmp' as their prefix.
```
{code}
```
The answer should not contain any explanation or triple ticks.
Functions not in scope does not need to be defined.
"""
        logger.debug(f"prompt:\n{prompt}")
        simplified = await a_llm(prompt)
        simplified = simplified.replace('```', "")
        logger.debug(f"simplified:\n{simplified}")
        return simplified
    return code


async def to_source(assign_target: str, src: Injected, visited: set = None):
    if visited is None:
        visited = set()
    code = ""
    src = Injected.ensure_injected(src)
    from loguru import logger
    logger.info(f"visiting {assign_target}")
    for dep in src.complete_dependencies:
        if dep not in visited:
            visited |= {dep}
            code += await to_source(dep, mappings[dep], visited)

    match src:
        case InjectedPure() as p:
            last_code = await to_source__instance(assign_target, p)
        case InjectedFunction(tgt_func, _km) as f:
            last_code = await get_source_func(assign_target, tgt_func)
        case PartialInjectedFunction(InjectedFunction(func)) as pif:
            last_code = await get_source_func(assign_target, func)
        case EvaledInjected(value, tree):
            from loguru import logger
            logger.info(tree)
            logger.info(value)
            last_code = await expr_to_source(assign_target, tree, visited)
        case ZippedInjected(a, b):
            prep = await to_source('zip_left', a, visited) + "\n" + await to_source("zip_right", b, visited) + "\n"
            last_code = prep + "\n" + f"{assign_target} = (zip_left,zip_right)\n"
        case MappedInjected(src, f):
            prep = await get_source_func('mapped_mapper', f) + "\n"
            prep += await to_source('mapped_src', src, visited) + "\n"
            last_code = prep + f"{assign_target} = mapped_mapper(mapped_src)\n"
        case _:
            raise ValueError(f"Unsupported type {src}")

    # code = f"# -> {assign_target}\n" + code
    code += last_code + "\n"
    # code += f"# <- {assign_target}\n"

    return code


async def simplify_code(target_name, code):
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
    return await a_llm(prompt)


src = asyncio.run(to_source('target', mappings['target']))
print(src)
# print(f"__________________")
# print(asyncio.run(simplify_code('target',src)))
# print(inspect.getsource(Injected.__add__))
# %%
"""
PartialInjectedFunction() returns
src.proxy()
so, the mapping holds that info.
"""
