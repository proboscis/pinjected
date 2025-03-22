import asyncio
from io import BytesIO
from pathlib import Path

import pydub
from beartype import beartype
from injected_utils.injected_cache_utils import sqlite_cache, async_cached
from openai import AsyncOpenAI
from openai.types.audio import Transcription
from pinjected import *
from tqdm import tqdm


def convert_mp4_to_mp3(input_file: str, output_file: str = None) -> str:
    """
    Convert an MP4 file to MP3 format.

    Args:
    input_file (str): Path to the input MP4 file.
    output_file (str, optional): Path for the output MP3 file. If not provided,
                                 it will use the same name as the input file
                                 with an .mp3 extension.

    Returns:
    str: Path to the output MP3 file.

    Raises:
    FileNotFoundError: If the input file doesn't exist.
    RuntimeError: If there's an error during the conversion process.
    """
    import moviepy.editor as mp
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if output_file is None:
        output_file = input_path.with_suffix('.mp3')
    else:
        output_file = Path(output_file)

    try:
        # Try to load as video first
        try:
            clip = mp.VideoFileClip(str(input_path))
        except Exception as video_error:
            # If loading as video fails, try to load as audio
            try:
                clip = mp.AudioFileClip(str(input_path))
            except Exception as audio_error:
                raise RuntimeError(f"Failed to load file as video ({str(video_error)}) or audio ({str(audio_error)})")

        # Extract audio (or use the audio directly if it's an audio file)
        audio = clip.audio if hasattr(clip, 'audio') else clip

        # Write audio to file
        audio.write_audiofile(str(output_file))

        # Close the clips
        audio.close()
        if audio != clip:
            clip.close()

        return str(output_file)
    except Exception as e:
        raise RuntimeError(f"Error converting {input_file} to MP3: {str(e)}")


@injected
@beartype
async def a_transcribe_bytes(async_openai_client: AsyncOpenAI,logger, /, sound_bytes: BytesIO) -> str:
    response: Transcription = await async_openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=sound_bytes,
    )
    return response.text


@injected
async def a_transcribe_audio_segment(
        a_transcribe_bytes,
        a_split_segment_to_chunks,
        logger,
        /,
        segment: pydub.AudioSegment,
        bitrate="96k"
) -> str:
    transcription = ""
    bar = tqdm(desc="Transcribing chunks")
    i = 0
    from pinjected.compatibility.task_group import TaskGroup
    async def task(i, buffer):
        logger.info(f"Transcribing chunk of size {len(byte_segment.read()) / 1024 / 1024:.2f} MB")
        text = await a_transcribe_bytes(sound_bytes=buffer)
        logger.info(f"Transcribed chunk {i}: {text}")
        bar.update(1)
        return text

    async with TaskGroup() as tg:
        tasks = []
        async for byte_segment in a_split_segment_to_chunks(segment, bitrate=bitrate):
            tasks.append(tg.create_task(task(i, byte_segment)))
            i += 1
    for task in tasks:
        transcription += await task
    bar.close()
    return transcription


@injected
async def a_split_segment_to_chunks(
        logger, /,
        segment: pydub.AudioSegment,
        chunk_size_mb: float = 5,
        bitrate="96k",
):
    """
    recursively try to split the segment into chunks of size chunk_size_mb
    """
    from io import BytesIO
    def export(segment):
        out_bytes = BytesIO()
        out_bytes.name = "exported.mp3"
        segment.export(out_f=out_bytes, format="mp3", bitrate=bitrate)
        out_bytes.seek(0)
        size = len(out_bytes.read())
        out_bytes.seek(0)
        return out_bytes, size / 1024 / 1024

    async def impl(segment):
        assert isinstance(segment, pydub.AudioSegment)
        exported, size_mb = await asyncio.get_running_loop().run_in_executor(None,export,segment)
        if size_mb <= chunk_size_mb:
            sec = len(segment) / 1000
            logger.info(f"Exported chunk of size {size_mb:.2f} MB, duration {sec:.2f} sec")
            yield exported
        else:
            logger.info(f"Splitting chunk of size {size_mb:.2f} MB, duration {len(segment) / 1000:.2f} sec")
            half = len(segment) // 2
            async for item in impl(segment[:half]):
                yield item
            async for item in impl(segment[half:]):
                yield item

    async for item in impl(segment):
        yield item


# @async_cached(
#     cache=sqlite_cache(injected("cache_root_path") / "transcribe_mp3_file.sqlite"),
# )
@injected
async def a_transcribe_mp3_file(
        a_transcribe_audio_segment,
        /,
        file: Path,
        start_sec: float = None,
        end_sec: float = None) -> str:
    segment = await get_audio_segment(file)

    if start_sec is None:
        start_millis = 0
    else:
        start_millis = min(start_sec * 1000, len(segment) - 1)

    if end_sec is None:
        end_millis = len(segment) - 1
    else:
        end_millis = min(end_sec * 1000, len(segment) - 1)
    return await a_transcribe_audio_segment(segment[start_millis:end_millis])


async def get_audio_segment(file):
    file = Path(file)
    match file.suffix:
        case ".mp3":
            segment = pydub.AudioSegment.from_file(file, format="mp3")
        case ".mp4":
            mp3_file = file.with_suffix(".mp3")
            if not mp3_file.exists():
                convert_mp4_to_mp3(file, mp3_file)
            segment = pydub.AudioSegment.from_file(mp3_file, format="mp3")
        case ".wav":
            segment = pydub.AudioSegment.from_file(file, format="wav")
        case _:
            raise ValueError(f"Unsupported file type {file.suffix}")
    return segment


test_transcribe: IProxy = a_transcribe_mp3_file(Path("recording.mp3"))


@injected
async def __save_text(text: str, path: Path):
    path.write_text(text)


cmd_save_transcribe = __save_text(
    a_transcribe_mp3_file(injected("input_file")),
    injected("input_file").eval().map(Path).proxy.with_suffix(".txt")
)

__meta_design__ = instances(
)
