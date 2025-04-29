from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4

import cloudpickle

import wandb
from pinjected import *


@injected
async def cloudpickle_writer(data, path):
    path.write_bytes(cloudpickle.dumps(data))
    return path



@injected
async def cloudpickle_reader(path):
    return cloudpickle.loads(path.read_bytes())


Reader = Callable[[Path], Awaitable[object]]
Writer = Callable[[object, Path], Awaitable]


@injected
async def wandb_artifact(
        logger,
        wandb: wandb,
        __resolver__: AsyncResolver,
        cloudpickle_writer: Writer,
        cloudpickle_reader: Reader,
        /,
        tgt: Injected,
        identifier: str,
        type: str,
        writer: Writer | None = None,
        reader: Reader | None = None,
        description: str | None = None,
        metadata: dict | None = None
):
    entity, project, name = identifier.split("/")
    if metadata is None:
        metadata = dict()

    assert isinstance(tgt, (Injected, IProxy))
    api = wandb.Api()
    # Check if the artifact already exists
    if reader is None:
        reader = cloudpickle_reader
    if writer is None:
        writer = cloudpickle_writer
    assert callable(reader), f"reader is not callable: {reader}"
    assert callable(writer), f"writer is not callable: {writer}"
    try:
        artifact = api.artifact(f"{identifier}:latest")
        if artifact:
            # Artifact exists, download and return it
            logger.success(f"Artifact {identifier} found, downloading.")
            downloaded = artifact.download()
            logger.success(f"Artifact {identifier} downloaded.")

            return await reader(Path(downloaded) / "data")
    except wandb.errors.CommError:
        # Artifact doesn't exist, we'll create a new one
        logger.warning(f"Artifact {identifier} not found, creating a new one.")

    assert wandb.run.entity == entity, f"entity mismatch: {wandb.run.entity} != {entity}"
    assert wandb.run.project == project, f"project mismatch: {wandb.run.project} != {project}"

    art = wandb.Artifact(
        name=name,
        type=type,
        description=description,
        metadata=metadata
    )
    # else, log artifact
    data = await __resolver__[tgt]
    random_path = uuid4().hex[:8]
    write_dst = Path(wandb.run.path) / 'artifacts' / random_path / "data"
    write_dst.parent.mkdir(exist_ok=True, parents=True)
    await writer(data, write_dst)
    art.add_file(str(write_dst))
    wandb.log_artifact(art)
    logger.success(f"Artifact {identifier} logged.")
    # return the actual data
    return data
