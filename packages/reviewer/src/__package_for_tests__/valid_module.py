from pinjected.test import injected_pytest


@injected_pytest()
def test(some_configuration):
    # This, is a correct usage but detected as misuse.
    # aha, because @injected_pytest is not treated as injection point.
    print(some_configuration)


@injected_pytest()
def test_nested(some_configuration):
    def impl():
        # this gives a false positive.
        return some_configuration

    return impl()
