import asyncio
from dataclasses import dataclass
from typing import TypeVar, Callable, Optional

from returns.future import FutureResultE, future_safe, FutureResult
from returns.io import IOFailure, IOSuccess, IOResultE
from returns.maybe import Maybe, Nothing, Some
from returns.unsafe import unsafe_perform_io

from pinjected.di.design_spec.protocols import BindSpec, DesignSpec, ValidatorType, SpecDocProviderType
from pinjected.v2.keys import IBindKey, StrBindKey

T = TypeVar('T')


@dataclass(frozen=True)
class BindSpecImpl(BindSpec[T]):
    validator: Maybe[Callable[[IBindKey, T], FutureResultE[str]]] = Nothing
    spec_doc_provider: Maybe[Callable[[IBindKey], FutureResultE[str]]] = Nothing


@dataclass(frozen=True)
class MergedDesignSpec(DesignSpec):
    """
    A design spec created by merging multiple specs together.
    
    In the current implementation, when looking up a key, the specs are searched
    in the order they appear in the srcs list. The first spec that contains the key
    will be used. This means that the first spec in the list takes precedence.
    
    When using the + operator with DesignSpecImpl, the srcs list is created in the order
    [self, other], so the left-hand spec (self) takes precedence over the right-hand
    spec (other) for duplicate keys.
    """
    srcs: list[DesignSpec]

    def get_spec(self, key: IBindKey) -> Maybe[BindSpec]:
        """
        Search for a key in all source specs in order.
        Returns the first matching spec found from reverse order, or Nothing if no spec is found.
        
        This means that last specs in the srcs list take precedence over first ones.
        """
        for src in reversed(self.srcs):
            spec = src.get_spec(key)
            if spec is not Nothing:
                return spec
        return Nothing


@dataclass(frozen=True)
class DesignSpecImpl(DesignSpec):
    """
    Implementation of DesignSpec that stores bindings in a dictionary.
    
    When adding this spec to another spec with the + operator, the result is a MergedDesignSpec
    where this spec takes precedence over the other spec for duplicate keys.
    """
    specs: dict[IBindKey, BindSpec]

    def __add__(self, other: DesignSpec) -> DesignSpec:
        """
        Create a merged spec where this spec takes precedence over the other spec.
        
        The resulting MergedDesignSpec will check this spec first for each key,
        and only if the key is not found will it check the other spec.
        """
        return MergedDesignSpec(srcs=[self, other])

    def get_spec(self, key: IBindKey) -> Maybe[BindSpec]:
        """
        Look up a key in this spec's bindings.
        Returns Just(spec) if found, Nothing otherwise.
        """
        return Maybe.from_optional(self.specs.get(key))


class SimpleBindSpec(BindSpec[T]):
    def __init__(self,
                 validator: Optional[Callable[[T], str]] = None,
                 documentation: Optional[str] = None
                 ):
        self._validator = validator
        self._documentation = documentation

    @future_safe
    async def _validator_impl(self, key: IBindKey, item: T) -> str:
        error_msg = self._validator(item)
        if error_msg:
            raise ValueError(f"Validation failed for {key}: {error_msg}")
        return "success"

    @property
    def validator(self) -> Maybe[ValidatorType]:
        if self._validator is None:
            return Nothing
        return Some(self._validator)

    @future_safe
    async def _doc_impl(self, key: IBindKey) -> str:
        return self._documentation

    @property
    def spec_doc_provider(self) -> Maybe[SpecDocProviderType]:
        if self._documentation is None:
            return Nothing
        return Some(lambda key: FutureResult.from_value(self._documentation))


"""
Now, we need a way to accumulate specs from repo, so that RunContext can use it to provide better guidance.

"""

if __name__ == '__main__':
    from loguru import logger

    success = IOSuccess("success")
    failure = IOFailure(Exception())
    logger.info(success)  # IOSuccess(success)
    logger.info(failure)  # IOFailure(Exception())
    logger.info(success.value_or("hello"))  # IO(success)
    logger.info(failure.value_or("hello"))  # IO(hello)
    logger.info(unsafe_perform_io(success))  # Success(success)
    logger.info(unsafe_perform_io(failure))  # Failure(Exception())
    logger.info(unsafe_perform_io(success).unwrap())  # success
    logger.info(unsafe_perform_io(success.unwrap()))  # success


    # so, IOSuccess is a single monad rather than IO[Success[T]]
    # Ah, so we are to use @impure_safe for IOResult
    # @safe for Result
    # @future_safe for FutureResultE -> IOResultE
    @future_safe
    async def error_func():
        logger.warning(f"calling error func")
        raise Exception("error")


    fut_res: FutureResultE[str] = error_func()
    logger.info(fut_res)  # FutureResultE(Failure(Exception()))
    res: IOResultE[str] = asyncio.run(fut_res.awaitable())
    logger.info(res)  # => <IOResult: <Failure: error>>
    # wait, then..
    logger.info(unsafe_perform_io(res))  # => Failure(Exception('error'))


    # so, <IOResult: <Success: ...> is actually IOSuccess, while it looks like IO[Result[T]]
    # hmm, but we dont have value_or, for FutureResultE
    # what we have is lash
    @future_safe
    async def recover(fail):
        return "recovered"


    def recover2(fail):
        return FutureResult.from_value("recovered")


    logger.info(f"check recovering")
    recovered: FutureResultE = fut_res.lash(recover)
    recovered_2 = fut_res.lash(recover2)
    recovered_3 = fut_res.lash(lambda x: FutureResult.from_value("recovered"))
    logger.info(asyncio.run(fut_res.awaitable()))
    logger.info(asyncio.run(recovered.awaitable()))  # FutureResultE(Success(recovered))
    logger.info(asyncio.run(recovered_2.awaitable()))  # FutureResultE(Some(recovered))
    logger.info(asyncio.run(recovered_3.awaitable()))  # FutureResultE(Some(recovered))


    async def await_target(f: FutureResultE):
        return await f


    logger.info(asyncio.run(await_target(fut_res)))
    logger.info(asyncio.run(await_target(recovered)))  # FutureResultE(Success(recovered))
    logger.info(asyncio.run(await_target(recovered_2)))  # FutureResultE(Some(recovered))
    logger.info(asyncio.run(await_target(recovered_3)))  # FutureResultE(Some(recovered))

    # Checking Maybe Behavior
    some = Some("hello")
    none = Nothing
    logger.info(some)  # Some(hello)
    logger.info(none)  # Nothing
    logger.info(some.bind(lambda d: isinstance(d, str)))  # Some(True)
    logger.info(none.lash(lambda fail: "recovered"))  # Nothing
