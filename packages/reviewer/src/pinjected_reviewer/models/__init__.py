import hashlib

from injected_utils import async_cached, lzma_sqlite
from pinjected import injected, Injected
from pinjected_openai.openrouter.util import a_openrouter_chat_completion

a_cached_openrouter_chat_completion = async_cached(
    lzma_sqlite(injected('pinjected_reviewer_cache_path') / "openrouter_chat_completion_cache.sqlite"),
    key_hashers=Injected.dict(
        response_format=Injected.pure(lambda m: hashlib.sha256(str(m.model_json_schema()).encode()).hexdigest() if m is not None else "None")
    )
)(
    a_openrouter_chat_completion,
)

