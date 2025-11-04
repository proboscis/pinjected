# OpenRouter API Field Structure

This document tracks the availability of `providers` and `top_provider` fields across various models in the OpenRouter API.

## Structured Output Observations (November 2025)

Recent live tests against OpenRouter's `/chat/completions` endpoint with `response_format` enabled show the following behaviour:

- ✅ `openai/gpt-4o` and `openai/gpt-4o-mini` return valid JSON payloads (e.g. `{"answer":"Paris","confidence":0.99}`) that can be parsed directly.
- ✅ `google/gemini-2.0-flash-001` also returns well-formed JSON that satisfies our `SimpleResponse` schema.
- ⚠️ `openai/gpt-5`, `openai/gpt-5-nano`, and `openai/gpt-5-mini` respond with an **empty string** for `choices[0].message.content`, even though the models advertise `response_format`/`structured_outputs` support. Downstream parsing therefore fails with a validation error.
- ❌ `openai/gpt-4-turbo` currently rejects structured-output requests with `HTTP 400 Bad Request` when `response_format` is supplied.

Until OpenRouter/OpenAI fix the GPT-5 and GPT-4-turbo behaviour, our e2e tests intentionally fail when they encounter these empty-string / error responses.

## Field Availability by Model

| Model | has_providers | has_top_provider |
|-------|:------------:|:---------------:|
| `openai/gpt-4` | ❌ | ✅ |
| `openai/gpt-3.5-turbo` | ❌ | ✅ |
| `openai/gpt-4-0314` | ❌ | ✅ |
| `openai/gpt-4-32k` | ❌ | ✅ |
| `openai/gpt-4-32k-0314` | ❌ | ✅ |
| `openai/gpt-4-1106-preview` | ❌ | ✅ |
| `openai/gpt-3.5-turbo-16k` | ❌ | ✅ |
| `openai/gpt-3.5-turbo-instruct` | ❌ | ✅ |
| `openai/gpt-3.5-turbo-0613` | ❌ | ✅ |
| `openai/gpt-3.5-turbo-1106` | ❌ | ✅ |
| `meta-llama/llama-2-13b-chat` | ❌ | ✅ |
| `meta-llama/llama-2-70b-chat` | ❌ | ✅ |
| `anthropic/claude-2.0` | ❌ | ✅ |
| `anthropic/claude-2.0:beta` | ❌ | ✅ |
| `anthropic/claude-2.1` | ❌ | ✅ |
| `anthropic/claude-2.1:beta` | ❌ | ✅ |
| `anthropic/claude-2` | ❌ | ✅ |
| `anthropic/claude-2:beta` | ❌ | ✅ |
| `google/palm-2-chat-bison` | ❌ | ✅ |
| `google/palm-2-codechat-bison` | ❌ | ✅ |
| `google/palm-2-chat-bison-32k` | ❌ | ✅ |
| `google/palm-2-codechat-bison-32k` | ❌ | ✅ |
| `mistralai/mistral-7b-instruct-v0.1` | ❌ | ✅ |
| `mistralai/mistral-7b-instruct-v0.2` | ❌ | ✅ |
| `mistralai/mistral-tiny` | ❌ | ✅ |
| `mistralai/mistral-small` | ❌ | ✅ |
| `mistralai/mistral-medium` | ❌ | ✅ |
| `gryphe/mythomax-l2-13b` | ❌ | ✅ |
| `undi95/remm-slerp-l2-13b` | ❌ | ✅ |
| `undi95/toppy-m-7b` | ❌ | ✅ |
| `undi95/toppy-m-7b:free` | ❌ | ✅ |
| `jondurbin/airoboros-l2-70b` | ❌ | ✅ |
| `xwin-lm/xwin-lm-70b` | ❌ | ✅ |
| `alpindale/goliath-120b` | ❌ | ✅ |
| `huggingfaceh4/zephyr-7b-beta:free` | ❌ | ✅ |
| `huggingfaceh4/zephyr-7b-beta` | ❌ | ✅ |
| `mancer/weaver` | ❌ | ✅ |
| `nousresearch/nous-hermes-llama2-13b` | ❌ | ✅ |
| `nousresearch/nous-hermes-2-mixtral-8x7b-dpo` | ❌ | ✅ |
| `pygmalionai/mythalion-13b` | ❌ | ✅ |
| `neversleep/noromaid-20b` | ❌ | ✅ |
| `openchat/openchat-7b` | ❌ | ✅ |
| `openchat/openchat-7b:free` | ❌ | ✅ |
| `anthropic/claude-3-opus` | ✅ | ✅ |
| `anthropic/claude-3-opus:beta` | ✅ | ✅ |
| `anthropic/claude-3-sonnet` | ✅ | ✅ |
| `anthropic/claude-3-sonnet:beta` | ✅ | ✅ |
| `anthropic/claude-3-haiku` | ✅ | ✅ |
| `anthropic/claude-3-haiku:beta` | ✅ | ✅ |
| `anthropic/claude-3.5-sonnet` | ✅ | ❓ |
| `anthropic/claude-3.5-haiku` | ✅ | ❓ |
| `google/gemini-pro` | ✅ | ✅ |
| `google/gemini-pro-vision` | ✅ | ✅ |
| `google/gemini-pro-1.5` | ✅ | ✅ |
| `google/gemini-flash-1.5` | ✅ | ❓ |
| `meta-llama/llama-3-8b-instruct` | ✅ | ✅ |
| `meta-llama/llama-3-70b-instruct` | ✅ | ✅ |
| `meta-llama/llama-3.1-70b-instruct` | ✅ | ❓ |
| `meta-llama/llama-3.1-405b-instruct` | ✅ | ❓ |
| `mistralai/mistral-large` | ✅ | ✅ |
| `mistralai/mistral-large-2407` | ✅ | ❓ |
| `mistralai/mistral-nemo` | ✅ | ❓ |
| `mistralai/mixtral-8x7b` | ✅ | ✅ |
| `mistralai/mixtral-8x7b-instruct` | ✅ | ✅ |
| `mistralai/mixtral-8x22b-instruct` | ✅ | ✅ |
| `openai/gpt-4-turbo` | ✅ | ✅ |
| `openai/gpt-4-turbo-preview` | ✅ | ✅ |
| `openai/gpt-4o` | ✅ | ❓ |
| `openai/gpt-4o-mini` | ✅ | ❓ |
| `deepseek/deepseek-chat` | ✅ | ❓ |
| `deepseek/deepseek-r1` | ✅ | ❓ |
| `deepseek/deepseek-r1-distill-qwen-32b` | ✅ | ❓ |
| `cohere/command` | ✅ | ✅ |
| `cohere/command-r` | ✅ | ✅ |
| `cohere/command-r-03-2024` | ✅ | ✅ |
| `cohere/command-r-plus` | ✅ | ✅ |
| `cohere/command-r-plus-04-2024` | ✅ | ✅ |
| `microsoft/wizardlm-2-7b` | ✅ | ✅ |
| `microsoft/wizardlm-2-8x22b` | ✅ | ✅ |
| `openrouter/auto` | ✅ | ✅ |
| `cognitivecomputations/dolphin-mixtral-8x7b` | ✅ | ✅ |
| `sophosympatheia/midnight-rose-70b` | ✅ | ✅ |
| `neversleep/llama-3-lumimaid-8b` | ✅ | ✅ |
| `neversleep/llama-3-lumimaid-8b:extended` | ✅ | ✅ |
| `sao10k/fimbulvetr-11b-v2` | ✅ | ✅ |

**Legend**:  
✅ = Present  
❌ = Absent  
❓ = Uncertain (not enough data)

## Pattern Analysis

The API shows a clear transition pattern:

1. **Older Models (pre-2023/2024)**:
   - Typically only have `top_provider` field
   - Include older versions of established models

2. **Newer Models (2024+)**:
   - Have both `providers` array and `top_provider` field
   - Include recent model releases

3. **Latest Models**:
   - May eventually move to using only `providers` array 
   - Format still in transition

## Structure Details

### `top_provider` Structure
```json
"top_provider": {
    "context_length": 8192,
    "max_completion_tokens": 4096,
    "is_moderated": false
}
```

### `providers` Structure
```json
"providers": [
    {
        "id": "provider-id",
        "name": "Provider Name",
        "is_moderated": false,
        "context_length": 8192,
        "max_completion_tokens": 2048,
        "can_stream": true
    }
]
```
