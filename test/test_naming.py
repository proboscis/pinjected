from pinjected.di.partially_injected import PartiallyInjectedFunction


def test_naming_convention_for_injected_function():
    from pinjected import design, injected

    @injected
    def target_function(x, /, y, z):
        pass

    d = design(x=0)
    func = d.provide(target_function)
    assert isinstance(func, PartiallyInjectedFunction), (
        f"@injected function must return PartiallyInjectedFunction after resolution, got {type(func)}"
    )
