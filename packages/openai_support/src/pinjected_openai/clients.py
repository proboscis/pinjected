import os

from openai import AsyncOpenAI

from pinjected import instance


@instance
def async_openai_client(openai_api_key, openai_organization) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=openai_api_key, organization=openai_organization)


@instance
def openai_api_key() -> str:
    from loguru import logger

    logger.warning(f"using openai api key from environment variable")
    api_key = os.environ.get("OPENAI_API_KEY")
    assert api_key is not None, (
        "OPENAI_API_KEY environment variable must be set or openai_api_key must be injected."
    )
    return api_key


@instance
def openai_organization() -> str | None:
    """Retrieve the OpenAI organization identifier if present."""
    return os.environ.get("OPENAI_ORGANIZATION")
