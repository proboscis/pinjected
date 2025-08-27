"""Test module for the warning when a PartiallyInjectedFunction is returned."""

import asyncio
from unittest.mock import AsyncMock, patch

from pinjected import design, injected
from pinjected.di.partially_injected import PartiallyInjectedFunction
from pinjected.run_helpers.run_injected import RunContext


def test_warning_for_partially_injected_function() -> None:
    """Test that a warning is issued when a PartiallyInjectedFunction is returned."""

    @injected
    def test_func(x, /, y) -> int:
        return x + y

    d = design(x=10)
    func = d.provide(test_func)

    assert isinstance(func, PartiallyInjectedFunction)

    with patch("pinjected.run_helpers.run_injected.logger.warning") as mock_warning:
        from pinjected.di.design_spec.protocols import DesignSpec
        from pinjected.helper_structure import MetaContext, SpecTrace
        from pinjected.module_inspector import ModuleVarSpec

        spec_trace = SpecTrace(trace=[], accumulated=DesignSpec.empty())
        context = RunContext(
            src_meta_context=MetaContext(
                trace=[], accumulated=design(), spec_trace=spec_trace, key_to_path={}
            ),
            design=d,
            meta_overrides=design(),
            var=test_func,
            src_var_spec=ModuleVarSpec(var=test_func, var_path="test_module.test_func"),
            provision_callback=None,
        )

        with patch("pinjected.run_helpers.run_injected.AsyncResolver") as mock_resolver:
            mock_instance = mock_resolver.return_value

            async_provide_mock = AsyncMock()
            async_provide_mock.return_value = func
            mock_instance.provide = async_provide_mock

            async_destruct_mock = AsyncMock()
            mock_instance.destruct = async_destruct_mock

            asyncio.run(context.a_provide(test_func))

            warning_found = False
            for call_args in mock_warning.call_args_list:
                warning_msg = call_args[0][0]
                if "PartiallyInjectedFunction" in warning_msg:
                    warning_found = True
                    assert "IProxy entrypoint" in warning_msg
                    assert "pinjected run" in warning_msg
                    break

            assert warning_found, (
                "Expected warning message about PartiallyInjectedFunction not found"
            )
