from dataclasses import dataclass
from typing import List, Optional, Protocol, overload, Dict

from google.genai.types import GenerateContentResponseUsageMetadata, MediaModality
from PIL import Image

from pinjected import IProxy

@dataclass
class GeneratedImage:
    image_data: bytes
    mime_type: str
    prompt_used: str

    def to_pil_image(self) -> Image.Image: ...
    def save(self, path: str) -> None: ...
    def to_base64(self) -> str: ...

@dataclass
class GenerationResult:
    text: Optional[str]
    image: GeneratedImage
    model_used: str

class AGenerateImageProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        model: str,
    ) -> GenerationResult: ...

class AEditImageProtocol(Protocol):
    async def __call__(
        self,
        input_images: List[Image.Image],
        prompt: str,
        model: str,
    ) -> GenerationResult: ...

class ADescribeImageProtocol(Protocol):
    async def __call__(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ) -> str: ...

# Gen AI SDK functions
a_generate_image__genai: AGenerateImageProtocol
a_edit_image__genai: AEditImageProtocol
a_describe_image__genai: ADescribeImageProtocol

@overload
async def a_generate_image__genai(
    prompt: str, model: str
) -> IProxy[GenerationResult]: ...
@overload
async def a_edit_image__genai(
    input_images: List[Image.Image], prompt: str, model: str
) -> IProxy[GenerationResult]: ...
@overload
async def a_describe_image__genai(
    image_path: str, prompt: Optional[str] = ..., model: str = ...
) -> IProxy[str]: ...

# Additional symbols:
def extract_token_counts_from_usage_metadata(usage_metadata) -> Dict[str, int]: ...

class ModalityTokenCount:
    modality: MediaModality
    token_count: int

class UsageMetadata:
    prompt_token_count: Optional[int]
    candidates_token_count: Optional[int]
    total_token_count: Optional[int]
    prompt_tokens_details: Optional[List[ModalityTokenCount]]
    candidates_tokens_details: Optional[List[ModalityTokenCount]]
    cached_content_token_count: Optional[int]
    def extract_modality_specific_tokens(self) -> Dict[str, int]: ...

# Additional symbols:
def extract_modality_specific_tokens(
    usage_metadata: GenerateContentResponseUsageMetadata,
) -> Dict[str, int]: ...
