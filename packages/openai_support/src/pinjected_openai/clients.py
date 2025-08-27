import os

from openai import AsyncOpenAI

from pinjected import instance


@instance
def async_openai_client(openai_api_key, openai_organization) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=openai_api_key, organization=openai_organization)


@instance
def openai_api_key() -> str:
    from loguru import logger

    logger.warning("using openai api key from environment variable")
    os.environ.get("OPENAI_API_KEY", None)
    # assert api_key is not None, "OPENAI_API_KEY environment variable must be set, or openai_api_key must be set via pinjected injection."
    return ""
