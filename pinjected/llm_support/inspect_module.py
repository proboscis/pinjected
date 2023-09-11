import glob
from pathlib import Path
from typing import List

import loguru

from pinjected import instances, Injected, injected, providers

__meta_design__ = instances(
    default_design_paths=[
        "davinci.paper_indexer_design.gpt4_llm_design"
    ],
    #default_design_paths=["davinci.paper_indexer_design.gpt35_llm_design"],
    overrides=providers(
        logger=lambda: loguru.logger
    )
)

from pinjected.llm_support.inspect_module_prompts import INSPECT_TEMPLATE

def test(*xyz):
    pass

@injected
def count_tokens(count_token, /, targets: List[Path]):
    # find .py files recursively
    # count tokens in each file
    for pyf in targets:
        token = count_token(Path(pyf).read_text())
        print(f"file:{pyf} -> tokens:{token}")


@injected
def list_python_files(root: Path) -> List[Path]:
    # find .py files recursively
    # count tokens in each file
    py_files = list(glob.glob(str(root / '**/*.py'), recursive=True))
    return [Path(pyf) for pyf in py_files]


all_py_files = list_python_files(Path("./"))
see_tokens: Injected = count_tokens(list_python_files(Path("./")))


@injected
async def inspect_type(a_cached_smart_llm: 'str -> str', /, py_text: str) -> str:
    prompt = INSPECT_TEMPLATE + f"""
Now, please answer the infered type for each global declarations in the following python script.
```python
{py_text}
```
If the type cannot be infered, please answer 'unknown'.
For callable type signature, use T->U to represent a function that takes a T and returns a U, instead of Callable[[T],U].
"""
    return await a_cached_smart_llm(prompt)



@injected
def test_function(smart_prompt_helper,/,x):
    print(smart_prompt_helper)
    return x


ans:Injected = inspect_type(Path("/Users/s22625/repos/pinject-design/pinjected/llm_support/inspect_module.py").read_text())
