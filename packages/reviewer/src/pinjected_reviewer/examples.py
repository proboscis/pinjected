from pinjected import *


# pinjected-reviewer: ignore
@instance
async def dummy_config():
    return dict()


@injected
async def a_misuse_of_injected():
    from pinjected_reviewer.pytest_reviewer.coding_rule_plugin_impl import (
        a_pytest_plugin_impl,
    )

    print(
        dummy_config
    )  # mistake, dummy_config is IProxy object so it should be requested (not detected)
    print(
        dummy_config()
    )  # mistake, dummy_config is IProxy object so it cannot be requested (now detected)
    print(a_pytest_plugin_impl)
    print(a_pytest_plugin_impl())


@instance
async def another_misuse():
    print(
        dummy_config
    )  # mistake, dummy_config is IProxy object so it should be requested (not detected)
    print(
        dummy_config()
    )  # mistake, dummy_config is IProxy object so it cannot be requested (now detected)


async def yet_another_misuse():
    print(
        dummy_config
    )  # mistake, dummy_config is IProxy object so it should be requested (not detected)
    print(
        dummy_config()
    )  # mistake, dummy_config is IProxy object so it cannot be requested (now detected)


def correct_use() -> IProxy:
    return dummy_config


@injected
async def false_positive_case(dummy_config, /, arg):
    # The dummy_config is correctly injected, this is not an IProxy anymore
    # but our detector still flags it as a misuse inside inner functions
    def inner():
        # this is not an IProxy object but rather the resolved value that was injected
        # in the outer function, so it shouldn't be detected as a misuse
        print(dummy_config)

    return inner()
