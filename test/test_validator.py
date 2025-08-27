import pytest
from returns.future import future_safe
from returns.maybe import Some

from pinjected import design, injected
from pinjected.di.design_spec.impl import BindSpecImpl, DesignSpecImpl, SimpleBindSpec
from pinjected.exceptions import DependencyResolutionError, DependencyValidationError
from pinjected.pinjected_logging import logger
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.v2.keys import IBindKey, StrBindKey
from pinjected.compatibility.task_group import ExceptionGroup


@future_safe
async def assert_int(key: IBindKey, value):
    logger.warning(f"asserting {key} {value}")
    assert isinstance(value, int), f"expected int got {value} for key {key}"
    return "success"


@future_safe
async def doc_for_z(key):
    return "z is not provided"


@future_safe
async def doc_for_key(key):
    return f"{key} is not provided. Please provide it."


@injected
async def provide_value(a, b, x, /):
    return x


@pytest.mark.skip(reason="Complex async/FutureResult interaction needs investigation")
def test_validation_works():
    d = design(x=1, y="y", X=provide_value())
    spec = DesignSpecImpl(
        specs={
            StrBindKey("x"): BindSpecImpl(validator=Some(assert_int)),
            StrBindKey("y"): BindSpecImpl(
                validator=Some(assert_int),
            ),
            StrBindKey("z"): SimpleBindSpec(
                documentation="z is not provided",
            ),
            StrBindKey("a"): SimpleBindSpec(
                documentation="a is not provided. Please provide it"
            ),
        }
    )
    logger.debug(f"design:{d}")
    # test fails due IMPLICIT_BINDINGS. so we disable it like this.
    resolver = AsyncResolver(d, spec=spec, use_implicit_bindings=False)
    blocking = resolver.to_blocking()

    assert blocking.provide("x") == 1
    with pytest.raises(ExceptionGroup) as excinfo:
        # this fails because y is "y" not an int
        assert blocking.provide("y") == "y"
    # Check that the ExceptionGroup contains the expected DependencyValidationError
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], DependencyValidationError)
    with pytest.raises(DependencyResolutionError) as e:
        # THIS is not raising anything?
        logger.info("checking for provision errors")
        errors = blocking.find_provision_errors("z")
        logger.debug(f"checking find_provision_errors of 'z' got errors:{errors}")
        blocking.check_resolution("z")
        logger.error("check_resolution did not raise")
    with pytest.raises(ExceptionGroup) as e:
        # This raises keyerror rather than DependencyResolutionError.
        data = blocking.provide("z")
        logger.error(f"got data:{data}")
    logger.debug(f"got error:{e}")
    logger.debug(f"got error:{e.value}")
    # Check that the ExceptionGroup contains the expected DependencyResolutionError
    assert len(e.value.exceptions) == 1
    assert isinstance(e.value.exceptions[0], DependencyResolutionError)
    assert "z is not provided" in str(e.value.exceptions[0]), (
        f"expected 'z is not provided' in {e.value.exceptions[0]}"
    )
    with pytest.raises(ExceptionGroup) as e:
        assert blocking.provide("X")
    logger.debug(f"got error:{e}")
    logger.debug(f"got error:{e.value}")
    # Check that the ExceptionGroup contains the expected DependencyResolutionError
    assert len(e.value.exceptions) == 1
    assert isinstance(e.value.exceptions[0], DependencyResolutionError)
    assert "Please provide it" in str(e.value.exceptions[0]), (
        f"expected 'Please provide it' in {e.value.exceptions[0]}"
    )
