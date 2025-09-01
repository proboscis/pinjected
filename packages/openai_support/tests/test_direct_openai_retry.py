import pytest
from pinjected import design
from pinjected.test import injected_pytest
from httpx import ConnectTimeout


class _TestLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def success(self, *args, **kwargs):
        pass


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]
        self.usage = None


class _FakeChatCompletions:
    def __init__(self, to_raise_first: int, exc_factory, result_content: str = "ok"):
        self._remaining_failures = to_raise_first
        self._exc_factory = exc_factory
        self._result_content = result_content
        self.call_count = 0

    async def create(self, **kwargs):
        self.call_count += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise self._exc_factory()
        return _FakeResponse(self._result_content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeAsyncOpenAI:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


completions_retry = _FakeChatCompletions(
    to_raise_first=1, exc_factory=lambda: ConnectTimeout("timeout")
)
client_retry = _FakeAsyncOpenAI(completions_retry)


@injected_pytest(
    design(
        openai_organization="test-org",
        logger=_TestLogger(),
        async_openai_client=client_retry,
        openai_model_table=None,
        openai_state={},
        test_completions=completions_retry,
    )
)
async def test_a_sllm_openai_retries_once_on_connect_timeout(
    a_sllm_openai, test_completions, /
):
    result = await a_sllm_openai(
        text="hello",
        model="gpt-4o",
        max_tokens=10,
    )
    assert result == "ok"
    assert test_completions.call_count == 2


class _NonRetryError(Exception):
    pass


completions_nonretry = _FakeChatCompletions(
    to_raise_first=1, exc_factory=lambda: _NonRetryError("boom")
)
client_nonretry = _FakeAsyncOpenAI(completions_nonretry)


@injected_pytest(
    design(
        openai_organization="test-org",
        logger=_TestLogger(),
        async_openai_client=client_nonretry,
        openai_model_table=None,
        openai_state={},
        test_completions=completions_nonretry,
    )
)
async def test_a_sllm_openai_does_not_retry_on_non_retryable(
    a_sllm_openai, test_completions, /
):
    with pytest.raises(_NonRetryError):
        await a_sllm_openai(
            text="hello",
            model="gpt-4o",
            max_tokens=10,
        )
    assert test_completions.call_count == 1
