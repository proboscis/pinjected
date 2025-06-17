import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import httpx
from pydantic import BaseModel, Field, HttpUrl
from pydub import AudioSegment
from pydub.playback import play
from tenacity import retry, stop_after_attempt, wait_exponential

from pinjected import *


class VoiceStyle(BaseModel):
    id: int
    style: str


class VoiceActor(BaseModel):
    age: int | None = None
    birthDay: int | None = Field(default=None, ge=1, le=31)
    birthMonth: int | None = Field(default=None, ge=1, le=12)
    gender: str
    id: UUID
    largeImageUrl: HttpUrl
    mediumImageUrl: HttpUrl
    smallImageUrl: HttpUrl
    name: str
    recommendedEmotionalLevel: float = Field(ge=0.0, le=1.0)
    recommendedSoundDuration: float = Field(ge=0.0)
    recommendedVoiceSpeed: float = Field(ge=0.0)
    sampleScript: str
    sampleVoiceUrl: HttpUrl
    voiceStyles: list[VoiceStyle]


class VoiceActorList(BaseModel):
    voiceActors: list[VoiceActor]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._name_to_actor = {actor.name: actor for actor in self.voiceActors}

    def actor_by_name(self, name: str) -> VoiceActor:
        return self._name_to_actor[name]


class GeneratedVoice(BaseModel):
    audioFileDownloadUrl: str
    audioFileUrl: str
    duration: int
    remainingCredits: int


class VoiceResponse(BaseModel):
    generatedVoice: GeneratedVoice


@dataclass
class NijiVoiceParam:
    actor_name: str
    script: str
    sound_duration: float | None = None
    emotion_level: float | None = None
    format = "mp3"
    speed = 1.0

    """
Body Params
script
string
required
音声を合成するテキスト。3,000文字まで一度に生成可能です。また、<sp 1.0>xxxのようにタグで囲むことで、タグ内のテキストのスピードを変更することができます。<wait 0.3>のようにタグを入れると、入力した秒数分だけ間を挿入することができます。

speed
string
required
読み上げのスピード (0.4 〜 3.0)

emotionalLevel
string
音声の感情的な変動を制御します。値が小さいほど滑らかに、大きいほど感情豊かになります。(0 〜 1.5) 未指定の場合は、指定したVoice Actorの感情レベルの推奨値が使用されます。

soundDuration
string
音素の発音の長さを制御します。値が小さいほど短く、大きいほど長くなります。(0 〜 1.7) 未指定の場合は、指定したVoice Actorの音素の発音の長さの推奨値が使用されます。

format
string
Defaults to mp3
音声の形式 (mp3 or wav). デフォルト: mp3

"""

    def to_payload(self):
        payload = {
            "script": self.script,
            "speed": str(self.speed),
            "format": self.format,
        }
        if self.emotion_level is not None:
            payload["emotionalLevel"] = str(self.emotion_level)
        if self.sound_duration is not None:
            payload["soundDuration"] = str(self.sound_duration)
        return payload

    def cache_key(self):
        src_key = json.dumps(self.to_payload())
        hash = hashlib.md5(src_key.encode()).hexdigest()
        return hash


@injected
async def a_niji_generate_voice_raw(
    a_niji_post,
    niji_voice_actor_list: VoiceActorList,
    /,
    param: NijiVoiceParam,
) -> VoiceResponse:
    actor_id = niji_voice_actor_list.actor_by_name(param.actor_name).id
    data = await a_niji_post(
        endpoint=f"voice-actors/{actor_id}/generate-voice", payload=param.to_payload()
    )
    return VoiceResponse.model_validate(data)


@injected
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
async def a_niji_post(
    logger,
    niji_voice_api_key: str,
    niji_voice_api_url: str,
    /,
    endpoint: str,
    payload: dict,
) -> dict:
    logger.info(f"POST {endpoint} {payload}")
    header = {
        "accept": "application/json",
        "x-api-key": niji_voice_api_key,
        "content-type": "application/json",
    }
    url = f"{niji_voice_api_url}/{endpoint}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=header)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"POST {url} failed: {e}")
        raise e


@instance
async def niji_voice_actor_list(niji_voice_api_key: str, niji_voice_api_url: str):
    headers = {"accept": "application/json", "x-api-key": niji_voice_api_key}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{niji_voice_api_url}/voice-actors", headers=headers
        )
        return VoiceActorList.model_validate(response.json())


async def a_download_data(url) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


@injected
async def a_niji_voice_download(
    a_niji_generate_voice_raw, /, param: NijiVoiceParam, dst: Path
):
    response = await a_niji_generate_voice_raw(param=param)
    bytes = await a_download_data(response.generatedVoice.audioFileUrl)
    dst.write_bytes(bytes)
    return dst


@instance
def niji_voice_api_url():
    return "https://api.nijivoice.com/api/platform/v1"


_test_niji_voice_actor_list: IProxy = niji_voice_actor_list

_test_param = NijiVoiceParam(actor_name="水戸 明日菜", script="ハローワールド")
_test_param2 = NijiVoiceParam(actor_name="漆夜 蓮", script="ハローワールド")

_test_generate_voice: IProxy = a_niji_generate_voice_raw(param=_test_param2)

_test_download_voice: IProxy = a_niji_voice_download(
    param=_test_param, dst=Path("test.mp3")
)


@injected
async def a_niji_voice_generate_cached(
    a_niji_voice_download, niji_voice_cache_dir: Path, /, param: NijiVoiceParam
):
    cache_key = param.cache_key()
    cache_path = (
        niji_voice_cache_dir
        / param.actor_name
        / f"{param.script[:30]}<{cache_key}>.mp3"
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return cache_path
    result = await a_niji_voice_download(param=param, dst=cache_path)
    return result


@injected
async def a_niji_voice_play(
    a_niji_voice_generate_cached,
    logger,
    /,
    param: NijiVoiceParam,
):
    file_path = await a_niji_voice_generate_cached(param=param)

    def play_task():
        logger.info(f"{param.actor_name}: {param.script}")
        seg = AudioSegment.from_file(file_path)
        play(seg)

    await asyncio.get_event_loop().run_in_executor(None, play_task)
    return file_path


@dataclass
class NijiVoice:
    audio: AudioSegment

    async def a_play(self):
        await asyncio.get_event_loop().run_in_executor(None, play, self.audio)


@injected
async def a_niji_voice(
    a_niji_voice_generate_cached, /, param: NijiVoiceParam
) -> NijiVoice:
    file_path = await a_niji_voice_generate_cached(param=param)
    loaded = await asyncio.get_event_loop().run_in_executor(
        None, AudioSegment.from_file, file_path
    )
    return NijiVoice(audio=loaded)


@instance
def niji_voice_cache_dir():
    return Path("~/.cache/niji_voice").expanduser()


_test_play_voice: IProxy = a_niji_voice_play(
    param=NijiVoiceParam(
        actor_name="小夜",
        script="完成しました。",
        # emotion_level=0,
    )
)


_test_play_voice2: IProxy = a_niji_voice_play(
    param=NijiVoiceParam(
        actor_name="小夜",
        script="うーん、、、失敗しました。",
        # emotion_level=0,
    )
)


__meta_design__ = design(overrides=design())
