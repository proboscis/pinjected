#!/usr/bin/env python3
"""Test script to check what fields are available in Google Gen AI response."""

import asyncio
from google import genai


async def test_response_fields():
    """Test to see what fields the Gen AI API returns."""
    # Initialize client
    client = genai.Client(vertexai=True, project="cyberagent-050", location="global")

    # Simple text generation to inspect response
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello, please say hi back",
    )

    print("Response object attributes:")
    print(dir(response))
    print("\nResponse object type:", type(response))

    # Check for usage metadata
    if hasattr(response, "usage_metadata"):
        print("\nUsage metadata found!")
        print(response.usage_metadata)

    if hasattr(response, "usage"):
        print("\nUsage found!")
        print(response.usage)

    if hasattr(response, "token_count"):
        print("\nToken count found!")
        print(response.token_count)

    # Check candidates
    if response.candidates:
        print("\nCandidate attributes:")
        print(dir(response.candidates[0]))

        candidate = response.candidates[0]
        if hasattr(candidate, "usage_metadata"):
            print("\nCandidate usage metadata:", candidate.usage_metadata)
        if hasattr(candidate, "token_count"):
            print("\nCandidate token count:", candidate.token_count)

    print("\nResponse text:", response.text if hasattr(response, "text") else "No text")

    # Try to access as dict
    try:
        print("\nResponse as dict:")
        import json

        # Try to serialize response
        if hasattr(response, "to_dict"):
            print(json.dumps(response.to_dict(), indent=2))
        elif hasattr(response, "__dict__"):
            print(response.__dict__)
    except Exception as e:
        print(f"Could not convert to dict: {e}")


if __name__ == "__main__":
    asyncio.run(test_response_fields())
