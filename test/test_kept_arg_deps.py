from pinjected import injected, Injected, IProxy
from loguru import logger

webtoon_val = injected("webtoon_val")


@injected
async def a_run_conversation_with_monitoring(
    a,
    b,
    c,
    /,
    dataset: object,
    config: object,
    run_name: str,
    tags: list[str],
    test_mode: bool = False,
):
    pass


@injected
async def a_wandb_dataset_artifact(
    logger,
    a,
    b,
    /,
    tgt: Injected,
    identifier: str,
    artifact_type: str,
    tags: list[str],
    metadata: dict | None = None,
):
    pass


_webtoon_val_converted_internal: IProxy = Injected.procedure(
    # Log start
    _start := IProxy(
        lambda ds: logger.info(
            f"Starting full webtoon_val conversion ({len(ds)} samples)"
        )
    )(webtoon_val),
    # Run conversion with monitoring
    result := a_run_conversation_with_monitoring(
        dataset=webtoon_val,
        config="",
        run_name="",
        tags=["production", "webtoon", "lineart", "full_dataset"],
        test_mode=False,
    ),
    # Extract dataset and metrics
    converted_dataset := result[0],
    metrics := result[1],
    # Create wandb artifact
    artifact := a_wandb_dataset_artifact(
        tgt=converted_dataset,
        identifier="ailab-sge/sge-hub/webtoon_val_with_lineart",
        artifact_type="dataset",
        tags=["webtoon", "lineart", "SegSample", "converted", "production"],
        metadata={
            "source_dataset": "webtoon_val",
            "conversion_method": "sketch2line",
        },
    ),
)


def test_keep_arg_deps():
    tgt = converted_dataset
    func = a_wandb_dataset_artifact
    called = a_wandb_dataset_artifact(
        tgt=tgt,
        identifier="test_identifier",
        artifact_type="dataset",
        tags=["test", "artifact"],
        metadata={"key": "value"},
    )
    called_deps = Injected.ensure_injected(called).dependencies()
    tgt_deps = Injected.ensure_injected(tgt).dependencies()
    func_deps = Injected.ensure_injected(func).dependencies()
    assert called_deps == func_deps, (
        f"dependencies mismatch: {called_deps} != {func_deps} when combining {tgt_deps}"
    )
