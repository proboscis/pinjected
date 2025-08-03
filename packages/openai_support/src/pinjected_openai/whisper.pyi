from typing import overload, Any
from pathlib import Path
from io import BytesIO
import pydub
from pinjected import IProxy

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
async def a_transcribe_bytes(sound_bytes: BytesIO) -> IProxy[str]: ...
@overload
async def a_transcribe_audio_segment(
    segment: pydub.AudioSegment, bitrate=...
) -> IProxy[str]: ...
@overload
async def a_split_segment_to_chunks(
    segment: pydub.AudioSegment, chunk_size_mb: float = ..., bitrate=...
): ...
@overload
async def a_transcribe_mp3_file(
    file: Path, start_sec: float | None = ..., end_sec: float | None = ...
) -> IProxy[str]: ...
@overload
async def a__save_text(text: str, path: Path): ...

# Additional symbols:
test_transcribe: IProxy[Any]
cmd_save_transcribe: IProxy[Any]

def convert_mp4_to_mp3(input_file: str, output_file: str | None = ...) -> str: ...
async def get_audio_segment(file) -> Any: ...
