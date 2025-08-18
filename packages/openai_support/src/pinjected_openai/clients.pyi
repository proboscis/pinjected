from pinjected import IProxy
from openai import AsyncOpenAI

async_openai_client: IProxy[AsyncOpenAI]
openai_api_key: IProxy[str]
