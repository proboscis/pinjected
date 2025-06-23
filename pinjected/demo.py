from collections.abc import Callable
from pathlib import Path

from pinjected import Design, Injected, IProxy, design, injected

__design__: Design = design(
    openai_api_key="my secret key",
    model="text-davinci-003",
    max_tokens=1000,
    load_openai_api_key=Injected.pure(
        lambda: Path("~/openai_api_key.txt").expanduser().read_text().strip()
    ),
)

# This was previously referenced by default_design_paths, now merged into __design__
default_design: Design = __design__


@injected
def LLM(load_openai_api_key: str, model, max_tokens, /, prompt) -> str:
    # openai_api_key = Path("~/openai_api_key.txt").expanduser().read_text().strip()
    import openai

    return openai.Completion.create(
        load_openai_api_key(), prompt=prompt, model=model, max_tokens=max_tokens
    )["choices"][0]["text"]


@injected
def Gandalf(LLM: Callable[[str], str], /, user_message: str) -> str:
    return LLM(
        f"Respond to the user's message as if you were a Gandalf: {user_message}"
    )


test_greeting: IProxy = Gandalf("How are you?")
