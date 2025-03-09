import asyncio
from pprint import pformat

from pinjected.exporter.llm_exporter import PinjectedCodeExporter
from pinjected import instances, providers, injected, Design, instance
from pinjected.run_helpers.run_injected import load_user_default_design
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.visualize_di import DIGraph


#
# def to_content(img: "Image"):
#     from pinjected.logging import logger
#     # convert Image into jpeg bytes
#     jpg_bytes = io.BytesIO()
#     img.convert('RGB').save(jpg_bytes, format='jpeg', quality=95)
#     b64_image = base64.b64encode(jpg_bytes.getvalue()).decode('utf-8')
#     mb_of_b64 = len(b64_image) / 1024 / 1024
#     logger.info(f"image size: {mb_of_b64:.2f} MB in base64.")
#     return {
#         "type": 'image_url',
#         "image_url": f"data:image/jpeg;base64,{b64_image}"
#     }
#
#
# @injected
# async def a_repeat_for_rate_limit(task):
#     from pinjected.logging import logger
#     while True:
#         try:
#             return await task()
#         except RateLimitError as e:
#             logger.error(f"rate limit error: {e}")
#             pat = "Please retry after (\d+) seconds."
#             match = re.search(pat, e.message)
#             if match:
#                 seconds = int(match.group(1))
#                 logger.info(f"sleeping for {seconds} seconds")
#                 await asyncio.sleep(seconds)
#             else:
#                 logger.warning(f"failed to parse rate limit error message: {e.message}")
#                 await asyncio.sleep(10)
#
#
# @injected
# async def a_llm__openai(
#         async_openai_client: AsyncOpenAI,
#         a_repeat_for_rate_limit,
#         /,
#         text: str,
#         images: list["Image"],
#         model_name
# ) -> str:
#     assert isinstance(async_openai_client, AsyncOpenAI)
#
#     for img in images:
#         assert isinstance(img, "Image"), f"image is not Image, but {type(img)}"
#
#     async def task():
#         chat_completion = await async_openai_client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": 'text',
#                             "text": text
#                         },
#                         *[to_content(img) for img in images]
#                     ]
#                 }
#             ],
#             # model="gpt-4-vision-preview",
#             model=model_name,
#             max_tokens=2048
#         )
#         return chat_completion
#
#     chat_completion = await a_repeat_for_rate_limit(task)
#     res = chat_completion.choices[0].message.content
#     assert isinstance(res, str)
#     return res
#
#
# @instance
# def async_openai_client(openai_api_key) -> AsyncOpenAI:
#     return AsyncOpenAI(
#         api_key=openai_api_key,
#     )
#
#
# # @instance
# # def openai_api_key() -> str:
# #     import os
# #     if (api_key := os.environ.get('OPENAI_API_KEY', None)) is None:
# #         api_key = Path(os.path.expanduser("~/.openai_api_key.txt")).read_text().strip()
# #     return api_key
# @injected
# async def a_llm__gpt35(a_llm__openai, /, text):
#     return await a_llm__openai(text=text, images=[], model_name="gpt-3.5-turbo")
#
#
# @injected
# async def a_llm__gpt4_turbo(a_llm__openai, /, text):
#     return await a_llm__openai(text=text, images=[], model_name="gpt-4-turbo-preview")


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




# print(f"__________________")
# print(asyncio.run(simplify_code('target',src)))
# print(inspect.getsource(Injected.__add__))
# %%
"""
PartialInjectedFunction() returns
src.proxy()
so, the mapping holds that info.
"""
